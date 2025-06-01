from django.urls import path
from . import views

app_name = "engagement"

urlpatterns = [
    path('', views.homepage, name='homepage'),
    path('manual-import/', views.manual_import, name='manual_import'),
    path('auth-reminder/', views.auth_reminder, name='auth_reminder'),
    path('populate_olap_cube/', views.populate_olap_cube, name='populate_olap_cube'),
    path('check_olap_status/', views.check_olap_status, name='check_olap_status'),
    path("export-engagement/", views.export_engagement_csv, name="export_engagement_csv"),
    path('clear-session/', views.clear_session, name='clear_session'),
    path("select-features/", views.select_features_and_target, name="select_features"),
    path("train-model/", views.run_model_training, name="train_model"),
]