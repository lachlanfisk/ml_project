from django.urls import path
from . import views

app_name = "engagement"

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('manual-import/', views.manual_import, name='manual_import'),
    path('auth-reminder/', views.auth_reminder, name='auth_reminder'),
    path('populate_olap_cube/', views.populate_olap_cube, name='populate_olap_cube'),
    path('check_olap_status/', views.check_olap_status, name='check_olap_status'),
]