"""URL configuration for the lazarus project."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('web.urls')),
    path("corpses/", include("intake.urls")),
    path("corpses/", include("autopsy.urls")),
    path("corpses/", include("specgen.urls")),
]
