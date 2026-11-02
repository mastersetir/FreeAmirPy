from django import forms
from django.contrib.auth.forms import AuthenticationForm

from .models import User

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="نام کاربری",
        widget=forms.TextInput(attrs={"class": "form-input", "autofocus": True}),
    )
    password = forms.CharField(
        label="رمز عبور",
        widget=forms.PasswordInput(attrs={"class": "form-input"}),
    )

class UserCreateForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, label="رمز عبور")

    class Meta:
        model = User
        fields = ("username", "first_name", "last_name", "email", "phone", "role")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user
