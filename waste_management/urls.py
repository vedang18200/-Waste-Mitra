from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from waste_classifier.urls import api_urlpatterns

urlpatterns = [
    path('admin/', admin.site.urls),
    # Web interface (main site)
    path('', include('waste_classifier.urls')),
    # API endpoints
    path('api/', include(api_urlpatterns)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
