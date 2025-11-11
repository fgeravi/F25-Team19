# from django.urls import path
# from . import views

# app_name = 'catalogue'

# urlpatterns = [
#     path('', views.catalog_list, name='catalog_list'),
#     path('item/<int:item_id>/', views.catalog_item_detail, name='catalog_item_detail'),
# ]

from django.urls import path
from . import views

app_name = 'catalogue' 

urlpatterns = [
    path('<int:sponsor_id>/external/', views.external_products, name='external_products'),
    path('<int:sponsor_id>/add/<int:product_id>/', views.add_product_to_catalogue, name='add_product_to_catalogue'),
    path('<int:sponsor_id>/view/', views.view_catalogue, name='view_catalogue'),
    path("<int:sponsor_id>/delete/<int:item_id>/", views.delete_product, name="delete_catalogue_item"),
    path("<int:sponsor_id>/toggle/<int:item_id>/", views.toggle_item_status, name="toggle_item_status"),
    
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<int:cart_item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/update/<int:cart_item_id>/', views.update_cart_quantity, name='update_cart_quantity'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path('orders/export.csv', views.orders_csv, name='orders_csv'),
]