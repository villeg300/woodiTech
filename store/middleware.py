from .models import Cart

class CartMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            try:
                cart = Cart.objects.get(user=request.user)
                request.session['cart_count'] = cart.get_total_items()
            except Cart.DoesNotExist:
                request.session['cart_count'] = 0
        else:
            request.session['cart_count'] = 0
            
        response = self.get_response(request)
        return response
