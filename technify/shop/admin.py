from django.contrib import admin
from django.utils import timezone
from datetime import timedelta
from .models import Category, Product, Order, OrderItem, UserProfile, OTP

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'store_mode']
    list_filter = ['store_mode']
    prepopulated_fields = {'slug': ('name',)}


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ['product', 'quantity', 'price']


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price', 'in_stock', 'created_at']
    list_filter = ['category', 'in_stock', 'category__store_mode']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['price', 'in_stock']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'full_name', 'phone', 'delivery_address_summary', 'total', 'status', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at', 'city', 'province']
    search_fields = ['order_number', 'full_name', 'email', 'phone', 'address', 'city', 'province']
    readonly_fields = ['order_number', 'created_at', 'updated_at', 'subtotal', 'delivery_fee', 'total', 'formatted_delivery_address']
    inlines = [OrderItemInline]
    list_editable = ['status']
    date_hierarchy = 'created_at'
    
    def delivery_address_summary(self, obj):
        """Show brief delivery address in list view"""
        return f"{obj.city}, {obj.province}"
    delivery_address_summary.short_description = '📍 Delivery Location'
    
    def formatted_delivery_address(self, obj):
        """Show full formatted address in detail view"""
        from django.utils.safestring import mark_safe
        alt_phone_display = f' / {obj.alt_phone}' if obj.alt_phone else ''
        address2_display = f'{obj.address2}<br>' if obj.address2 else ''
        delivery_notes = f'<br><strong style="color: #000;">Delivery Notes:</strong><br><span style="color: #000;">{obj.delivery_instructions}</span>' if obj.delivery_instructions else ''
        
        address_html = f"""
        <div style="background: #f0f9ff; border: 2px solid #0284c7; padding: 20px; border-radius: 8px; font-family: Arial, sans-serif; color: #000;">
            <strong style="color: #0284c7; font-size: 18px;">📦 DELIVERY ADDRESS:</strong><br><br>
            <strong style="color: #000; font-size: 16px;">{obj.full_name}</strong><br>
            <span style="color: #000;">📞 {obj.phone}{alt_phone_display}</span><br>
            <span style="color: #000;">📧 {obj.email}</span><br><br>
            <strong style="color: #0284c7; font-size: 15px;">Shipping To:</strong><br>
            <span style="color: #000; font-size: 14px; line-height: 1.8;">
            {obj.address}<br>
            {address2_display}
            {obj.city}, {obj.province} {obj.postal_code}<br>
            {obj.country}
            </span>
            {delivery_notes}
        </div>
        """
        return mark_safe(address_html)
    formatted_delivery_address.short_description = '📍 Full Delivery Address'
    
    actions = [
        'mark_as_paid',
        'mark_as_shipped',
        'mark_as_delivered',
        'mark_as_cancelled',
        'delete_old_orders',
    ]
    
    def mark_as_paid(self, request, queryset):
        """Mark selected orders as paid"""
        updated = queryset.update(status='paid')
        self.message_user(request, f'{updated} order(s) marked as paid.')
    mark_as_paid.short_description = '✅ Mark as Paid'
    
    def mark_as_shipped(self, request, queryset):
        """Mark selected orders as shipped"""
        updated = queryset.update(status='shipped')
        self.message_user(request, f'{updated} order(s) marked as shipped.')
    mark_as_shipped.short_description = '🚚 Mark as Shipped'
    
    def mark_as_delivered(self, request, queryset):
        """Mark selected orders as delivered"""
        updated = queryset.update(status='delivered')
        self.message_user(request, f'{updated} order(s) marked as delivered.')
    mark_as_delivered.short_description = '📦 Mark as Delivered'
    
    def mark_as_cancelled(self, request, queryset):
        """Mark selected orders as cancelled"""
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} order(s) marked as cancelled.')
    mark_as_cancelled.short_description = '❌ Mark as Cancelled'
    
    def delete_old_orders(self, request, queryset):
        """Delete orders older than 2 months"""
        two_months_ago = timezone.now() - timedelta(days=60)
        old_orders = queryset.filter(created_at__lt=two_months_ago)
        count = old_orders.count()
        old_orders.delete()
        self.message_user(request, f'{count} order(s) older than 2 months deleted.')
    delete_old_orders.short_description = '🗑️ Delete Orders Older Than 2 Months'
    
    def get_queryset(self, request):
        """Automatically exclude orders older than 2 months from list view"""
        qs = super().get_queryset(request)
        # Show warning if there are old orders
        two_months_ago = timezone.now() - timedelta(days=60)
        old_count = qs.filter(created_at__lt=two_months_ago).count()
        if old_count > 0:
            self.message_user(
                request,
                f'Note: There are {old_count} order(s) older than 2 months. Use "Delete Orders Older Than 2 Months" action to clean them up.',
                level='warning'
            )
        return qs
    
    fieldsets = (
        ('Order Information', {
            'fields': ('order_number', 'status', 'created_at', 'updated_at')
        }),
        ('📍 Delivery Address - COPY THIS FOR SHIPPING', {
            'fields': ('formatted_delivery_address',),
            'description': 'Complete delivery address for shipping. Copy this information for your delivery service.'
        }),
        ('Customer Contact Details', {
            'fields': ('user', 'full_name', 'email', 'phone', 'alt_phone')
        }),
        ('Delivery Address Details', {
            'fields': ('address', 'address2', 'city', 'province', 'postal_code', 'country', 'delivery_instructions'),
            'classes': ('collapse',)
        }),
        ('Order Summary', {
            'fields': ('subtotal', 'delivery_fee', 'total', 'payment_method')
        }),
    )


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'phone', 'email_verified', 'phone_verified', 'city', 'created_at']
    search_fields = ['user__username', 'user__email', 'phone']
    readonly_fields = ['created_at']
    list_filter = ['email_verified', 'phone_verified']
    
    fieldsets = (
        ('User', {
            'fields': ('user',)
        }),
        ('Contact Information', {
            'fields': ('phone', 'email_verified', 'phone_verified')
        }),
        ('Address', {
            'fields': ('address', 'city', 'province', 'postal_code')
        }),
        ('Metadata', {
            'fields': ('created_at',)
        }),
    )


@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ['email', 'otp_code', 'purpose', 'is_used', 'created_at', 'expires_at', 'is_valid_status']
    list_filter = ['purpose', 'is_used', 'created_at']
    search_fields = ['email', 'otp_code']
    readonly_fields = ['created_at', 'expires_at']
    date_hierarchy = 'created_at'
    
    def is_valid_status(self, obj):
        """Display if OTP is currently valid"""
        if obj.is_valid():
            return '✅ Valid'
        elif obj.is_used:
            return '❌ Used'
        else:
            return '⏰ Expired'
    is_valid_status.short_description = 'Status'
    
    fieldsets = (
        ('OTP Details', {
            'fields': ('email', 'otp_code', 'purpose')
        }),
        ('Status', {
            'fields': ('is_used', 'created_at', 'expires_at')
        }),
    )


# Customize Django Admin Site Branding
admin.site.site_header = "Technify Administration"
admin.site.site_title = "Technify Admin Portal"
admin.site.index_title = "Welcome to Technify Admin Dashboard"
