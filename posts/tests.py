import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from .models import Post

class PostPublishingFlowTests(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.admin_user = User.objects.create_superuser(
            username='admin_test',
            password='password123',
            email='admin@test.com'
        )

    def test_valid_post_creation_saves_to_db(self):
        # 1. Fetch create page to get CSRF token
        page_response = self.client.get('/create.html')
        csrf_token = page_response.cookies['csrftoken'].value

        # 2. Submit valid post
        response = self.client.post(
            '/api/posts/',
            data=json.dumps({'title': 'Unit Test Post', 'content': 'Content from test'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json().get('success'))
        self.assertEqual(Post.objects.count(), 1)
        post = Post.objects.first()
        self.assertEqual(post.title, 'Unit Test Post')
        self.assertEqual(post.content, 'Content from test')

    def test_empty_submission_rejected(self):
        page_response = self.client.get('/create.html')
        csrf_token = page_response.cookies['csrftoken'].value

        # Empty title
        res1 = self.client.post(
            '/api/posts/',
            data=json.dumps({'title': '', 'content': 'Valid content'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        self.assertEqual(res1.status_code, 400)
        self.assertIn('error', res1.json())

        # Empty content
        res2 = self.client.post(
            '/api/posts/',
            data=json.dumps({'title': 'Valid title', 'content': ''}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        self.assertEqual(res2.status_code, 400)
        self.assertIn('error', res2.json())
        self.assertEqual(Post.objects.count(), 0)

    def test_csrf_protection_enforced(self):
        # Submission without CSRF token must be forbidden (403)
        response = self.client.post(
            '/api/posts/',
            data=json.dumps({'title': 'No CSRF', 'content': 'Test'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Post.objects.count(), 0)

    def test_api_posts_list_returns_saved_posts(self):
        Post.objects.create(title='Post 1', content='Content 1')
        Post.objects.create(title='Post 2', content='Content 2')

        response = self.client.get('/api/posts/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['posts']), 2)
        # Verify descending order by created_at
        self.assertEqual(data['posts'][0]['title'], 'Post 2')
        self.assertEqual(data['posts'][1]['title'], 'Post 1')

    def test_post_visible_in_django_admin(self):
        Post.objects.create(title='Admin Visible Post', content='Checking admin page')
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin/posts/post/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Visible Post')

