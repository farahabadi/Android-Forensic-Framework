# forensics/forms.py
from django import forms

class ProjectForm(forms.Form):
    name = forms.CharField(label='Project Name', max_length=100)
    description = forms.CharField(label='Description', widget=forms.Textarea, required=False)

class ApplicationForm(forms.Form):
    package_name = forms.CharField(label='Package Name', max_length=200)
    is_rooted = forms.BooleanField(label='Device is Rooted', required=False)
