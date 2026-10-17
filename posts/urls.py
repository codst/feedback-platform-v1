from django.urls import path
from . import views

urlpatterns = [
    # Public pages
    path('', views.index, name='index'),
    path('index.html', views.index, name='index_html'),
    path('explore/', views.explore, name='explore'),
    path('explore.html', views.explore, name='explore_html'),
    path('project.html', views.project, name='project'),
    path('feedback.html', views.feedback, name='feedback'),

    # Create post (login required — enforced in the view)
    path('create/', views.create, name='create'),
    path('create.html', views.create, name='create_html'),

    # Edit and delete (login required + ownership — enforced in views)
    path('posts/<int:post_id>/edit/', views.edit_post, name='edit_post'),
    path('posts/<int:post_id>/delete/', views.delete_post, name='delete_post'),

    # Dashboard (login required)
    path('dashboard/', views.dashboard, name='dashboard'),

    # Public user profiles
    path('users/<str:username>/', views.public_profile, name='public_profile'),

    # Post detail, like, and comments
    path('posts/<int:post_id>/', views.post_detail, name='post_detail'),
    path('posts/<int:post_id>/like/', views.toggle_like, name='toggle_like'),
    path('posts/<int:post_id>/comments/', views.add_comment, name='add_comment'),
    path('posts/<int:post_id>/comments/<int:comment_id>/edit/', views.edit_comment, name='edit_comment'),
    path('posts/<int:post_id>/comments/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),

    # JSON API used by script.js
    path('api/posts/', views.api_posts, name='api_posts'),
    path('api/posts/<int:post_id>/like/', views.toggle_like, name='api_toggle_like'),
]
