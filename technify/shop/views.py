from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib import messages
from decimal import Decimal
import json
from datetime import datetime

from .models import Product, Category, Order, OrderItem, OTP
from .forms import CheckoutForm, PasswordResetRequestForm, PasswordResetVerifyForm, PasswordResetConfirmForm
from .notifications import NotificationService

from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from .forms import SignUpForm, EmailLoginForm
from .ratelimit import (
    rate_limit_login,
    rate_limit_signup,
    rate_limit_password_reset,
    rate_limit_otp,
)


def index(request):
    """Homepage with product listing"""
    store_mode = request.session.get('store_mode', 'electronics')
    category_slug = request.GET.get('category', 'all')
    search_query = request.GET.get('q', '').strip()

    # Get categories for the current store mode
    categories = Category.objects.filter(store_mode=store_mode)

    # Get products
    if category_slug == 'all':
        products = Product.objects.filter(category__store_mode=store_mode)
    else:
        category = get_object_or_404(Category, slug=category_slug, store_mode=store_mode)
        products = Product.objects.filter(category=category)

    # Search functionality
    if search_query:
        from django.db.models import Q
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(features__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    # Sorting
    sort_by = request.GET.get('sort', 'featured')
    if sort_by == 'price-low':
        products = products.order_by('price')
    elif sort_by == 'price-high':
        products = products.order_by('-price')
    elif sort_by == 'name':
        products = products.order_by('name')

    context = {
        'store_mode': store_mode,
        'categories': categories,
        'products': products,
        'current_category': category_slug,
        'search_query': search_query,
    }

    return render(request, 'shop/index.html', context)


def product_detail(request, slug):
    """Product detail page"""
    product = get_object_or_404(Product, slug=slug)
    store_mode = request.session.get('store_mode', 'electronics')

    # Get related products
    related_products = Product.objects.filter(
        category=product.category,
        in_stock=True
    ).exclude(id=product.id)[:4]

    context = {
        'product': product,
        'store_mode': store_mode,
        'related_products': related_products,
    }

    return render(request, 'shop/product_detail.html', context)


def cart(request):
    """Shopping cart page"""
    store_mode = request.session.get('store_mode', 'electronics')
    cart_items = get_cart_items(request)

    # Calculate amount needed for free delivery
    free_delivery_threshold = Decimal('500.00')

    subtotal = sum((item['total'] for item in cart_items), Decimal('0.00'))
    if subtotal <= 0:
        delivery_fee = Decimal('0.00')
    else:
        delivery_fee = Decimal('100.00') if subtotal < free_delivery_threshold else Decimal('0.00')

    total = subtotal + delivery_fee
    amount_for_free_delivery = max(Decimal('0.00'), free_delivery_threshold - subtotal)

    context = {
        'store_mode': store_mode,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'delivery_fee': delivery_fee,
        'total': total,
        'amount_for_free_delivery': amount_for_free_delivery,
        'free_delivery_threshold': free_delivery_threshold,
    }

    return render(request, 'shop/cart.html', context)


@login_required
def checkout(request):
    """Checkout page with Yoco Checkout API integration - LOGIN REQUIRED"""
    from django.conf import settings
    import requests

    store_mode = request.session.get('store_mode', 'electronics')
    cart_items = get_cart_items(request)

    if not cart_items:
        messages.warning(request, 'Your cart is empty!')
        return redirect('shop:cart')

    subtotal = sum(item['total'] for item in cart_items)
    delivery_fee = Decimal('100.00') if subtotal < 500 else Decimal('0.00')
    total = subtotal + delivery_fee

    if request.method == 'POST':
        form = CheckoutForm(request.POST)

        if form.is_valid():
            # Create order first
            order = form.save(commit=False)
            order.order_number = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            order.subtotal = subtotal
            order.delivery_fee = delivery_fee
            order.total = total
            order.country = 'South Africa'

            if request.user.is_authenticated:
                order.user = request.user

            order.save()

            # Create order items
            cart = request.session.get('cart', {})
            for product_id, item in cart.items():
                product = Product.objects.get(id=product_id)
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item['quantity'],
                    price=product.price
                )

            # Create Yoco Checkout session
            payment_method = form.cleaned_data.get('payment_method')

            if payment_method == 'card':
                yoco_secret_key = getattr(settings, 'YOCO_SECRET_KEY', '')
                if not yoco_secret_key or 'REPLACE_ME' in yoco_secret_key:
                    messages.error(
                        request,
                        'Card payments are disabled in this demo. Set YOCO_SECRET_KEY (test key) in your .env to enable Yoco checkout.',
                    )
                    order.delete()  # Clean up the order
                    return redirect('shop:checkout')
                try:
                    # Build return URLs
                    success_url = request.build_absolute_uri(f'/payment-success/{order.order_number}/')
                    cancel_url = request.build_absolute_uri('/checkout/')

                    # Create Yoco checkout
                    yoco_url = 'https://payments.yoco.com/api/checkouts'
                    headers = {
                        'Authorization': f'Bearer {settings.YOCO_SECRET_KEY}',
                        'Content-Type': 'application/json',
                    }

                    payload = {
                        'amount': int(float(total) * 100),  # Amount in cents
                        'currency': 'ZAR',
                        'successUrl': success_url,
                        'cancelUrl': cancel_url,
                        'failureUrl': cancel_url,
                        'metadata': {
                            'orderNumber': order.order_number,
                            'customerEmail': order.email,
                            'customerName': order.full_name,
                        }
                    }

                    print(f"Creating Yoco checkout for order {order.order_number}, amount: {payload['amount']} cents")  # Debug
                    response = requests.post(yoco_url, json=payload, headers=headers)
                    print(f"Yoco response status: {response.status_code}")  # Debug

                    if response.status_code == 200:  # Yoco returns 200, not 201
                        checkout_data = response.json()
                        redirect_url = checkout_data.get('redirectUrl')
                        print(f"Yoco redirect URL: {redirect_url}")  # Debug

                        # Store order number in session for success page
                        request.session['pending_order'] = order.order_number
                        request.session.modified = True

                        # Redirect to Yoco payment page
                        return redirect(redirect_url)
                    else:
                        # Show detailed error for debugging
                        error_detail = f"Status: {response.status_code}, Response: {response.text}"
                        print(f"Yoco API Error: {error_detail}")  # Log to console
                        messages.error(request, f'Payment gateway error: {response.status_code}. Please contact support.')
                        order.delete()  # Clean up the order
                        return redirect('shop:checkout')

                except Exception as e:
                    print(f"Exception during Yoco checkout: {str(e)}")  # Debug
                    messages.error(request, f'Payment error: {str(e)}')
                    order.delete()
                    return redirect('shop:checkout')
            else:
                # Other payment methods
                messages.info(request, 'This payment method is coming soon!')
                order.delete()
                return redirect('shop:checkout')
        else:
            # Form has validation errors - display them
            print("Form validation errors:", form.errors)  # Debug log
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

            # Return form with errors
            context = {
                'store_mode': store_mode,
                'form': form,
                'cart_items': cart_items,
                'subtotal': subtotal,
                'delivery_fee': delivery_fee,
                'total': total,
            }
            return render(request, 'shop/checkout.html', context)
    else:
        form = CheckoutForm()

    context = {
        'store_mode': store_mode,
        'form': form,
        'cart_items': cart_items,
        'subtotal': subtotal,
        'delivery_fee': delivery_fee,
        'total': total,
    }

    return render(request, 'shop/checkout.html', context)


