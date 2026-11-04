import logging
import random
from datetime import datetime, date, timedelta
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods

from .models import Product, Contact, Reserv, SignupOTP
from .forms import (
    ProductForm,
    ReservationForm,
    ContactForm,
    SignupForm,
    LoginForm,
    AdminLoginForm,
    CreateAdminForm,
    OTPVerifyForm,
    ForgotPasswordForm,
    ResetPasswordForm,
)

User = get_user_model()
logger = logging.getLogger(__name__)


def _handle_email_error(request, error, otp, action="verification"):
    """Format a clear diagnostic warning when SMTP fails to deliver email."""
    logger.error(f"[Email Error] Could not send {action} email: {error}")
    err_str = str(error)
    if any(k in err_str for k in ("535", "BadCredentials", "Username and Password not accepted", "SMTPServerDisconnected")):
        messages.warning(
            request,
            f"Gmail SMTP Error: Google ne password reject kar diya (BadCredentials). "
            f"Aapka naya 16-character App Password .env file me set nahi hai. (OTP: {otp})"
        )
    else:
        messages.warning(request, f"Could not send email automatically ({error}). OTP: {otp}")


# ==============================================================================
# Security Decorator: Strict Admin Access Control
# ==============================================================================

def admin_required(view_func):
    """
    Strict security decorator:
    1. If user is not authenticated: Redirect to admin login (/admin-login/) with ?next=.
    2. If user is authenticated but NOT staff/superuser: Block access completely,
       display an explicit security warning, and redirect to 'home'.
       Customer accounts can NEVER open the dashboard.
    3. If user is staff/superuser: Allow access.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Administrator login required to access the Admin Panel.")
            return redirect(f"{reverse('admin_login')}?next={request.path}")
        if not (request.user.is_staff or request.user.is_superuser):
            messages.error(
                request,
                "Access Denied: Only administrators can access the Dashboard. Customer accounts are strictly prohibited."
            )
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


# ==============================================================================
# Public Customer Views
# ==============================================================================

def home(request):
    """Homepage showing hero, about snippet, featured services and products."""
    products = Product.objects.all().order_by('-id')
    return render(request, 'index.html', {'products': products})


def about(request):
    """About us page."""
    output = request.GET.get('output')
    return render(request, 'about.html', {'output': output})


def menu(request):
    """Menu page listing all available hot and cold coffee items."""
    products = Product.objects.all().order_by('-id')
    return render(request, 'menu.html', {'products': products})


def service(request):
    """Services showcase page."""
    return render(request, 'service.html')


def testimonial(request):
    """Customer testimonials page."""
    return render(request, 'testimonial.html')


@login_required(login_url="login")
def reservation(request):
    """Table reservation view for authenticated customers."""
    if request.method == "POST":
        form = ReservationForm(request.POST)
        if form.is_valid():
            res_date = form.cleaned_data['date']
            res_time = form.cleaned_data['time']

            # Duplicate slot check
            if Reserv.objects.filter(date=res_date, time=res_time).exists():
                messages.error(request, "This date and time slot is already fully booked. Please choose another time.")
                return render(request, "reservation.html", {"form": form})

            instance = form.save()
            messages.success(request, f"Table reserved successfully for {instance.date} at {instance.time}!")

            # Send confirmation email
            try:
                send_mail(
                    subject="KOPPEE - Reservation Confirmation",
                    message=(
                        f"Dear {instance.name},\n\n"
                        f"Your table reservation at KOPPEE has been confirmed!\n\n"
                        f"Details:\n"
                        f"- Date: {instance.date}\n"
                        f"- Time: {instance.time}\n"
                        f"- Guests: {instance.person}\n\n"
                        f"Thank you for choosing KOPPEE Coffee Shop!"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[instance.email, settings.DEFAULT_FROM_EMAIL],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"[Email Error] Could not send reservation email: {e}")

            return redirect("reservation")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
            return render(request, "reservation.html", {"form": form})

    form = ReservationForm()
    return render(request, "reservation.html", {"form": form})


@login_required(login_url="login")
def contact(request):
    """Customer contact inquiry form."""
    success = ""
    if request.method == "POST":
        form = ContactForm(request.POST)
        if form.is_valid():
            item = form.save()
            messages.success(request, "Your message has been sent successfully. We will contact you soon!")
            success = "Your message has been sent successfully."

            try:
                send_mail(
                    subject=f"New Contact Inquiry: {item.subject}",
                    message=(
                        f"New message received from customer:\n\n"
                        f"Name: {item.name}\n"
                        f"Email: {item.email}\n"
                        f"Subject: {item.subject}\n\n"
                        f"Message:\n{item.message}"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.DEFAULT_FROM_EMAIL],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"[Email Error] Could not send contact email: {e}")

            return redirect("contact")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field.title()}: {error}")
    else:
        form = ContactForm()

    return render(request, "contact.html", {"success": success, "form": form})


# ==============================================================================
# Customer Authentication Views (Login, Signup, OTP Verification)
# ==============================================================================

def login_view(request):
    """
    Customer Login View:
    - Dedicated for customer sign in using Email & Password.
    - If account is unverified, resends verification OTP and redirects to verify_otp.
    - Once registered & verified, customers login with just Email & Password (no OTP).
    """
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('dashboard')
        return redirect('home')

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")

        if not email or not password:
            messages.error(request, "Please enter both your email address and password.")
            return render(request, 'login.html')

        user = authenticate(request, username=email, password=password)

        if user is None:
            # Check if this user exists with inactive status (unverified signup)
            candidate = User.objects.filter(email__iexact=email).first()
            if candidate and candidate.check_password(password):
                if not candidate.is_active:
                    # Resend OTP for unverified customer
                    otp = str(random.randint(100000, 999999))
                    request.session["signup_email"] = candidate.email
                    SignupOTP.objects.filter(email=candidate.email).delete()
                    SignupOTP.objects.create(
                        email=candidate.email,
                        otp=otp,
                        expiry_at=timezone.now() + timedelta(minutes=10)
                    )
                    try:
                        send_mail(
                            subject="KOPPEE - Email Verification Code",
                            message=(
                                f"Hello,\n\n"
                                f"Please verify your email to activate your KOPPEE customer account.\n"
                                f"Your verification OTP is: {otp}\n\n"
                                f"Valid for 10 minutes."
                            ),
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            recipient_list=[candidate.email],
                            fail_silently=True,
                        )
                    except Exception as e:
                        print(f"[Email Error] Could not send OTP: {e}")

                    messages.info(request, f"Your account is not verified yet. A verification code has been sent to {candidate.email}. Please verify to activate.")
                    return redirect("verify_otp")
                else:
                    user = candidate

        if user is not None:
            if not user.is_active:
                messages.error(request, "Your account is not active. Please complete email verification or contact support.")
                return render(request, 'login.html')

            login(request, user)

            # If an admin logged in through customer login, redirect to dashboard
            if user.is_staff or user.is_superuser:
                messages.info(request, f"Administrator account '{user.email}' detected. Redirecting to Admin Dashboard.")
                return redirect('dashboard')

            messages.success(request, f"Welcome back, {user.email}!")

            next_url = request.GET.get('next')
            if next_url:
                if (next_url.startswith('/dashboard') or next_url.startswith('/products') or next_url.startswith('/admin-login') or next_url.startswith('/admin')) and not user.is_staff:
                    messages.warning(request, "Dashboard access is restricted to Administrator accounts. Redirected to home.")
                    return redirect('home')
                return redirect(next_url)

            return redirect('home')

        messages.error(request, "Invalid customer email or password. Please check your credentials or create a new account.")

    return render(request, 'login.html')


def user_logout(request):
    """Customer logout view."""
    logout(request)
    messages.info(request, "You have been logged out successfully.")
    return redirect("login")


def signup(request):
    """
    Customer Registration View:
    - New customer enters email and password.
    - Sends a 6-digit OTP to customer's email.
    - Stores unverified inactive account.
    - Redirects to verify_otp for email verification.
    """
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password")

        if not email or not password:
            messages.error(request, "Please enter both email and password.")
            return render(request, "signup.html")

        if confirm_password and password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "signup.html")

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
            return render(request, "signup.html")

        existing_user = User.objects.filter(email=email).first()
        if existing_user and existing_user.is_active:
            messages.error(request, "This email is already registered and verified. Please sign in.")
            return redirect("login")

        # Create or update inactive customer user
        if existing_user:
            existing_user.set_password(password)
            existing_user.is_active = False
            existing_user.is_staff = False
            existing_user.is_superuser = False
            existing_user.save()
        else:
            User.objects.create_user(
                email=email,
                password=password,
                is_active=False,
                is_staff=False,
                is_superuser=False
            )

        # Generate OTP
        otp = str(random.randint(100000, 999999))
        request.session["signup_email"] = email

        SignupOTP.objects.filter(email=email).delete()
        SignupOTP.objects.create(
            email=email,
            otp=otp,
            expiry_at=timezone.now() + timedelta(minutes=10)
        )

        try:
            send_mail(
                subject="KOPPEE - Signup OTP Verification",
                message=(
                    f"Welcome to KOPPEE Coffee Shop!\n\n"
                    f"Your registration verification code is: {otp}\n\n"
                    f"This code will expire in 10 minutes. Do not share this code with anyone.\n"
                    f"Once verified, your account will be activated and you can log in directly with your email and password."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            messages.success(request, f"Verification OTP sent to {email}. Please check your inbox.")
        except Exception as e:
            _handle_email_error(request, e, otp, "signup verification")

        return redirect("verify_otp")

    return render(request, "signup.html")


def verify_otp(request):
    """
    Verify customer registration OTP:
    - Verifies 6-digit OTP sent to customer's email.
    - Activates account (is_active=True).
    - Logs user in.
    - After this registration, customer logs in with just email & password!
    """
    email = request.session.get("signup_email")
    if not email:
        messages.error(request, "Verification session expired. Please sign up or request a code again.")
        return redirect("signup")

    if request.method == "POST":
        otp = request.POST.get("otp", "").strip()

        # Find OTP for this specific email
        otp_record = SignupOTP.objects.filter(email=email, otp=otp).order_by('-created_at').first()
        if not otp_record:
            otp_record = SignupOTP.objects.filter(otp=otp).order_by('-created_at').first()

        if not otp_record:
            messages.error(request, "Invalid OTP code. Please check and try again.")
            return render(request, "verify_otp.html", {"email": email})

        if not otp_record.is_valid():
            otp_record.delete()
            messages.error(request, "This OTP has expired. Please sign up again to receive a fresh code.")
            return redirect("signup")

        # Activate user
        user = User.objects.filter(email=email).first()
        if user:
            user.is_active = True
            user.save()
            login(request, user)
            otp_record.delete()
            request.session.pop("signup_email", None)
            messages.success(
                request,
                "Account verified and registered successfully! You can now log in anytime with just your email and password."
            )
            return redirect("home")
        else:
            messages.error(request, "User account not found. Please sign up again.")
            return redirect("signup")

    return render(request, "verify_otp.html", {"email": email})


def resend_otp(request):
    """
    Resend signup verification OTP to the customer's email.
    """
    email = request.session.get("signup_email")
    if not email:
        email = request.POST.get("email", "").strip().lower()

    if not email:
        messages.error(request, "Verification session expired. Please sign up again.")
        return redirect("signup")

    request.session["signup_email"] = email

    # Generate fresh 6-digit OTP
    otp = str(random.randint(100000, 999999))

    # Replace old OTPs
    SignupOTP.objects.filter(email=email).delete()
    SignupOTP.objects.create(
        email=email,
        otp=otp,
        expiry_at=timezone.now() + timedelta(minutes=10)
    )

    try:
        send_mail(
            subject="KOPPEE - Resend OTP Verification",
            message=(
                f"Welcome to KOPPEE Coffee Shop!\n\n"
                f"Your new registration verification code is: {otp}\n\n"
                f"This code will expire in 10 minutes.\n"
                f"Do not share this code with anyone."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        messages.success(request, f"A new verification OTP has been sent to {email}. Please check your inbox.")
    except Exception as e:
        _handle_email_error(request, e, otp, "resend OTP")

    return redirect("verify_otp")


# ==============================================================================
# Admin Authentication Views (Direct - No OTP Verification)
# ==============================================================================

def admin_login_view(request):
    """
    Dedicated Admin Login View:
    - Direct sign-in using ANY username or email and password.
    - Valid email format is NOT required (e.g. 'admin', 'root', 'superadmin', 'manager', or any custom text).
    - NO email verification and NO OTP required.
    - Strictly reserved for administrators: customer accounts are rejected.
    - Upon successful authentication, redirects to /dashboard/.
    """
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('dashboard')
        messages.warning(
            request,
            "You are currently logged in as a Customer. Please sign in with an Administrator account to open the Admin Panel."
        )

    if request.method == "POST":
        identifier = request.POST.get("username_or_email", "").strip()
        password = request.POST.get("password", "")

        if not identifier or not password:
            messages.error(request, "Please enter both admin username/email and password.")
            return render(request, "admin_login.html")

        # 1. Direct authentication using identifier
        user = authenticate(request, username=identifier, password=password)

        # 2. Flexible lookup: Valid email format is NOT required
        if user is None:
            # Check exact match
            candidate = User.objects.filter(email__iexact=identifier).first()

            # If not matched directly, check if identifier matches prefix before @
            if not candidate:
                candidate = User.objects.filter(
                    Q(email__istartswith=f"{identifier}@") |
                    Q(email__iexact=f"{identifier}@koppee.com") |
                    Q(email__iexact=f"{identifier}@example.com") |
                    Q(email__iexact=f"{identifier}@gmail.com")
                ).filter(Q(is_staff=True) | Q(is_superuser=True)).first()

            # If still not found, check all staff/superusers whose password matches
            if not candidate:
                for staff_user in User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)):
                    if staff_user.check_password(password):
                        if (
                            identifier.lower() in ('admin', 'administrator', 'root', 'superadmin', 'manager')
                            or identifier.lower() in staff_user.email.lower()
                            or User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).count() == 1
                        ):
                            candidate = staff_user
                            break

            if candidate and candidate.check_password(password):
                user = candidate

        # 3. Bootstrap default admin if database is completely empty of admins
        if user is None:
            admin_count = User.objects.filter(Q(is_staff=True) | Q(is_superuser=True)).count()
            if admin_count == 0:
                user = User.objects.create_superuser(email=identifier, password=password)
                user.is_active = True
                user.save()
                messages.info(request, f"Default administrator account initialized with username '{user.email}'.")

        # 4. Role validation
        if user is not None:
            # STRICT ROLE CHECK: Customer accounts CANNOT log in through Admin Portal!
            if not (user.is_staff or user.is_superuser):
                messages.error(
                    request,
                    "Access Denied: This account does not have administrator privileges. Customer accounts are strictly prohibited from the Admin Dashboard. Please use the Customer Login."
                )
                return render(request, "admin_login.html")

            # Admin verified: Direct login without email OTP!
            user.is_active = True
            user.save()
            login(request, user)
            messages.success(request, f"Administrator '{user.email}' authenticated successfully. Welcome to KOPPEE Dashboard!")

            next_url = request.GET.get('next')
            if next_url and (next_url.startswith('/dashboard') or next_url.startswith('/products') or next_url.startswith('/admin')):
                return redirect(next_url)
            return redirect('dashboard')

        messages.error(request, "Invalid administrator username/email or password. Please try again.")

    return render(request, "admin_login.html")


def admin_logout(request):
    """Admin logout view - redirects back to Admin Login."""
    logout(request)
    messages.info(request, "You have been signed out from the Administrator Control Panel.")
    return redirect("admin_login")


# ==============================================================================
# Password Recovery Views
# ==============================================================================

def forgot_password(request):
    """Request password reset OTP."""
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        user = User.objects.filter(email=email, is_active=True).first()

        if not user:
            messages.error(request, "No active account found with this email address.")
            return render(request, "forgot_password.html")

        otp = str(random.randint(100000, 999999))
        request.session["reset_email"] = email
        request.session["reset_otp"] = otp
        request.session["reset_time"] = timezone.now().isoformat()

        try:
            send_mail(
                subject="KOPPEE - Password Reset OTP",
                message=(
                    f"Hello,\n\n"
                    f"You requested a password reset for your KOPPEE account.\n"
                    f"Your reset code is: {otp}\n\n"
                    f"This code is valid for 10 minutes. If you did not request this, please ignore."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            messages.success(request, f"Password reset OTP sent to {email}.")
        except Exception as e:
            _handle_email_error(request, e, otp, "password reset")

        return redirect("reset_password")

    return render(request, "forgot_password.html")


def reset_password(request):
    """Reset password using OTP."""
    email = request.session.get("reset_email")
    saved_otp = request.session.get("reset_otp")
    reset_time = request.session.get("reset_time")

    if not email or not saved_otp or not reset_time:
        messages.error(request, "Password reset session expired. Please request OTP again.")
        return redirect("forgot_password")

    if request.method == "POST":
        otp = request.POST.get("otp", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password")

        if otp != saved_otp:
            messages.error(request, "Invalid OTP. Please enter the correct code.")
            return render(request, "reset_password.html", {"email": email})

        if confirm_password and password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "reset_password.html", {"email": email})

        if len(password) < 6:
            messages.error(request, "Password must be at least 6 characters long.")
            return render(request, "reset_password.html", {"email": email})

        if timezone.now() > datetime.fromisoformat(reset_time) + timedelta(minutes=10):
            messages.error(request, "OTP has expired. Please request a new one.")
            return redirect("forgot_password")

        user = User.objects.filter(email=email).first()
        if user:
            user.set_password(password)
            user.save()

            request.session.pop("reset_otp", None)
            request.session.pop("reset_email", None)
            request.session.pop("reset_time", None)

            messages.success(request, "Password reset successfully! Please login with your new password.")
            return redirect("login")
        else:
            messages.error(request, "User account not found.")
            return redirect("forgot_password")

    return render(request, "reset_password.html", {"email": email})


# ==============================================================================
# Admin Dashboard & Management Views (Protected with @admin_required)
# ==============================================================================

@admin_required
def dashboard(request):
    """Admin summary dashboard showing total metrics and recent items."""
    users_count = User.objects.count()
    reservations_count = Reserv.objects.count()
    contacts_count = Contact.objects.count()
    products_count = Product.objects.count()

    recent_reservations = Reserv.objects.all().order_by('-date', '-time')[:5]
    recent_contacts = Contact.objects.all().order_by('-id')[:5]

    return render(request, 'dashboard.html', {
        'users': users_count,
        'reservations': reservations_count,
        'contacts': contacts_count,
        'products': products_count,
        'recent_reservations': recent_reservations,
        'recent_contacts': recent_contacts,
    })


@admin_required
def users_page(request):
    """Admin view for listing all registered users."""
    all_users = User.objects.all().order_by('-date_joined')
    return render(request, 'admin_users.html', {'all_users': all_users})


@admin_required
def create_admin(request):
    """
    Admin view to create a new administrator account (superuser or staff):
    - Valid email format is NOT required (can be any username or email string).
    - No email verification or OTP needed for admin accounts.
    - Directly activated upon creation.
    - Able to sign in immediately via /admin or /admin-login/.
    """
    if request.method == "POST":
        form = CreateAdminForm(request.POST)
        if form.is_valid():
            username_or_email = form.cleaned_data['username_or_email']
            password = form.cleaned_data['password']
            role = form.cleaned_data['role']
            first_name = form.cleaned_data.get('first_name', '')
            last_name = form.cleaned_data.get('last_name', '')
            is_active = form.cleaned_data.get('is_active', True)

            is_superuser = (role == 'superuser')
            is_staff = True

            user = User.objects.create(
                email=username_or_email,
                first_name=first_name,
                last_name=last_name,
                is_staff=is_staff,
                is_superuser=is_superuser,
                is_active=is_active,
            )
            user.set_password(password)
            user.save()

            role_title = "Superadmin" if is_superuser else "Staff Administrator"
            messages.success(
                request,
                f"New {role_title} '{user.email}' created successfully! They can now log in directly at /admin."
            )
            return redirect('users_page')
        else:
            messages.error(request, "Failed to create administrator account. Please check the errors below.")
    else:
        form = CreateAdminForm()

    return render(request, "create_admin.html", {"form": form})


@admin_required
def toggle_user_status(request, pk):
    """Toggle user active status from custom admin."""
    user_obj = get_object_or_404(User, pk=pk)
    if user_obj == request.user:
        messages.error(request, "You cannot deactivate your own admin account.")
        return redirect('users_page')

    user_obj.is_active = not user_obj.is_active
    user_obj.save()
    status_str = "activated" if user_obj.is_active else "deactivated"
    messages.success(request, f"User account '{user_obj.email}' has been {status_str}.")
    return redirect('users_page')


@admin_required
def delete_user(request, pk):
    """Delete a user account from custom admin."""
    user_obj = get_object_or_404(User, pk=pk)
    if user_obj == request.user:
        messages.error(request, "You cannot delete your own admin account.")
        return redirect('users_page')

    email = user_obj.email
    user_obj.delete()
    messages.success(request, f"User account '{email}' deleted successfully.")
    return redirect('users_page')


@admin_required
def reservations_page(request):
    """Admin view for listing all table reservations."""
    all_reservations = Reserv.objects.all().order_by('-date', '-time')
    return render(request, 'admin_reservation.html', {'all_reservations': all_reservations})


@admin_required
def contacts_page(request):
    """Admin view for listing customer inquiries."""
    all_contacts = Contact.objects.all().order_by('-id')
    return render(request, 'admin_contact.html', {'all_contacts': all_contacts})


@admin_required
def view_reservation(request, pk):
    """Admin details view for a reservation."""
    reservation_obj = get_object_or_404(Reserv, pk=pk)
    return render(request, 'view_reservation.html', {'reservation': reservation_obj})


@admin_required
def edit_reservation(request, pk):
    """Admin edit reservation."""
    reservation_obj = get_object_or_404(Reserv, pk=pk)

    if request.method == "POST":
        form = ReservationForm(request.POST, instance=reservation_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Reservation updated successfully.")
            return redirect('reservations_page')
        else:
            messages.error(request, "Please correct the errors in the form.")
    else:
        form = ReservationForm(instance=reservation_obj)

    return render(request, 'edit_reservation.html', {
        'reservation': reservation_obj,
        'form': form
    })


@admin_required
def delete_reservation(request, pk):
    """Admin delete reservation (accepts POST or confirmed GET)."""
    reservation_obj = get_object_or_404(Reserv, pk=pk)
    reservation_obj.delete()
    messages.success(request, "Reservation removed successfully.")
    return redirect('reservations_page')


@admin_required
def view_contact(request, pk):
    """Admin details view for a contact inquiry."""
    contact_obj = get_object_or_404(Contact, pk=pk)
    return render(request, 'view_contact.html', {'contact': contact_obj})


@admin_required
def edit_contact(request, pk):
    """Admin edit contact message."""
    contact_obj = get_object_or_404(Contact, pk=pk)

    if request.method == "POST":
        form = ContactForm(request.POST, instance=contact_obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Contact message updated successfully.")
            return redirect('contacts_page')
    else:
        form = ContactForm(instance=contact_obj)

    return render(request, 'edit_contact.html', {
        'contact': contact_obj,
        'form': form
    })


@admin_required
def delete_contact(request, pk):
    """Admin delete contact message."""
    contact_obj = get_object_or_404(Contact, pk=pk)
    contact_obj.delete()
    messages.success(request, "Contact message deleted successfully.")
    return redirect('contacts_page')


# ==============================================================================
# Admin Product Management Views (Protected with @admin_required)
# ==============================================================================

@admin_required
def product_list(request):
    """Admin list of all products."""
    products = Product.objects.all().order_by('-id')
    return render(request, 'product_list.html', {'products': products})


@admin_required
def add_product(request):
    """Admin add new product."""
    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"Product '{product.name}' added successfully!")
            return redirect("product_list")
        else:
            messages.error(request, "Failed to add product. Please check the form errors.")
    else:
        form = ProductForm()

    return render(request, "add_product.html", {'form': form})


@admin_required
def edit_product(request, pk):
    """Admin edit existing product."""
    product = get_object_or_404(Product, pk=pk)

    if request.method == "POST":
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f"Product '{product.name}' updated successfully!")
            return redirect('product_list')
        else:
            messages.error(request, "Failed to update product. Please check the form errors.")
    else:
        form = ProductForm(instance=product)

    return render(request, 'edit_product.html', {
        'product': product,
        'form': form
    })


@admin_required
def delete_product(request, pk):
    """Admin delete product."""
    product = get_object_or_404(Product, pk=pk)
    name = product.name
    product.delete()
    messages.success(request, f"Product '{name}' deleted successfully.")
    return redirect('product_list')
