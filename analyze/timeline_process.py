import os
import sqlite3
from datetime import datetime
import pytz
from PIL import Image
from scapy.all import rdpcap
import csv

def process_timeline(project_path):
    base_path = os.path.join(project_path, "processed_data", "timeline")
    os.makedirs(base_path, exist_ok=True)
    
    # Process different data sources
    contacts_timeline = process_contacts(os.path.join(project_path, "extract", "other", "important_databases", "contacts2.db"))
    calendar_timeline = process_calendar(os.path.join(project_path, "extract", "other", "important_databases", "calendar.db"))
    sms_timeline = process_sms(os.path.join(project_path, "extract", "other", "important_databases", "mmssms.db"))
    calllog_timeline = process_calllogs(os.path.join(project_path, "extract", "other", "important_databases", "calllog.db"))
    media_timeline = process_media(os.path.join(project_path, "extract", "media", "sdcard"))
    apps_timeline = process_apps(os.path.join(project_path, "processed_data", "apps"))
    
    # Combine all timelines
    combined = contacts_timeline + calllog_timeline + media_timeline  + calendar_timeline + sms_timeline + apps_timeline
    combined.sort(key=lambda x: x["timestamp"])
    
    # Save individual timelines
    save_timeline(contacts_timeline, os.path.join(base_path, "contacts"))
    save_timeline(calendar_timeline, os.path.join(base_path, "calendar"))
    save_timeline(calllog_timeline, os.path.join(base_path, "calllogs"))
    save_timeline(sms_timeline, os.path.join(base_path, "sms"))
    save_timeline(media_timeline, os.path.join(base_path, "media"))
    save_timeline(apps_timeline, os.path.join(base_path, "apps"))
    save_timeline(combined, os.path.join(base_path, "combined"))

def save_timeline(timeline, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "timeline.csv")
    
    with open(csv_path, "w") as f:
        f.write("timestamp,type,event,details\n")
        for event in timeline:
            f.write(f"{event['timestamp']},{event['type']},{event['event']},\"{event['details']}\"\n")


def process_calendar(db_path):
    timeline = []
    if not os.path.exists(db_path):
        print(f"Calendar DB not found at {db_path}")
        return timeline
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = """
SELECT 
    e._id AS event_id,
    c.calendar_displayName AS calendar_name,
    e.title,
    e.description,
    e.eventLocation,
    datetime(e.dtstart / 1000, 'unixepoch', 'localtime') AS start_time,
    datetime(e.dtend / 1000, 'unixepoch', 'localtime') AS end_time
FROM Events AS e
JOIN Calendars AS c ON e.calendar_id = c._id
ORDER BY e.dtstart DESC;
        """
        cursor.execute(query)
        for row in cursor.fetchall():
            event_id, calendar_name, title, description, location, start_time_str, end_time_str = row
            
            try:
                start_ts = datetime.strptime(start_time_str, '%Y-%m-%d %H:%M:%S').timestamp()
            except Exception:
                start_ts = None

            details = f"Calendar: {calendar_name}, Title: {title or 'N/A'}, Description: {description or 'N/A'}, Location: {location or 'N/A'}"

            timeline.append({
                "timestamp": start_ts,
                "type": "calendar",
                "event": "Calendar event",
                "details": details
            })

        conn.close()
    except Exception as e:
        print(f"Error processing calendar events: {e}")
    return timeline


def process_contacts(db_path):
    timeline = []
    if not os.path.exists(db_path):
        print(f"Contacts DB not found at {db_path}")
        return timeline
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        query = """
SELECT
  c._id AS contact_id,
  dn.data1 AS display_name,
  datetime(c.contact_last_updated_timestamp/1000, 'unixepoch', 'localtime') AS last_updated
FROM contacts AS c
JOIN raw_contacts AS rc
  ON rc.contact_id = c._id
JOIN data AS dn
  ON dn.raw_contact_id = rc._id
 AND dn.mimetype_id = (
       SELECT _id FROM mimetypes WHERE mimetype = 'vnd.android.cursor.item/name'
     )
GROUP BY c._id
ORDER BY c.contact_last_updated_timestamp DESC;
        """
        cursor.execute(query)
        for row in cursor.fetchall():
            contact_id, name, last_updated_str = row
            # Parse datetime string to timestamp
            try:
                last_updated_dt = datetime.strptime(last_updated_str, '%Y-%m-%d %H:%M:%S')
                last_updated_ts = last_updated_dt.timestamp()
            except Exception:
                last_updated_ts = None

            timeline.append({
                "timestamp": last_updated_ts,
                "type": "contact",
                "event": "Contact updated",
                "details": f"ID: {contact_id}, Name: {name}"
            })
        conn.close()
    except Exception as e:
        print(f"Error processing contacts: {e}")
    return timeline

