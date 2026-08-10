"""Re-run the resize pipeline over images uploaded before it existed."""
from django.core.management.base import BaseCommand

from core import images
from core.models import SiteContent
from item.models import Item


class Command(BaseCommand):
    help = 'Resize and re-encode existing product images and the hero banner.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **options):
        before = after = 0
        done = 0

        for item in Item.objects.exclude(image=''):
            if not item.image:
                continue
            try:
                original = item.image.size
            except (FileNotFoundError, ValueError):
                self.stderr.write(f'  missing file for {item.name}, skipped')
                continue

            if options['dry_run']:
                self.stdout.write(f'  would reprocess {item.name} ({original/1024:.0f}KB)')
                continue

            full = images.full(item.image)
            item.image.save(full.name, full, save=False)
            thumb = images.thumbnail(item.image)
            item.thumbnail.save(thumb.name, thumb, save=False)
            # _original_image already matches, so save() will not re-encode.
            item._original_image = item.image.name
            super(Item, item).save()

            before += original
            after += item.image.size + item.thumbnail.size
            done += 1

        content = SiteContent.load()
        if content.hero_image and not options['dry_run']:
            resized = images.process(content.hero_image, max_side=2200)
            content.hero_image.save(resized.name, resized, save=False)
            content._original_hero = content.hero_image.name
            content.save()
            self.stdout.write('  hero banner reprocessed')

        if done:
            self.stdout.write(self.style.SUCCESS(
                f'{done} image(s): {before/1024/1024:.1f}MB → {after/1024/1024:.1f}MB '
                f'({100 - after/before*100:.0f}% smaller)'))
