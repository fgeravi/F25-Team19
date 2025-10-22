from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from organizations.models import Organization
from .models import Catalogue, CatalogueItem
from .utils import fetch_products_from_api
from users.models import SponsorProfile
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

    # Always use the "Default Catalogue"
    catalogue, _ = Catalogue.objects.get_or_create(
        organization=organization,
        name="Default Catalogue"
    )

    items = catalogue.items.all()  # assuming you have a related_name="items" on CatalogueItem

    return render(request, "catalogue/view_catalogue.html", {
        "organization": organization,
        "catalogue": catalogue,
        "items": items,
    })
