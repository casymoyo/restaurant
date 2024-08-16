from .views import Dashboard
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path
from django.views import defaults as default_views

urlpatterns = [
    path('pos/', include('pos.urls', namespace='pos')),
    path('', Dashboard, name='dashborad'),
    path("admin/", admin.site.urls),
    path('settings/', include('settings.urls', namespace='settings')),
    path('users/', include('users.urls', namespace='users')),
    path('analytics/', include('analytics.urls')),
    path('finance/', include('finance.urls', namespace='finance')),
    path('inventory/', include('inventory.urls', namespace='inventory')),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
