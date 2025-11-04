from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.urls import reverse  
from organizations.models import Organization
from .models import (
    Catalogue,
    CatalogueItem,
    CartItem,
    Order,
    OrderItem,
)
from .utils import fetch_products_from_api
from users.models import SponsorProfile, DriverProfile, send_driver_notification
from rewards.models import award_points_to_driver
import requests

# --------------------------
# External products for sponsors
# --------------------------
@login_required
def external_products(request, sponsor_id):
    """
    Show external products that a sponsor can add to their catalogue.
    Only the sponsor themselves can view this page.
    """
    sponsor = get_object_or_404(SponsorProfile, id=sponsor_id)

    # Check that the logged-in user is the sponsor
    if request.user != sponsor.user:
        messages.error(request, "You are not authorized to view this page.")
        return render(request, "catalogue/forbidden.html")

    # Fetch external products
    try:
        products = fetch_products_from_api()
    except Exception:
        messages.error(request, "Failed to fetch products from the external API.")
        products = []

    return render(request, "catalogue/external_products.html", {
        "sponsor": sponsor,
        "products": products,
    })


@login_required
def add_product_to_catalogue(request, sponsor_id, product_id):
    """
    Add a product to the sponsor's personal catalogue.
    """
    sponsor = get_object_or_404(SponsorProfile, id=sponsor_id)

    # Only allow the sponsor themselves
    if request.user != sponsor.user:
        messages.error(request, "You are not authorized to add products to this catalogue.")
        return redirect("catalogue:external_products", sponsor_id=sponsor_id)

    # Get or create the sponsor's catalogue
    catalogue, _ = Catalogue.objects.get_or_create(
        sponsor=sponsor,
        name="Default Catalogue"
    )

    # Fetch product from external API
    response = requests.get(f"https://api.escuelajs.co/api/v1/products/{product_id}")
    if response.status_code != 200:
        messages.error(request, "Failed to fetch product from the external API.")
        return redirect("catalogue:external_products", sponsor_id=sponsor_id)

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

    messages.success(request, f"{product_data['title']} added to your catalogue.")
    return redirect("catalogue:view_catalogue", sponsor_id=sponsor_id)


# --------------------------
# View catalogue
# --------------------------
@login_required
def view_catalogue(request, sponsor_id):
    """
    View a sponsor-specific catalogue.
    """
    sponsor = get_object_or_404(SponsorProfile, id=sponsor_id)
    user = request.user

    # Get or create the sponsor's catalogue
    catalogue, _ = Catalogue.objects.get_or_create(
        sponsor=sponsor,
        name="Default Catalogue"
    )

    # Only show active items to drivers
    if user.is_sponsor and user == sponsor.user:
        items = catalogue.items.all()
    else:
        items = catalogue.items.filter(is_active=True)

    # Search
    query = request.GET.get("q")
    if query:
        items = items.filter(product_name__icontains=query)

    # Sorting
    sort = request.GET.get("sort")
    if sort == "low_to_high":
        items = items.order_by("price")
    elif sort == "high_to_low":
        items = items.order_by("-price")

    return render(request, "catalogue/view_catalogue.html", {
        "sponsor": sponsor,
        "catalogue": catalogue,
        "items": items,
        "user": user,
        "sort": sort,
    })



# ---------------------------------------
# Delete product from catalogue (sponsor)
# ---------------------------------------
@login_required
def delete_product(request, sponsor_id, item_id):
    # Only allow sponsors to delete
    if not request.user.is_sponsor:
        messages.error(request, "You do not have permission to delete items.")
        return redirect("home")

    sponsor = get_object_or_404(SponsorProfile, id=sponsor_id)

    # Ensure the sponsor owns this catalogue
    if request.user != sponsor.user:
        messages.error(request, "You cannot delete items from another sponsor's catalogue.")
        return redirect("catalogue:view_catalogue", sponsor_id=sponsor.id)

    # Get the catalogue item
    item = get_object_or_404(
        CatalogueItem,
        id=item_id,
        catalogue__sponsor=sponsor
    )

    item.delete()
    messages.success(request, f"'{item.product_name}' was removed from the catalogue.")
    return redirect("catalogue:view_catalogue", sponsor_id=sponsor.id)


@login_required
def toggle_item_status(request, sponsor_id, item_id):
    # Only allow sponsors to modify
    if not request.user.is_sponsor:
        messages.error(request, "You do not have permission to modify items.")
        return redirect("home")

    sponsor = get_object_or_404(SponsorProfile, id=sponsor_id)

    # Ensure the sponsor owns this catalogue
    if request.user != sponsor.user:
        messages.error(request, "You cannot modify items from another sponsor's catalogue.")
        return redirect("catalogue:view_catalogue", sponsor_id=sponsor.id)

    # Get the catalogue item
    item = get_object_or_404(
        CatalogueItem,
        id=item_id,
        catalogue__sponsor=sponsor
    )

    item.is_active = not item.is_active
    item.save()

    status = "enabled" if item.is_active else "disabled"
    messages.success(request, f"'{item.product_name}' has been {status}.")
    return redirect("catalogue:view_catalogue", sponsor_id=sponsor.id)



