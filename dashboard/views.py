from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render

from item.models import Item

@login_required
def index(request):
    items = Item.objects.filter(created_by=request.user).order_by('-created_at')
    available = items.filter(is_sold=False)

    return render(request, 'dashboard/index.html', {
        'items': items,
        'sold_count': items.filter(is_sold=True).count(),
        'available_value': available.aggregate(total=Sum('price'))['total'] or 0,
    })
