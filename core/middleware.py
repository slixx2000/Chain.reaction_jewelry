"""Turn a rate-limit trip into an honest 429 rather than a bare 403."""
from django.http import JsonResponse
from django.shortcuts import render
from django_ratelimit.exceptions import Ratelimited


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        if not isinstance(exception, Ratelimited):
            return None

        wants_json = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            or 'application/json' in request.headers.get('Accept', '')
        )
        if wants_json:
            return JsonResponse(
                {'detail': 'Too many requests. Please slow down.'}, status=429)

        return render(request, '429.html', status=429)
