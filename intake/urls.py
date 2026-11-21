from django.urls import path

from . import views

app_name = "intake"

urlpatterns = [
    path("new/", views.upload, name="upload"),
    path("demo/", views.demo, name="demo"),
    path("<int:pk>/", views.detail, name="detail"),
]
