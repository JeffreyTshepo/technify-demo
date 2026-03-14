"""
Rate limiting decorators for protecting authentication endpoints
"""
from django_ratelimit.decorators import ratelimit
from django.http import HttpResponse


def rate_limit_login(func):
    """Rate limit for login attempts: 5 per minute per IP"""
    return ratelimit(key='ip', rate='5/m', method='POST', block=True)(func)


def rate_limit_signup(func):
    """Rate limit for signup attempts: 3 per hour per IP"""
    return ratelimit(key='ip', rate='3/h', method='POST', block=True)(func)


def rate_limit_password_reset(func):
    """Rate limit for password reset requests: 3 per hour per IP"""
    return ratelimit(key='ip', rate='3/h', method='POST', block=True)(func)


def rate_limit_otp(func):
    """Rate limit for OTP verification: 10 per 15 minutes per IP"""
    return ratelimit(key='ip', rate='10/15m', method='POST', block=True)(func)


def rate_limit_api(func):
    """Rate limit for API endpoints: 60 per minute per IP"""
    return ratelimit(key='ip', rate='60/m', method=['GET', 'POST'], block=True)(func)
