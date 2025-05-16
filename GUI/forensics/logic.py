import sqlite3
import pyshark
from django.core.files.storage import FileSystemStorage


def parse_sqlite(db_path):
    """Extract SQLite database structure and content"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    tables = []
    # Fetch all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    for (table_name,) in cursor.fetchall():
        # Get column definitions
        cursor.execute(f"PRAGMA table_info('{table_name}')")
        columns = [col[1] for col in cursor.fetchall()]
        # Fetch up to 50 rows of data
        cursor.execute(f"SELECT * FROM '{table_name}' LIMIT 50")
        rows = cursor.fetchall()
        tables.append({
            'name': table_name,
            'columns': columns,
            'rows': rows
        })
    conn.close()
    return tables


def parse_pcap(pcap_path):
    """Parse PCAP files using PyShark"""
    cap = pyshark.FileCapture(pcap_path)
    packets = []
    for packet in cap:
        # Safely extract IP fields if present
        src = packet.ip.src if hasattr(packet, 'ip') else ''
        dst = packet.ip.dst if hasattr(packet, 'ip') else ''
        packets.append({
            'timestamp': packet.sniff_time,
            'protocol': packet.highest_layer,
            'source': src,
            'destination': dst,
            'length': int(packet.length)
        })
        if len(packets) >= 1000:  # Limit for performance
            break
    cap.close()
    return packets
