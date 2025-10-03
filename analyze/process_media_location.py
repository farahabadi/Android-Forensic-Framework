import os
import csv
import json
import re
import subprocess
import shutil
from pathlib import Path
from datetime import datetime, timezone

from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import exifread

# ---------- small helpers ----------
def _float_from_ratio(r):
    if hasattr(r, "num") and hasattr(r, "den"):
        return float(r.num) / float(r.den)
    if hasattr(r, "numerator") and hasattr(r, "denominator"):
        return float(r.numerator) / float(r.denominator)
    if isinstance(r, tuple) and len(r) == 2:
        return float(r[0]) / float(r[1])
    return float(r)

def _dms_to_decimal(dms):
    d = _float_from_ratio(dms[0])
    m = _float_from_ratio(dms[1])
    s = _float_from_ratio(dms[2])
    return d + (m / 60.0) + (s / 3600.0)

def parse_gps_from_pil_gpsinfo(gps_ifd):
    if not gps_ifd:
        return None, None
    gps = {}
    for key, val in gps_ifd.items():
        gps[GPSTAGS.get(key, key)] = val
    lat = gps.get('GPSLatitude')
    lat_ref = gps.get('GPSLatitudeRef')
    lon = gps.get('GPSLongitude')
    lon_ref = gps.get('GPSLongitudeRef')
    if lat and lat_ref and lon and lon_ref:
        try:
            dec_lat = _dms_to_decimal(lat)
            if str(lat_ref).upper() != 'N':
                dec_lat = -dec_lat
            dec_lon = _dms_to_decimal(lon)
            if str(lon_ref).upper() != 'E':
                dec_lon = -dec_lon
            return dec_lat, dec_lon
        except Exception:
            return None, None
    return None, None

def parse_gps_from_exifread_tags(tags):
    lat = tags.get('GPS GPSLatitude')
    lat_ref = tags.get('GPS GPSLatitudeRef')
    lon = tags.get('GPS GPSLongitude')
    lon_ref = tags.get('GPS GPSLongitudeRef')
    if lat and lat_ref and lon and lon_ref:
        try:
            def conv(coord):
                d = float(coord.values[0].num) / float(coord.values[0].den)
                m = float(coord.values[1].num) / float(coord.values[1].den)
                s = float(coord.values[2].num) / float(coord.values[2].den)
                return d + m / 60.0 + s / 3600.0
            latitude = conv(lat)
            if str(lat_ref.values[0]).upper() != 'N':
                latitude = -latitude
            longitude = conv(lon)
            if str(lon_ref.values[0]).upper() != 'E':
                longitude = -longitude
            return latitude, longitude
        except Exception:
            return None, None
    return None, None

def parse_iso6709(s):
    if not s:
        return None, None
    m = re.search(r'([+-]?\d+(?:\.\d+))\s*([+-]?\d+(?:\.\d+))', s)
    if m:
        try:
            return float(m.group(1)), float(m.group(2))
        except Exception:
            return None, None
    return None, None

def parse_datetime_to_unix(dt_str):
    if not dt_str:
        return None
    if isinstance(dt_str, bytes):
        try:
            dt_str = dt_str.decode('utf-8', errors='ignore')
        except Exception:
            dt_str = str(dt_str)
    s = str(dt_str).strip()
    try:
        if re.match(r'^\d{4}:\d{2}:\d{2}\s+\d{2}:\d{2}:\d{2}', s):
            dt = datetime.strptime(s.split('\0')[0], '%Y:%m:%d %H:%M:%S')
            return int(dt.replace(tzinfo=timezone.utc).timestamp())
    except Exception:
        pass
    try:
        if s.endswith('Z'):
            s2 = s[:-1] + '+00:00'
        else:
            s2 = s
        try:
            dt = datetime.fromisoformat(s2)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except Exception:
            pass
    except Exception:
        pass
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y:%m:%d %H:%M:%S'):
        try:
            dt = datetime.strptime(s.split('\0')[0], fmt)
            dt = dt.replace(tzinfo=timezone.utc)
            return int(dt.timestamp())
        except Exception:
            continue
    m = re.search(r'(\d{4})[:\-](\d{2})[:\-](\d{2}).*?(\d{2}):(\d{2}):(\d{2})', s)
    if m:
        try:
            dt = datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                          int(m.group(4)), int(m.group(5)), int(m.group(6)),
                          tzinfo=timezone.utc)
            return int(dt.timestamp())
        except Exception:
            pass
    return None

# ---------- image gps/time ----------
def get_image_gps_and_unix_time(image_path: Path):
    try:
        img = Image.open(image_path)
        exif = img.getexif()
        if exif:
            decoded = {}
            for tag_id, value in exif.items():
                decoded[TAGS.get(tag_id, tag_id)] = value
            gps_ifd = decoded.get('GPSInfo')
            lat, lon = parse_gps_from_pil_gpsinfo(gps_ifd)
            dt_raw = None
            for k in ('DateTimeOriginal', 'DateTime', 'DateTimeDigitized'):
                if k in decoded and decoded[k]:
                    dt_raw = decoded[k]
                    break
            unix_ts = parse_datetime_to_unix(dt_raw)
            if lat is not None and lon is not None:
                return lat, lon, unix_ts
    except Exception:
        pass

    try:
        with open(image_path, 'rb') as f:
            tags = exifread.process_file(f, details=False)
            lat, lon = parse_gps_from_exifread_tags(tags)
            dt_raw = None
            for k in ('EXIF DateTimeOriginal', 'Image DateTime', 'EXIF DateTimeDigitized'):
                if k in tags:
                    dt_raw = str(tags[k])
                    break
            unix_ts = parse_datetime_to_unix(dt_raw)
            if lat is not None and lon is not None:
                return lat, lon, unix_ts
    except Exception:
        pass

    return None, None, None

