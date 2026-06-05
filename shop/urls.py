from django.urls import path
from . import views
from .views import agent_chat

urlpatterns = [
    path("", views.home, name="home"),

    path("add-to-cart/<int:product_id>/", views.add_to_cart, name="add_to_cart"),
    path("cart/", views.cart_view, name="cart"),
    path("remove-from-cart/<int:cart_id>/", views.remove_from_cart, name="remove_from_cart"),

    path("checkout/", views.checkout, name="checkout"),
    path("payment/<int:order_id>/", views.payment, name="payment"),

    path("register/", views.register_view, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path('ai-agent/', views.ai_agent, name='ai_agent'),
    path("dashboard/", views.dashboard, name="dashboard"),

    path("chat/", agent_chat, name="agent_chat"),
]