# --------------------------
# CART VIEWS
# --------------------------
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


@login_required
def clear_cart(request):
    if not request.user.is_driver:
        messages.error(request, "Only drivers can modify the cart.")
        return redirect("home")
    
    if request.method == "POST":
        deleted_count = CartItem.objects.filter(user=request.user).delete()[0]
        if deleted_count > 0:
            messages.success(request, "Cart cleared successfully.")
        else:
            messages.info(request, "Cart is already empty.")
    
    return redirect("catalogue:view_cart")


# --------------------------
# ORDER / CHECKOUT FLOWS
# --------------------------

@login_required
def checkout_submit(request):
    """
    Turn current cart into an Order, deduct points, clear cart.
    """
    if not getattr(request.user, "is_driver", False):
        messages.error(request, "Only drivers can place orders.")
        return redirect("home")

    driver = request.user
    cart_items = CartItem.objects.filter(user=driver).select_related("catalogue_item")

    if not cart_items.exists():
        messages.error(request, "Your cart is empty.")
        return redirect("catalogue:view_cart")

    # assume all items are from same org catalogue
    first_item = cart_items.first()
    org = first_item.catalogue_item.catalogue.organization if first_item else None

    with transaction.atomic():
        order = Order.objects.create(
            driver=driver,
            organization=org,
            status=Order.STATUS_PENDING,
        )

        total_points_cost = 0

        # copy cart items into order items
        for ci in cart_items:
            item = ci.catalogue_item
            line_cost = (item.price or 0) * ci.quantity
            total_points_cost += line_cost

            OrderItem.objects.create(
                order=order,
                catalogue_item=item,
                product_name=item.product_name,
                product_id=item.product_id,
                price_each=item.price,
                quantity=ci.quantity,
            )

        # deduct points using existing helper
        if total_points_cost > 0:
            ok, msg = award_points_to_driver(
                sponsor_user=None,   # this is a redemption, not a sponsor gift
                driver_user=driver,
                points=-int(total_points_cost),
                reason=f"Order #{order.id} redemption",
            )
            if not ok:
                messages.error(request, f"Could not submit order: {msg}")
                raise transaction.TransactionManagementError(msg)

        # snapshot balance
        driver.refresh_from_db()
        order.balance_after_submit = driver.driverprofile.current_points
        order.save(update_fields=["balance_after_submit"])

        # clear cart
        cart_items.delete()

        # >>> CHANGED: send a clear, linkable notification with the order number
        order_url = reverse("catalogue:order_detail", kwargs={"order_id": order.id})
        send_driver_notification(
            driver_user=driver,
            content=f"Your order #{order.id} has been placed.",
            notif_type="order_placed",
            metadata_extra={
                "order_id": order.id,
                "link": order_url,
                "total_points": int(total_points_cost),
            },
        )

    messages.success(request, f"Order #{order.id} submitted!")
    return redirect("catalogue:order_detail", order_id=order.id)


@login_required
def my_orders(request):
    """
    Show list of all orders for this driver.
    """
    if not getattr(request.user, "is_driver", False):
        messages.error(request, "Only drivers can view orders.")
        return redirect("home")

    orders = (
        Order.objects.filter(driver=request.user)
        .order_by("-created_at")
        .prefetch_related("items")
    )

    return render(request, "catalogue/my_orders.html", {"orders": orders})


@login_required
def order_detail(request, order_id):
    """
    Show one specific order and its items.
    """
    order = get_object_or_404(Order, id=order_id, driver=request.user)

    return render(request, "catalogue/order_detail.html", {
        "order": order,
        "editable": order.is_editable,
    })


@login_required
def cancel_order(request, order_id):
    """
    Cancel an order if still pending and refund points.
    """
    order = get_object_or_404(Order, id=order_id, driver=request.user)

    if not order.is_editable:
        messages.error(request, "This order can no longer be cancelled.")
        return redirect("catalogue:order_detail", order_id=order.id)

    refund_points = order.total_cost_points

    with transaction.atomic():
        # mark cancelled
        order.status = Order.STATUS_CANCELLED
        order.save(update_fields=["status"])

        # refund points
        if refund_points > 0:
            ok, msg = award_points_to_driver(
                sponsor_user=None,
                driver_user=request.user,
                points=int(refund_points),
                reason=f"Refund for cancelled Order #{order.id}",
            )
            if not ok:
                messages.error(request, f"Order cancelled but refund issue: {msg}")

        order_url = reverse("catalogue:order_detail", kwargs={"order_id": order.id})
        send_driver_notification(
            driver_user=request.user,
            content=f"Order #{order.id} was cancelled. {refund_points} points refunded.",
            notif_type="order_cancelled",
            metadata_extra={
                "order_id": order.id,
                "link": order_url,
                "refunded_points": int(refund_points) if refund_points else 0,
            },
        )

    messages.success(request, f"Order #{order.id} cancelled and points refunded.")
    return redirect("catalogue:my_orders")