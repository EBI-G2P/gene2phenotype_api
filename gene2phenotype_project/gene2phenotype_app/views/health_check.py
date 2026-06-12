# app_project/views.py
from django.http import JsonResponse
from django.db import connection, OperationalError

def health_check(request):
    """Liveness probe — Check if application is up."""
    return JsonResponse({"status": "healthy"}, status=200)

def readiness_check(request):
    """Readiness probe — Check DB connect to see if app can handle traffic."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return JsonResponse({"status": "ready", "database": "connected"}, status=200)
    except OperationalError:
        # Catch specific DB error
        return JsonResponse({"status": "unavailable"}, status=503)