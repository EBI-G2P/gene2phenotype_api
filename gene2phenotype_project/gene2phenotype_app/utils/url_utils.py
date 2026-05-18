from django.conf import settings


def build_public_url(path: str) -> str:
    """
    Build a public URL using the configured canonical application base URL.
    """
    base_url = settings.PUBLIC_APP_URL.rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{base_url}{normalized_path}"
