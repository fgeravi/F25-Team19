# users/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
# Import your custom User model
from .models import User  # Or from users.models import User

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta:
        model = User
        fields = ['username', 'email']