# ================================
# models.py
# ================================

from django.db import models
from django.contrib.auth.models import User


# ---------------- CATEGORY ----------------
class Category(models.Model):

    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


# ---------------- PRODUCT ----------------
class Product(models.Model):

    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    name = models.CharField(max_length=200)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True
    )

    description = models.TextField()

    stock = models.PositiveIntegerField(default=0)

    image = models.ImageField(
        upload_to='products/',
        blank=True,
        null=True
    )

    organic = models.BooleanField(default=True)

    featured = models.BooleanField(default=False)

    fast_delivery = models.BooleanField(default=True)

    rating = models.FloatField(default=4.5)

    created_at = models.DateTimeField(auto_now_add=True)

    def final_price(self):

        if self.discount_price:
            return self.discount_price

        return self.price

    def __str__(self):
        return self.name


# ---------------- CART ----------------
class Cart(models.Model):

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField(default=1)

    def subtotal(self):

        return self.product.final_price() * self.quantity

    def __str__(self):

        return f"{self.user.username} - {self.product.name}"


# ---------------- ORDER ----------------
class Order(models.Model):

    STATUS_CHOICES = [

        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled'),

    ]

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE
    )

    full_name = models.CharField(max_length=200)

    address = models.TextField()

    phone = models.CharField(max_length=20)

    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='Pending'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):

        return f"Order #{self.id}"


# ---------------- ORDER ITEM ----------------
class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE
    )

    quantity = models.PositiveIntegerField()

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def subtotal(self):

        return self.price * self.quantity

    def __str__(self):

        return f"{self.product.name} x {self.quantity}"