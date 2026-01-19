from rest_framework.views import exception_handler
from rest_framework import status


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is None:
        return None

    # Only rewrite 404 and 401 responses
    if (
        (
            response.status_code == status.HTTP_404_NOT_FOUND
            or response.status_code == status.HTTP_401_UNAUTHORIZED
        )
        and isinstance(response.data, dict)
        and "detail" in response.data
    ):
        response.data["error"] = response.data.pop("detail")

    return response
