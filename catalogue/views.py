from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from organizations.models import Organization
from .models import Catalogue, CatalogueItem, CartItem
from .utils import fetch_products_from_api
from users.models import SponsorProfile, DriverProfile
import requests

# --------------------------
# External products for sponsors
# --------------------------
@login_required
def external_products(request, org_id):
    organization = get_object_or_404(Organization, id=org_id)

    # Only the sponsor of this org can view
    try:
        sponsor_profile = SponsorProfile.objects.get(organization=organization)
        if request.user != sponsor_profile.user:
            messages.error(request, "You are not authorized to view this page.")
            return render(request, "catalogue/forbidden.html")
    except SponsorProfile.DoesNotExist:
        messages.error(request, "This organization has no assigned sponsor.")
        return render(request, "catalogue/forbidden.html")

    # Fetch external products
    try:
        products = fetch_products_from_api()
    except Exception:
        messages.error(request, "Failed to fetch products from the external API.")
        products = []

    return render(request, "catalogue/external_products.html", {
        "organization": organization,
        "products": products,
    })


# --------------------------
# Add product to org's catalogue
# --------------------------
@login_required
def add_product_to_catalogue(request, org_id, product_id):
    organization = get_object_or_404(Organization, id=org_id)

    # Only sponsor can add products
    try:
        sponsor_profile = SponsorProfile.objects.get(organization=organization)
        if request.user != sponsor_profile.user:
            messages.error(request, "You are not authorized to add products.")
            return redirect("catalogue:view_catalogue", org_id=org_id)
    except SponsorProfile.DoesNotExist:
        messages.error(request, "This organization has no assigned sponsor.")
        return redirect("catalogue:view_catalogue", org_id=org_id)

    # Get or create catalogue
    catalogue, _ = Catalogue.objects.get_or_create(
        organization=organization, name="Default Catalogue"
    )

    # Fetch product from external API
    response = requests.get(f"https://api.escuelajs.co/api/v1/products/{product_id}")
    if response.status_code != 200:
        messages.error(request, "Failed to fetch product from external API.")
        return redirect("catalogue:external_products", org_id=org_id)

    product_data = response.json()

    CatalogueItem.objects.get_or_create(
        catalogue=catalogue,
        product_id=str(product_data["id"]),
        defaults={
            "product_name": product_data["title"],
            "product_url": f"https://fake-store-api.com/products/{product_data['id']}",
            "price": product_data["price"],
            "image_url": product_data["images"][0] if product_data.get("images") else None,
            "category": product_data.get("category", {}).get("name", "Uncategorized"),
        }
    )

    messages.success(request, f"{product_data['title']} added to catalogue.")
    return redirect("catalogue:view_catalogue", org_id=org_id)


# --------------------------
# View catalogue
# --------------------------
@login_required
def view_catalogue(request, org_id):

    organization = get_object_or_404(Organization, id=org_id)
    user = request.user

    catalogue, _ = Catalogue.objects.get_or_create(
        organization=organization,
        name="Default Catalogue"
    )

    if user.is_sponsor:
        items = catalogue.items.all()
    else:
        items = catalogue.items.filter(is_active=True)

    query = request.GET.get("q")
    if query:
        items = items.filter(product_name__icontains=query)


    return render(request, "catalogue/view_catalogue.html", {
        "organization": organization,
        "catalogue": catalogue,
        "items": items,
        "user": user,
    })


