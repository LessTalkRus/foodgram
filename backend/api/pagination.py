from rest_framework.pagination import PageNumberPagination


class CustomPagination(PageNumberPagination):
    """Постраничная пагинация с поддержкой параметра `limit`."""

    page_size_query_param = "limit"
    page_size = 6
