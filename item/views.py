from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from .models import Item, Category
from .forms import ItemForm



def items(request):
    # Sold pieces stay in the grid as proof the work sells, but always sort last.
    items = Item.objects.select_related('category').order_by('is_sold', '-created_at')
    categories = Category.objects.all()
    selected_category = request.GET.get('category', '')
    query = request.GET.get('q', '').strip()

    if selected_category:
        items = items.filter(category_id=selected_category)

    if query:
        items = items.filter(Q(name__icontains=query) | Q(description__icontains=query))

    sold_count = items.filter(is_sold=True).count()
    page = Paginator(items, 12).get_page(request.GET.get('page'))

    return render(
        request,
        'item/items.html',
        {
            'items': page,
            'page': page,
            'categories': categories,
            'selected_category': selected_category,
            'query': query,
            'sold_count': sold_count,
            'available_count': page.paginator.count - sold_count,
        },
    )

def detail(request, pk):
    item = get_object_or_404(Item.objects.select_related('category'), pk=pk)
    related_items = Item.objects.filter(
        category=item.category, is_sold=False
    ).exclude(pk=item.pk)[:4]

    return render(request, 'item/detail.html', {
        'item': item,
        'related_items': related_items,
    })

@login_required
def new_item(request):
    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.created_by = request.user
            item.save()
            messages.success(request, f'"{item.name}" has been listed.')
            return redirect('item:detail', pk=item.id)
    else:
        form = ItemForm()
    return render(request, 'item/new_item.html',
                  {'form': form,
                   'title': 'Add New Item'
                   })

@login_required
def edit(request, pk):
    item = get_object_or_404(Item, pk=pk, created_by=request.user)

    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Changes saved.')
            return redirect('item:detail', pk=item.id)
    else:
        form = ItemForm(instance=item)

    return render(request, 'item/edit_item.html', {
        'form': form,
        'title': 'Edit Item',
        'item': item,
    })


@login_required
@require_POST
def delete(request, pk):
    item = get_object_or_404(Item, pk=pk, created_by=request.user)
    name = item.name
    item.delete()
    messages.success(request, f'"{name}" has been deleted.')

    return redirect('dashboard:index')
