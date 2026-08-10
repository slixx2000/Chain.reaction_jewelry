from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from core.storefront import placements

from .models import Category, Item

LABEL_STYLE = (
    '<span style="background:{};color:{};padding:2px 8px;border-radius:10px;'
    'font-size:11px;margin-right:4px;white-space:nowrap">{}</span>'
)
MUTED = '<span style="color:#999">{}</span>'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'available_count', 'sold_count')
    search_fields = ('name',)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _available=Count('items', filter=Q(items__is_sold=False)),
            _sold=Count('items', filter=Q(items__is_sold=True)),
        )

    @admin.display(description='For sale', ordering='_available')
    def available_count(self, category):
        return category._available

    @admin.display(description='Sold', ordering='_sold')
    def sold_count(self, category):
        return category._sold


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    # get_list_display() splices in the placement column; this is the checkable baseline.
    list_display = ('preview', 'name', 'category', 'price', 'badge', 'is_sold', 'created_at')
    list_display_links = ('preview', 'name')
    list_editable = ('price', 'badge', 'is_sold')
    list_filter = ('is_sold', 'badge', 'category', 'created_at')
    search_fields = ('name', 'description')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'large_preview')
    list_per_page = 25
    actions = ('mark_as_sold', 'mark_as_available', 'clear_badge')

    fieldsets = (
        ('What you are selling', {
            'fields': ('name', 'category', 'description'),
            'description': 'The name shows on every card. Keep it short — long names are '
                           'truncated on the storefront.',
        }),
        ('Price and availability', {
            'fields': ('price', 'badge', 'is_sold'),
            'description': 'Prices are in ZMW. Ticking <b>sold</b> pulls the piece off the shop '
                           'immediately — it stops appearing anywhere and can no longer be added '
                           'to a bag. Paid orders tick this for you. A <b>badge</b> is the corner '
                           'label on the card; sold pieces show a grey "Sold Out" stamp instead.',
        }),
        ('Photo', {
            'fields': ('image', 'large_preview'),
            'description': 'Square images look best. Cards crop to a landscape strip, so keep the '
                           'piece centred.',
        }),
        ('Record', {
            'fields': ('created_by', 'created_at'),
            'classes': ('collapse',),
            'description': 'Newest pieces lead the storefront, so this date decides the running order.',
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category', 'created_by')

    def get_list_display(self, request):
        """Built per request so the placement lookup runs once, not once per row."""
        where = placements()

        @admin.display(description='Shows on')
        def shows_on(item):
            if item.is_sold:
                return format_html(MUTED, 'Sold — hidden')

            labels = []
            if item.pk == where['hero_id']:
                labels.append(('#d29f22', '#000', 'Hero'))
            if item.pk in where['best_seller_ids']:
                labels.append(('#5d0018', '#fff', 'Best seller'))
            if item.pk in where['new_arrival_ids'] and item.pk != where['hero_id']:
                labels.append(('#252628', '#ddd', 'New arrivals'))

            if not labels:
                return format_html(MUTED, 'Browse page only')

            return format_html_join('', LABEL_STYLE, labels)

        columns = list(self.list_display)
        columns.insert(columns.index('created_at'), shows_on)
        return tuple(columns)

    @admin.display(description='')
    def preview(self, item):
        if not item.image:
            return mark_safe(
                '<div style="width:56px;height:56px;background:#2b2b2b;border-radius:6px;'
                'display:flex;align-items:center;justify-content:center;color:#777;'
                'font-size:10px">no photo</div>'
            )
        return format_html(
            '<img src="{}" style="width:56px;height:56px;object-fit:cover;border-radius:6px">',
            item.image.url,
        )

    @admin.display(description='Current photo')
    def large_preview(self, item):
        if not item.image:
            return 'No photo uploaded yet.'
        return format_html(
            '<img src="{}" style="max-width:320px;border-radius:8px">', item.image.url
        )

    def save_model(self, request, obj, form, change):
        if not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    @admin.action(description='Mark selected as sold (removes them from the shop)')
    def mark_as_sold(self, request, queryset):
        updated = queryset.update(is_sold=True)
        self.message_user(request, f'{updated} piece(s) marked sold and pulled from the shop.')

    @admin.action(description='Mark selected as available (puts them back on sale)')
    def mark_as_available(self, request, queryset):
        updated = queryset.update(is_sold=False)
        self.message_user(request, f'{updated} piece(s) are back on sale.')

    @admin.action(description='Remove the badge from selected pieces')
    def clear_badge(self, request, queryset):
        updated = queryset.update(badge='')
        self.message_user(request, f'Badge removed from {updated} piece(s).')
