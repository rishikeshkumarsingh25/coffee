from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.utils import timezone


class UserManager(BaseUserManager):

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)

        user = self.model(
            email=email,
            **extra_fields
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        return self.create_user(
            email,
            password,
            **extra_fields
        )


class User(AbstractUser):
    username = None
    email = models.CharField(max_length=254, unique=True, verbose_name="Email or Username")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.email


class SignupOTP(models.Model):
    email = models.EmailField(blank=True, default='')
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expiry_at = models.DateTimeField(default=timezone.now)

    def is_valid(self):
        return timezone.now() <= self.expiry_at

    def __str__(self):
        return f"{self.email} - {self.otp}" if self.email else self.otp


class Contact(models.Model):
    name = models.CharField(max_length=50)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField(max_length=500)

    class Meta:
        ordering = ['-id']

    def __str__(self):
        return f"{self.name} - {self.subject}"


class Reserv(models.Model):
    name = models.CharField(max_length=50)
    email = models.EmailField()
    date = models.DateField()
    time = models.TimeField()
    person = models.PositiveIntegerField()

    class Meta:
        ordering = ['-date', '-time']

    def __str__(self):
        return f"{self.name} ({self.date} at {self.time})"


class Product(models.Model):
    CATEGORY_CHOICES = [
        ('Hot Coffee', 'Hot Coffee'),
        ('Cold Coffee', 'Cold Coffee'),
    ]

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50, default='Hot Coffee')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)

    class Meta:
        ordering = ['-id']

    @property
    def image_url(self):
        if self.image:
            try:
                return self.image.url
            except ValueError:
                pass
        return '/static/img/menu-1.jpg'

    def __str__(self):
        return f"{self.name} (₹{self.price})"