# ---------- ffprobe / exiftool helpers ----------
def _run_ffprobe(path: Path):
    if not shutil.which('ffprobe'):
        return None
    try:
        cmd = ['ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams', str(path)]
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return json.loads(out)
    except Exception:
        return None

def _try_exiftool(path: Path):
    if not shutil.which('exiftool'):
        return None
    try:
        out = subprocess.check_output(['exiftool', '-json', str(path)], stderr=subprocess.STDOUT)
        data = json.loads(out)
        if isinstance(data, list) and data:
            return data[0]
    except Exception:
        return None

def get_video_gps_and_unix_time(video_path: Path):
    ff = _run_ffprobe(video_path)
    if ff:
        fmt = ff.get('format', {})
        tags = fmt.get('tags', {}) or {}
        iso = tags.get('com.apple.quicktime.location.ISO6709') or tags.get('location') or tags.get('location-eng')
        latlon = None
        if iso:
            latlon = parse_iso6709(iso)
        if not latlon and isinstance(iso, str):
            mlat = re.search(r'lat(?:itude)?[:=]\s*([+-]?\d+(?:\.\d+))', iso, re.I)
            mlon = re.search(r'lon(?:gitude)?[:=]\s*([+-]?\d+(?:\.\d+))', iso, re.I)
            if mlat and mlon:
                try:
                    latlon = (float(mlat.group(1)), float(mlon.group(1)))
                except Exception:
                    latlon = None
        if not latlon:
            combined = ' '.join(str(v) for v in tags.values())
            latlon = parse_iso6709(combined)
        capture_raw = tags.get('creation_time') or tags.get('com.apple.quicktime.creationdate') or tags.get('creation_time')
        unix_ts = parse_datetime_to_unix(capture_raw)
        if latlon and latlon[0] is not None and latlon[1] is not None:
            return latlon[0], latlon[1], unix_ts

    et = _try_exiftool(video_path)
    if et:
        lat = et.get('GPSLatitude')
        lon = et.get('GPSLongitude')
        def parse_latlon_str(s):
            if s is None:
                return None
            m = re.search(r'([+-]?\d+(?:\.\d+)?)', str(s))
            if m:
                try:
                    return float(m.group(1))
                except Exception:
                    return None
            p = parse_iso6709(str(s))
            if p[0] is not None:
                return p[0]
            return None
        if lat and lon:
            latf = parse_latlon_str(lat)
            lonf = parse_latlon_str(lon)
            capture_raw = et.get('CreateDate') or et.get('TrackCreateDate') or et.get('MediaCreateDate') or et.get('ModifyDate')
            unix_ts = parse_datetime_to_unix(capture_raw)
            return latf, lonf, unix_ts
        composite = et.get('Composite:GPSPosition') or et.get('GPSPosition')
        if composite:
            m = re.search(r'([+-]?\d+(?:\.\d+)).*?([+-]?\d+(?:\.\d+))', str(composite))
            if m:
                try:
                    latf = float(m.group(1)); lonf = float(m.group(2))
                    capture_raw = et.get('CreateDate') or et.get('MediaCreateDate')
                    unix_ts = parse_datetime_to_unix(capture_raw)
                    return latf, lonf, unix_ts
                except Exception:
                    pass
    return None, None, None

def file_mtime_unix(path: Path):
    return int(path.stat().st_mtime)

# ---------- main: append to existing csv ----------
def append_locations_to_csv(img_dir, vid_dir, existing_csv_path):
    img_exts = {'.jpg', '.jpeg', '.png', '.tiff', '.heic', '.webp'}
    vid_exts = {'.mp4', '.mov', '.avi', '.mkv', '.3gp', '.mts', '.mpg', '.mpeg'}

    rows_to_append = []

    # images
    if os.path.isdir(img_dir):
        for file in Path(img_dir).iterdir():
            if file.is_file() and file.suffix.lower() in img_exts:
                lat, lon, unix_ts = get_image_gps_and_unix_time(file)
                if lat is not None and lon is not None:
                    if unix_ts is None:
                        unix_ts = file_mtime_unix(file)
                    details = f"{lat},{lon}"
                    rows_to_append.append({
                        'timestamp': int(unix_ts),
                        'type': 'Location',
                        'event': 'image_captured',
                        'details': details
                    })

    # videos
    if os.path.isdir(vid_dir):
        for file in Path(vid_dir).iterdir():
            if file.is_file() and file.suffix.lower() in vid_exts:
                lat, lon, unix_ts = get_video_gps_and_unix_time(file)
                if lat is not None and lon is not None:
                    if unix_ts is None:
                        unix_ts = file_mtime_unix(file)
                    details = f"{lat},{lon}"
                    rows_to_append.append({
                        'timestamp': int(unix_ts),
                        'type': 'Location',
                        'event': 'video_captured',
                        'details': details
                    })

    # ensure CSV exists & header present; append rows
    csv_path = Path(existing_csv_path)
    write_header = not csv_path.exists()
    with open(csv_path, 'a', newline='', encoding='utf-8') as f:
        fieldnames = ['timestamp', 'type', 'event', 'details']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        for r in rows_to_append:
            writer.writerow(r)

    return len(rows_to_append)

# ---------- usage ----------
if __name__ == '__main__':
    img_directory = '/path/to/images'     # <- change
    vid_directory = '/path/to/videos'     # <- change
    existing_csv = '/path/to/existing.csv'  # <- change (file that has timestamp,type,event,details)

    count = append_locations_to_csv(img_directory, vid_directory, existing_csv)
    print(f"Appended {count} rows to {existing_csv}")
