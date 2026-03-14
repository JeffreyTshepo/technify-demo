"""
Security Middleware for Technify
Provides additional security layers beyond Django defaults
"""
import logging
import re
import time
from django.http import HttpResponseForbidden, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.cache import cache
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

logger = logging.getLogger(__name__)


# Track failed login attempts
class LoginAttemptTracker:
    """Track and block suspicious login attempts"""
    
    MAX_ATTEMPTS = 5
    LOCKOUT_DURATION = 900  # 15 minutes
    
    @classmethod
    def get_key(cls, identifier):
        return f"login_attempts:{identifier}"
    
    @classmethod
    def record_attempt(cls, identifier):
        """Record a failed login attempt"""
        key = cls.get_key(identifier)
        attempts = cache.get(key, 0)
        attempts += 1
        cache.set(key, attempts, cls.LOCKOUT_DURATION)
        return attempts
    
    @classmethod
    def is_locked_out(cls, identifier):
        """Check if identifier is locked out"""
        key = cls.get_key(identifier)
        attempts = cache.get(key, 0)
        return attempts >= cls.MAX_ATTEMPTS
    
    @classmethod
    def reset(cls, identifier):
        """Reset login attempts"""
        key = cls.get_key(identifier)
        cache.delete(key)


@receiver(user_logged_in)
def reset_login_attempts(sender, request, user, **kwargs):
    """Reset login attempts on successful login"""
    ip = request.META.get('REMOTE_ADDR')
    LoginAttemptTracker.reset(ip)
    LoginAttemptTracker.reset(user.email)


class SecurityHeadersMiddleware(MiddlewareMixin):
    """Add comprehensive security headers to all responses"""
    
    def process_response(self, request, response):
        # Content Security Policy
        response['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' https://payments.yoco.com https://js.yoco.com https://c.yoco.com; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "connect-src 'self' https://payments.yoco.com https://api.yoco.com https://c.yoco.com; "
            "frame-src https://payments.yoco.com https://c.yoco.com; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self' https://payments.yoco.com https://c.yoco.com; "
            "frame-ancestors 'none'; "
            "upgrade-insecure-requests;"
        )
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy (formerly Feature Policy)
        response['Permissions-Policy'] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(self), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )
        
        # Additional security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        
        return response


class SQLInjectionProtectionMiddleware(MiddlewareMixin):
    """
    Detect and block potential SQL injection attempts
    Note: Django ORM already protects against SQL injection, 
    but this adds an extra layer by monitoring suspicious patterns
    """
    
    # Common SQL injection patterns
    SQL_PATTERNS = [
        r"(\bUNION\b.*\bSELECT\b)",
        r"(\bSELECT\b.*\bFROM\b.*\bWHERE\b)",
        r"(\bINSERT\b.*\bINTO\b)",
        r"(\bUPDATE\b.*\bSET\b)",
        r"(\bDELETE\b.*\bFROM\b)",
        r"(\bDROP\b.*\bTABLE\b)",
        r"(\bEXEC\b|\bEXECUTE\b)",
        r"(--|;|\/\*|\*\/)",
        r"(\bOR\b\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+)",
        r"(\bOR\b\s+['\"]?[a-z]+['\"]?\s*=\s*['\"]?[a-z]+)",
        r"('.*--)",
        r"(1\s*=\s*1)",
        r"(sleep\(|benchmark\(|pg_sleep\()",
    ]
    
    def process_request(self, request):
        # Check GET parameters
        for key, value in request.GET.items():
            if self._contains_sql_injection(value):
                logger.warning(f"SQL Injection attempt detected in GET parameter '{key}': {value[:100]}")
                return HttpResponseForbidden("Invalid request detected")
        
        # Check POST parameters
        for key, value in request.POST.items():
            if isinstance(value, str) and self._contains_sql_injection(value):
                logger.warning(f"SQL Injection attempt detected in POST parameter '{key}': {value[:100]}")
                return HttpResponseForbidden("Invalid request detected")
        
        return None
    
    def _contains_sql_injection(self, value):
        """Check if value contains SQL injection patterns"""
        if not isinstance(value, str):
            return False
        
        value_upper = value.upper()
        
        for pattern in self.SQL_PATTERNS:
            if re.search(pattern, value_upper, re.IGNORECASE):
                return True
        
        return False


class XSSProtectionMiddleware(MiddlewareMixin):
    """
    Detect and block potential XSS (Cross-Site Scripting) attempts
    Note: Django templates auto-escape by default, but this adds extra protection
    """
    
    # Common XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",  # Event handlers like onclick=
        r"<iframe[^>]*>",
        r"<object[^>]*>",
        r"<embed[^>]*>",
        r"<applet[^>]*>",
        r"eval\s*\(",
        r"expression\s*\(",
        r"vbscript:",
        r"<svg[^>]*onload",
    ]
    
    def process_request(self, request):
        # Check GET parameters
        for key, value in request.GET.items():
            if self._contains_xss(value):
                logger.warning(f"XSS attempt detected in GET parameter '{key}': {value[:100]}")
                return HttpResponseForbidden("Invalid request detected")
        
        # Check POST parameters (except for specific safe fields)
        safe_fields = ['password', 'password1', 'password2']  # Don't check passwords
        for key, value in request.POST.items():
            if key not in safe_fields and isinstance(value, str) and self._contains_xss(value):
                logger.warning(f"XSS attempt detected in POST parameter '{key}': {value[:100]}")
                return HttpResponseForbidden("Invalid request detected")
        
        return None
    
    def _contains_xss(self, value):
        """Check if value contains XSS patterns"""
        if not isinstance(value, str):
            return False
        
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        
        return False


