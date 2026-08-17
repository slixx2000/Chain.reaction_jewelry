from django.contrib import admin
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html

from .models import SiteContent

admin.site.site_header = 'Chain Reaction'
admin.site.site_title = 'Chain Reaction admin'
admin.site.index_title = 'Shop management'
admin.site.empty_value_display = '—'


@admin.register(SiteContent)
class SiteContentAdmin(admin.ModelAdmin):
    """A single always-present row, so the list view just jumps straight to it."""

    readonly_fields = ('hero_preview', 'studio_preview', 'updated_at')
    fieldsets = (
        ('Landing page banner', {
            'fields': ('hero_image', 'hero_image_alt', 'hero_preview'),
            'description': 'This is the full-width image behind the headline on the home page. '
                           'Landscape works best — the headline sits over the middle, so avoid '
                           'putting the subject dead centre. Clear the image to go back to the '
                           'placeholder.',
        }),
        ('Studio / flat-lay', {
            'fields': ('studio_image', 'studio_image_alt', 'studio_preview'),
            'description': 'The tall image beside the “Why us” story further down the home '
                           'page. Portrait works best, around 1200 × 1600. Clear the image '
                           'to go back to the placeholder.',
        }),
        (None, {'fields': ('updated_at',)}),
    )

    def has_add_permission(self, request):
        return False  # load() guarantees the row exists.

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        content = SiteContent.load()
        return redirect(reverse('admin:core_sitecontent_change', args=[content.pk]))

    @admin.display(description='Preview')
    def hero_preview(self, content):
        if not content.hero_image:
            return 'No banner uploaded — the home page is showing the placeholder.'
        return format_html(
            '<img src="{}" style="max-width:520px;width:100%;display:block">',
            content.hero_image.url,
        )

    @admin.display(description='Preview')
    def studio_preview(self, content):
        if not content.studio_image:
            return 'No photo uploaded — the home page is showing the placeholder.'
        return format_html(
            '<img src="{}" style="max-width:320px;width:100%;display:block">',
            content.studio_image.url,
        )