# ========================================
# AJAX VIEWS
# ========================================

@require_POST
def add_to_cart(request, product_id):
    """Add product to cart via AJAX"""
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.POST.get('quantity', 1))

    cart = request.session.get('cart', {})

    if str(product_id) in cart:
        cart[str(product_id)]['quantity'] += quantity
    else:
        cart[str(product_id)] = {
            'quantity': quantity,
            'name': product.name,
            'price': str(product.price),
        }

    request.session['cart'] = cart
    request.session.modified = True

    cart_count = sum(item['quantity'] for item in cart.values())

    return JsonResponse({
        'success': True,
        'message': f'{product.name} added to cart!',
        'cart_count': cart_count
    })


@require_POST
def update_cart(request, product_id):
    """Update cart item quantity via AJAX"""
    quantity = int(request.POST.get('quantity', 1))
    cart = request.session.get('cart', {})

    if str(product_id) in cart:
        cart[str(product_id)]['quantity'] = quantity
        request.session['cart'] = cart
        request.session.modified = True

    cart_count = sum(item['quantity'] for item in cart.values())

    return JsonResponse({
        'success': True,
        'cart_count': cart_count
    })


@require_POST
def remove_from_cart(request, product_id):
    """Remove item from cart via AJAX"""
    cart = request.session.get('cart', {})

    if str(product_id) in cart:
        del cart[str(product_id)]
        request.session['cart'] = cart
        request.session.modified = True

    cart_count = sum(item['quantity'] for item in cart.values())

    return JsonResponse({
        'success': True,
        'cart_count': cart_count
    })


