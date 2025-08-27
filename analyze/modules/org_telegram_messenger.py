import os
import re
import sqlite3
from datetime import datetime
import pandas as pd
import json

# -------------------------
# Helpers for blob parsing
# -------------------------
def _extract_utf8_candidates(blob):
    if not blob:
        return []
    try:
        text = blob.decode('utf-8', errors='ignore')
    except Exception:
        text = ''
    candidates = re.findall(r'[\w\u0600-\u06FF\-\@\./\:\+\,\'\"\(\)\?\!\s]{3,400}', text)
    out, seen = [], set()
    for c in candidates:
        s = c.strip()
        if len(s) >= 3 and s not in seen:
            seen.add(s)
            out.append(s)
    return out

def _guess_message_text_from_blob(blob):
    cands = _extract_utf8_candidates(blob)
    if not cands:
        return None
    cands_sorted = sorted(cands, key=len, reverse=True)
    for cand in cands_sorted:
        if 3 <= len(cand) <= 800:
            return cand
    return cands_sorted[0]

def _parse_user_data_blob(blob):
    """
    Improved: extract phone, IDs, usernames, invite links.
    """
    out = {'raw_text': None, 'phone': None, 'other_ids': [], 'username_or_link': None}
    if not blob:
        return out
    try:
        text = blob.decode('utf-8', errors='ignore')
    except Exception:
        text = ''
    out['raw_text'] = text

    # Extract Telegram links
    link_match = re.search(r'(https://t\.me/[^\s"\']+)', text)
    if link_match:
        out['username_or_link'] = link_match.group(1)

    # Extract username
    uname_match = re.search(r'"username"\s*:\s*"([^"]+)"', text)
    if uname_match:
        out['username_or_link'] = "https://t.me/" + uname_match.group(1)

    # Phones/IDs
    digits = re.findall(r'\+?\d{7,16}', text)
    phones, other_ids = [], []
    for d in digits:
        nd = d.lstrip('+')
        if 7 <= len(nd) <= 14:
            phones.append(nd)
        else:
            other_ids.append(nd)
    out['phone'] = phones[0] if phones else None
    out['other_ids'] = other_ids
    return out

# -------------------------
# Core maps
# -------------------------
def _build_user_map(conn):
    cur = conn.cursor()
    user_map = {}
    try:
        cur.execute("SELECT uid, name, data FROM users")
        for uid, name, data in cur.fetchall():
            parsed = _parse_user_data_blob(data)
            user_map[uid] = {
                'name': name,
                'raw_data': parsed['raw_text'],
                'phone_in_blob': parsed['phone'],
                'other_ids_in_blob': parsed['other_ids'],
                'username_or_link': parsed['username_or_link'],
            }
    except Exception:
        pass
    return user_map

def _build_chat_map(conn):
    cur = conn.cursor()
    chat_map = {}
    try:
        cur.execute("SELECT uid, name, data FROM chats")
        for uid, name, data in cur.fetchall():
            txt = ''
            if data:
                try:
                    txt = data.decode('utf-8', errors='ignore')
                except Exception:
                    txt = ''
            chat_map[uid] = {'name': name, 'raw_data': txt}
    except Exception:
        pass
    return chat_map

def _detect_chat_type(uid, chat_map):
    try:
        if uid is None:
            return 'unknown'
        iv = int(uid)
        if iv > 0:
            return 'private'
        cid = abs(iv)
        info = chat_map.get(cid)
        if info:
            raw = (info.get('raw_data') or '').lower()
            name = (info.get('name') or '')
            if 'channel' in raw or 'megagroup' in raw or 'supergroup' in raw:
                return 'channel'
            if 'کانال' in name:
                return 'channel'
            return 'group'
        return 'group' if iv < 0 else 'private'
    except Exception:
        return 'unknown'

# -------------------------
# Main
# -------------------------
def start(data_address, save_address):
    if os.path.isdir(data_address):
        possible = [
            os.path.join(data_address, "files", "cache4.db"),
            os.path.join(data_address, "cache4.db"),
            os.path.join(data_address, "db", "cache4.db"),
        ]
        db_path = next((p for p in possible if os.path.exists(p)), None)
    else:
        db_path = data_address if os.path.exists(data_address) else None

    if not db_path:
        raise FileNotFoundError(f"Database not found at {data_address}")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    user_map = _build_user_map(conn)
    chat_map = _build_chat_map(conn)

    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages_v2'")
    if not cur.fetchall():
        possible_msgs = [r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
        raise RuntimeError("messages_v2 table not found. Available: " + ", ".join(possible_msgs))

    cur.execute("SELECT mid, uid, date, out, data FROM messages_v2 ORDER BY date DESC")
    rows = cur.fetchall()

    records = []
    for mid, uid, date_int, out_flag, data_blob in rows:
        # skip empty/service blobs (bug #3 fix)
        message_text = _guess_message_text_from_blob(data_blob) if data_blob else None
        if not message_text or message_text.strip() == "":
            continue

        ts, ts_unix = None, None
        try:
            if date_int is not None:
                ts_unix = int(date_int)
                ts = datetime.fromtimestamp(ts_unix).strftime('%Y-%m-%d %H:%M:%S')
        except Exception:
            pass

        chat_id, chat_name = None, None
        if uid is not None:
            uval = int(uid)
            if uval > 0:
                chat_id = uval
                um = user_map.get(uval, {})
                chat_name = um.get('name') or str(uval)
            else:
                chat_id = -uval
                chat_name = chat_map.get(chat_id, {}).get('name', str(chat_id))

        chat_type = _detect_chat_type(uid, chat_map)

        sender, sender_phone, sender_other_id = None, None, None
        if out_flag is not None and int(out_flag) == 1:
            sender = 'me'
        else:
            if uid and int(uid) > 0:
                um = user_map.get(int(uid), {})
                sender = um.get('username_or_link') or um.get('name') or str(uid)
                sender_phone = um.get('phone_in_blob')
                sender_other_id = (um.get('other_ids_in_blob') or [None])[0]
            else:
                # group/channel: don’t guess names blindly → just mark as group_member
                sender = "group_member"

        peer_phone, peer_other_id = None, None
        if uid and int(uid) > 0:
            um = user_map.get(int(uid), {})
            peer_phone = um.get('phone_in_blob')
            peer_other_id = (um.get('other_ids_in_blob') or [None])[0]

        records.append({
            'mid': mid,
            'timestamp': ts,
            'timestamp_unix': ts_unix,
            'sender': sender,
            'sender_phone_in_blob': sender_phone,
            'sender_telegram_id_in_blob': sender_other_id,
            'chat_id': chat_id,
            'chat_name': chat_name,
            'chat_type': chat_type,
            'peer_phone_in_blob': peer_phone,
            'peer_telegram_id_in_blob': peer_other_id,
            'message': message_text
        })

    conn.close()

    os.makedirs(save_address, exist_ok=True)
    out_path = os.path.join(save_address, "timeline.csv")
    df = pd.DataFrame(records)
    df.to_csv(out_path, index=False)
    print(f"Saved {len(df)} messages to {out_path}")
    return df
