from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponseNotAllowed
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from .forms import RegisterForm, LoginForm


def get_safe_redirect_url(request, redirect_to=None):
    """
    Validate redirect destination to prevent Open Redirect vulnerabilities.
    Only allows internal URLs matching the current host and scheme.
    """
    if not redirect_to:
        redirect_to = request.POST.get('next') or request.GET.get('next')
    
    if redirect_to and url_has_allowed_host_and_scheme(
        url=redirect_to,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure()
    ):
        return redirect_to
    
    return getattr(settings, 'LOGIN_REDIRECT_URL', '/')


def register_view(request):
    """
    User registration view.
    Validates user input, hashes password, saves to database, and initiates a session.
    """
    if request.user.is_authenticated:
        return redirect(get_safe_redirect_url(request))

    redirect_to = request.POST.get('next') or request.GET.get('next') or ''

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Automatically log the user in after successful registration
            login(request, user)
            messages.success(request, f"Welcome to Feedback Platform, {user.username}! Your account has been created.")
            return redirect(get_safe_redirect_url(request, redirect_to))
        else:
            messages.error(request, "Please correct the errors below to register.")
    else:
        form = RegisterForm()

    return render(request, 'register.html', {
        'form': form,
        'next': redirect_to,
    })


def login_view(request):
    """
    User login view.
    Authenticates credentials and establishes a Django session.
    """
    if request.user.is_authenticated:
        return redirect(get_safe_redirect_url(request))

    redirect_to = request.POST.get('next') or request.GET.get('next') or ''

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect(get_safe_redirect_url(request, redirect_to))
        else:
            messages.error(request, "Invalid username or password. Please try again.")
    else:
        form = LoginForm(request)

    return render(request, 'login.html', {
        'form': form,
        'next': redirect_to,
    })


@require_POST
def logout_view(request):
    """
    User logout view.
    Requires POST method and valid CSRF token to prevent logout CSRF attacks.
    Flushes the user session and redirects.
    """
    logout(request)
    messages.info(request, "You have been successfully logged out.")
    logout_redirect = getattr(settings, 'LOGOUT_REDIRECT_URL', '/')
    return redirect(logout_redirect)
