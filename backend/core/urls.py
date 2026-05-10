"""URL configuration for HabitHamster."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('habits.api.urls')),
    path('', include('habits.urls')),
]

if settings.DEBUG:
    static_root = settings.STATIC_ROOT
    media_root = settings.MEDIA_ROOT
    urlpatterns += static(settings.STATIC_URL, document_root=static_root)
    urlpatterns += static(settings.MEDIA_URL, document_root=media_root)
