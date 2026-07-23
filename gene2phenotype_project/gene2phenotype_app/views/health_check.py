from django.db import DatabaseError, connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe


@require_safe
@never_cache
def health_check(request):
    """Liveness probe: check if the application process is responding."""
    return JsonResponse({"status": "healthy"})


@require_safe
@never_cache
def readiness_check(request):
    """Readiness probe: check if the app can connect to the database."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except DatabaseError:
        return JsonResponse(
            {"status": "not_ready", "database": "unavailable"},
            status=503,
        )

    return JsonResponse({"status": "ready", "database": "connected"})
