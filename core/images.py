"""Turn a phone photo into something a mobile connection can actually load.

An unprocessed 12MP JPEG is 3-6MB. The browse grid shows twelve at ~350px wide.
Serving the originals there is the single worst performance problem the site
has, so every upload is resized on the way in.
"""
import io
from pathlib import Path

from django.core.files.base import ContentFile
from PIL import Image, ImageOps

# Longest edge, in pixels.
FULL_SIZE = 1600      # detail page, retina-comfortable
THUMB_SIZE = 700      # grid cards at ~350px CSS, doubled for retina
QUALITY = 82          # visually lossless enough for jewelry, roughly 1/20th the bytes


def process(image_field, max_side, quality=QUALITY):
    """Return a resized, EXIF-stripped WebP `ContentFile`, or None.

    WebP because it is both smaller than JPEG and keeps transparency, so one
    output format covers every input we accept.
    """
    if not image_field:
        return None

    image_field.open()
    with Image.open(image_field) as img:
        # Phones record orientation in EXIF rather than rotating the pixels.
        # Apply it now, because stripping EXIF afterwards would lose it and the
        # picture would appear sideways.
        img = ImageOps.exif_transpose(img)

        if img.mode not in ('RGB', 'RGBA'):
            img = img.convert('RGBA' if 'A' in img.mode else 'RGB')

        if max(img.size) > max_side:
            img.thumbnail((max_side, max_side), Image.LANCZOS)

        buffer = io.BytesIO()
        # No exif= argument, so location data from the phone is dropped.
        img.save(buffer, format='WEBP', quality=quality, method=4)

    stem = Path(image_field.name).stem or 'image'
    return ContentFile(buffer.getvalue(), name=f'{stem}.webp')


def full(image_field):
    return process(image_field, FULL_SIZE)


def thumbnail(image_field):
    return process(image_field, THUMB_SIZE)
