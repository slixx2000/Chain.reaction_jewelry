from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.shortcuts import render, redirect
from item.models import Item, Category
from .forms import SignUpForm
# Create your views here.


def index(request):
    items = Item.objects.all()
    categories = Category.objects.all()
    return render(request, 'core/index.html', {'items': items, 'categories': categories})

def contact(request):
    return render(request, 'core/contact.html')

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            form.save()

            return redirect('/login/')
            # You can add a success message or redirect to a login page here
    else:
        form = SignUpForm()
    return render(request, 'core/signup.html', {'form': form})

def logout(request):
    auth_logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('core:index')