from django.urls import path
from . import views

app_name = 'catalogue'

urlpatterns = [
    # --- Sponsor / Catalogue Management ---
    path('<int:org_id>/external/', views.external_products, name='external_products'),
    path('<int:org_id>/add/<int:product_id>/', views.add_product_to_catalogue, name='add_product_to_catalogue'),
    path('<int:org_id>/view/', views.view_catalogue, name='view_catalogue'),
    path('<int:org_id>/delete/<int:item_id>/', views.delete_product, name='delete_catalogue_item'),
    path('<int:org_id>/toggle/<int:item_id>/', views.toggle_item_status, name='toggle_item_status'),

    # --- Cart (Driver) ---
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:cart_item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:cart_item_id>/', views.update_cart_quantity, name='update_cart_quantity'),

    # --- Checkout / Orders (Driver) ---
    path('checkout/submit/', views.checkout_submit, name='checkout_submit'),
    path('orders/', views.my_orders, name='my_orders'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
]