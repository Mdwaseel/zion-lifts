"""Pagination for admin lists.

Separate from the public API's, which pages at 48 because the site renders whole
collections at once. A table of records is read a screenful at a time and is
often filtered, so it pages smaller and lets the client ask for more.
"""

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class AdminPagination(PageNumberPagination):
    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 200

    def get_paginated_response(self, data):
        # The table needs to draw "page 3 of 11" and size its own pager, which
        # next/previous URLs alone do not allow.
        return Response(
            {
                "count": self.page.paginator.count,
                "page": self.page.number,
                "pages": self.page.paginator.num_pages,
                "page_size": self.get_page_size(self.request),
                "results": data,
            }
        )
