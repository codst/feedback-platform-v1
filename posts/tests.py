import json
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from .models import Post


class PostPublishingFlowTests(TestCase):
    """Existing Phase 1 tests — preserved unchanged."""

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.admin_user = User.objects.create_superuser(
            username='admin_test',
            password='password123',
            email='admin@test.com'
        )

    def test_valid_post_creation_saves_to_db(self):
        # Must be logged in now
        self.client.force_login(self.admin_user)
        page_response = self.client.get('/create/')
        csrf_token = page_response.cookies['csrftoken'].value

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
        # Author is set from the session, not client input
        self.assertEqual(post.author, self.admin_user)

    def test_empty_submission_rejected(self):
        self.client.force_login(self.admin_user)
        page_response = self.client.get('/create/')
        csrf_token = page_response.cookies['csrftoken'].value

        res1 = self.client.post(
            '/api/posts/',
            data=json.dumps({'title': '', 'content': 'Valid content'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        self.assertEqual(res1.status_code, 400)
        self.assertIn('error', res1.json())

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
        self.client.force_login(self.admin_user)
        response = self.client.post(
            '/api/posts/',
            data=json.dumps({'title': 'No CSRF', 'content': 'Test'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Post.objects.count(), 0)

    def test_api_posts_list_returns_saved_posts(self):
        # Create posts with authors (required by model)
        Post.objects.create(title='Post 1', content='Content 1', author=self.admin_user)
        Post.objects.create(title='Post 2', content='Content 2', author=self.admin_user)

        response = self.client.get('/api/posts/')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data['posts']), 2)
        self.assertEqual(data['posts'][0]['title'], 'Post 2')
        self.assertEqual(data['posts'][1]['title'], 'Post 1')
        # Phase 2: API now includes author info
        self.assertIn('author', data['posts'][0])
        self.assertEqual(data['posts'][0]['author'], 'admin_test')

    def test_post_visible_in_django_admin(self):
        Post.objects.create(title='Admin Visible Post', content='Checking admin page', author=self.admin_user)
        self.client.force_login(self.admin_user)
        response = self.client.get('/admin/posts/post/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Visible Post')


class PostAuthenticationTests(TestCase):
    """Phase 2: Authentication and authorization tests."""

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.alice = User.objects.create_user(
            username='alice', email='alice@example.com', password='AlicePass123!'
        )
        self.bob = User.objects.create_user(
            username='bob', email='bob@example.com', password='BobPass456!'
        )
        self.alice_post = Post.objects.create(
            title="Alice's Post", content="Written by Alice", author=self.alice
        )

    # -----------------------------------------------------------------------
    # Scenario 1 & 5: Auth required to create post
    # -----------------------------------------------------------------------

    def test_anonymous_cannot_create_post_via_api(self):
        """Scenario 5: Anonymous visitor cannot create a post."""
        response = self.client.get('/')
        csrf_token = response.cookies['csrftoken'].value

        res = self.client.post(
            '/api/posts/',
            data=json.dumps({'title': 'Anon post', 'content': 'Should fail'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        self.assertEqual(res.status_code, 401)
        self.assertTrue(res.json().get('login_required'))
        self.assertEqual(Post.objects.count(), 1)  # Only Alice's post

    def test_anonymous_create_page_redirects_to_login(self):
        """@login_required on create view redirects anonymous users."""
        response = self.client.get('/create/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_authenticated_user_can_create_post(self):
        """Scenario 1: A registered user logs in and creates a post."""
        self.client.force_login(self.alice)
        get_response = self.client.get('/create/')
        csrf_token = get_response.cookies['csrftoken'].value

        res = self.client.post(
            '/api/posts/',
            data=json.dumps({'title': 'New post', 'content': 'Some content'}),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        self.assertEqual(res.status_code, 201)
        new_post = Post.objects.get(title='New post')
        # Author is set from session, not client input
        self.assertEqual(new_post.author, self.alice)

    # -----------------------------------------------------------------------
    # Scenario 7: Tampering with author ID does not change ownership
    # -----------------------------------------------------------------------

    def test_submitted_author_id_is_ignored(self):
        """Scenario 7: Even if Bob sends Alice's user ID, post belongs to Bob."""
        self.client.force_login(self.bob)
        get_response = self.client.get('/create/')
        csrf_token = get_response.cookies['csrftoken'].value

        # Bob sends Alice's user ID as 'author' in the request body
        res = self.client.post(
            '/api/posts/',
            data=json.dumps({
                'title': 'Tampered post',
                'content': 'Bob tries to forge Alice as author',
                'author': self.alice.id,          # Ignored
                'author_id': self.alice.id,       # Ignored
                'user_id': self.alice.id,         # Ignored
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        self.assertEqual(res.status_code, 201)
        tampered_post = Post.objects.get(title='Tampered post')
        # Despite the tamper attempt, the author is Bob (from session)
        self.assertEqual(tampered_post.author, self.bob)
        self.assertNotEqual(tampered_post.author, self.alice)

    # -----------------------------------------------------------------------
    # Scenario 2 & 3: Post appears in admin and shows correct author on Explore
    # -----------------------------------------------------------------------

    def test_post_shows_correct_author_on_explore_api(self):
        """Scenario 3: The post shows the correct author's username."""
        response = self.client.get('/api/posts/')
        self.assertEqual(response.status_code, 200)
        posts = response.json()['posts']
        self.assertEqual(len(posts), 1)
        self.assertEqual(posts[0]['author'], 'alice')
        self.assertIn('/users/alice/', posts[0]['author_profile_url'])

    # -----------------------------------------------------------------------
    # Scenario 6 & 8: Only owner can edit/delete; unauthorized requests blocked
    # -----------------------------------------------------------------------

    def test_owner_can_edit_own_post(self):
        """Alice can edit her own post."""
        self.client.force_login(self.alice)
        get_response = self.client.get(reverse('edit_post', args=[self.alice_post.id]))
        self.assertEqual(get_response.status_code, 200)
        csrf_token = get_response.cookies['csrftoken'].value

        post_response = self.client.post(
            reverse('edit_post', args=[self.alice_post.id]),
            data={'title': 'Updated title', 'content': 'Updated content'},
            HTTP_X_CSRFTOKEN=csrf_token
        )
        self.assertEqual(post_response.status_code, 302)
        self.alice_post.refresh_from_db()
        self.assertEqual(self.alice_post.title, 'Updated title')

    def test_non_owner_cannot_edit_post(self):
        """Scenario 6: Bob cannot edit Alice's post — gets 404, not Alice's data."""
        self.client.force_login(self.bob)
        response = self.client.get(reverse('edit_post', args=[self.alice_post.id]))
        # 404 because get_object_or_404(Post, id=..., author=request.user) fails for Bob
        self.assertEqual(response.status_code, 404)

    def test_owner_can_delete_own_post(self):
        """Alice can delete her own post."""
        self.client.force_login(self.alice)
        get_response = self.client.get('/')
        csrf_token = get_response.cookies['csrftoken'].value

        response = self.client.post(
            reverse('delete_post', args=[self.alice_post.id]),
            HTTP_X_CSRFTOKEN=csrf_token
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Post.objects.filter(id=self.alice_post.id).exists())

    def test_non_owner_cannot_delete_post(self):
        """Scenario 6 & 8: Bob cannot delete Alice's post."""
        self.client.force_login(self.bob)
        get_response = self.client.get('/')
        csrf_token = get_response.cookies['csrftoken'].value

        response = self.client.post(
            reverse('delete_post', args=[self.alice_post.id]),
            HTTP_X_CSRFTOKEN=csrf_token
        )
        # 404 — ownership check fails
        self.assertEqual(response.status_code, 404)
        # Scenario 8: Post is still in the database
        self.assertTrue(Post.objects.filter(id=self.alice_post.id).exists())

    def test_anonymous_cannot_delete_post(self):
        """Scenario 8: Anonymous deletion request does not modify the database."""
        get_response = self.client.get('/')
        csrf_token = get_response.cookies['csrftoken'].value

        response = self.client.post(
            reverse('delete_post', args=[self.alice_post.id]),
            HTTP_X_CSRFTOKEN=csrf_token
        )
        # @login_required redirects to login
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
        # Post is untouched
        self.assertTrue(Post.objects.filter(id=self.alice_post.id).exists())

    def test_delete_requires_post_method(self):
        """Delete via GET is rejected with 405."""
        self.client.force_login(self.alice)
        response = self.client.get(reverse('delete_post', args=[self.alice_post.id]))
        self.assertEqual(response.status_code, 405)
        self.assertTrue(Post.objects.filter(id=self.alice_post.id).exists())

    # -----------------------------------------------------------------------
    # Scenario 4 & 9: Dashboard — own posts, empty state
    # -----------------------------------------------------------------------

    def test_dashboard_shows_own_posts(self):
        """Scenario 4: Post appears on its author's dashboard."""
        self.client.force_login(self.alice)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alice&#x27;s Post")
        # Bob's name should not appear on Alice's dashboard
        self.assertNotContains(response, 'bob')

    def test_dashboard_shows_empty_state_for_new_user(self):
        """Scenario 9: A user with no posts sees a useful empty state."""
        self.client.force_login(self.bob)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "haven't published")

    def test_dashboard_requires_login(self):
        """Anonymous users are redirected to login when accessing dashboard."""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_dashboard_uses_session_user_not_url(self):
        """
        The dashboard view uses request.user (session), not a URL parameter.
        Bob cannot see Alice's dashboard by any URL manipulation.
        """
        self.client.force_login(self.bob)
        # There's only one dashboard URL — it always shows the current session user
        response = self.client.get(reverse('dashboard'))
        self.assertNotContains(response, "Alice's Post")

    # -----------------------------------------------------------------------
    # Scenario 4 & 10: Public profile pages and 404 for nonexistent users
    # -----------------------------------------------------------------------

    def test_public_profile_shows_user_posts(self):
        """Scenario 4: Post appears on its author's public profile."""
        response = self.client.get(reverse('public_profile', args=['alice']))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'alice')
        self.assertContains(response, "Alice&#x27;s Post")

    def test_public_profile_does_not_expose_email(self):
        """Public profile never exposes email or password data."""
        response = self.client.get(reverse('public_profile', args=['alice']))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'alice@example.com')

    def test_nonexistent_profile_returns_404(self):
        """Scenario 10: Visiting /users/nobody/ returns 404."""
        response = self.client.get(reverse('public_profile', args=['nobody']))
        self.assertEqual(response.status_code, 404)

    # -----------------------------------------------------------------------
    # Scenario 11: Existing posts preserved after migration
    # -----------------------------------------------------------------------

    def test_existing_post_has_author(self):
        """Scenario 11: Alice's post (created in setUp) has an author."""
        post = Post.objects.get(id=self.alice_post.id)
        self.assertIsNotNone(post.author)
        self.assertEqual(post.author.username, 'alice')

    # -----------------------------------------------------------------------
    # Scenario 12: Phase 1 auth still works
    # -----------------------------------------------------------------------

    def test_login_logout_still_works(self):
        """Scenario 12: Registration, login, logout remain functional."""
        # Register
        get_response = self.client.get(reverse('register'))
        csrf_token = get_response.cookies['csrftoken'].value
        reg_response = self.client.post(
            reverse('register'),
            data={
                'username': 'newphase2user',
                'email': 'newphase2@example.com',
                'password1': 'Phase2Pass123!',
                'password2': 'Phase2Pass123!',
            },
            HTTP_X_CSRFTOKEN=csrf_token
        )
        self.assertEqual(reg_response.status_code, 302)
        new_user = User.objects.get(username='newphase2user')
        self.assertTrue(new_user.check_password('Phase2Pass123!'))

        # Logout
        index_response = self.client.get('/')
        csrf_token = index_response.cookies['csrftoken'].value
        logout_response = self.client.post(reverse('logout'), HTTP_X_CSRFTOKEN=csrf_token)
        self.assertEqual(logout_response.status_code, 302)
        self.assertNotIn('_auth_user_id', self.client.session)

    # -----------------------------------------------------------------------
    # Bug Audit Tests: Fallbacks, Redirects, PRG & Author Security
    # -----------------------------------------------------------------------

    def test_authorless_post_renders_unknown_author_fallback(self):
        """Authorless posts display 'Unknown author' fallback and do not crash."""
        post = Post.objects.create(title="Legacy Note", content="From old system", author=None)
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Legacy Note")
        self.assertContains(response, "by Unknown author")

        # Test string representation handles None author safely
        self.assertIn("Unknown author", str(post))

        # Test API response provides 'Unknown author' and null profile URL
        api_res = self.client.get('/api/posts/')
        self.assertEqual(api_res.status_code, 200)
        posts_data = api_res.json()['posts']
        legacy_data = next((p for p in posts_data if p['id'] == post.id), None)
        self.assertIsNotNone(legacy_data)
        self.assertEqual(legacy_data['author'], 'Unknown author')
        self.assertIsNone(legacy_data['author_profile_url'])

    def test_create_post_server_form_redirects_to_explore(self):
        """Form submission via server-side POST redirects to intended destination (/#explore)."""
        self.client.force_login(self.alice)
        page_res = self.client.get('/create/')
        csrf_token = page_res.cookies['csrftoken'].value

        response = self.client.post(
            reverse('create'),
            data={'title': 'Server Created Post', 'content': 'Server content'},
            HTTP_X_CSRFTOKEN=csrf_token
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/#explore')
        self.assertNotEqual(response.url, '/create/index.html')

        post = Post.objects.get(title='Server Created Post')
        self.assertEqual(post.author, self.alice)

    def test_create_post_api_never_trusts_client_author_param(self):
        """API ignores any client-supplied author field and always assigns request.user."""
        self.client.force_login(self.alice)
        page_res = self.client.get('/')
        csrf_token = page_res.cookies['csrftoken'].value

        response = self.client.post(
            '/api/posts/',
            data=json.dumps({
                'title': 'Spoofed Author Post',
                'content': 'Attempting spoof',
                'author': 'bob',
                'author_id': self.bob.id
            }),
            content_type='application/json',
            HTTP_X_CSRFTOKEN=csrf_token
        )
        self.assertEqual(response.status_code, 201)
        post = Post.objects.get(title='Spoofed Author Post')
        # Must be alice, never bob
        self.assertEqual(post.author, self.alice)
        self.assertNotEqual(post.author, self.bob)

    def test_authorless_post_cannot_be_edited_or_deleted_by_regular_user(self):
        """Authorless posts return 404 on edit/delete attempts by regular users."""
        post = Post.objects.create(title="Unowned Post", content="Cannot touch", author=None)
        self.client.force_login(self.alice)

        # Edit attempt
        edit_res = self.client.get(reverse('edit_post', args=[post.id]))
        self.assertEqual(edit_res.status_code, 404)

        # Delete attempt
        page_res = self.client.get('/')
        csrf_token = page_res.cookies['csrftoken'].value
        del_res = self.client.post(
            reverse('delete_post', args=[post.id]),
            HTTP_X_CSRFTOKEN=csrf_token
        )
        self.assertEqual(del_res.status_code, 404)
        self.assertTrue(Post.objects.filter(id=post.id).exists())
