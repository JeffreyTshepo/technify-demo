from django import forms
from .models import Order, OTP
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import re
import phonenumbers
from phonenumbers import NumberParseException


class CheckoutForm(forms.ModelForm):
    PROVINCE_CHOICES = [
        ('', 'Select Province'),
        ('Gauteng', 'Gauteng'),
        ('Western Cape', 'Western Cape'),
        ('KwaZulu-Natal', 'KwaZulu-Natal'),
        ('Eastern Cape', 'Eastern Cape'),
        ('Limpopo', 'Limpopo'),
        ('Mpumalanga', 'Mpumalanga'),
        ('North West', 'North West'),
        ('Free State', 'Free State'),
        ('Northern Cape', 'Northern Cape'),
    ]
    
    PAYMENT_CHOICES = [
        ('card', '💳 Credit/Debit Card (Yoco)'),
        ('payfast', '🏦 PayFast (Coming Soon)'),
        ('eft', '🏧 EFT/Bank Transfer (Coming Soon)'),
    ]
    
    province = forms.ChoiceField(choices=PROVINCE_CHOICES, required=True)
    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'payment-radio'}),
        initial='card',
        required=True
    )
    
    class Meta:
        model = Order
        fields = [
            'full_name', 'email', 'phone', 'alt_phone',
            'address', 'address2', 'city', 'province', 'postal_code',
            'delivery_instructions', 'payment_method'
        ]
        widgets = {
            'delivery_instructions': forms.Textarea(attrs={'rows': 3, 'placeholder': 'e.g., Leave at front door, Ring doorbell twice...'}),
        }


def validate_strong_password(password):
    """
    Validate that password contains:
    - At least 1 uppercase letter
    - At least 1 lowercase letter
    - At least 1 number
    - At least 1 special character
    - Minimum 8 characters
    """
    if len(password) < 8:
        raise ValidationError('Password must be at least 8 characters long.')
    
    if not re.search(r'[A-Z]', password):
        raise ValidationError('Password must contain at least one uppercase letter.')
    
    if not re.search(r'[a-z]', password):
        raise ValidationError('Password must contain at least one lowercase letter.')
    
    if not re.search(r'\d', password):
        raise ValidationError('Password must contain at least one number.')
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        raise ValidationError('Password must contain at least one special character (!@#$%^&*(),.?":{}|<>).')
    
    return password


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=100, 
        required=True, 
        widget=forms.TextInput(attrs={'placeholder': 'First Name', 'class': 'form-input'})
    )
    last_name = forms.CharField(
        max_length=100, 
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Last Name', 'class': 'form-input'})
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Email Address (must be real)', 'class': 'form-input'}),
        help_text='Must be a valid, existing email address'
    )
    phone = forms.CharField(
        max_length=20,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Phone Number (e.g., 0821234567)', 'class': 'form-input'}),
        help_text='Enter a valid South African phone number'
    )
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-input'}),
        help_text='Must contain: 1 uppercase, 1 lowercase, 1 number, 1 special character (min 8 chars)'
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password', 'class': 'form-input'})
    )
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name', 'phone', 'password1', 'password2']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            raise ValidationError('This email address is already registered.')
        
        # Basic email format validation (Django does this, but we add extra checks)
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValidationError('Please enter a valid email address.')
        
        # Check for common fake email patterns
        fake_domains = ['test.com', 'example.com', 'fake.com', 'dummy.com', 'tempmail.com']
        domain = email.split('@')[1].lower()
        if domain in fake_domains:
            raise ValidationError('Please use a real email address. Fake emails are not allowed.')
        
        return email
    
    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        
        try:
            # Parse phone number (assume South African if no country code)
            if not phone.startswith('+'):
                phone_parsed = phonenumbers.parse(phone, 'ZA')
            else:
                phone_parsed = phonenumbers.parse(phone, None)
            
            # Validate phone number
            if not phonenumbers.is_valid_number(phone_parsed):
                raise ValidationError('Please enter a valid phone number.')
            
            # Check if it's a possible number
            if not phonenumbers.is_possible_number(phone_parsed):
                raise ValidationError('This phone number format is not valid.')
            
            # Format the phone number consistently
            formatted_phone = phonenumbers.format_number(phone_parsed, phonenumbers.PhoneNumberFormat.E164)
            
            return formatted_phone
            
        except NumberParseException:
            raise ValidationError('Please enter a valid phone number (e.g., 0821234567).')
    
    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        return validate_strong_password(password1)
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']  # Use email as username
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        # Ensure signup users are customers only (not staff or admin)
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
            # Save phone number to profile
            user.profile.phone = self.cleaned_data['phone']
            user.profile.save()
        return user


class EmailLoginForm(forms.Form):
    """Simplified login form that uses email"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Email Address', 'class': 'form-input', 'autofocus': True})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Password', 'class': 'form-input'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = None
    
    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')
        
        if email and password:
            from django.contrib.auth import authenticate
            
            # Find user by email
            try:
                user_obj = User.objects.get(email=email)
                
                # Block staff/admin from customer login
                if user_obj.is_staff or user_obj.is_superuser:
                    raise ValidationError('Invalid email or password.')
                
                # Try authentication - check password
                if user_obj.check_password(password):
                    self.user = user_obj
                else:
                    raise ValidationError('Invalid email or password.')
                    
            except User.DoesNotExist:
                raise ValidationError('Invalid email or password.')
        
        return self.cleaned_data
    
    def get_user(self):
        return self.user


class PasswordResetRequestForm(forms.Form):
    """Form for requesting password reset OTP"""
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Enter your email address', 'class': 'form-input', 'autofocus': True})
    )
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        try:
            User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValidationError('No account found with this email address.')
        return email


class PasswordResetVerifyForm(forms.Form):
    """Form for verifying OTP code"""
    otp_code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter 6-digit OTP',
            'class': 'form-input',
            'autofocus': True,
            'pattern': '[0-9]{6}',
            'inputmode': 'numeric'
        })
    )
    
    def __init__(self, *args, email=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.email = email
    
    def clean_otp_code(self):
        otp_code = self.cleaned_data.get('otp_code')
        
        if not otp_code.isdigit():
            raise ValidationError('OTP must contain only numbers.')
        
        if self.email:
            otp = OTP.verify_otp(self.email, otp_code, purpose='password_reset')
            if not otp:
                raise ValidationError('Invalid or expired OTP. Please request a new one.')
        
        return otp_code


class PasswordResetConfirmForm(forms.Form):
    """Form for setting new password"""
    password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={'placeholder': 'New Password', 'class': 'form-input'}),
        help_text='Must contain: 1 uppercase, 1 lowercase, 1 number, 1 special character (min 8 chars)'
    )
    password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm New Password', 'class': 'form-input'})
    )
    
    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        return validate_strong_password(password1)
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError('Passwords do not match.')
        
        return cleaned_data
