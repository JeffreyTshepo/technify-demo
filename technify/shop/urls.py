from django.urls import path
from . import views

app_name = 'shop'

urlpatterns = [
    path('', views.index, name='index'),
    path('product/<slug:slug>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart, name='cart'),
    path('checkout/', views.checkout, name='checkout'),
    
    # Authentication URLs
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Password Reset URLs
    path('password-reset/', views.password_reset_request, name='password_reset_request'),
    path('password-reset/verify/', views.password_reset_verify, name='password_reset_verify'),
    path('password-reset/confirm/', views.password_reset_confirm, name='password_reset_confirm'),
    
    # User Account URLs
    path('my-account/', views.my_account, name='my_account'),
    path('order/<str:order_number>/', views.order_detail, name='order_detail'),
    
    # Payment URLs
    path('payment-success/<str:order_number>/', views.payment_success, name='payment_success'),
    
    # Policy Pages
    path('shipping-policy/', views.shipping_policy, name='shipping_policy'),
    path('terms/', views.terms, name='terms'),
    path('returns/', views.returns_policy, name='returns'),
    
    # AJAX endpoints
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('update-cart/<int:product_id>/', views.update_cart, name='update_cart'),
    path('remove-from-cart/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('set-store-mode/<str:mode>/', views.set_store_mode, name='set_store_mode'),
]