"""Upload guards. Used by every ImageField on the site."""
from django.conf import settings
from django.core.exceptions import ValidationError

ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP'}
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp'}


def validate_image_upload(uploaded):
    """Reject files that are too big, or that are not actually images.

    Pillow has already parsed the file by the time an ImageField validator
    runs, so `uploaded.image.format` is the *real* format — checking that
    rather than the filename means a renamed .exe cannot slip through.
    """
    size = getattr(uploaded, 'size', None)
    if size and size > settings.MAX_UPLOAD_BYTES:
        limit_mb = settings.MAX_UPLOAD_BYTES / (1024 * 1024)
        actual_mb = size / (1024 * 1024)
        raise ValidationError(
            f'That image is {actual_mb:.1f}MB. Please keep it under {limit_mb:.0f}MB — '
            f'most phones let you export a smaller version.'
        )

    image_format = getattr(getattr(uploaded, 'image', None), 'format', None)
    if image_format and image_format.upper() not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError(
            f'{image_format} images are not supported. Use JPEG, PNG or WebP.'
        )