def set_store_mode(request, mode):
    """Set store mode (electronics or gaming)"""
    if mode in ['electronics', 'gaming']:
        request.session['store_mode'] = mode
        request.session.modified = True

    return JsonResponse({'success': True, 'mode': mode})


# ========================================
# HELPER FUNCTIONS
# ========================================

def get_cart_items(request):
    """Get cart items with full product details"""
    cart = request.session.get('cart', {})
    cart_items = []

    for product_id, item in cart.items():
        try:
            product = Product.objects.get(id=product_id)
            cart_items.append({
                'product': product,
                'quantity': item['quantity'],
                'price': product.price,
                'total': product.price * item['quantity']
            })
        except Product.DoesNotExist:
            continue

    return cart_items


# ========================================
# AUTHENTICATION VIEWS
# ========================================

@rate_limit_signup
def signup_view(request):
    """User registration with email and SMS notifications"""
    if request.user.is_authenticated:
        return redirect('shop:index')

    store_mode = request.session.get('store_mode', 'electronics')

    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()

            # Send welcome notifications
            phone_number = user.profile.phone
            NotificationService.send_welcome_notification(user, phone_number)

            login(request, user)
            messages.success(request, f'Welcome {user.first_name}! Your account has been created. Check your email and SMS for confirmation.')
            return redirect('shop:index')
    else:
        form = SignUpForm()

    context = {
        'form': form,
        'store_mode': store_mode,
    }
    return render(request, 'shop/signup.html', context)


@rate_limit_login
def login_view(request):
    """User login with EMAIL - CUSTOMERS ONLY"""
    if request.user.is_authenticated:
        # Silently redirect staff users without revealing admin status
        if request.user.is_staff or request.user.is_superuser:
            logout(request)
            return redirect('shop:login')
        return redirect('shop:index')

    store_mode = request.session.get('store_mode', 'electronics')

    if request.method == 'POST':
        form = EmailLoginForm(request.POST)
        if form.is_valid():
            user = form.get_user()
            if user:
                # Log the user in
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')

                # Show success message
                messages.success(request, f'Welcome back, {user.first_name}!')

                # Redirect to next page or homepage
                next_page = request.GET.get('next', 'shop:index')
                return redirect(next_page)
            else:
                messages.error(request, 'Login failed. Please try again.')
        else:
            # Show form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = EmailLoginForm()

    context = {
        'form': form,
        'store_mode': store_mode,
    }
    return render(request, 'shop/login.html', context)


def logout_view(request):
    """User logout"""
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('shop:index')


# ========================================
# USER ACCOUNT VIEWS
# ========================================

@login_required
def my_account(request):
    """User account page - CUSTOMERS ONLY"""
    store_mode = request.session.get('store_mode', 'electronics')

    # Get user's orders
    orders = Order.objects.filter(user=request.user).order_by('-created_at')

    context = {
        'store_mode': store_mode,
        'orders': orders,
    }
    return render(request, 'shop/my_account.html', context)


@login_required
def order_detail(request, order_number):
    """View single order details"""
    store_mode = request.session.get('store_mode', 'electronics')
    order = get_object_or_404(Order, order_number=order_number, user=request.user)

    context = {
        'store_mode': store_mode,
        'order': order,
    }
    return render(request, 'shop/order_detail.html', context)


# ========================================
# PAYMENT VIEWS
# ========================================

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt  # Yoco callback doesn't have CSRF token
def payment_success(request, order_number):
    """Payment success callback from Yoco with notifications"""
    try:
        order = Order.objects.get(order_number=order_number)

        # Update order status to paid
        order.status = 'paid'
        order.save()

        # Send order confirmation notifications (email + SMS)
        NotificationService.send_order_confirmation(order)

        # Clear cart
        request.session['cart'] = {}
        if 'pending_order' in request.session:
            del request.session['pending_order']
        request.session.modified = True

        messages.success(request, f'🎉 Payment successful! Order {order_number} confirmed. Check your email and SMS for details.')

        # Redirect to order detail if user is logged in, else homepage
        if request.user.is_authenticated and order.user == request.user:
            return redirect('shop:order_detail', order_number=order_number)
        else:
            return redirect('shop:index')

    except Order.DoesNotExist:
        messages.error(request, 'Order not found.')
        return redirect('shop:index')


