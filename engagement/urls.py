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
    path("predict-form/", views.predict_form_view, name="predict_form"),
    path("train-tree/", views.train_decision_tree, name="train_tree"),
    path("train-linear/", views.train_linear_model_view, name="train_linear_model"),
    path("plot-linear/", views.run_linear_plot_view, name="plot_linear"),
]