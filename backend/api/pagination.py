from rest_framework.pagination import PageNumberPagination


class CustomPagination(PageNumberPagination):
    """Пагинация как в ТЗ/тестах: count/next/previous/results + ?limit=."""
    page_size_query_param = 'limit'
    page_size = 6
