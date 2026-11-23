from django.urls import path

from . import views

app_name = "parity"

urlpatterns = [
    path("<int:pk>/check/", views.detail, name="check"),
]
