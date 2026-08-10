from django.contrib import messages
from django.contrib.auth import logout as auth_logout
from django.db.models import Count, Q
from django.shortcuts import render, redirect
from item.models import Category
from . import storefront
from .forms import SignUpForm
# Create your views here.


def index(request):
    new_arrivals = storefront.new_arrivals()

    return render(request, 'core/index.html', {
        'hero_item': new_arrivals[0] if new_arrivals else None,
        'new_arrivals': new_arrivals,
        # The whole catalogue, not just the slice shown above.
        'available_count': storefront.available_items().count(),
        'best_sellers': storefront.best_sellers(),
        'categories': Category.objects.annotate(
            available_count=Count('items', filter=Q(items__is_sold=False))
        ).filter(available_count__gt=0),
    })

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