# ========================================
# PASSWORD RESET VIEWS
# ========================================

@rate_limit_password_reset
def password_reset_request(request):
    """Step 1: Request password reset - generates and sends OTP"""
    if request.user.is_authenticated:
        return redirect('shop:index')

    store_mode = request.session.get('store_mode', 'electronics')

    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            # Get user
            try:
                user = User.objects.get(email=email)

                # Generate OTP
                otp = OTP.generate_otp(email, purpose='password_reset', expiry_minutes=10)

                # Send OTP via email
                NotificationService.send_password_reset_otp(email, otp.otp_code, user.first_name)

                # Store email in session for next step
                request.session['reset_email'] = email
                request.session.modified = True

                messages.success(request, 'OTP sent! Check your email and enter the 6-digit code.')
                return redirect('shop:password_reset_verify')

            except User.DoesNotExist:
                messages.error(request, 'No account found with this email address.')
    else:
        form = PasswordResetRequestForm()

    context = {
        'form': form,
        'store_mode': store_mode,
    }
    return render(request, 'shop/password_reset_request.html', context)


@rate_limit_otp
def password_reset_verify(request):
    """Step 2: Verify OTP code"""
    if request.user.is_authenticated:
        return redirect('shop:index')

    # Check if email is in session
    email = request.session.get('reset_email')
    if not email:
        messages.error(request, 'Please start the password reset process again.')
        return redirect('shop:password_reset_request')

    store_mode = request.session.get('store_mode', 'electronics')

    if request.method == 'POST':
        form = PasswordResetVerifyForm(request.POST, email=email)
        if form.is_valid():
            otp_code = form.cleaned_data['otp_code']

            # Verify OTP
            otp = OTP.verify_otp(email, otp_code, purpose='password_reset')
            if otp:
                # Mark OTP as used
                otp.is_used = True
                otp.save()

                # Store verified status in session
                request.session['otp_verified'] = True
                request.session.modified = True

                messages.success(request, 'OTP verified! Now set your new password.')
                return redirect('shop:password_reset_confirm')
            else:
                messages.error(request, 'Invalid or expired OTP. Please try again.')
    else:
        form = PasswordResetVerifyForm(email=email)

    context = {
        'form': form,
        'store_mode': store_mode,
        'email': email,
    }
    return render(request, 'shop/password_reset_verify.html', context)


def password_reset_confirm(request):
    """Step 3: Set new password"""
    if request.user.is_authenticated:
        return redirect('shop:index')

    # Check if OTP was verified
    if not request.session.get('otp_verified'):
        messages.error(request, 'Please verify your OTP first.')
        return redirect('shop:password_reset_request')

    email = request.session.get('reset_email')
    if not email:
        messages.error(request, 'Please start the password reset process again.')
        return redirect('shop:password_reset_request')

    store_mode = request.session.get('store_mode', 'electronics')

    if request.method == 'POST':
        form = PasswordResetConfirmForm(request.POST)
        if form.is_valid():
            password = form.cleaned_data['password1']

            # Update user password
            try:
                user = User.objects.get(email=email)

                # Ensure username is set to email (for authentication compatibility)
                if user.username != email:
                    user.username = email

                # Set new password
                user.set_password(password)
                user.save()

                # Clear password reset session data
                if 'reset_email' in request.session:
                    del request.session['reset_email']
                if 'otp_verified' in request.session:
                    del request.session['otp_verified']

                # Regenerate session for security
                request.session.cycle_key()

                # Automatically log the user in after successful password reset
                login(request, user, backend='django.contrib.auth.backends.ModelBackend')

                messages.success(request, '✅ Password reset successful! You are now logged in.')
                return redirect('shop:index')

            except User.DoesNotExist:
                messages.error(request, 'User not found.')
                return redirect('shop:password_reset_request')
    else:
        form = PasswordResetConfirmForm()

    context = {
        'form': form,
        'store_mode': store_mode,
    }
    return render(request, 'shop/password_reset_confirm.html', context)

# ========================================
# POLICY PAGES
# ========================================

def shipping_policy(request):
    store_mode = request.session.get('store_mode', 'electronics')
    return render(request, 'shop/shipping_policy.html', {'store_mode': store_mode})

def terms(request):
    store_mode = request.session.get('store_mode', 'electronics')
    return render(request, 'shop/terms.html', {'store_mode': store_mode})

def returns_policy(request):
    store_mode = request.session.get('store_mode', 'electronics')
    return render(request, 'shop/returns.html', {'store_mode': store_mode})