# ---------------------------------------
# Delete product from catalogue (sponsor)
# ---------------------------------------
@login_required
def delete_product(request, org_id, item_id):
    organization = get_object_or_404(Organization, id=org_id)

    # Only allow sponsors to delete
    if not request.user.is_sponsor:
        messages.error(request, "You do not have permission to delete items.")
        return redirect("catalogue:view_catalogue", org_id=org_id)

    # Safely get sponsor profile
    sponsor_profile = getattr(request.user, "sponsorprofile", None)

    # Verify sponsor belongs to this organization
    if not sponsor_profile or sponsor_profile.organization != organization:
        messages.error(request, "You cannot delete items from another organization's catalogue.")
        return redirect("catalogue:view_catalogue", org_id=org_id)

    # Get the catalogue item within this org
    item = get_object_or_404(
        CatalogueItem,
        id=item_id,
        catalogue__organization=organization
    )

    # Delete it
    item.delete()
    messages.success(request, f"'{item.product_name}' was removed from the catalogue.")
    return redirect("catalogue:view_catalogue", org_id=org_id)


@login_required
def toggle_item_status(request, org_id, item_id):
    organization = get_object_or_404(Organization, id=org_id)

    if not request.user.is_sponsor:
        messages.error(request, "You do not have permission to modify items.")
        return redirect("catalogue:view_catalogue", org_id=org_id)

    sponsor_profile = getattr(request.user, "sponsorprofile", None)

    if not sponsor_profile or sponsor_profile.organization != organization:
        messages.error(request, "You cannot modify items from another organization's catalogue.")
        return redirect("catalogue:view_catalogue", org_id=org_id)

    item = get_object_or_404(
        CatalogueItem,
        id=item_id,
        catalogue__organization=organization
    )

    item.is_active = not item.is_active
    item.save()
    
    status = "enabled" if item.is_active else "disabled"
    messages.success(request, f"'{item.product_name}' has been {status}.")
    return redirect("catalogue:view_catalogue", org_id=org_id)


@login_required
def view_cart(request):
    if not request.user.is_driver:
        messages.error(request, "Only drivers can access the shopping cart.")
        return redirect("home")
    
    cart_items = CartItem.objects.filter(user=request.user).select_related('catalogue_item')
    
    total = sum(item.get_total_price() for item in cart_items)
    
    return render(request, "catalogue/cart.html", {
        "cart_items": cart_items,
        "total": total,
    })


@login_required
def add_to_cart(request, item_id):
    if not request.user.is_driver:
        messages.error(request, "Only drivers can add items to cart.")
        return redirect("home")
    
    catalogue_item = get_object_or_404(CatalogueItem, id=item_id)
    
    if not catalogue_item.is_active:
        messages.error(request, "This item is currently unavailable.")
        org_id = catalogue_item.catalogue.organization.id
        return redirect("catalogue:view_catalogue", org_id=org_id)
    
    cart_item, created = CartItem.objects.get_or_create(
        user=request.user,
        catalogue_item=catalogue_item,
        defaults={'quantity': 1}
    )
    
    if not created:
        cart_item.quantity += 1
        cart_item.save()
        messages.success(request, f"Increased quantity of '{catalogue_item.product_name}' in cart.")
    else:
        messages.success(request, f"'{catalogue_item.product_name}' added to cart.")
    
    org_id = catalogue_item.catalogue.organization.id
    return redirect("catalogue:view_catalogue", org_id=org_id)


@login_required
def remove_from_cart(request, cart_item_id):
    if not request.user.is_driver:
        messages.error(request, "Only drivers can modify the cart.")
        return redirect("home")
    
    cart_item = get_object_or_404(CartItem, id=cart_item_id, user=request.user)
    product_name = cart_item.catalogue_item.product_name
    cart_item.delete()
    
    messages.success(request, f"'{product_name}' removed from cart.")
    return redirect("catalogue:view_cart")


@login_required
def update_cart_quantity(request, cart_item_id):
    if not request.user.is_driver:
        messages.error(request, "Only drivers can modify the cart.")
        return redirect("home")
    
    if request.method == "POST":
        cart_item = get_object_or_404(CartItem, id=cart_item_id, user=request.user)
        quantity = int(request.POST.get("quantity", 1))
        
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, "Quantity updated.")
        else:
            cart_item.delete()
            messages.success(request, "Item removed from cart.")
    
    return redirect("catalogue:view_cart")