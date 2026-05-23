from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q, Sum
from django.contrib.auth.models import User
from django.contrib import messages

from .models import Product, Cart, Order, OrderItem,Category
from .forms import RegisterForm, CheckoutForm


# ---------------- HOME ----------------

def home(request):

    query = request.GET.get('q')
    category_id = request.GET.get('category')

    products = Product.objects.all()

    # SEARCH
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    # CATEGORY FILTER
    if category_id:
        products = products.filter(category_id=category_id)

    # GET ALL CATEGORIES
    categories = Category.objects.all()

    # CART COUNT
    cart_count = 0

    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(
            user=request.user
        ).count()

    return render(request, 'shop/home.html', {

        'products': products,
        'categories': Category.objects.all(),
        'cart_count': cart_count,
        'query': query,

    })

# ---------------- ADD TO CART ----------------
@login_required
def add_to_cart(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        product=product
    )

    # NEW ITEM
    if created:

        if product.stock < 1:
            messages.error(request, "Product out of stock")
            return redirect('home')

        cart_item.quantity = 1
        cart_item.save()

    # EXISTING ITEM
    else:

        if cart_item.quantity + 1 > product.stock:
            messages.error(request, "Not enough stock available")
            return redirect('home')

        cart_item.quantity += 1
        cart_item.save()

    messages.success(request, "Item added to cart")

    return redirect('home')


# ---------------- CART ----------------
@login_required
def cart_view(request):

    cart_items = Cart.objects.filter(user=request.user)

    total = sum(
        item.product.price * item.quantity
        for item in cart_items
    )

    return render(request, 'shop/cart.html', {
        'cart_items': cart_items,
        'total': total,
    })


# ---------------- REMOVE FROM CART ----------------
@login_required
def remove_from_cart(request, cart_id):

    item = get_object_or_404(
        Cart,
        id=cart_id,
        user=request.user
    )

    item.delete()

    messages.success(request, "Item removed from cart")

    return redirect('cart')


# ---------------- CHECKOUT ----------------
@login_required
def checkout(request):

    cart_items = Cart.objects.filter(user=request.user)

    if not cart_items.exists():
        messages.error(request, "Your cart is empty")
        return redirect('home')

    total = sum(
        item.product.price * item.quantity
        for item in cart_items
    )

    if request.method == 'POST':

        form = CheckoutForm(request.POST)

        if form.is_valid():

            # CREATE ORDER
            order = Order.objects.create(
                user=request.user,
                full_name=form.cleaned_data['full_name'],
                address=form.cleaned_data['address'],
                phone=form.cleaned_data['phone'],
                total_amount=total,
                status="Pending"
            )

            # CREATE ORDER ITEMS
            for item in cart_items:

                product = item.product

                # STOCK CHECK
                if item.quantity > product.stock:

                    messages.error(
                        request,
                        f"Not enough stock for {product.name}"
                    )

                    order.delete()

                    return redirect('cart')

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item.quantity,
                    price=product.price,
                )

                # REDUCE STOCK
                product.stock -= item.quantity
                product.save()

            # CLEAR CART
            cart_items.delete()

            return redirect(
                'payment',
                order_id=order.id
            )

    else:
        form = CheckoutForm()

    return render(request, 'shop/checkout.html', {
        'form': form,
        'total': total,
    })


# ---------------- PAYMENT ----------------
# ---------------- PAYMENT ----------------
@login_required
def payment(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    if request.method == 'POST':

        payment_method = request.POST.get('payment_method')

        # ---------------- UPI ----------------
        if payment_method == "UPI":

            upi_id = request.POST.get('upi_id')

            if not upi_id:
                messages.error(request, "Please enter UPI ID")

                return render(request, 'shop/payment.html', {
                    'order': order,
                })

            return render(request, 'shop/payment_success.html', {

                'order': order,
                'payment_method': 'UPI',
                'upi_id': upi_id,

            })

        # ---------------- CARD ----------------
        elif payment_method == "CARD":

            card_number = request.POST.get('card_number')
            cvv = request.POST.get('cvv')

            if not card_number or not cvv:

                messages.error(request, "Please enter card details")

                return render(request, 'shop/payment.html', {
                    'order': order,
                })

            return render(request, 'shop/payment_success.html', {

                'order': order,
                'payment_method': 'CARD',

            })

        # ---------------- COD ----------------
        elif payment_method == "COD":

            return render(request, 'shop/payment_success.html', {

                'order': order,
                'payment_method': 'Cash on Delivery',

            })

        else:

            messages.error(request, "Please select payment method")

            return render(request, 'shop/payment.html', {
                'order': order,
            })

    return render(request, 'shop/payment.html', {
        'order': order,
    })
# ---------------- REGISTER ----------------
def register_view(request):

    form = RegisterForm(request.POST or None)

    if request.method == 'POST':

        if form.is_valid():

            user = form.save()

            login(request, user)

            return redirect('home')

    return render(
        request,
        'shop/register.html',
        {
            'form': form
        }
    )


# ---------------- LOGIN ----------------
def login_view(request):

    form = AuthenticationForm(
        data=request.POST or None
    )

    if request.method == 'POST':

        if form.is_valid():

            login(
                request,
                form.get_user()
            )

            return redirect('home')

    return render(
        request,
        'shop/login.html',
        {
            'form': form
        }
    )


# ---------------- LOGOUT ----------------
def logout_view(request):

    logout(request)

    return redirect('home')


# ---------------- DASHBOARD ----------------
@login_required
def dashboard(request):

    if not request.user.is_staff:
        return redirect('home')

    # TOTAL COUNTS
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    total_users = User.objects.count()

    # REVENUE
    total_revenue = Order.objects.aggregate(
        total=Sum('total_amount')
    )['total'] or 0

    # ORDER STATUS
    pending_orders = Order.objects.filter(
        status='Pending'
    ).count()

    delivered_orders = Order.objects.filter(
        status='Delivered'
    ).count()

    # RECENT ORDERS
    recent_orders = Order.objects.all().order_by(
        '-created_at'
    )[:10]

    # SALES ANALYTICS
    labels = [
        "Mon",
        "Tue",
        "Wed",
        "Thu",
        "Fri",
        "Sat",
        "Sun"
    ]

    sales = [
        1200,
        1800,
        1400,
        2500,
        2100,
        3000,
        2800
    ]

    return render(request, 'shop/dashboard.html', {

        'total_products': total_products,
        'total_orders': total_orders,
        'total_users': total_users,
        'total_revenue': total_revenue,

        'pending_orders': pending_orders,
        'delivered_orders': delivered_orders,

        'recent_orders': recent_orders,

        'labels': labels,
        'sales': sales,
    })