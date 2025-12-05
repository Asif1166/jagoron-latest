from django.urls import path
from . import views
from django.views.generic import TemplateView # <-- ADD THIS LINE

urlpatterns = [
    path('', views.home, name='home'),
    path('ajax/get-subsections/', views.get_subsections, name='get_subsections'),
    path('news/', views.news_page, name='news_page'),
    path('news/detail/<int:news_id>/', views.news_detail, name='news_detail'),
    path('default-pages/<str:link>/', views.default_page_detail, name='default_page_detail'),
    path('jagoron-1lakh/', views.generate_photo, name='generate_photo'),

    path('search/', views.search_news, name='search_news'),
    

    path('s/<str:short_code>/', views.redirect_short_url, name='redirect_short_url'),
    path('api/create-short-url/', views.create_short_url, name='create_short_url'),

    path('news/react/<int:news_id>/', views.react_to_news, name='react_to_news'),
    
    path(
        'editor/', 
        TemplateView.as_view(template_name="pages/editor_profile.html"), 
        name='static_editor_page'
    ),
    path('ckeditor/upload/', views.ckeditor_upload, name='ckeditor_upload'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/dashboard/image-stats/', views.dashboard_image_stats, name='dashboard_image_stats'),
    path('admin/dashboard/reporter-stats/', views.dashboard_reporter_stats, name='dashboard_reporter_stats'),
    path('admin/dashboard/content-stats/', views.dashboard_content_stats, name='dashboard_content_stats'),
    
]