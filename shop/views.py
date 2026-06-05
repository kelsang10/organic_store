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
from .utils import build_context, get_ai_answer


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


# ================= AI HELPERS =================
def build_context():
    articles = SustainabilityArticle.objects.all()

    context = []

    for a in articles:
        if a.content:
            chunks = a.content.split()

            for i in range(0, len(chunks), 200):
                context.append({
                    "text": " ".join(chunks[i:i+200]),
                    "source": a.title
                })

    return context


def get_ai_answer(question, context):

    question = question.lower()
    keywords = [w for w in question.split() if len(w) > 3]

    best_match = None
    best_score = 0

    for item in context:

        text = item["text"].lower()

        score = sum(1 for k in keywords if k in text)

        if question in text:
            score += 5

        if len(text) > 800:
            score -= 1

        if score > best_score:
            best_score = score
            best_match = item

    if best_match and best_score >= 2:
        return {
            "answer": best_match["text"],
            "source": best_match["source"]
        }

    return {
        "answer": "No relevant article found in admin database.",
        "source": None
    }


# ================= AI PAGE =================
def ai_agent(request):

    answer = ""
    products = []
    source = ""

    if request.method == "POST":

        question = request.POST.get("question", "").strip().lower()

        context = build_context()

        if "organic farming" in question:
            answer = "Organic farming reduces chemicals and improves soil health."
            source = "System"
            products = Product.objects.filter(organic=True)[:3]

        elif "food waste" in question:
            answer = "Reducing food waste helps environment and saves resources."
            source = "System"
            products = Product.objects.filter(organic=True)[:3]

        elif "immunity" in question:
            answer = "Citrus fruits, ginger, turmeric boost immunity."
            source = "System"
            products = Product.objects.filter(organic=True)[:3]

        elif "protein" in question:
            answer = "Beans, lentils, nuts are high in protein."
            source = "System"
            products = Product.objects.all()[:3]

        else:
            result = get_ai_answer(question, context)
            answer = result["answer"]
            source = result["source"]
            products = Product.objects.filter(organic=True)[:3]

    return render(request, "shop/ai_agent.html", {
        "answer": answer,
        "products": products,
        "source": source
    })


# ================= CHAT API =================
@csrf_exempt
def agent_chat(request):

    if request.method != "POST":
        return JsonResponse({"answer": "Only POST allowed"})

    question = request.POST.get("question", "").strip().lower()

    if not question:
        return JsonResponse({"answer": "Please ask a question."})

    context = build_context()

    if "delivery" in question or "deliver" in question:
        answer = "Yes, we provide home delivery for organic products."
        source = "System"

    elif "order" in question or "buy" in question:
        answer = "You can order products from our website cart."
        source = "System"

    elif "price" in question or "cost" in question:
        answer = "Prices depend on product type. Check product page."
        source = "System"

    else:
        result = get_ai_answer(question, context)
        answer = result["answer"]
        source = result["source"]

    products = Product.objects.filter(organic=True)[:3]

    return JsonResponse({
        "answer": answer,
        "source": source,
        "products": list(products.values("id", "name", "price"))
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