def process_calllogs(db_path):
    timeline = []
    if not os.path.exists(db_path):
        print(f"Calllog DB not found at {db_path}")
        return timeline
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        query = """
        SELECT
          _id,
          number,
          CASE type
            WHEN 1 THEN 'INCOMING'
            WHEN 2 THEN 'OUTGOING'
            WHEN 3 THEN 'MISSED'
            ELSE 'OTHER'
          END AS call_type,
          duration,
          datetime(date/1000,'unixepoch','localtime') AS call_time
        FROM calls
        ORDER BY date DESC;
        """
        cursor.execute(query)
        for row in cursor.fetchall():
            call_id, number, call_type, duration, call_time_str = row
            try:
                call_time_dt = datetime.strptime(call_time_str, '%Y-%m-%d %H:%M:%S')
                call_time_ts = call_time_dt.timestamp()
            except Exception:
                call_time_ts = None

            timeline.append({
                "timestamp": call_time_ts,
                "type": "call",
                "event": f"{call_type} call",
                "details": f"Number: {number}, Duration: {duration} sec"
            })
        conn.close()
    except Exception as e:
        print(f"Error processing call logs: {e}")
    return timeline

def process_media(media_path):
    timeline = []
    for root, _, files in os.walk(media_path):
        for file in files:
            file_path = os.path.join(root, file)
            
            # Get file system timestamps
            fs_times = {
                "created": os.path.getctime(file_path),
                "modified": os.path.getmtime(file_path)
            }
            
            # Get EXIF data for images
            exif_time = None
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                try:
                    with Image.open(file_path) as img:
                        exif = img.getexif()
                        if 36867 in exif:  # DateTimeOriginal
                            exif_time = datetime.strptime(exif[36867], '%Y:%m:%d %H:%M:%S').timestamp()
                except Exception as e:
                    pass
                
            timeline.append({
                "timestamp": exif_time or fs_times["modified"],
                "type": "media",
                "event": "File created",
                "details": f"Path: {os.path.relpath(file_path, media_path)}",
                "source": "EXIF" if exif_time else "Filesystem"
            })
    
    return timeline


def process_sms(db_path):
    timeline = []
    if not os.path.exists(db_path):
        print(f"SMS DB not found at {db_path}")
        return timeline
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        query = """
SELECT
    _id,
    address,
    date,
    date_sent,
    body,
    type
FROM sms
ORDER BY date DESC;
        """
        cursor.execute(query)
        for row in cursor.fetchall():
            msg_id, address, date_ms, date_sent_ms, body, msg_type = row

            # Convert timestamps
            try:
                date_str = datetime.fromtimestamp(date_ms / 1000).strftime('%Y-%m-%d %H:%M:%S')
                timestamp = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S').timestamp()
            except:
                timestamp = None

            try:
                sent_str = datetime.fromtimestamp(date_sent_ms / 1000).strftime('%Y-%m-%d %H:%M:%S') if date_sent_ms else None
            except:
                sent_str = None

            if msg_type == 1:
                direction = "Received"
                contact = f"Sender: {address}"
                extra_info = f", Sent Time: {sent_str}" if sent_str else ""
            elif msg_type == 2:
                direction = "Sent"
                contact = f"Receiver: {address}"
                extra_info = ""
            else:
                direction = f"Type {msg_type}"
                contact = f"Address: {address}"
                extra_info = ""

            details = f"{direction} SMS | {contact}, Body: {body or '[empty]'}{extra_info}"

            timeline.append({
                "timestamp": timestamp,
                "type": "sms",
                "event": direction,
                "details": details
            })

        conn.close()
    except Exception as e:
        print(f"Error processing SMS messages: {e}")
    return timeline

##############################################

def process_apps(project_path):
    """
    Scan processed_data/apps/<app_dir> for CSV files, read rows and produce timeline events.
    - type => 'applications'
    - event => '<parent-directory-name>-event'
    - details => include filename, relative path, and key=value pairs from the row (excluding timestamp)
    """
    timeline = []

    # Walk only one level deep: each app directory directly under apps_root
    for app_dir in sorted(os.listdir(project_path)):
        app_dir_full = os.path.join(project_path, app_dir)
        if not os.path.isdir(app_dir_full):
            continue

        # find CSV files inside this app_dir (non-recursive)
        for fname in sorted(os.listdir(app_dir_full)):
            if not fname.lower().endswith(".csv"):
                continue
            file_path = os.path.join(app_dir_full, fname)
            rel_path = os.path.relpath(file_path, project_path)
            parent_name = os.path.basename(app_dir_full) or app_dir  # directory name
            event_name = f"{parent_name}-event"

            try:
                with open(file_path, newline='', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        ts = ""
                        details = ""
                        print("parent name", parent_name)
                        if (parent_name == "org.telegram.messenger" or parent_name == "org.telegram.messenger.web"):
                            ts = row["timestamp_unix"]
                            print("ts:  " , ts)
                            if ts is not '':
                                ts = int(float(ts))
                            else:
                                ts = 0
                            message = row["message"]
                            if (message is None):
                                print("xxxxxxxxxx   m is none")
                            details = "dialogue: " + row["chat_name"] + " user: " + row["sender"] + " message: " + message
                            
                        
                        print("ts: ", ts, " event: ", event_name, " details: ", details)
                        timeline.append({
                            "timestamp": ts,
                            "type": "applications",
                            "event": event_name,
                            "details": details
                        })
            except Exception as e:
                # keep processing other files
                print(f"Error reading app CSV {file_path}: {e}")
                continue

    return timeline

