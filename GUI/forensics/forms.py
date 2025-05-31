# forensics/forms.py
from django import forms

class ProjectForm(forms.Form):
    name = forms.CharField(label='Project Name', max_length=100)
    description = forms.CharField(label='Description', widget=forms.Textarea, required=False)

class ApplicationForm(forms.Form):
    package_names = forms.MultipleChoiceField(
        label="Package Names",
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        choices=[]
    )
    is_rooted = forms.BooleanField(label='Device is Rooted', required=False)

    def __init__(self, *args, **kwargs):
        package_choices = kwargs.pop('package_choices', [])
        super().__init__(*args, **kwargs)
        self.fields['package_names'].choices = package_choices


class ProjectSelectForm(forms.Form):
    project_name = forms.ChoiceField(label='Select a Project', choices=[])

    def __init__(self, *args, **kwargs):
        project_choices = kwargs.pop('project_choices', [])
        super().__init__(*args, **kwargs)
        self.fields['project_name'].choices = project_choices