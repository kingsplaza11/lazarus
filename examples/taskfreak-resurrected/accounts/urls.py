from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("user/password/", views.user_password, name="user_password"),
    path("user/details/", views.user_details, name="user_details"),
    path("user/list/", views.user_list, name="user_list"),
    path("user/edit/", views.user_edit, name="user_edit"),
    path("user/register/", views.user_register, name="user_register"),
]
