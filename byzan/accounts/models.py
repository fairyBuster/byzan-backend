from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.timezone import now


class User(AbstractUser):
    GENDER_CHOICES = [
        ("male", "Male"),
        ("female", "Female"),
    ]

    email = models.EmailField(unique=True)  # Email unik untuk setiap pengguna
    username = models.CharField(
        max_length=30, unique=True
    )  # Username unik untuk setiap pengguna
    full_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=20, blank=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    birthday = models.DateField(null=True, blank=True)
    instagram_link = models.URLField(blank=True)
    facebook_link = models.URLField(blank=True)
    email_verified = models.BooleanField(default=False)

    USERNAME_FIELD = "email"  # Menggunakan email sebagai username
    REQUIRED_FIELDS = ["username"]  # Username tetap wajib diisi

    def __str__(self):
        return self.email


# Create your models here.
