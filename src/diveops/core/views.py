"""Core views for DiveOps."""

from django.http import JsonResponse
from django.shortcuts import redirect, render


def health_check(request):
    """Health check endpoint for container orchestration."""
    from django.db import connection

    try:
        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        return JsonResponse({"status": "healthy", "database": "connected"})
    except Exception as e:
        return JsonResponse(
            {"status": "unhealthy", "error": str(e)},
            status=503,
        )


def index(request):
    """Homepage view."""
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect("diveops:excursion-list")
        return redirect("portal:dashboard")

    return render(request, "index.html")
