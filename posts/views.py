import json
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from .forms import PostForm
from .models import Post

User = get_user_model()


# ---------------------------------------------------------------------------
# Public views (no login required)
# ---------------------------------------------------------------------------

@ensure_csrf_cookie
def index(request):
    """Homepage: shows the hero section and the Explore section with all posts."""
    posts = Post.objects.select_related('author').all()  # Meta ordering handles -created_at
    return render(request, 'index.html', {'posts': posts})


def explore(request):
    return redirect('/#explore')


def project(request):
    return render(request, 'project.html')


def feedback(request):
    return render(request, 'feedback.html')


def public_profile(request, username):
    """
    Public profile page for any registered user.
    URL: /users/<username>/
    - Resolves username to a User object (404 if not found).
    - Shows only the user's username and their posts.
    - Never exposes email, password data, or any private field.
    """
    profile_user = get_object_or_404(User, username=username)
    user_posts = Post.objects.filter(author=profile_user).select_related('author')
    return render(request, 'profile.html', {
        'profile_user': profile_user,
        'user_posts': user_posts,
    })


# ---------------------------------------------------------------------------
# Create post (login required)
# ---------------------------------------------------------------------------

@login_required
@ensure_csrf_cookie
def create(request):
    """
    Post creation view. Requires authentication.

    Key security points:
    - @login_required redirects anonymous users to the login page.
    - The author is ALWAYS set to request.user on the server.
    - The form never accepts an author field from the client.
    """
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)  # Don't write to DB yet
            post.author = request.user       # Assign the authenticated user as author
            post.save()
            messages.success(request, f'Your post "{post.title}" has been published!')
            return redirect('/#explore')
        # Form invalid — fall through to render with errors
    else:
        form = PostForm()

    return render(request, 'create.html', {'form': form})


# ---------------------------------------------------------------------------
# Edit post (login required + ownership check)
# ---------------------------------------------------------------------------

@login_required
def edit_post(request, post_id):
    """
    Edit an existing post. Requires login AND ownership.

    The ownership check uses get_object_or_404(Post, id=post_id, author=request.user).
    This single query both retrieves the post AND verifies ownership.
    If the post exists but belongs to another user, Django returns 404 —
    not 403, deliberately, to avoid leaking that the post exists.
    """
    post = get_object_or_404(Post, id=post_id, author=request.user)

    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, f'Your post "{post.title}" has been updated.')
            return redirect('dashboard')
        # Form invalid — fall through to render with errors
    else:
        form = PostForm(instance=post)

    return render(request, 'edit_post.html', {'form': form, 'post': post})


# ---------------------------------------------------------------------------
# Delete post (login required + ownership check + POST only)
# ---------------------------------------------------------------------------

@login_required
@require_POST
def delete_post(request, post_id):
    """
    Delete a post. Requires login AND ownership AND a POST request.

    @require_POST ensures you cannot delete a post by visiting a URL (GET).
    The CSRF middleware protects this form from cross-site request forgery.
    Ownership is verified server-side — no client input can override it.
    """
    post = get_object_or_404(Post, id=post_id, author=request.user)
    title = post.title
    post.delete()
    messages.success(request, f'Your post "{title}" has been deleted.')
    return redirect('dashboard')


# ---------------------------------------------------------------------------
# Dashboard (login required)
# ---------------------------------------------------------------------------

@login_required
def dashboard(request):
    """
    Personal dashboard for the authenticated user.

    Always uses request.user — the user stored in the server session.
    No user ID is accepted from the URL or request body.
    """
    user_posts = Post.objects.filter(author=request.user)
    return render(request, 'dashboard.html', {
        'user_posts': user_posts,
    })


# ---------------------------------------------------------------------------
# API endpoint (used by script.js on the Create page)
# ---------------------------------------------------------------------------

def api_posts(request):
    """
    JSON API for the Create page frontend.

    GET  /api/posts/  — public, returns all posts with author username.
    POST /api/posts/  — requires authentication; assigns author server-side.
    """
    if request.method == 'GET':
        posts = Post.objects.select_related('author').all()
        data = [
            {
                'id': post.id,
                'title': post.title,
                'content': post.content,
                'created_at': post.created_at.isoformat(),
                'author': post.author.username if post.author else 'Unknown author',
                'author_profile_url': f'/users/{post.author.username}/' if post.author else None,
            }
            for post in posts
        ]
        return JsonResponse({'posts': data}, status=200)

    elif request.method == 'POST':
        # Require authentication for creating posts via the API
        if not request.user.is_authenticated:
            return JsonResponse(
                {'error': 'You must be logged in to publish a post.', 'login_required': True},
                status=401
            )

        title = ''
        content = ''

        if request.content_type and 'application/json' in request.content_type:
            try:
                body = json.loads(request.body.decode('utf-8'))
                title = body.get('title', '').strip()
                content = body.get('content', '').strip()
            except (json.JSONDecodeError, UnicodeDecodeError):
                return JsonResponse({'error': 'Invalid JSON data.'}, status=400)
        else:
            title = request.POST.get('title', '').strip()
            content = request.POST.get('content', '').strip()

        if not title or not content:
            return JsonResponse({'error': 'Please fill in both title and content.'}, status=400)

        if len(title) > 200:
            return JsonResponse({'error': 'Title must be 200 characters or fewer.'}, status=400)

        # Author is set from the session — never from the request body.
        post = Post.objects.create(title=title, content=content, author=request.user)
        return JsonResponse({
            'success': True,
            'message': 'Post published successfully.',
            'post': {
                'id': post.id,
                'title': post.title,
                'content': post.content,
                'created_at': post.created_at.isoformat(),
                'author': post.author.username if post.author else 'Unknown author',
                'author_profile_url': f'/users/{post.author.username}/' if post.author else None,
            }
        }, status=201)

    return JsonResponse({'error': 'Method not allowed.'}, status=405)
