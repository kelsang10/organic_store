from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.db.models import Q, Sum
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .models import (
    Product, Cart, Order, OrderItem,
    Category, KnowledgeBase, SustainabilityArticle
)

from .forms import RegisterForm, CheckoutForm
from .rag_engine import get_ai_answer

# ================= HOME =================
def home(request):

    query = request.GET.get('q')
    category_id = request.GET.get('category')

    products = Product.objects.all()

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query)
        )

    if category_id:
        products = products.filter(category_id=category_id)

    cart_count = 0
    if request.user.is_authenticated:
        cart_count = Cart.objects.filter(user=request.user).count()

    categories = Category.objects.all()

    return render(request, 'shop/home.html', {
        'products': products,
        'categories': categories,
        'cart_count': cart_count,
        'query': query,
    })


# ================= CART =================
@login_required
def add_to_cart(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    cart_item, created = Cart.objects.get_or_create(
        user=request.user,
        product=product
    )

    if created:
        if product.stock < 1:
            messages.error(request, "Product out of stock")
            return redirect('home')
        cart_item.quantity = 1
    else:
        if cart_item.quantity + 1 > product.stock:
            messages.error(request, "Not enough stock available")
            return redirect('home')
        cart_item.quantity += 1

    cart_item.save()

    messages.success(request, "Item added to cart")
    return redirect('home')


@login_required
def cart_view(request):

    cart_items = Cart.objects.select_related('product').filter(user=request.user)

    total = sum(item.product.price * item.quantity for item in cart_items)

    return render(request, 'shop/cart.html', {
        'cart_items': cart_items,
        'total': total,
    })


@login_required
def remove_from_cart(request, cart_id):

    item = get_object_or_404(Cart, id=cart_id, user=request.user)
    item.delete()

    messages.success(request, "Item removed from cart")
    return redirect('cart')


# ================= CHECKOUT =================
@login_required
def checkout(request):

    cart_items = Cart.objects.filter(user=request.user)

    if not cart_items.exists():
        messages.error(request, "Your cart is empty")
        return redirect('home')

    total = sum(item.product.price * item.quantity for item in cart_items)

    if request.method == 'POST':

        form = CheckoutForm(request.POST)

        if form.is_valid():

            # validate stock first
            for item in cart_items:
                if item.quantity > item.product.stock:
                    messages.error(request, f"Not enough stock for {item.product.name}")
                    return redirect('cart')

            order = Order.objects.create(
                user=request.user,
                full_name=form.cleaned_data['full_name'],
                address=form.cleaned_data['address'],
                phone=form.cleaned_data['phone'],
                total_amount=total,
                status="Pending"
            )

            for item in cart_items:
                product = item.product

                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item.quantity,
                    price=product.price,
                )

                product.stock -= item.quantity
                product.save()

            cart_items.delete()

            return redirect('payment', order_id=order.id)

    else:
        form = CheckoutForm()

    return render(request, 'shop/checkout.html', {
        'form': form,
        'total': total,
    })


# ================= AI PAGE =================
def ai_agent(request):

    answer = ""
    products = []
    source = ""

    if request.method == "POST":

        question = request.POST.get(
            "question",
            ""
        ).strip()

        result = get_ai_answer(question)

        answer = result["answer"]
        source = result["source"]

        products = Product.objects.filter(
            organic=True
        )[:3]

    return render(
        request,
        "shop/ai_agent.html",
        {
            "answer": answer,
            "products": products,
            "source": source
        }
    )


# ================= CHAT API =================
@csrf_exempt
def agent_chat(request):

    if request.method != "POST":
        return JsonResponse({
            "answer": "Only POST requests allowed."
        })

    question = request.POST.get(
        "question",
        ""
    ).strip()

    if not question:
        return JsonResponse({
            "answer": "Please ask a question."
        })

    # Store-related questions
    if "delivery" in question.lower():

        answer = (
            "Yes, we provide home delivery "
            "for organic products."
        )

        source = "System"

    elif (
        "order" in question.lower()
        or
        "buy" in question.lower()
    ):

        answer = (
            "You can order products using "
            "the cart and checkout system."
        )

        source = "System"

    elif (
        "price" in question.lower()
        or
        "cost" in question.lower()
    ):

        answer = (
            "Product prices are shown on "
            "the product details page."
        )

        source = "System"

    else:

        result = get_ai_answer(question)

        answer = result["answer"]
        source = result["source"]

    products = Product.objects.filter(
        organic=True
    )[:3]

    return JsonResponse({
        "answer": answer,
        "source": source,
        "products": list(
            products.values(
                "id",
                "name",
                "price"
            )
        )
    })

# ================= PAYMENT =================
@login_required
def payment(request, order_id):

    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method == 'POST':

        method = request.POST.get('payment_method')

        if method == "UPI":
            upi_id = request.POST.get('upi_id')
            if not upi_id:
                messages.error(request, "Enter UPI ID")
                return render(request, "shop/payment.html", {'order': order})

            return render(request, "shop/payment_success.html", {
                "order": order,
                "payment_method": "UPI"
            })

        elif method == "CARD":
            card = request.POST.get('card_number')
            cvv = request.POST.get('cvv')

            if not card or not cvv:
                messages.error(request, "Enter card details")
                return render(request, "shop/payment.html", {'order': order})

            return render(request, "shop/payment_success.html", {
                "order": order,
                "payment_method": "CARD"
            })

        elif method == "COD":
            return render(request, "shop/payment_success.html", {
                "order": order,
                "payment_method": "COD"
            })

        else:
            messages.error(request, "Select payment method")

    return render(request, "shop/payment.html", {'order': order})


# ================= AUTH =================
def register_view(request):

    form = RegisterForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        user = form.save()
        auth_login(request, user)
        return redirect("home")

    return render(request, "shop/register.html", {"form": form})


def login_view(request):

    form = AuthenticationForm(data=request.POST or None)

    if request.method == "POST" and form.is_valid():
        auth_login(request, form.get_user())
        return redirect("home")

    return render(request, "shop/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("home")


# ================= DASHBOARD =================
@login_required
def dashboard(request):

    if not request.user.is_staff:
        return redirect("home")

    return render(request, "shop/dashboard.html", {
        "total_products": Product.objects.count(),
        "total_orders": Order.objects.count(),
        "total_users": User.objects.count(),

        "total_revenue": Order.objects.aggregate(
            total=Sum('total_amount')
        )['total'] or 0,

        "pending_orders": Order.objects.filter(status="Pending").count(),
        "delivered_orders": Order.objects.filter(status="Delivered").count(),

        "recent_orders": Order.objects.all().order_by("-created_at")[:10],

        "labels": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
        "sales": [1200, 1800, 1400, 2500, 2100, 3000, 2800],
    })