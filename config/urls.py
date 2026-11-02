from django.contrib import admin
from django.urls import include, path

from apps.core import pwa_views

urlpatterns = [
    # PWA from root (correct scope for service worker)
    path("service-worker.js", pwa_views.service_worker, name="service_worker"),
    path("manifest.json", pwa_views.manifest, name="manifest"),
    path("browser-config.js", pwa_views.browser_config, name="browser_config"),

    path("admin/", admin.site.urls),
    path("accounts/", include("apps.accounts.urls")),
    path("accounting/", include("apps.accounting.urls")),
    path("sales/", include("apps.sales.urls")),
    path("purchases/", include("apps.purchases.urls")),
    path("inventory/", include("apps.inventory.urls")),
    path("hr/", include("apps.hr.urls")),
    path("moadian/", include("apps.moadian.urls")),
    path("api/v1/", include("apps.api.urls")),
    path("", include("apps.core.urls")),
]
