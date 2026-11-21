from django import forms

from .github import GitHubError, parse_github_url
from .safety import MAX_UPLOAD_BYTES, MSG_INVALID

MSG_TOO_BIG = "Corpses must be 20 MB or smaller."
MSG_NEED_ONE = "Provide a zip file or a GitHub URL."
MSG_ONLY_ONE = "Provide a zip file or a GitHub URL, not both."


class CorpseUploadForm(forms.Form):
    name = forms.CharField(max_length=200, label="Name this corpse")
    archive = forms.FileField(required=False, label="Zip file")
    github_url = forms.CharField(required=False, max_length=500, label="GitHub URL")

    def clean_archive(self):
        archive = self.cleaned_data.get("archive")
        if archive:
            if not archive.name.lower().endswith(".zip"):
                raise forms.ValidationError(MSG_INVALID)
            if archive.size > MAX_UPLOAD_BYTES:
                raise forms.ValidationError(MSG_TOO_BIG)
        return archive

    def clean_github_url(self):
        url = (self.cleaned_data.get("github_url") or "").strip()
        if url:
            try:
                parse_github_url(url)
            except GitHubError as exc:
                raise forms.ValidationError(str(exc))
        return url

    def clean(self):
        cleaned = super().clean()
        has_zip = bool(cleaned.get("archive"))
        has_url = bool(cleaned.get("github_url"))
        if not self.errors:
            if has_zip and has_url:
                raise forms.ValidationError(MSG_ONLY_ONE)
            if not has_zip and not has_url:
                raise forms.ValidationError(MSG_NEED_ONE)
        return cleaned
