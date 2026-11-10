from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib import messages
from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponseNotAllowed
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_encode, urlsafe_base64_decode
from django.views.decorators.http import require_POST, require_http_methods
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


@require_http_methods(["GET", "POST", "HEAD"])
def register_view(request):
    """
    User registration view (Phase 5.2 - Strict Mode).
    Validates user input, hashes password, saves inactive user (is_active=False),
    and sends an email verification link.
    """
    if request.user.is_authenticated:
        return redirect(get_safe_redirect_url(request))

    redirect_to = request.POST.get('next') or request.GET.get('next') or ''

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            user.save()

            # Generate secure token and base64-encoded user ID
            token = default_token_generator.make_token(user)
            uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

            # Build activation link using local development domain
            activation_path = reverse('verify_email', kwargs={'uidb64': uidb64, 'token': token})
            activation_url = f"http://127.0.0.1:8000{activation_path}"

            # Send verification email
            subject = "Activate your Feedback Platform account"
            message = (
                f"Hi {user.username},\n\n"
                f"Please click the link below to verify your email address and activate your account:\n"
                f"{activation_url}\n\n"
                f"If you did not register for an account, please ignore this email."
            )
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@localhost')
            send_mail(
                subject=subject,
                message=message,
                from_email=from_email,
                recipient_list=[user.email],
                fail_silently=False,
            )

            messages.success(request, f"Welcome to Feedback Platform, {user.username}! Please check your email to activate your account.")
            return redirect(get_safe_redirect_url(request, redirect_to))
        else:
            messages.error(request, "Please correct the errors below to register.")
    else:
        form = RegisterForm()

    return render(request, 'register.html', {
        'form': form,
        'next': redirect_to,
    })


@require_http_methods(["GET", "POST", "HEAD"])
def verify_email_view(request, uidb64, token):
    """
    Decodes the user ID, verifies the activation token,
    activates the account (is_active=True), logs the user in,
    and redirects to the index page.
    """
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        login(request, user)
        messages.success(request, f"Welcome to Feedback Platform, {user.username}! Your email has been verified.")
        return redirect('index')
    else:
        messages.error(request, "The activation link is invalid or has expired.")
        return redirect('index')


@require_http_methods(["GET", "POST", "HEAD"])
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
@login_required
def logout_view(request):
    """
    User logout view.
    Requires POST method, authenticated session, and valid CSRF token to prevent logout CSRF attacks.
    Flushes the user session and redirects.
    """
    logout(request)
    messages.info(request, "You have been successfully logged out.")
    logout_redirect = getattr(settings, 'LOGOUT_REDIRECT_URL', '/')
    return redirect(logout_redirect)
