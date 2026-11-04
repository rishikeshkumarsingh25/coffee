from datetime import date, timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from .models import Product, Reserv, Contact, SignupOTP
from .forms import ProductForm, ReservationForm, SignupForm

User = get_user_model()


class ModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="testuser@example.com",
            password="testpassword123"
        )
        self.product = Product.objects.create(
            name="Espresso",
            category="Hot Coffee",
            price=150.00,
            description="Rich dark espresso"
        )
        self.reservation = Reserv.objects.create(
            name="Rishi",
            email="rishi@example.com",
            date=date.today() + timedelta(days=2),
            time="18:30:00",
            person=4
        )
        self.contact = Contact.objects.create(
            name="John Doe",
            email="john@example.com",
            subject="Catering Inquiry",
            message="Do you cater for events?"
        )
        self.otp = SignupOTP.objects.create(
            email="otp@example.com",
            otp="123456",
            expiry_at=timezone.now() + timedelta(minutes=10)
        )

    def test_user_creation(self):
        self.assertEqual(self.user.email, "testuser@example.com")
        self.assertTrue(self.user.check_password("testpassword123"))
        self.assertEqual(str(self.user), "testuser@example.com")

    def test_product_fallback_image(self):
        self.assertEqual(self.product.image_url, "/static/img/menu-1.jpg")
        self.assertIn("Espresso", str(self.product))

    def test_reservation_str(self):
        self.assertIn("Rishi", str(self.reservation))

    def test_contact_str(self):
        self.assertIn("Catering Inquiry", str(self.contact))

    def test_otp_validity(self):
        self.assertTrue(self.otp.is_valid())
        self.otp.expiry_at = timezone.now() - timedelta(minutes=1)
        self.assertFalse(self.otp.is_valid())


class ViewAccessTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            email="customer@example.com",
            password="customerpassword123"
        )
        self.staff_user = User.objects.create_superuser(
            email="admin@example.com",
            password="adminpassword123"
        )

    def test_public_pages_status_codes(self):
        for route_name in ['home', 'about', 'service', 'menu', 'testimonial', 'login', 'admin_login', 'signup']:
            response = self.client.get(reverse(route_name))
            self.assertEqual(response.status_code, 200)

    def test_reservation_requires_login(self):
        response = self.client.get(reverse('reservation'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_dashboard_strict_admin_protection(self):
        # 1. Anonymous user redirected to Admin Login
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin_login'), response.url)

        # 2. Authenticated Customer user is strictly DENIED and redirected to home
        self.client.login(username="customer@example.com", password="customerpassword123")
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'))

        # Also check customer blocked from products management
        response = self.client.get(reverse('product_list'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'))
        self.client.logout()

        # 3. Staff user granted access (200 OK)
        self.client.login(username="admin@example.com", password="adminpassword123")
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(reverse('dashboard'), '/admin/')

        # Both /admin/ and /dashboard/ load the dashboard directly
        self.assertEqual(self.client.get('/admin/').status_code, 200)
        self.assertEqual(self.client.get('/dashboard/').status_code, 200)

    def test_product_list_requires_staff(self):
        response = self.client.get(reverse('product_list'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin_login'), response.url)

        self.client.login(username="admin@example.com", password="adminpassword123")
        response = self.client.get(reverse('product_list'))
        self.assertEqual(response.status_code, 200)

    def test_custom_admin_toggle_user_status(self):
        self.client.login(username="admin@example.com", password="adminpassword123")
        self.assertTrue(self.user.is_active)
        response = self.client.post(reverse('toggle_user_status', args=[self.user.pk]))
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_custom_admin_delete_user(self):
        self.client.login(username="admin@example.com", password="adminpassword123")
        response = self.client.post(reverse('delete_user', args=[self.user.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(User.objects.filter(pk=self.user.pk).exists())

    def test_admin_direct_login_no_otp(self):
        # Admin logs in via admin_login without OTP using email
        response = self.client.post(reverse('admin_login'), {
            'username_or_email': 'admin@example.com',
            'password': 'adminpassword123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))

    def test_admin_direct_login_with_username_prefix(self):
        # Admin logs in via admin_login typing "admin"
        response = self.client.post(reverse('admin_login'), {
            'username_or_email': 'admin',
            'password': 'adminpassword123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))

    def test_admin_login_with_non_email_username(self):
        # Admin user with plain username (not a valid email format, e.g. 'superboss')
        User.objects.create_superuser(
            email='superboss',
            password='secretpassword'
        )
        response = self.client.post(reverse('admin_login'), {
            'username_or_email': 'superboss',
            'password': 'secretpassword'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('dashboard'))

    def test_customer_cannot_login_through_admin_portal(self):
        # Customer attempts to use admin login portal
        response = self.client.post(reverse('admin_login'), {
            'username_or_email': 'customer@example.com',
            'password': 'customerpassword123'
        })
        # Stays on admin login page with error (200), not logged in to dashboard
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Access Denied")

    def test_customer_signup_requires_otp(self):
        # Customer signup creates inactive user and sends OTP
        response = self.client.post(reverse('signup'), {
            'email': 'newcustomer@example.com',
            'password': 'customerpass123',
            'confirm_password': 'customerpass123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('verify_otp'))

        created = User.objects.filter(email='newcustomer@example.com').first()
        self.assertIsNotNone(created)
        self.assertFalse(created.is_active)
        self.assertFalse(created.is_staff)

        # OTP is created for customer
        otp_obj = SignupOTP.objects.filter(email='newcustomer@example.com').first()
        self.assertIsNotNone(otp_obj)

        # Verify OTP activates user and logs them in
        session = self.client.session
        session['signup_email'] = 'newcustomer@example.com'
        session.save()

        verify_response = self.client.post(reverse('verify_otp'), {
            'otp': otp_obj.otp
        })
        self.assertEqual(verify_response.status_code, 302)
        self.assertRedirects(verify_response, reverse('home'))

        created.refresh_from_db()
        self.assertTrue(created.is_active)

    def test_resend_otp_generates_new_otp(self):
        session = self.client.session
        session['signup_email'] = 'resendcustomer@example.com'
        session.save()

        SignupOTP.objects.create(
            email='resendcustomer@example.com',
            otp='111111',
            expiry_at=timezone.now() + timedelta(minutes=10)
        )

        response = self.client.post(reverse('resend_otp'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('verify_otp'))

        # Check new OTP created
        new_otp = SignupOTP.objects.filter(email='resendcustomer@example.com').first()
        self.assertIsNotNone(new_otp)
        self.assertNotEqual(new_otp.otp, '111111')

    def test_customer_subsequent_login_no_otp_needed(self):
        # Once registered/active, customer logs in with just email and password
        response = self.client.post(reverse('login'), {
            'email': 'customer@example.com',
            'password': 'customerpassword123'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'))


class FormValidationTestCase(TestCase):
    def test_product_form_invalid_negative_price(self):
        form = ProductForm(data={
            'name': 'Cold Brew',
            'category': 'Cold Coffee',
            'price': -50.00,
            'description': 'Smooth cold brew'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('price', form.errors)

    def test_reservation_form_invalid_past_date(self):
        form = ReservationForm(data={
            'name': 'Alice',
            'email': 'alice@example.com',
            'date': date.today() - timedelta(days=1),
            'time': '14:00',
            'person': 2
        })
        self.assertFalse(form.is_valid())
        self.assertIn('date', form.errors)

    def test_signup_form_mismatched_passwords(self):
        form = SignupForm(data={
            'email': 'newuser@example.com',
            'password': 'password123',
            'confirm_password': 'mismatchpassword'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('confirm_password', form.errors)


class CreateAdminTestCase(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            email='masteradmin',
            password='masterpassword123'
        )
        self.customer = User.objects.create_user(
            email='regular@example.com',
            password='customerpass123'
        )

    def test_anonymous_redirected_from_create_admin(self):
        response = self.client.get(reverse('create_admin'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin-login/', response.url)

    def test_customer_strictly_blocked_from_create_admin(self):
        self.client.login(username='regular@example.com', password='customerpass123')
        response = self.client.get(reverse('create_admin'))
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('home'))

    def test_admin_can_access_create_admin_page(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('create_admin'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'New Administrator Details')
        self.assertContains(response, 'Create Administrator')

    def test_admin_can_create_new_admin_and_new_admin_can_login(self):
        self.client.force_login(self.admin)
        response = self.client.post(reverse('create_admin'), {
            'username_or_email': 'manager_alex',
            'role': 'superuser',
            'first_name': 'Alex',
            'last_name': 'Smith',
            'password': 'alexsecurepass123',
            'confirm_password': 'alexsecurepass123',
            'is_active': 'on'
        })
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('users_page'))

        # Check DB record
        new_admin = User.objects.get(email='manager_alex')
        self.assertTrue(new_admin.is_staff)
        self.assertTrue(new_admin.is_superuser)
        self.assertTrue(new_admin.is_active)
        self.assertEqual(new_admin.first_name, 'Alex')

        # Now test that the newly created admin can log in directly at admin_login without OTP
        self.client.logout()
        login_resp = self.client.post(reverse('admin_login'), {
            'username_or_email': 'manager_alex',
            'password': 'alexsecurepass123'
        })
        self.assertEqual(login_resp.status_code, 302)
        self.assertRedirects(login_resp, reverse('dashboard'))
