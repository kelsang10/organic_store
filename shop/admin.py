from django.contrib import admin
from .models import Category, Product, Cart, Order, OrderItem


# ---------------- CATEGORY ----------------
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ('name',)


# ---------------- PRODUCT ----------------
@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'price', 'category')
    list_filter = ('category',)
    search_fields = ('name',)
    list_editable = ('price',)
    ordering = ('id',)


# ---------------- CART ----------------
@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'product', 'quantity')
    list_filter = ('user',)
    search_fields = ('user__username', 'product__name')


# ---------------- ORDER ----------------
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username',)
    list_editable = ('status',)
    ordering = ('-created_at',)


# ---------------- ORDER ITEM ----------------
@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'product', 'quantity', 'price')
    search_fields = ('order__id', 'product__name')