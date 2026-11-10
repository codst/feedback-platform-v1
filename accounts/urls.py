from django.urls import path, reverse_lazy
from django.contrib.auth.views import (
    PasswordResetView,
    PasswordResetDoneView,
    PasswordResetConfirmView,
    PasswordResetCompleteView,
)
from . import views

urlpatterns = [
    path('register/', views.register_view, name='register'),
    path('register.html', views.register_view, name='register_html'),
    path('login/', views.login_view, name='login'),
    path('login.html', views.login_view, name='login_html'),
    path('logout/', views.logout_view, name='logout'),

    # Email Verification
    path('verify-email/<str:uidb64>/<str:token>/', views.verify_email_view, name='verify_email'),
    path('verify-email/<str:uidb64>/<str:token>/', views.verify_email_view, name='verify_email_view'),
    path('verify/<str:uidb64>/<str:token>/', views.verify_email_view),

    # Password Reset
    path(
        'password_reset/',
        PasswordResetView.as_view(
            template_name='registration/password_reset_form.html',
            email_template_name='registration/password_reset_email.html',
            subject_template_name='registration/password_reset_subject.txt',
            success_url=reverse_lazy('password_reset_done'),
            extra_email_context={'domain': '127.0.0.1:8000', 'protocol': 'http'},
        ),
        name='password_reset',
    ),
    path(
        'password-reset/',
        PasswordResetView.as_view(
            template_name='registration/password_reset_form.html',
            email_template_name='registration/password_reset_email.html',
            subject_template_name='registration/password_reset_subject.txt',
            success_url=reverse_lazy('password_reset_done'),
            extra_email_context={'domain': '127.0.0.1:8000', 'protocol': 'http'},
        ),
    ),
    path(
        'password_reset/done/',
        PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    path(
        'password-reset/done/',
        PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html',
        ),
    ),
    path(
        'reset/<uidb64>/<token>/',
        PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html',
            success_url=reverse_lazy('password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    path(
        'password-reset-confirm/<uidb64>/<token>/',
        PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html',
            success_url=reverse_lazy('password_reset_complete'),
        ),
    ),
    path(
        'reset/done/',
        PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
    path(
        'password-reset-complete/',
        PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html',
        ),
    ),
]
