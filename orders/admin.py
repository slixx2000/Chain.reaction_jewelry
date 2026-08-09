from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('item', 'name', 'price', 'quantity')
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('reference', 'full_name', 'phone', 'operator', 'total', 'status', 'created_at')
    list_filter = ('status', 'operator', 'created_at')
    search_fields = ('reference', 'full_name', 'phone', 'email', 'bila_collection_id')
    readonly_fields = (
        'reference', 'total', 'currency', 'bila_collection_id', 'bila_status',
        'failure_reason', 'created_at', 'updated_at', 'paid_at',
    )
    inlines = (OrderItemInline,)
    date_hierarchy = 'created_at'
