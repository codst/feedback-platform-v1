from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('index.html', views.index, name='index_html'),
    path('create/', views.create, name='create'),
    path('create.html', views.create, name='create_html'),
    path('explore/', views.explore, name='explore'),
    path('explore.html', views.explore, name='explore_html'),
    path('project.html', views.project, name='project'),
    path('feedback.html', views.feedback, name='feedback'),
    path('api/posts/', views.api_posts, name='api_posts'),
]
