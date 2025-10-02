# forensics/views.py
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import FileResponse, Http404,  HttpResponseBadRequest
from forensics.forms import ProjectForm, ApplicationForm, ProjectSelectForm
import mimetypes
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..',)))
from addresses import get_app_modules, set_current_project_desc, get_current_project_desc
import main
from util.image_utils import compare_projects_identities
from .logic import parse_sqlite, parse_pcap
import subprocess
import csv
import datetime
import pytz
import json
from django.utils.html import escape
import datetime, json
import re

imgs = ["jpg", "png","jpeg"]

def create_project(request):
    """Create a new project."""
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project_name = form.cleaned_data['name']
            desc = form.cleaned_data['description']
            set_current_project_desc(desc)

            # Ensure project directory exists
            project_path = os.path.join(settings.PROJECTS_DIR, project_name)
            os.makedirs(project_path, exist_ok=True)

            return redirect("http://127.0.0.1:8000/project/{aa}/add_application".format(aa=project_name), project_name=project_name)  # Redirect to project detail view
    else:
        form = ProjectForm()
    return render(request, 'create_project.html', {'form': form})
##############################################################################################################


PROJECT_ROOT_DIR = "projects"
def list_projects():
    """Return a list of project names (as folder names)."""
    try:
        projects = [
            name for name in os.listdir(PROJECT_ROOT_DIR)
            if os.path.isdir(os.path.join(PROJECT_ROOT_DIR, name))
        ]
        return [(name, name) for name in sorted(projects)]
    except Exception:
        return []

def select_project(request):
    """View for selecting a project to browse."""
    project_choices = list_projects()
    form = ProjectSelectForm(project_choices=project_choices)

    if request.method == 'POST':
        # Handle Browse Project form
        if 'project_name' in request.POST:
            form = ProjectSelectForm(request.POST, project_choices=project_choices)
            if form.is_valid():
                project_name = form.cleaned_data['project_name']
                return redirect(f"/project/{project_name}/browse")

        # Handle Compare Projects form
        elif 'compare_submit' in request.POST:
            project_name1 = request.POST.get('project1')
            project_name2 = request.POST.get('project2')
            type = request.POST.get('compare_type')
            print("1: ", project_name1, "  2: ", project_name2)
            if project_name1 and project_name2 and project_name1 != project_name2:
                return redirect(f"/compare/{project_name1}/{project_name2}/{type}")
            else:
                print("error two are same")

    return render(request, 'select_project.html', {
        'form': form,
        'project_choices': project_choices  # Not used directly in template but needed for form initialization
    })



##############################################################################################################

def project_detail(request, project_name):
    """Show details for a specific project."""
    project_data = evidence_database.get_project_data(project_name)
    return render(request, 'project_detail.html', {'project_name': project_name, 'project_desc': project_data})

##############################################################################################################3

def get_package_names():
    """Returns a list of installed package names from the connected device."""
    try:
        output = subprocess.check_output(
            ["adb", "shell", "pm", "list", "packages", "-3"], text=True
        )
        packages = [line.strip().split(":")[1] for line in output.strip().splitlines()]
        return [(pkg, pkg) for pkg in packages]  # Django expects (value, label)
    except subprocess.CalledProcessError:
        return []

def add_application(request, project_name):
    """Add an application to the project."""
    package_choices = get_package_names()

    if request.method == 'POST':
        form = ApplicationForm(request.POST, package_choices=package_choices)
        if form.is_valid():
            package_names = form.cleaned_data['package_names']
            is_rooted = form.cleaned_data['is_rooted']
            print(package_names)

            res = main.start_project(project_name, is_rooted, package_names)

            return redirect(f"http://127.0.0.1:8000/project/{project_name}/browse")
    else:
        form = ApplicationForm(package_choices=package_choices)

    return render(request, 'add_application.html', {
        'form': form,
        'project_name': project_name
    })

#########################################################################################################################################3

