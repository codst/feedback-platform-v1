from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse


class AccountsAuthenticationTests(TestCase):
    def setUp(self):
        # Enforce CSRF checks on the test client to test security headers and tokens
        self.client = Client(enforce_csrf_checks=True)
        self.password = "Secur3P@ssw0rd!"
        self.existing_user = User.objects.create_user(
            username="existinguser",
            email="existing@example.com",
            password=self.password
        )

    def test_registration_page_loads_with_csrf_token(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="email"')
        self.assertContains(response, 'name="password1"')
        self.assertContains(response, 'name="password2"')

    def test_successful_registration(self):
        page_response = self.client.get(reverse('register'))
        csrf_token = page_response.cookies['csrftoken'].value

        data = {
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password1': 'Str0ngP@ssword123',
            'password2': 'Str0ngP@ssword123',
        }
        response = self.client.post(
            reverse('register'),
            data=data,
            HTTP_X_CSRFTOKEN=csrf_token
        )

        # Should redirect to index upon success
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')

        # Verify user was saved to the database
        user = User.objects.filter(username='newuser').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'newuser@example.com')
        # Verify password is NOT stored as plaintext
        self.assertNotEqual(user.password, 'Str0ngP@ssword123')
        self.assertTrue(user.check_password('Str0ngP@ssword123'))

        # Verify user is automatically logged in via session
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_registration_password_mismatch(self):
        page_response = self.client.get(reverse('register'))
        csrf_token = page_response.cookies['csrftoken'].value

        data = {
            'username': 'mismatchuser',
            'email': 'mismatch@example.com',
            'password1': 'Str0ngP@ssword123',
            'password2': 'DifferentPassword456',
        }
        response = self.client.post(
            reverse('register'),
            data=data,
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='mismatchuser').exists())
        self.assertContains(response, "The two password fields didn’t match.")

    def test_registration_duplicate_username(self):
        page_response = self.client.get(reverse('register'))
        csrf_token = page_response.cookies['csrftoken'].value

        data = {
            'username': 'existinguser',
            'email': 'another@example.com',
            'password1': 'Str0ngP@ssword123',
            'password2': 'Str0ngP@ssword123',
        }
        response = self.client.post(
            reverse('register'),
            data=data,
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A user with that username already exists.")

    def test_registration_duplicate_email(self):
        page_response = self.client.get(reverse('register'))
        csrf_token = page_response.cookies['csrftoken'].value

        data = {
            'username': 'anotheruser',
            'email': 'existing@example.com',
            'password1': 'Str0ngP@ssword123',
            'password2': 'Str0ngP@ssword123',
        }
        response = self.client.post(
            reverse('register'),
            data=data,
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A user with this email address already exists.")

    def test_registration_csrf_protected(self):
        data = {
            'username': 'no_csrf_user',
            'email': 'no_csrf@example.com',
            'password1': 'Str0ngP@ssword123',
            'password2': 'Str0ngP@ssword123',
        }
        # Post without CSRF token
        response = self.client.post(reverse('register'), data=data)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(User.objects.filter(username='no_csrf_user').exists())

    def test_login_page_loads(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="csrfmiddlewaretoken"')
        self.assertContains(response, 'name="username"')
        self.assertContains(response, 'name="password"')

    def test_successful_login(self):
        page_response = self.client.get(reverse('login'))
        csrf_token = page_response.cookies['csrftoken'].value

        data = {
            'username': 'existinguser',
            'password': self.password,
        }
        response = self.client.post(
            reverse('login'),
            data=data,
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')
        # Check session contains user ID
        self.assertEqual(int(self.client.session['_auth_user_id']), self.existing_user.pk)

    def test_invalid_login_wrong_password(self):
        page_response = self.client.get(reverse('login'))
        csrf_token = page_response.cookies['csrftoken'].value

        data = {
            'username': 'existinguser',
            'password': 'WrongPassword123',
        }
        response = self.client.post(
            reverse('login'),
            data=data,
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(response, "Invalid username or password.")

    def test_login_csrf_protected(self):
        data = {
            'username': 'existinguser',
            'password': self.password,
        }
        response = self.client.post(reverse('login'), data=data)
        self.assertEqual(response.status_code, 403)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_open_redirect_prevented_on_login(self):
        page_response = self.client.get(reverse('login') + '?next=https://malicious-external-site.com')
        csrf_token = page_response.cookies['csrftoken'].value

        data = {
            'username': 'existinguser',
            'password': self.password,
            'next': 'https://malicious-external-site.com'
        }
        response = self.client.post(
            reverse('login'),
            data=data,
            HTTP_X_CSRFTOKEN=csrf_token
        )

        # Must NOT redirect to external malicious site; must fallback to '/'
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')

    def test_internal_redirect_allowed_on_login(self):
        page_response = self.client.get(reverse('login') + '?next=/create.html')
        csrf_token = page_response.cookies['csrftoken'].value

        data = {
            'username': 'existinguser',
            'password': self.password,
            'next': '/create.html'
        }
        response = self.client.post(
            reverse('login'),
            data=data,
            HTTP_X_CSRFTOKEN=csrf_token
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/create.html')

    def test_logout_via_post_succeeds(self):
        # First log in the user
        self.client.force_login(self.existing_user)
        self.assertEqual(int(self.client.session['_auth_user_id']), self.existing_user.pk)

        # Fetch index to obtain CSRF token
        page_response = self.client.get(reverse('index'))
        csrf_token = page_response.cookies['csrftoken'].value

        # Issue POST logout
        response = self.client.post(reverse('logout'), HTTP_X_CSRFTOKEN=csrf_token)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, '/')

        # Session must be cleared
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_via_get_is_rejected(self):
        self.client.force_login(self.existing_user)
        # Attempt logout via GET - must return 405 Method Not Allowed
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 405)
        # Session must still be active
        self.assertEqual(int(self.client.session['_auth_user_id']), self.existing_user.pk)

    def test_logout_csrf_protected(self):
        self.client.force_login(self.existing_user)
        # Issue POST logout without CSRF token
        response = self.client.post(reverse('logout'))
        self.assertEqual(response.status_code, 403)
        # Session must still be active
        self.assertEqual(int(self.client.session['_auth_user_id']), self.existing_user.pk)

    def test_navigation_renders_auth_status_correctly(self):
        # 1. Unauthenticated request
        anon_response = self.client.get(reverse('index'))
        self.assertContains(anon_response, 'Login')
        self.assertContains(anon_response, 'Register')
        self.assertNotContains(anon_response, 'Logout')
        self.assertNotContains(anon_response, 'existinguser')

        # 2. Authenticated request
        self.client.force_login(self.existing_user)
        auth_response = self.client.get(reverse('index'))
        self.assertContains(auth_response, 'Logout')
        self.assertContains(auth_response, 'existinguser')
        self.assertNotContains(auth_response, '>Login<')
        self.assertNotContains(auth_response, '>Register<')
