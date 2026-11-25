from django import forms

from .models import Project

PROJECT_STATUS_CHOICES = [
    (1, "Active"),
    (2, "On hold"),
    (3, "Completed"),
    (4, "Cancelled"),
]


class ProjectForm(forms.ModelForm):
    status = forms.TypedChoiceField(choices=PROJECT_STATUS_CHOICES, coerce=int, initial=1)

    class Meta:
        model = Project
        fields = ["name", "description"]

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        if not name:
            raise forms.ValidationError("A project name is required.")
        return name


class InviteForm(forms.Form):
    invitee = forms.CharField(max_length=120)


# Status keys recorded in ItemStatus. 5 is DONE_STATUS in core/views.py.
TASK_STATUS_CHOICES = [
    (1, "Open"),
    (2, "In progress"),
    (3, "On hold"),
    (5, "Done"),
]
PRIORITY_CHOICES = [(i, str(i)) for i in range(0, 10)]


class TaskForm(forms.Form):
    title = forms.CharField(max_length=255)
    description = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 5}))
    priority = forms.TypedChoiceField(choices=PRIORITY_CHOICES, coerce=int, initial=5)
    deadlinedate = forms.DateField(
        required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        input_formats=["%Y-%m-%d"],
    )
    project = forms.ModelChoiceField(queryset=Project.objects.none())
    member = forms.ModelChoiceField(queryset=None)
    showprivate = forms.BooleanField(required=False)

    def __init__(self, *args, projects=None, **kwargs):
        from accounts.models import Member

        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = projects if projects is not None else Project.objects.none()
        self.fields["member"].queryset = Member.objects.filter(enabled=True)

    def clean_title(self):
        title = self.cleaned_data["title"].strip()
        if not title:
            raise forms.ValidationError("A title is required.")
        return title

    def clean(self):
        data = super().clean()
        project, assignee = data.get("project"), data.get("member")
        if project and assignee and not project.memberproject_set.filter(member=assignee).exists():
            self.add_error("member", "The assignee must be a member of the project.")
        return data


class CommentForm(forms.Form):
    body = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}), max_length=10000)

    def clean_body(self):
        body = self.cleaned_data["body"].strip()
        if not body:
            raise forms.ValidationError("A comment cannot be empty.")
        return body
