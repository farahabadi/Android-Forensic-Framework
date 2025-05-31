import os
import sqlite3
from datetime import datetime
import pytz
from PIL import Image
from scapy.all import rdpcap

def process_timeline(project_path):
    base_path = os.path.join(project_path, "processed_data", "timeline")
    os.makedirs(base_path, exist_ok=True)
    
    # Process different data sources
    contacts_timeline = process_contacts(os.path.join(project_path, "extract", "other", "important_databases", "contacts2.db"))
    calllog_timeline = process_calllogs(os.path.join(project_path, "extract", "other", "important_databases", "calllog.db"))
    media_timeline = process_media(os.path.join(project_path, "extract", "media", "sdcard"))
    network_timeline = process_network(os.path.join(project_path, "extract", "network", "net.pcap"))
    
    # Combine all timelines
    combined = contacts_timeline + calllog_timeline + media_timeline + network_timeline
    combined.sort(key=lambda x: x["timestamp"])
    
    # Save individual timelines
    save_timeline(contacts_timeline, os.path.join(base_path, "contacts"))
    save_timeline(calllog_timeline, os.path.join(base_path, "calllogs"))
    save_timeline(media_timeline, os.path.join(base_path, "media"))
    save_timeline(network_timeline, os.path.join(base_path, "network"))
    save_timeline(combined, os.path.join(base_path, "combined"))

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
                "timestamp": exif_time or fs_times["created"],
                "type": "media",
                "event": "File created",
                "details": f"Path: {os.path.relpath(file_path, media_path)}",
                "source": "EXIF" if exif_time else "Filesystem"
            })
    
    return timeline

def process_network(pcap_path):
    timeline = []
    try:
        packets = rdpcap(pcap_path)
        for pkt in packets:
            timestamp = pkt.time
            details = f"{pkt.summary()} | Protocol: {pkt.name}"
            timeline.append({
                "timestamp": timestamp,
                "type": "network",
                "event": "Network activity",
                "details": details
            })
    except Exception as e:
        print(f"Error processing network data: {e}")
    return timeline

def save_timeline(timeline, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    csv_path = os.path.join(output_dir, "timeline.csv")
    
    with open(csv_path, "w") as f:
        f.write("timestamp,type,event,details\n")
        for event in timeline:
            f.write(f"{event['timestamp']},{event['type']},{event['event']},\"{event['details']}\"\n")
