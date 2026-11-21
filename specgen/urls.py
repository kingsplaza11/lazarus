from django.urls import path

from . import views

app_name = "specgen"

urlpatterns = [
    path("<int:pk>/spec/", views.detail, name="detail"),
    path("<int:pk>/spec/generate/", views.generate, name="generate"),
    path("<int:pk>/spec/download/", views.download, name="download"),
    path("<int:pk>/spec/file/", views.download_file, name="file"),
]
