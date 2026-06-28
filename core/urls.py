from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

admin.site.site_header = '🧠 Smart SCID — پنل مدیریت'
admin.site.site_title = 'Smart SCID Admin'
admin.site.index_title = 'مدیریت سیستم مصاحبه بالینی'

urlpatterns = [
    # Admin
    path('admin/', admin.site.urls),

    path('api/accounts/', include('accounts.api.v1.urls')),
    
    # Interview API
    path('api/interviews/', include('interview.api.v1.urls')),

    # Swagger/OpenAPI
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]