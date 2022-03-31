from django.db import models


def recalc_cart(cart):
    cart_date = cart.products.aggregate(models.Sum("final_price"), models.Count('id'))
    if cart_date.get('final_price__sum'):
        cart.final_price = cart_date['final_price__sum']
    else:
        cart.final_price = 0
    cart.total_products = cart_date['id__count']
    cart.save()