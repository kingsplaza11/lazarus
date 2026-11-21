from django.urls import path

from . import views

app_name = "autopsy"

urlpatterns = [
    path("<int:pk>/autopsy/", views.report, name="report"),
    path("<int:pk>/autopsy/run/", views.run, name="run"),
]
