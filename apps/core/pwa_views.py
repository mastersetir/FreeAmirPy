"""سرو کردن فایل‌های PWA از ریشه (برای scope درست)."""
import os
from django.conf import settings
from django.http import HttpResponse, Http404
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

def _serve_file(filename: str, content_type: str) -> HttpResponse:
    path = os.path.join(settings.BASE_DIR, "static", filename)
    if not os.path.exists(path):
        raise Http404(f"{filename} not found")
    with open(path, "rb") as f:
        content = f.read()
    response = HttpResponse(content, content_type=content_type)
    if filename == "service-worker.js":
        response["Service-Worker-Allowed"] = "/"
    return response

@never_cache
@require_GET
def service_worker(request):
    return _serve_file("service-worker.js", "application/javascript; charset=utf-8")

@never_cache
@require_GET
def manifest(request):
    return _serve_file("manifest.json", "application/manifest+json; charset=utf-8")

@never_cache
@require_GET
def browser_config(request):
    return HttpResponse(
        f"window.FREEAMIR_DEBUG = {str(settings.DEBUG).lower()};\n"
        f"window.FREEAMIR_VERSION = '1.0.0';\n",
        content_type="application/javascript; charset=utf-8",
    )
