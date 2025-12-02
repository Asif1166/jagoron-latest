from .forms import SimpleRegisterForm
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from .forms import EmailLoginForm
from django.contrib.auth.models import User
# Create your views here.
def register(request):
    if request.method == 'POST':
        form = SimpleRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('/')  # or wherever you want to redirect
    else:
        form = SimpleRegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


def login_view(request):
    form = EmailLoginForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            try:
                user = User.objects.get(email=email)
                user = authenticate(request, username=user.username, password=password)
                if user:
                    login(request, user)
                    return redirect('/')  # Or wherever you want
            except User.DoesNotExist:
                pass

            form.add_error(None, 'Invalid email or password.')

    return render(request, 'accounts/login.html', {'form': form})


@login_required
def profile(request):
    return render(request, 'accounts/profile.html')


def custom_logout(request):
    logout(request)
    return redirect('login') 