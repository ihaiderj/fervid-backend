from core.responses import success_response, error_response


class APIResponseMixin:
    """Mixin for class-based views returning Supabase-compatible envelopes."""

    def success(self, data=None, message=None, status_code=200):
        return success_response(data=data, message=message, status_code=status_code)

    def error(self, error, code=None, status_code=400):
        return error_response(error=error, code=code, status_code=status_code)