def timeline_view(request, project_name):
    """Display timeline of forensic events"""
    project_path = os.path.join(settings.PROJECTS_DIR, project_name)
    timeline_path = os.path.join(project_path, "processed_data", "timeline", "combined", "timeline.csv")
    
    if not os.path.exists(timeline_path):
        raise Http404("Timeline data not processed yet")

    timeline_data = []
    with open(timeline_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Convert timestamp to datetime object
            try:
                dt = datetime.datetime.fromtimestamp(float(row['timestamp']), tz=pytz.UTC)
            except (ValueError, TypeError):
                dt = None
                
            timeline_data.append({
                'timestamp': dt,
                'type': row['type'],
                'event': row['event'],
                'details': row['details'],
                'content': row.get('content', '')
            })

    # Sort by timestamp descending
    timeline_data.sort(key=lambda x: x['timestamp'] or datetime.min, reverse=True)

    return render(request, 'timeline.html', {
        'project_name': project_name,
        'timeline_data': timeline_data
    })




##############################################################################################################

def compare_view(request, project_name1, project_name2, type):
    print("Comparing:", project_name1, project_name2, type)
    project1_path = os.path.join(settings.PROJECTS_DIR, project_name1)
    project2_path = os.path.join(settings.PROJECTS_DIR, project_name2)
    p1_identity_path = os.path.join(project1_path, "processed_data", "faces", "identities")
    p2_identity_path = os.path.join(project2_path, "processed_data", "faces", "identities")

    if (type == "timeline"):
        timeline_data1 = read_timeline(project_name1)
        timeline_data2 = read_timeline(project_name2)
        return render(request, 'compare_timelines.html', {
            'project_name1': project_name1,
            'project_name2': project_name2,
            'timeline_data1': timeline_data1,
            'timeline_data2': timeline_data2
        })
    elif (type == "persons"):
        matched_identities = compare_projects_identities(p1_identity_path, p2_identity_path, thresh=0.5)

        matched_data = []
        for id1_path, id2_path in matched_identities:
            files1 = [os.path.join(id1_path, f) for f in os.listdir(id1_path) if f.lower().rsplit('.', 1)[-1] in imgs]
            first_file = files1[0]

            files2 = [os.path.join(id2_path, f) for f in os.listdir(id2_path) if f.lower().rsplit('.', 1)[-1] in imgs]
            second_file = files2[0]

            url1 = settings.MEDIA_URL + os.path.relpath(first_file, settings.MEDIA_ROOT)
            url2 = settings.MEDIA_URL + os.path.relpath(second_file, settings.MEDIA_ROOT)

            print("first: ", first_file, "second: ", second_file)
            id1_name = os.path.basename(id1_path)
            id2_name = os.path.basename(id2_path)


            matched_data.append({
                'id1_name': id1_name,
                'id2_name': id2_name,
                'id1_imgs_zipped': url1,
                'id2_imgs_zipped': url2,
            })

        return render(request, 'compare_persons.html', {
            'project_name1': project_name1,
            'project_name2': project_name2,
            'matched_data': matched_data,
        })
        
    else:
        raise Http404("Comparison type not supported")

def read_timeline(project_name):
    """Helper to read timeline data for a project."""
    project_path = os.path.join(settings.PROJECTS_DIR, project_name)
    timeline_path = os.path.join(project_path, "processed_data", "timeline", "combined", "timeline.csv")
    if not os.path.exists(timeline_path):
        return []
    timeline_data = []
    with open(timeline_path, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                dt = datetime.datetime.fromtimestamp(float(row['timestamp']), tz=pytz.UTC)
            except (ValueError, TypeError):
                dt = None
            timeline_data.append({
                'timestamp': dt,
                'type': row['type'],
                'event': row['event'],
                'details': row['details'],
                'content': row.get('content', '')
            })
    # Sort by timestamp descending
    timeline_data.sort(key=lambda x: x['timestamp'] or datetime.datetime.min, reverse=True)
    return timeline_data


#############################################################################################################################################

def modules_view(request, project_name):
    list = get_app_modules()
    print(type(list), list, project_name) 
    return render(request, 'modules.html', {
        'project_name': project_name,
        'modules': list
    })

#############################################################################################################################################
# please add your view method here to implement
def telegram_view(request, project_name):
    """
    Shows message dialogues grouped into Private / Group / Channel tabs.
    Reads processed timeline CSV with extra fields for media/location.
    """
    timeline_path = os.path.join(
        settings.PROJECTS_DIR,
        project_name,
        "processed_data",
        "apps",
        "org.telegram.messenger",
        "timeline.csv"
    )
    timeline_path2 = os.path.join(
        settings.PROJECTS_DIR,
        project_name,
        "processed_data",
        "apps",
        "org.telegram.messenger.web",
        "timeline.csv"
    )
    if not os.path.exists(timeline_path):
        if not os.path.exists(timeline_path2):
            raise Http404("Timeline data not processed yet")
        else:
            timeline_path = timeline_path2

    messages = []
    with open(timeline_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Normalize timestamp (as before)
            ts_unix = None
            try:
                if row.get('timestamp_unix'):
                    ts_unix = int(float(row['timestamp_unix']))
                elif row.get('timestamp'):
                    dt = datetime.datetime.fromisoformat(row['timestamp'])
                    ts_unix = int(dt.replace(tzinfo=datetime.timezone.utc).timestamp())
            except Exception:
                ts_unix = None

            sender = row.get('sender') or ''
            chat_name = row.get('chat_name') or ''
            # Clean up names (e.g. remove extra junk, split on semicolon)
            if ';' in chat_name:
                chat_name = chat_name.split(';')[0]
            chat_name = re.sub(r'[^A-Za-z0-9\u0600-\u06FF\s]', '', chat_name).strip()
            sender = re.sub(r'[^A-Za-z0-9\u0600-\u06FF@.\s]', '', sender).strip()

            # Combine message or location
            message_text = row.get('message') or ''
            lat = row.get('latitude') or None
            lon = row.get('longitude') or None

            # If latitude/longitude present, override message_text for display
            if lat and lon:
                # Format as "Location: lat, lon"
                message_text = f"Location: {lat}, {lon}"

            messages.append({
                'mid': row.get('mid'),
                'timestamp_unix': ts_unix,
                'timestamp': row.get('timestamp') or '',
                'sender': sender,
                'chat_id': row.get('chat_id') or '',
                'chat_name': chat_name or 'Unknown',
                'chat_type': (row.get('chat_type') or 'private').lower(),
                'message': message_text or ''
            })

    # (Grouping and sorting logic as before)
    dialogues = {}
    for m in messages:
        ctype = (m.get('chat_type') or 'private').lower()
        cid = str(m.get('chat_id') or 'unknown')
        dialogues.setdefault(ctype, {})
        if cid not in dialogues[ctype]:
            dialogues[ctype][cid] = {
                'chat_id': cid,
                'chat_name': m.get('chat_name') or cid,
                'messages': []
            }
        dialogues[ctype][cid]['messages'].append(m)
    # Sort each dialogue's messages by timestamp
    for ctype, chats in dialogues.items():
        for cid, info in chats.items():
            info['messages'].sort(key=lambda x: x['timestamp_unix'] or 0)
    dialogues_json = {ctype: list(chats.values()) for ctype, chats in dialogues.items()}

    context = {
        'project_name': project_name,
        'dialogues_json': json.dumps(dialogues_json, ensure_ascii=False)
    }
    return render(request, 'telegram.html', context)

#############################################################################################################################################
#############################################################################################################################################

def safe_join(base, *paths):
    # Prevent directory traversal
    final_path = os.path.normpath(os.path.join(base, *paths))
    if not final_path.startswith(base):
        raise ValueError("Attempted Directory Traversal")
    return final_path

def get_breadcrumbs(subpath):
    """Returns a list of (name, subpath) for breadcrumbs."""
    crumbs = []
    if subpath:
        parts = subpath.split('/')
        for i in range(len(parts)):
            crumbs.append((parts[i], '/'.join(parts[:i+1])))
    return crumbs

def browse_project(request, project_name, subpath=""):
    desc = get_current_project_desc()
    base_path = os.path.join('projects', project_name)
    try:
        full_path = safe_join(base_path, subpath)
    except ValueError:
        raise Http404("Invalid path")

    if not os.path.exists(full_path):
        raise Http404("Path not found")

    if os.path.isfile(full_path):
        return handle_file(request, project_name, subpath, full_path)

    # Directory view
    items = []
    for item in sorted(os.listdir(full_path)):
        item_path = os.path.join(full_path, item)
        rel_url = os.path.join(subpath, item) if subpath else item
        is_image = item.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp'))
        is_text = item.lower().endswith(('.txt', '.log', '.csv', '.xml'))
        is_pcap = item.lower().endswith('.pcap')
        is_db = item.lower().endswith('.db')
        preview = None
        items.append({
            "name": item,
            "is_dir": os.path.isdir(item_path),
            "is_image": is_image,
            "is_text": is_text,
            "is_pcap": is_pcap,
            "is_db": is_db,
            "url": rel_url,
            "preview": preview,
            "file_url": get_file_url(project_name, rel_url) if is_image else "",
        })

    breadcrumbs = get_breadcrumbs(subpath)
    context = {
        "project": project_name,
        "path": subpath.split('/') if subpath else [],
        "breadcrumbs": breadcrumbs,
        "items": items,
        "desc": desc,
    }
    return render(request, "browse.html", context)

def handle_file(request, project, subpath, full_path):
    filename = os.path.basename(full_path)
    parent_subpath = os.path.dirname(subpath)
    if filename.lower().endswith(('.txt', '.log', '.csv', '.xml')):
        try:
            with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(20480)
        except Exception:
            content = "[Unable to read text file]"
        return render(request, "text.html", {
            "project": project,
            "subpath": subpath,
            "parent_subpath": parent_subpath,
            "filename": filename,
            "content": content,
        })
    elif filename.lower().endswith('.pcap'):
        # For PCAP, just show the "open in Wireshark" UI
        return render(request, "pcap.html", {
            "project": project,
            "subpath": subpath,
            "parent_subpath": parent_subpath,
            "filename": filename,
            "full_path": full_path,
        })
    elif filename.lower().endswith('.db'):
        # For DB: parse using helper, show tables/columns/rows
        tables = parse_sqlite(full_path)
        return render(request, "db.html", {
            "project": project,
            "subpath": subpath,
            "parent_subpath": parent_subpath,
            "filename": filename,
            "tables": tables,
        })
    elif filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
        # Serve image file directly
        content_type = mimetypes.guess_type(full_path)[0] or 'application/octet-stream'
        return FileResponse(open(full_path, 'rb'), content_type=content_type)
    else:
        # Other file: offer as download
        return FileResponse(open(full_path, 'rb'), as_attachment=True, filename=filename)

def get_file_url(project, rel_url):
    """Constructs the media file URL for image previews (must be served via MEDIA_URL)."""
    return settings.MEDIA_URL + f"{project}/{rel_url}"