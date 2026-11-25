from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("print/list/", views.print_list, name="print_list"),
    path("project/edit/", views.project_edit, name="project_edit"),
    path("project/list/", views.project_list, name="project_list"),
    path("task/", views.task, name="task"),
    path("public/", views.public, name="public"),
    path("rss/", views.rss, name="rss"),
    path("error/", views.error, name="error"),
    path("install/", views.install, name="install"),
    path("skin/", views.set_skin, name="set_skin"),
]
