"""
Notification service for sending emails and SMS
"""
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from twilio.rest import Client
import logging

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending email and SMS notifications"""
    
    @staticmethod
    def send_email(subject, recipient_list, template_name=None, context=None, html_message=None, plain_message=None):
        """
        Send email notification
        
        Args:
            subject: Email subject
            recipient_list: List of recipient email addresses
            template_name: Optional template name for HTML email
            context: Context for template rendering
            html_message: Direct HTML message (if template_name not provided)
            plain_message: Plain text message
        """
        try:
            if template_name and context:
                html_message = render_to_string(template_name, context)
                plain_message = strip_tags(html_message)
            
            if not plain_message and html_message:
                plain_message = strip_tags(html_message)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=recipient_list,
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Email sent successfully to {recipient_list}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {recipient_list}: {str(e)}")
            return False
    
    @staticmethod
    def send_sms(phone_number, message):
        """
        Send SMS notification via Twilio
        
        Args:
            phone_number: Recipient phone number (must include country code, e.g., +27...)
            message: SMS message text
        """
        try:
            # Check if Twilio is configured
            if not hasattr(settings, 'TWILIO_ACCOUNT_SID') or not settings.TWILIO_ACCOUNT_SID:
                logger.warning("Twilio not configured. SMS not sent.")
                return False
            
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            
            # Ensure phone number has country code
            if not phone_number.startswith('+'):
                # Assume South African number if no country code
                phone_number = f"+27{phone_number.lstrip('0')}"
            
            message = client.messages.create(
                body=message,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=phone_number
            )
            
            logger.info(f"SMS sent successfully to {phone_number}. SID: {message.sid}")
            return True
        except Exception as e:
            logger.error(f"Failed to send SMS to {phone_number}: {str(e)}")
            return False
    
    @staticmethod
    def send_welcome_notification(user, phone_number=None):
        """Send welcome email and SMS after account creation"""
        # Send welcome email
        subject = f"Welcome to Technify, {user.first_name}! 🎉"
        html_message = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2563eb;">Welcome to Technify!</h2>
                <p>Hi {user.first_name},</p>
                <p>Thank you for creating an account with us! We're excited to have you as part of our community.</p>
                <p>Your account details:</p>
                <ul>
                    <li><strong>Email:</strong> {user.email}</li>
                    <li><strong>Name:</strong> {user.first_name} {user.last_name}</li>
                </ul>
                <p>You can now:</p>
                <ul>
                    <li>✓ Browse our wide range of electronics and gaming products</li>
                    <li>✓ Add items to your cart and checkout securely</li>
                    <li>✓ Track your orders in your account dashboard</li>
                    <li>✓ Receive exclusive offers and updates</li>
                </ul>
                <p style="margin-top: 30px;">
                    <a href="https://technify.co.za" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">Start Shopping</a>
                </p>
                <p style="margin-top: 30px; color: #666; font-size: 14px;">
                    If you have any questions, feel free to contact our support team.
                </p>
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                <p style="color: #999; font-size: 12px;">Technify - Your Tech & Gaming Destination</p>
            </div>
        </body>
        </html>
        """
        
        NotificationService.send_email(
            subject=subject,
            recipient_list=[user.email],
            html_message=html_message
        )
        
        # Send welcome SMS if phone number provided
        if phone_number:
            sms_message = f"Welcome to Technify, {user.first_name}! 🎉 Your account has been created successfully. Start shopping now at https://technify.co.za"
            NotificationService.send_sms(phone_number, sms_message)
    
    @staticmethod
    def send_order_confirmation(order):
        """Send order confirmation email and SMS"""
        # Prepare order items list
        items_html = ""
        for item in order.items.all():
            items_html += f"""
            <tr>
                <td style="padding: 10px; border-bottom: 1px solid #eee;">{item.product.name}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: center;">{item.quantity}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">R{item.price}</td>
                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">R{item.total}</td>
            </tr>
            """
        
        # Send email
        subject = f"Order Confirmation - {order.order_number} ✅"
        html_message = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #10b981;">Order Confirmed! 🎉</h2>
                <p>Hi {order.full_name},</p>
                <p>Thank you for your order! We've received your payment and are processing your order.</p>
                
                <div style="background-color: #f3f4f6; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0;">Order Details</h3>
                    <p><strong>Order Number:</strong> {order.order_number}</p>
                    <p><strong>Order Date:</strong> {order.created_at.strftime('%B %d, %Y at %I:%M %p')}</p>
                    <p><strong>Status:</strong> <span style="color: #10b981;">Paid</span></p>
                </div>
                
                <h3>Items Ordered</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="background-color: #f9fafb;">
                            <th style="padding: 10px; text-align: left; border-bottom: 2px solid #ddd;">Product</th>
                            <th style="padding: 10px; text-align: center; border-bottom: 2px solid #ddd;">Qty</th>
                            <th style="padding: 10px; text-align: right; border-bottom: 2px solid #ddd;">Price</th>
                            <th style="padding: 10px; text-align: right; border-bottom: 2px solid #ddd;">Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                </table>
                
                <div style="margin-top: 20px; text-align: right;">
                    <p><strong>Subtotal:</strong> R{order.subtotal}</p>
                    <p><strong>Delivery Fee:</strong> R{order.delivery_fee}</p>
                    <p style="font-size: 18px; color: #2563eb;"><strong>Total:</strong> R{order.total}</p>
                </div>
                
                <div style="background-color: #eff6ff; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <h3 style="margin-top: 0;">Delivery Address</h3>
                    <p>{order.address}<br>
                    {order.city}, {order.province}<br>
                    {order.postal_code}<br>
                    {order.country}</p>
                </div>
                
                <p style="margin-top: 30px;">We'll send you another notification when your order is shipped.</p>
                
                <p style="margin-top: 30px;">
                    <a href="https://technify.co.za/my-account/" style="background-color: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">View Order</a>
                </p>
                
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                <p style="color: #999; font-size: 12px;">Technify - Your Tech & Gaming Destination</p>
            </div>
        </body>
        </html>
        """
        
        NotificationService.send_email(
            subject=subject,
            recipient_list=[order.email],
            html_message=html_message
        )
        
        # Send SMS
        sms_message = f"Order confirmed! 🎉 Order #{order.order_number} has been received. Total: R{order.total}. Track your order at https://technify.co.za/my-account/"
        NotificationService.send_sms(order.phone, sms_message)
    
    @staticmethod
    def send_password_reset_otp(email, otp_code, user_name=""):
        """Send password reset OTP via email and SMS"""
        subject = "Password Reset OTP - Technify 🔐"
        html_message = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                <h2 style="color: #2563eb;">Password Reset Request</h2>
                <p>Hi{' ' + user_name if user_name else ''},</p>
                <p>We received a request to reset your password. Use the OTP code below to proceed:</p>
                
                <div style="background-color: #f3f4f6; padding: 20px; border-radius: 5px; margin: 20px 0; text-align: center;">
                    <h1 style="color: #2563eb; font-size: 36px; letter-spacing: 5px; margin: 0;">{otp_code}</h1>
                </div>
                
                <p><strong>This OTP will expire in 10 minutes.</strong></p>
                
                <p style="color: #dc2626; margin-top: 20px;">
                    ⚠️ If you didn't request a password reset, please ignore this email or contact support if you're concerned about your account security.
                </p>
                
                <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                <p style="color: #999; font-size: 12px;">Technify - Your Tech & Gaming Destination</p>
            </div>
        </body>
        </html>
        """
        
        return NotificationService.send_email(
            subject=subject,
            recipient_list=[email],
            html_message=html_message
        )
