from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm


class RegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']


class CheckoutForm(forms.Form):
    full_name = forms.CharField(max_length=200)
    address = forms.CharField(widget=forms.Textarea)
    phone = forms.CharField(max_length=20)


class PaymentForm(forms.Form):
    PAYMENT_CHOICES = [
        ('COD', 'Cash on Delivery'),
        ('UPI', 'UPI'),
        ('CARD', 'Credit/Debit Card'),
    ]

    payment_method = forms.ChoiceField(
        choices=PAYMENT_CHOICES,
        widget=forms.RadioSelect
    )