from django import forms
from django.utils import timezone
from datetime import datetime, date
from .models import Product, Reserv, Contact, User


class ProductForm(forms.ModelForm):
    category = forms.ChoiceField(
        choices=Product.CATEGORY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Product
        fields = ['name', 'category', 'price', 'description', 'image']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product Name'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Price (₹)', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Description', 'rows': 4}),
            'image': forms.FileInput(attrs={'class': 'form-control-file'}),
        }

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise forms.ValidationError("Price must be greater than zero.")
        return price


class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reserv
        fields = ['name', 'email', 'date', 'time', 'person']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control p-4', 'placeholder': 'Your Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control p-4', 'placeholder': 'Your Email'}),
            'date': forms.DateInput(attrs={'class': 'form-control p-4 datetimepicker-input', 'placeholder': 'YYYY-MM-DD', 'type': 'date'}),
            'time': forms.TimeInput(attrs={'class': 'form-control p-4 datetimepicker-input', 'placeholder': 'HH:MM', 'type': 'time'}),
            'person': forms.NumberInput(attrs={'class': 'form-control p-4', 'placeholder': 'Number of Guests', 'min': '1', 'max': '50'}),
        }

    def clean_date(self):
        res_date = self.cleaned_data.get('date')
        if res_date and res_date < date.today():
            raise forms.ValidationError("Reservation date cannot be in the past.")
        return res_date

    def clean_person(self):
        person = self.cleaned_data.get('person')
        if person is not None and person < 1:
            raise forms.ValidationError("Number of persons must be at least 1.")
        return person


class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields = ['name', 'email', 'subject', 'message']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control p-4', 'placeholder': 'Your Name', 'required': True}),
            'email': forms.EmailInput(attrs={'class': 'form-control p-4', 'placeholder': 'Your Email', 'required': True}),
            'subject': forms.TextInput(attrs={'class': 'form-control p-4', 'placeholder': 'Subject', 'required': True}),
            'message': forms.Textarea(attrs={'class': 'form-control py-3 px-4', 'placeholder': 'Message', 'rows': 5, 'required': True}),
        }


class SignupForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password (min 6 characters)'}),
        min_length=6
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'})
    )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your email'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter your password'})
    )


class AdminLoginForm(forms.Form):
    username_or_email = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Admin Username or Email',
            'autocomplete': 'username',
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Admin Password',
            'autocomplete': 'current-password',
        })
    )


class OTPVerifyForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={'class': 'form-control text-center', 'placeholder': '6-digit OTP', 'autocomplete': 'one-time-code'})
    )


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter your registered email'})
    )


class ResetPasswordForm(forms.Form):
    otp = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={'class': 'form-control text-center', 'placeholder': '6-digit OTP'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'New Password (min 6 characters)'}),
        min_length=6
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm New Password'})
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data


class CreateAdminForm(forms.Form):
    """Form to create a new administrator account directly from the admin dashboard."""
    ROLE_CHOICES = [
        ('superuser', 'Superadmin (Full system access & user management)'),
        ('staff', 'Staff Admin (Dashboard & store management access)'),
    ]

    username_or_email = forms.CharField(
        max_length=254,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Admin Username or Email (e.g. admin2, manager, or admin@koppee.com)',
            'autocomplete': 'off',
            'required': True,
        }),
        help_text="Valid email format is NOT required. You can enter any username or email.",
    )
    first_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name (optional)',
        })
    )
    last_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name (optional)',
        })
    )
    role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        initial='superuser',
        widget=forms.Select(attrs={'class': 'custom-select custom-select-lg'})
    )
    password = forms.CharField(
        min_length=6,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Password (min 6 characters)',
            'autocomplete': 'new-password',
            'required': True,
        })
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Confirm Password',
            'autocomplete': 'new-password',
            'required': True,
        })
    )
    is_active = forms.BooleanField(
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'custom-control-input'})
    )

    def clean_username_or_email(self):
        val = self.cleaned_data.get('username_or_email', '').strip()
        if not val:
            raise forms.ValidationError("Admin username or email is required.")
        if User.objects.filter(email__iexact=val).exists():
            raise forms.ValidationError(f"An account with username/email '{val}' already exists.")
        return val

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password')
        p2 = cleaned_data.get('confirm_password')
        if p1 and p2 and p1 != p2:
            self.add_error('confirm_password', "Passwords do not match.")
        return cleaned_data