class RequestSizeMiddleware(MiddlewareMixin):
    """Limit request size to prevent DOS attacks"""
    
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10 MB
    
    def process_request(self, request):
        if request.META.get('CONTENT_LENGTH'):
            content_length = int(request.META['CONTENT_LENGTH'])
            if content_length > self.MAX_REQUEST_SIZE:
                logger.warning(f"Request too large: {content_length} bytes from IP {request.META.get('REMOTE_ADDR')}")
                return HttpResponseForbidden("Request too large")
        return None


class SuspiciousUserAgentMiddleware(MiddlewareMixin):
    """Block known malicious user agents and bots"""
    
    BLOCKED_USER_AGENTS = [
        'sqlmap',
        'nikto',
        'nmap',
        'masscan',
        'nessus',
        'openvas',
        'w3af',
        'dirbuster',
        'metasploit',
        'havij',
        'acunetix',
        'bsqlbf',
    ]
    
    def process_request(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        
        for blocked_agent in self.BLOCKED_USER_AGENTS:
            if blocked_agent in user_agent:
                logger.warning(f"Blocked suspicious user agent: {user_agent} from IP {request.META.get('REMOTE_ADDR')}")
                return HttpResponseForbidden("Access denied")
        
        return None


class SessionSecurityMiddleware(MiddlewareMixin):
    """Enhanced session security to prevent session hijacking"""
    
    def process_request(self, request):
        if request.user.is_authenticated:
            # Check if session has security markers
            if '_user_agent' not in request.session:
                # First time after login, set markers
                self._set_security_markers(request)
            else:
                # Validate session
                if not self._validate_session(request):
                    # Session validation failed - possible hijacking attempt
                    logger.warning(
                        f"Session validation failed for user {request.user.username} "
                        f"from IP {request.META.get('REMOTE_ADDR')}"
                    )
                    # Log out the user
                    from django.contrib.auth import logout
                    logout(request)
                    return HttpResponseForbidden("Session validation failed. Please log in again.")
        
        return None
    
    def _set_security_markers(self, request):
        """Set security markers on session"""
        request.session['_user_agent'] = request.META.get('HTTP_USER_AGENT', '')[:200]
        # Note: IP checking is optional and disabled by default due to mobile networks
        # request.session['_user_ip'] = request.META.get('REMOTE_ADDR')
    
    def _validate_session(self, request) -> bool:
        """Validate session hasn't been hijacked"""
        # Check user agent
        stored_agent = request.session.get('_user_agent', '')
        current_agent = request.META.get('HTTP_USER_AGENT', '')[:200]
        
        if stored_agent and stored_agent != current_agent:
            return False
        
        # Optional: Check IP (disabled by default)
        # stored_ip = request.session.get('_user_ip')
        # current_ip = request.META.get('REMOTE_ADDR')
        # if stored_ip and stored_ip != current_ip:
        #     return False
        
        return True


class BruteForceProtectionMiddleware(MiddlewareMixin):
    """Protect against brute force attacks"""
    
    PROTECTED_PATHS = ['/login/', '/signup/', '/password-reset/']
    MAX_REQUESTS = 10
    TIME_WINDOW = 60  # seconds
    
    def process_request(self, request):
        # Only check POST requests to protected paths
        if request.method == 'POST' and any(request.path.startswith(path) for path in self.PROTECTED_PATHS):
            ip = request.META.get('REMOTE_ADDR')
            key = f"brute_force:{ip}:{request.path}"
            
            # Get current request count
            request_data = cache.get(key, {'count': 0, 'first_request': time.time()})
            
            # Check if within time window
            if time.time() - request_data['first_request'] > self.TIME_WINDOW:
                # Reset counter
                request_data = {'count': 1, 'first_request': time.time()}
            else:
                request_data['count'] += 1
            
            # Check if exceeded limit
            if request_data['count'] > self.MAX_REQUESTS:
                logger.warning(f"Brute force attack detected from IP {ip} on {request.path}")
                return HttpResponse("Too many requests. Please try again later.", status=429)
            
            # Update cache
            cache.set(key, request_data, self.TIME_WINDOW)
        
        return None


class PathTraversalProtectionMiddleware(MiddlewareMixin):
    """Protect against path traversal attacks"""
    
    TRAVERSAL_PATTERNS = [
        r'\.\.',
        r'%2e%2e',
        r'\.\./',
        r'\.\.\\',
        r'%252e',
        r'%c0%ae',
    ]
    
    def process_request(self, request):
        # Check URL path
        path = request.path.lower()
        
        for pattern in self.TRAVERSAL_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                logger.warning(f"Path traversal attempt detected: {request.path} from IP {request.META.get('REMOTE_ADDR')}")
                return HttpResponseForbidden("Invalid path")
        
        # Check GET parameters
        for key, value in request.GET.items():
            if self._contains_traversal(value):
                logger.warning(f"Path traversal in GET parameter '{key}': {value} from IP {request.META.get('REMOTE_ADDR')}")
                return HttpResponseForbidden("Invalid parameter")
        
        return None
    
    def _contains_traversal(self, value):
        """Check if value contains path traversal patterns"""
        if not isinstance(value, str):
            return False
        
        for pattern in self.TRAVERSAL_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                return True
        
        return False
