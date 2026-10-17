import json
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_POST
from django.db.models import Count
from django.urls import reverse
from .forms import PostForm, CommentForm
from .models import Post, Like, Comment

User = get_user_model()


# ---------------------------------------------------------------------------
# Public views (no login required)
# ---------------------------------------------------------------------------

@ensure_csrf_cookie
def index(request):
    """Homepage: shows the hero section and the Explore section with all posts."""
    posts = Post.objects.select_related('author').annotate(
        likes_count=Count('likes', distinct=True),
        comments_count=Count('comments', distinct=True),
    ).order_by('-created_at', '-id')
    user_liked_post_ids = set()
    if request.user.is_authenticated:
        user_liked_post_ids = set(
            Like.objects.filter(user=request.user).values_list('post_id', flat=True)
        )
    for p in posts:
        p.has_liked = p.id in user_liked_post_ids

    return render(request, 'index.html', {'posts': posts})


def explore(request):
    return redirect('/#explore')


def project(request):
    """
    Legacy/fallback project route.
    If ?id=X is present, redirects to /posts/X/.
    Otherwise, redirects to the latest post or explore.
    """
    post_id = request.GET.get('id')
    if post_id:
        return redirect('post_detail', post_id=post_id)
    latest_post = Post.objects.first()
    if latest_post:
        return redirect('post_detail', post_id=latest_post.id)
    return redirect('/#explore')


def feedback(request):
    return render(request, 'feedback.html')


@ensure_csrf_cookie
def post_detail(request, post_id):
    """
    Dedicated post page showing full content, likes, comments, and sharing.
    Stable and directly accessible by URL (/posts/<post_id>/).
    """
    post = get_object_or_404(Post.objects.select_related('author'), id=post_id)
    comments = post.comments.select_related('author').all()
    like_count = post.likes.count()
    comment_count = comments.count()
    has_liked = False
    if request.user.is_authenticated:
        has_liked = post.likes.filter(user=request.user).exists()

    comment_form = CommentForm()
    share_url = request.build_absolute_uri()

    return render(request, 'project.html', {
        'post': post,
        'comments': comments,
        'like_count': like_count,
        'comment_count': comment_count,
        'has_liked': has_liked,
        'comment_form': comment_form,
        'share_url': share_url,
    })


