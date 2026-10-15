from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('register.html', views.register_view, name='register_html'),
    path('login/', views.login_view, name='login'),
    path('login.html', views.login_view, name='login_html'),
    path('logout/', views.logout_view, name='logout'),
]
