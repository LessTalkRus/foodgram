from rest_framework.pagination import PageNumberPagination

from backend.constants import DEFAULT_PAGE_SIZE


class CustomPagination(PageNumberPagination):
    """Постраничная пагинация с поддержкой параметра `limit`."""

    page_size_query_param = "limit"
    page_size = DEFAULT_PAGE_SIZE
