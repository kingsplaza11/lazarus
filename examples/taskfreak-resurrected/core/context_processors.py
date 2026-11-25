from django.conf import settings


def skin(request):
    """Expose the chosen skin (cookie) and the available skins to templates."""
    chosen = request.COOKIES.get("skin", settings.DEFAULT_SKIN)
    if chosen not in settings.SKINS:
        chosen = settings.DEFAULT_SKIN
    return {"skin": chosen, "skins": settings.SKINS}


def member(request):
    """Expose the signed-in Member (session-based auth) to templates."""
    from accounts.views import current_member
    return {"member": current_member(request) if hasattr(request, "session") else None}
