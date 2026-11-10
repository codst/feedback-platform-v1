from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


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
        """Phase 5.2: Successful registration creates inactive user and sends verification email."""
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

        # Verify user was saved to the database as inactive (Strict Mode)
        user = User.objects.filter(username='newuser').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'newuser@example.com')
        self.assertFalse(user.is_active)
        # Verify password is NOT stored as plaintext
        self.assertNotEqual(user.password, 'Str0ngP@ssword123')
        self.assertTrue(user.check_password('Str0ngP@ssword123'))

        # Verify user is NOT automatically logged in
        self.assertNotIn('_auth_user_id', self.client.session)

        # Verify verification email was sent
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn(user.email, email.to)
        self.assertIn('127.0.0.1:8000', email.body)
        self.assertIn('verify-email', email.body)

    def test_verify_email_success(self):
        """Phase 5.2: Verifying email activates the account, logs the user in, and redirects to index."""
        user = User.objects.create_user(
            username='inactiveuser',
            email='inactive@example.com',
            password='TestPassword123!',
            is_active=False
        )
        token = default_token_generator.make_token(user)
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

        url = reverse('verify_email', kwargs={'uidb64': uidb64, 'token': token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('index'))

        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_verify_email_invalid_token(self):
        """Phase 5.2: Invalid activation token does not activate user or log them in."""
        user = User.objects.create_user(
            username='inactiveuser2',
            email='inactive2@example.com',
            password='TestPassword123!',
            is_active=False
        )
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        invalid_token = "invalid-token"

        url = reverse('verify_email', kwargs={'uidb64': uidb64, 'token': invalid_token})
        response = self.client.get(url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('index'))

        user.refresh_from_db()
        self.assertFalse(user.is_active)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_password_reset_flow(self):
        """Phase 5.2: Password reset sends email and allows password change."""
        # 1. GET password reset page
        response = self.client.get(reverse('password_reset'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="csrfmiddlewaretoken"')

        csrf_token = response.cookies['csrftoken'].value

        # 2. POST to request password reset
        mail.outbox.clear()
        post_response = self.client.post(
            reverse('password_reset'),
            data={'email': self.existing_user.email},
            HTTP_X_CSRFTOKEN=csrf_token
        )
        self.assertEqual(post_response.status_code, 302)
        self.assertEqual(post_response.url, reverse('password_reset_done'))

        # Check reset email
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn(self.existing_user.email, email.to)
        self.assertIn('127.0.0.1:8000', email.body)

        # 3. Complete reset using token
        token = default_token_generator.make_token(self.existing_user)
        uidb64 = urlsafe_base64_encode(force_bytes(self.existing_user.pk))
        confirm_url = reverse('password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})

        # PasswordResetConfirmView redirects to /set-password/ to prevent token referrer leakage
        confirm_page = self.client.get(confirm_url, follow=True)
        self.assertEqual(confirm_page.status_code, 200)
        csrf_token2 = confirm_page.cookies['csrftoken'].value

        new_password = "BrandNewPassword123!"
        submit_url = confirm_page.redirect_chain[0][0] if confirm_page.redirect_chain else confirm_url
        submit_response = self.client.post(
            submit_url,
            data={
                'new_password1': new_password,
                'new_password2': new_password,
            },
            HTTP_X_CSRFTOKEN=csrf_token2
        )
        self.assertEqual(submit_response.status_code, 302)
        self.assertEqual(submit_response.url, reverse('password_reset_complete'))

        # Verify password was updated
        self.existing_user.refresh_from_db()
        self.assertTrue(self.existing_user.check_password(new_password))

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

    def test_anonymous_cannot_access_logout_action(self):
        """Phase 5.1: Anonymous users cannot access protected logout action."""
        index_res = self.client.get(reverse('index'))
        csrf_token = index_res.cookies['csrftoken'].value

        # Anonymous POST to logout must redirect to login
        response = self.client.post(reverse('logout'), HTTP_X_CSRFTOKEN=csrf_token)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_anonymous_logout_via_get_rejected_with_405(self):
        """Phase 5.1: GET request to logout endpoint is rejected with 405 even when unauthenticated."""
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 405)

    def test_disallowed_http_methods_rejected_on_auth_views(self):
        """Unsupported HTTP methods return 405."""

        register_page = self.client.get(reverse('register'))
        csrf_token = register_page.cookies['csrftoken'].value

        reg_delete = self.client.delete(
            reverse('register'),
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(reg_delete.status_code, 405)

        login_page = self.client.get(reverse('login'))
        csrf_token = login_page.cookies['csrftoken'].value

        login_put = self.client.put(
            reverse('login'),
            HTTP_X_CSRFTOKEN=csrf_token,
        )
        self.assertEqual(login_put.status_code, 405)
