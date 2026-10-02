"""
Allow selected views to be embedded in an <iframe> on trusted external sites.
"""
from functools import wraps

from django.conf import settings
from django.views.decorators.clickjacking import xframe_options_exempt


def allow_embedding(view_func):
    """Drop X-Frame-Options and send CSP frame-ancestors from settings.FRAME_ANCESTORS."""

    @xframe_options_exempt
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        response = view_func(request, *args, **kwargs)
        ancestors = " ".join(["'self'", *getattr(settings, "FRAME_ANCESTORS", [])])
        response["Content-Security-Policy"] = f"frame-ancestors {ancestors}"
        return response

    return wrapper
