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
    path('<int:org_id>/external/', views.external_products, name='external_products'),
    path('<int:org_id>/add/<int:product_id>/', views.add_product_to_catalogue, name='add_product_to_catalogue'),
    path('<int:org_id>/view/', views.view_catalogue, name='view_catalogue'),
]