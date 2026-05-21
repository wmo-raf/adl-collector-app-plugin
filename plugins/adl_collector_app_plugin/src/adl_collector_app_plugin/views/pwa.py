from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie


@ensure_csrf_cookie
def field_pwa(request):
    """Serves the PWA shell page for field observers."""
    return render(request, "adl_collector_app_plugin/pwa_shell.html")


def field_service_worker(request):
    """
    Serves the service worker JS via Django so it is scoped to the field-app
    URL rather than /static/ (static files can only control pages under /static/).
    """
    from django.http import HttpResponse
    content = render(request, "adl_collector_app_plugin/sw.js")
    return HttpResponse(
        content.content,
        content_type="application/javascript",
        headers={"Service-Worker-Allowed": "/"},
    )
