# forensics/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('create_project/', views.create_project, name='create_project'),
    path('project/<str:project_name>/', views.project_detail, name='project_detail'),
    path('select_project/', views.select_project, name='select_project'),
    path('project/<str:project_name>/add_application/', views.add_application, name='add_application'),
    path('project/<str:project_name>/browse/', views.browse_project, name='browse_project'),
    path('project/<str:project_name>/browse/<path:subpath>/', views.browse_project, name='browse_project'),
    path('project/<str:project_name>/timeline/', views.timeline_view, name='timeline_view'),
    path('compare/<str:project_name1>/<str:project_name2>/<str:type>/', views.compare_view, name='compare_view'),
]
