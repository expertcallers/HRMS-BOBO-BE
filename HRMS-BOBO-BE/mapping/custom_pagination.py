from rest_framework import status, pagination
from rest_framework.exceptions import APIException
from rest_framework.response import Response


class NotFound(APIException):
    status_code = status.HTTP_200_OK
    default_detail = {
        "next": None,
        "previous": None,
        "count": 0,
        "results": []
    }

    def __init__(self, detail=None):
        if detail is not None:
            self.detail = detail
        else:
            self.detail = self.default_detail


class CustomPagination(pagination.PageNumberPagination):
    page_size_query_param = 'page_size'

    def paginate_queryset(self, queryset, request, view=None):
        """
        Paginate a queryset if required, either returning a
        page object, or `None` if pagination is not configured for this view.
        """
        page_size = self.get_page_size(request)
        if not page_size:
            return None

        paginator = self.django_paginator_class(queryset, page_size)
        page_number = request.query_params.get(self.page_query_param, 1)
        if page_number in self.last_page_strings:
            page_number = paginator.num_pages

        try:
            self.page = paginator.page(page_number)
        except Exception as exc:
            # Here it is
            raise NotFound()

        if paginator.num_pages > 1 and self.template is not None:
            # The browsable API should display pagination controls.
            self.display_page_controls = True

        self.request = request

        return list(self.page)

    def get_paginated_response(self, data):
        return Response({
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'count': self.page.paginator.count,
            'results': data
        })
