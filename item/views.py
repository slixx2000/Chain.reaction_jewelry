from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from .models import Item, Category
from .forms import EditItemForm, newItemForm



def items(request):
    items = Item.objects.filter(is_sold=False).order_by('-created_at')
    categories = Category.objects.all()
    selected_category = request.GET.get('category', '')
    query = request.GET.get('q', '').strip()

    if selected_category:
        items = items.filter(category_id=selected_category)

    if query:
        items = items.filter(Q(name__icontains=query) | Q(description__icontains=query))

    return render(
        request,
        'item/items.html',
        {
            'items': items,
            'categories': categories,
            'selected_category': selected_category,
            'query': query,
        },
    )

def detail(request, pk):
    item = get_object_or_404(Item, pk=pk)
    related_items = Item.objects.filter(category=item.category).exclude(pk=item.pk)[:4]

    return render(request, 'item/detail.html', {
        'item': item,
        'related_items': related_items,
    })
    
@login_required    
def new_item(request):
    if request.method == 'POST':
        form = newItemForm(request.POST, request.FILES)
        if form.is_valid():
            item = form.save(commit=False)
            item.created_by = request.user
            item.save()
            return redirect('item:detail', pk=item.id)
    else:
        form = newItemForm()
    return render(request, 'item/new_item.html', 
                  {'form': form, 
                   'title': 'Add New Item'
                   })

@login_required
def edit(request, pk):
    item = get_object_or_404(Item, pk=pk, created_by=request.user)

    if request.method == 'POST':
        form = EditItemForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            form.save()
            return redirect('item:detail', pk=item.id)
    else:
        form = EditItemForm(instance=item)

    return render(request, 'item/edit_item.html', {
        'form': form,
        'title': 'Edit Item',
        'item': item,
    })


@login_required
def delete(request, pk):
    item = get_object_or_404(Item, pk=pk, created_by=request.user)
    item.delete()

    return redirect('dashboard:index')

