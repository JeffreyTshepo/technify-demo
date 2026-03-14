from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta
import random
import string

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone = models.CharField(max_length=20, blank=True)
    email_verified = models.BooleanField(default=False)
    phone_verified = models.BooleanField(default=False)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)
    postal_code = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

# Auto-create profile when user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


class OTP(models.Model):
    """OTP model for password recovery and verification"""
    email = models.EmailField()
    otp_code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=50, choices=[
        ('password_reset', 'Password Reset'),
        ('email_verification', 'Email Verification'),
    ])
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    def __str__(self):
        return f"OTP for {self.email} - {self.purpose}"
    
    def is_valid(self):
        """Check if OTP is valid (not expired and not used)"""
        return not self.is_used and timezone.now() < self.expires_at
    
    @classmethod
    def generate_otp(cls, email, purpose='password_reset', expiry_minutes=10):
        """Generate a new OTP code"""
        # Generate 6-digit OTP
        otp_code = ''.join(random.choices(string.digits, k=6))
        
        # Delete any existing unused OTPs for this email and purpose
        cls.objects.filter(email=email, purpose=purpose, is_used=False).delete()
        
        # Create new OTP
        otp = cls.objects.create(
            email=email,
            otp_code=otp_code,
            purpose=purpose,
            expires_at=timezone.now() + timedelta(minutes=expiry_minutes)
        )
        return otp
    
    @classmethod
    def verify_otp(cls, email, otp_code, purpose='password_reset'):
        """Verify an OTP code"""
        try:
            otp = cls.objects.get(
                email=email,
                otp_code=otp_code,
                purpose=purpose,
                is_used=False
            )
            if otp.is_valid():
                return otp
            return None
        except cls.DoesNotExist:
            return None


class Category(models.Model):
    STORE_MODES = [
        ('electronics', 'Electronics'),
        ('gaming', 'Gaming'),
    ]
    
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    store_mode = models.CharField(max_length=20, choices=STORE_MODES)
    
    class Meta:
        verbose_name_plural = 'Categories'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.name} ({self.store_mode})"


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    features = models.TextField(blank=True, help_text="Enter features separated by commas")
    in_stock = models.BooleanField(default=True)
    
    image1 = models.ImageField(upload_to='products/', blank=True, null=True)
    image2 = models.ImageField(upload_to='products/', blank=True, null=True)
    image3 = models.ImageField(upload_to='products/', blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_features_list(self):
        if self.features:
            return [f.strip() for f in self.features.split(',')]
        return []
    
    def get_images(self):
        images = []
        if self.image1:
            images.append(self.image1.url)
        if self.image2:
            images.append(self.image2.url)
        if self.image3:
            images.append(self.image3.url)
        return images if images else ['/static/images/placeholder.jpg']


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]
    
    PAYMENT_METHODS = [
        ('card', 'Credit/Debit Card'),
        ('paypal', 'PayPal'),
        ('eft', 'EFT/Bank Transfer'),
    ]
    
    order_number = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    full_name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    alt_phone = models.CharField(max_length=20, blank=True)
    
    address = models.TextField()
    address2 = models.TextField(blank=True)
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)
    country = models.CharField(max_length=100, default='South Africa')
    delivery_instructions = models.TextField(blank=True)
    
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)
    delivery_fee = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order {self.order_number}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    @property
    def total(self):
        return self.quantity * self.price
    
    def __str__(self):
        return f"{self.quantity}x {self.product.name}"
