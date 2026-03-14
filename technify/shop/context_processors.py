def cart_count(request):
    """Context processor to make cart count available in all templates"""
    cart = request.session.get('cart', {})
    count = sum(item['quantity'] for item in cart.values())
    return {'cart_count': count}