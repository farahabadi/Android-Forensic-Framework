import os
import re
import sqlite3
import json
import xml.etree.ElementTree as ET
import logging
from pathlib import Path

# Configure logging to capture output
logging.basicConfig(filename="sensitive_data_log.log", level=logging.INFO)

# Regular Expressions for sensitive data
patterns = {
    "password": r"(\b(?:password|pass|pwd|key)[\s=:]*[A-Za-z0-9@#$%^&*()_+=-]+)",
    "location": r"\b(lat|long|location|latitude|longitude)[\s=:]*[-+]?[0-9]*\.?[0-9]+\b",
    "health_data": r"(\b(?:health|medical)[\s=:]*[A-Za-z0-9]+)",
    "card_number": r"\b(?:\d{4}[-\s]??\d{4}[-\s]??\d{4}[-\s]??\d{4})\b",  # Simple example
    "urls": r"\b(?:http|https)://[^\s]+",
    "emails": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
    "credit_card": r"\b(?:\d{4}[-\s]??\d{4}[-\s]??\d{4}[-\s]??\d{4})\b",
    "pii": r"(\b(?:ssn|dob|phone|email|address)[\s=:]*[A-Za-z0-9\s,]+)"
}

def search_files(app_address):
    """
    Search and return relevant files within the app directory, 
    including SQL databases, shared preferences, and cache files.
    """
    relevant_files = []
    for root, dirs, files in os.walk(app_address):
        for file in files:
            if file.endswith('.db') or file.endswith('.xml') or file.endswith('.json'):
                relevant_files.append(os.path.join(root, file))
    return relevant_files

def search_sensitive_data(file_path, patterns):
    """
    Search for sensitive data (PII, passwords, location, health data, etc.) in a file using regex patterns.
    """
    found_data = {key: [] for key in patterns.keys()}
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
            
            for key, pattern in patterns.items():
                found_data[key] = re.findall(pattern, content)
    except Exception as e:
        logging.error(f"Error processing {file_path}: {e}")
    return found_data

def extract_from_sqlite(file_path):
    """
    Extract data from SQLite databases, looking for potentially sensitive tables or fields.
    """
    found_data = {}
    try:
        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT * FROM {table_name};")
            rows = cursor.fetchall()
            for row in rows:
                found_data[table_name] = row

        conn.close()
    except sqlite3.Error as e:
        logging.error(f"SQLite error in {file_path}: {e}")
    return found_data

def extract_from_preferences(file_path):
    """
    Extract data from shared preferences (usually stored as XML or JSON).
    """
    found_data = {}
    try:
        if file_path.endswith('.xml'):
            tree = ET.parse(file_path)
            root = tree.getroot()
            for elem in root.iter():
                found_data[elem.tag] = elem.text
        elif file_path.endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as file:
                data = json.load(file)
                found_data.update(data)
    except Exception as e:
        logging.error(f"Error reading preferences from {file_path}: {e}")
    return found_data

def extract_from_cache(file_path):
    """
    Extract data from cache files, typically binary or compressed formats.
    """
    found_data = {}
    try:
        with open(file_path, 'rb') as file:
            content = file.read()
            found_data['cache'] = content[:100]  # Read first 100 bytes as an example
    except Exception as e:
        logging.error(f"Error reading cache from {file_path}: {e}")
    return found_data

def log_results(found_data, file_path):
    """
    Log sensitive data findings to a file or report.
    """
    if any(found_data.values()):
        print(f"Found sensitive data in: {file_path}")
        with open("projects/new1/processed_data/apps/telegram/res.txt", 'w+') as of:
            for key, data in found_data.items():
                if data:
                    of.write("path: {path} key: {key} data: {data}\n".format(path=file_path, key=key, data=data))

def process_app_data(app_name, app_address):
    """
    Main method to process app data, search for sensitive information, and log results.
    """
    print("start process app data")
    print("app name : ", app_name, "app address: ", app_address)
    logging.info(f"Processing app data for: {app_name} at {app_address}")
    
    files = search_files(app_address)
    
    for file_path in files:
        print("file: ", file_path)
        logging.info(f"Processing file: {file_path}")
        
        # Search for sensitive data
        found_data = search_sensitive_data(file_path, patterns)
        print(found_data)
        
        # Log any found sensitive data
        log_results(found_data, file_path)
        
        # If the file is a SQLite database, extract further information
        if file_path.endswith('.db'):
            db_data = extract_from_sqlite(file_path)
            log_results(db_data, file_path)
        
        # If the file is a shared preference, extract data
        elif file_path.endswith('.xml') or file_path.endswith('.json'):
            pref_data = extract_from_preferences(file_path)
            log_results(pref_data, file_path)
        
        # Handle cache files
        elif file_path.endswith('.cache'):
            cache_data = extract_from_cache(file_path)
            log_results(cache_data, file_path)

def process_files(app_address, patterns):
    """
    Process all files within a directory to extract sensitive information.
    """
    relevant_files = search_files(app_address)
    
    for file_path in relevant_files:
        found_data = search_sensitive_data(file_path, patterns)
        if found_data:
            log_results(found_data, file_path)

def search_database_for_sensitive_info(db_file):
    """
    Special search to extract and log sensitive information from SQLite database files.
    """
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        for table in tables:
            table_name = table[0]
            cursor.execute(f"SELECT * FROM {table_name}")
            rows = cursor.fetchall()
            for row in rows:
                for col, value in enumerate(row):
                    for key, pattern in patterns.items():
                        if isinstance(value, str) and re.search(pattern, value):
                            logging.info(f"Sensitive data found in {db_file} -> {table_name} -> Column {col}: {value}")
        
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Database error {e} while searching {db_file}")

def analyze_log_data(log_file):
    """
    Analyze the log file for any patterns of concern that may have been detected during searches.
    """
    try:
        with open(log_file, 'r') as file:
            content = file.read()
            for key, pattern in patterns.items():
                matches = re.findall(pattern, content)
                if matches:
                    logging.info(f"Pattern {key} found in log data: {matches}")
    except Exception as e:
        logging.error(f"Error processing log data: {e}")


def analyze_shared_prefs(app_address):
    """
    Special method to analyze shared preferences files for potential sensitive information.
    """
    prefs_dir = os.path.join(app_address, "shared_prefs")
    
    if os.path.exists(prefs_dir):
        prefs_files = [os.path.join(prefs_dir, f) for f in os.listdir(prefs_dir) if f.endswith('.xml')]
        for file in prefs_files:
            pref_data = extract_from_preferences(file)
            if pref_data:
                log_results(pref_data, file)
