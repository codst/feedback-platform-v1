import json
from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import Post

def index(request):
    posts = Post.objects.all().order_by('-created_at')
    return render(request, 'index.html', {'posts': posts})

def explore(request):
    return redirect('/#explore')

def create(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()

        if not title or not content:
            return render(request, 'create.html', {
                'error': 'Please fill in both title and content.',
                'title': title,
                'content': content,
            })

        if len(title) > 200:
            return render(request, 'create.html', {
                'error': 'Title must be 200 characters or fewer.',
                'title': title,
                'content': content,
            })

        Post.objects.create(title=title, content=content)
        return redirect('/#explore')

    return render(request, 'create.html')

def api_posts(request):
    if request.method == 'GET':
        posts = Post.objects.all().order_by('-created_at')
        data = [
            {
                'id': post.id,
                'title': post.title,
                'content': post.content,
                'created_at': post.created_at.isoformat(),
            }
            for post in posts
        ]
        return JsonResponse({'posts': data}, status=200)

    elif request.method == 'POST':
        title = ''
        content = ''

        if request.content_type == 'application/json':
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

        post = Post.objects.create(title=title, content=content)
        return JsonResponse({
            'success': True,
            'message': 'Post published successfully.',
            'post': {
                'id': post.id,
                'title': post.title,
                'content': post.content,
                'created_at': post.created_at.isoformat(),
            }
        }, status=201)

    return JsonResponse({'error': 'Method not allowed.'}, status=405)

def project(request):
    return render(request, 'project.html')

def feedback(request):
    return render(request, 'feedback.html')

