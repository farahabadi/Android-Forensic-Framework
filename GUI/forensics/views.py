# forensics/views.py
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import FileResponse, Http404,  HttpResponseBadRequest
from forensics.forms import ProjectForm, ApplicationForm, ProjectSelectForm
import mimetypes
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..',)))
import main
from .logic import parse_sqlite, parse_pcap
import subprocess

def create_project(request):
    """Create a new project."""
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project_name = form.cleaned_data['name']

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

    if request.method == 'POST':
        form = ProjectSelectForm(request.POST, project_choices=project_choices)
        if form.is_valid():
            project_name = form.cleaned_data['project_name']
            return redirect(f"/project/{project_name}/browse")
    else:
        form = ProjectSelectForm(project_choices=project_choices)

    return render(request, 'select_project.html', {'form': form})

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
            ["adb", "shell", "pm", "list", "packages"], text=True
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
            package_name = form.cleaned_data['package_name']
            is_rooted = form.cleaned_data['is_rooted']

            res = main.start_project(project_name, is_rooted, package_name)

            return redirect(f"http://127.0.0.1:8000/project/{project_name}/browse")
    else:
        form = ApplicationForm(package_choices=package_choices)

    return render(request, 'add_application.html', {
        'form': form,
        'project_name': project_name
    })


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