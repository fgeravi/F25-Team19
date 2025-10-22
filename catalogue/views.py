# from django.shortcuts import render, get_object_or_404, redirect
# from django.contrib.auth.decorators import login_required
# from django.contrib import messages
# from django.core.paginator import Paginator
# from django.db.models import F
# from .models import CatalogueItem, ItemView


# @login_required
# def catalog_list(request):
#     """
#     Display catalog items with sorting options and recently viewed items.
#     Only accessible by drivers.
#     """
#     # Check if user is a driver
#     if not request.user.is_driver:
#         messages.error(request, "You must be a driver to access the catalog.")
#         return redirect('home')

#     # Get driver's organization
#     try:
#         driver_profile = request.user.driverprofile
#         organization = driver_profile.organization
#     except AttributeError:
#         messages.error(request, "Driver profile not found.")
#         return redirect('home')

#     if not organization:
#         messages.error(request, "You must be assigned to an organization to view the catalog.")
#         return redirect('home')

#     # Get all catalog items for the driver's organization
#     items = CatalogueItem.objects.filter(
#         catalogue__organization=organization
#     ).select_related('catalogue')

#     # Handle sorting
#     sort_by = request.GET.get('sort_by', 'newest')
    
#     if sort_by == 'popular':
#         items = items.order_by('-view_count', '-created_at')
#         sort_display = "Most Popular"
#     else:  # Default to 'newest'
#         items = items.order_by('-created_at')
#         sort_display = "Newest"

#     # Pagination
#     paginator = Paginator(items, 12)  # Show 12 items per page
#     page_number = request.GET.get('page')
#     page_obj = paginator.get_page(page_number)

#     # Get recently viewed items (last 5)
#     recently_viewed = ItemView.objects.filter(
#         user=request.user,
#         catalogue_item__catalogue__organization=organization
#     ).select_related('catalogue_item', 'catalogue_item__catalogue')[:5]

#     context = {
#         'page_obj': page_obj,
#         'sort_by': sort_by,
#         'sort_display': sort_display,
#         'recently_viewed': recently_viewed,
#         'organization': organization,
#     }
#     return render(request, 'catalogue/catalog_list.html', context)


# @login_required
# def catalog_item_detail(request, item_id):
#     """
#     Display detailed information about a catalog item.
#     Records the view in ItemView and increments view_count.
#     Only accessible by drivers.
#     """
#     # Check if user is a driver
#     if not request.user.is_driver:
#         messages.error(request, "You must be a driver to access the catalog.")
#         return redirect('home')

#     # Get the catalog item
#     item = get_object_or_404(CatalogueItem, pk=item_id)

#     # Verify the item belongs to the driver's organization
#     try:
#         driver_profile = request.user.driverprofile
#         organization = driver_profile.organization
        
#         if item.catalogue.organization != organization:
#             messages.error(request, "This item is not available in your organization's catalog.")
#             return redirect('catalogue:catalog_list')
#     except AttributeError:
#         messages.error(request, "Driver profile not found.")
#         return redirect('home')

#     # Record the view (creates new or updates existing)
#     ItemView.objects.update_or_create(
#         user=request.user,
#         catalogue_item=item,
#         defaults={'viewed_at': None}  # auto_now will set the timestamp
#     )

#     # Increment view count
#     CatalogueItem.objects.filter(pk=item_id).update(view_count=F('view_count') + 1)
    
#     # Refresh the item to get updated view_count
#     item.refresh_from_db()

#     context = {
#         'item': item,
#     }
#     return render(request, 'catalogue/catalog_item_detail.html', context)

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from organizations.models import Organization
from .models import Catalogue, CatalogueItem
from .utils import fetch_products_from_api
import requests

# view for acuiring external products for sponsors to choose
@login_required
def external_products(request, org_id):
    organization = get_object_or_404(Organization, id=org_id)
    
    # Optionally check that the user is the sponsor for this org
    if request.user != organization.sponsor:
        return render(request, "catalogue/forbidden.html")

    products = fetch_products_from_api()
    return render(request, "catalogue/external_products.html", {
        "organization": organization,
        "products": products
    })

# view for adding to orgs' catalogue
@login_required
def add_product_to_catalogue(request, org_id, product_id):
    organization = get_object_or_404(Organization, id=org_id)
    catalogue, _ = Catalogue.objects.get_or_create(
        organization=organization, name="Default Catalogue"
    )

    response = requests.get(f"https://api.escuelajs.co/api/v1/products/{product_id}")
    if response.status_code != 200:
        return redirect("external_products", org_id=org_id)
    product_data = response.json()

    CatalogueItem.objects.get_or_create(
        catalogue=catalogue,
        product_id=str(product_data["id"]),
        defaults={
            "product_name": product_data["title"],
            "product_url": f"https://fake-store-api.com/products/{product_data['id']}",
            "price": product_data["price"],
            "image_url": product_data["images"][0] if product_data["images"] else None,
        }
    )
    return redirect("view_catalogue", org_id=org_id)

# view to view catalogue
@login_required
def view_catalogue(request, org_id):
    organization = get_object_or_404(Organization, id=org_id)
    catalogue = Catalogue.objects.filter(organization=organization).first()

    return render(request, "catalogue/view_catalogue.html", {
        "organization": organization,
        "catalogue": catalogue,
    })
