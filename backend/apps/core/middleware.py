import threading

_current_request = threading.local()


def get_current_request():
    return getattr(_current_request, 'request', None)


class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        _current_request.request = request
        response = self.get_response(request)
        _current_request.request = None
        return response
