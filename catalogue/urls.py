from django.urls import path
from . import views

app_name = 'catalogue'

urlpatterns = [
    path('', views.catalog_list, name='catalog_list'),
    path('item/<int:item_id>/', views.catalog_item_detail, name='catalog_item_detail'),
]