def public_profile(request, username):
    """
    Public profile page for any registered user.
    URL: /users/<username>/
    - Resolves username to a User object (404 if not found).
    - Shows only the user's username and their posts.
    - Never exposes email, password data, or any private field.
    """
    profile_user = get_object_or_404(User, username=username)
    user_posts = Post.objects.filter(author=profile_user).select_related('author').annotate(
        likes_count=Count('likes', distinct=True),
        comments_count=Count('comments', distinct=True),
    ).order_by('-created_at', '-id')
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
    JSON API for the Explore and Create pages.

    GET  /api/posts/  — public, returns all posts with author username, like count, comment count.
    POST /api/posts/  — requires authentication; assigns author server-side.
    """
    if request.method == 'GET':
        posts = Post.objects.select_related('author').annotate(
            likes_count=Count('likes', distinct=True),
            comments_count=Count('comments', distinct=True),
        ).order_by('-created_at', '-id')
        user_liked_post_ids = set()
        if request.user.is_authenticated:
            user_liked_post_ids = set(
                Like.objects.filter(user=request.user).values_list('post_id', flat=True)
            )
        data = [
            {
                'id': post.id,
                'title': post.title,
                'content': post.content,
                'created_at': post.created_at.isoformat(),
                'author': post.author.username if post.author else 'Unknown author',
                'author_profile_url': f'/users/{post.author.username}/' if post.author else None,
                'detail_url': f'/posts/{post.id}/',
                'likes_count': post.likes_count,
                'comments_count': post.comments_count,
                'has_liked': post.id in user_liked_post_ids,
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
                'detail_url': f'/posts/{post.id}/',
                'likes_count': 0,
                'comments_count': 0,
                'has_liked': False,
            }
        }, status=201)

    return JsonResponse({'error': 'Method not allowed.'}, status=405)


# ---------------------------------------------------------------------------
# Social Features: Likes and Comments
# ---------------------------------------------------------------------------

@require_POST
def toggle_like(request, post_id):
    """
    Like or unlike a post. Requires authentication.
    Enforces DB uniqueness constraint and toggles state safely.
    Supports both JSON (AJAX) responses and form-POST redirects.
    """
    is_json = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        'application/json' in request.headers.get('Accept', '') or
        (request.content_type and 'application/json' in request.content_type)
    )

    if not request.user.is_authenticated:
        if is_json:
            return JsonResponse(
                {'error': 'You must be logged in to like posts.', 'login_required': True},
                status=401
            )
        messages.error(request, 'Please log in to like posts.')
        return redirect(f'/login/?next=/posts/{post_id}/')

    post = get_object_or_404(Post, id=post_id)

    existing_like = Like.objects.filter(post=post, user=request.user).first()
    if existing_like:
        existing_like.delete()
        liked = False
    else:
        Like.objects.get_or_create(post=post, user=request.user)
        liked = True

    like_count = post.likes.count()

    if is_json:
        return JsonResponse({
            'success': True,
            'liked': liked,
            'like_count': like_count,
        })

    return redirect(request.META.get('HTTP_REFERER') or reverse('post_detail', args=[post.id]))


@require_POST
def add_comment(request, post_id):
    """
    Add a comment to a post. Requires authentication.
    Assigns author = request.user and post = post server-side.
    """
    is_json = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        'application/json' in request.headers.get('Accept', '') or
        (request.content_type and 'application/json' in request.content_type)
    )

    if not request.user.is_authenticated:
        if is_json:
            return JsonResponse(
                {'error': 'You must be logged in to comment.', 'login_required': True},
                status=401
            )
        messages.error(request, 'Please log in to comment.')
        return redirect(f'/login/?next=/posts/{post_id}/')

    post = get_object_or_404(Post, id=post_id)

    if request.content_type and 'application/json' in request.content_type:
        try:
            body = json.loads(request.body.decode('utf-8'))
            content = body.get('content', '').strip()
        except (json.JSONDecodeError, UnicodeDecodeError):
            return JsonResponse({'error': 'Invalid JSON data.'}, status=400)
        form = CommentForm({'content': content})
    else:
        form = CommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        comment.save()
        messages.success(request, 'Your comment has been posted.')

        if is_json:
            return JsonResponse({
                'success': True,
                'message': 'Comment posted successfully.',
                'comment': {
                    'id': comment.id,
                    'author': comment.author.username,
                    'author_profile_url': f'/users/{comment.author.username}/',
                    'content': comment.content,
                    'created_at': comment.created_at.strftime('%b %d, %Y, %I:%M %p'),
                },
                'comment_count': post.comments.count(),
            }, status=201)

        return redirect('post_detail', post_id=post.id)

    if is_json:
        errors = [err for errlist in form.errors.values() for err in errlist]
        return JsonResponse({'error': ' '.join(errors)}, status=400)

    for field, errors in form.errors.items():
        for error in errors:
            messages.error(request, error)
    return redirect('post_detail', post_id=post.id)


@login_required
def edit_comment(request, post_id, comment_id):
    """
    Edit an existing comment. Only the comment's author can edit.
    Returns 404 if post or comment doesn't exist, or if current user is not author.
    """
    post = get_object_or_404(Post, id=post_id)
    comment = get_object_or_404(Comment, id=comment_id, post=post, author=request.user)

    if request.method == 'POST':
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your comment has been updated.')
            return redirect('post_detail', post_id=post.id)
    else:
        form = CommentForm(instance=comment)

    return render(request, 'edit_comment.html', {
        'form': form,
        'post': post,
        'comment': comment,
    })


@login_required
@require_POST
def delete_comment(request, post_id, comment_id):
    """
    Delete a comment.
    Authorized for:
    1) Comment author (own comment)
    2) Post owner (moderating comments on their own post)
    Returns 404 for unauthorized users to prevent existence leak.
    """
    post = get_object_or_404(Post, id=post_id)
    comment = get_object_or_404(Comment, id=comment_id, post=post)

    if comment.author != request.user and post.author != request.user:
        raise Http404("Comment not found or permission denied.")

    comment.delete()
    messages.success(request, 'Comment has been deleted.')

    is_json = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        'application/json' in request.headers.get('Accept', '')
    )
    if is_json:
        return JsonResponse({'success': True, 'comment_count': post.comments.count()})

    return redirect('post_detail', post_id=post.id)
