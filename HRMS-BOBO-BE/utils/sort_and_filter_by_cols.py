import json

from django.db.models import Q
from rest_framework.exceptions import ValidationError, ErrorDetail


def get_sort_and_filter_by_cols(data, fields_look_up=None):
    sort_field = json.loads(data.get('sort_field', '[]'))
    sortby = json.loads(data.get('sort', '[]'))
    # logger.info("sort_field={0} sortby={1}".format(sort_field, sortby))
    order_by_cols = ['id']
    if type(sort_field) is not list or type(sortby) is not list:
        raise ValidationError(
            "sort_field and sort must be of type list".format(type(sort_field), type(sortby)))
    if len(sort_field) != len(sortby):
        raise ValidationError("sort_field and sortby must of same size")

    if sort_field and sortby and len(sort_field) > 0 and len(sortby) > 0:
        order_by_cols = []
        for index, sfield in enumerate(sort_field):
            sortbyval = sortby[index].lower()
            if sfield and sortbyval in ['asc', 'desc']:
                sfield = get_lookup_field(sfield, fields_look_up)
                sfield = sfield if sortbyval == 'asc' else "-{0}".format(sfield)
                order_by_cols.append(sfield)
    query = Q()
    filter_by = json.loads(data.get('filter_by', '{}'))
    or_fields = json.loads(data.get('or_fields', '{}'))
    and_fields = json.loads(data.get('and_fields', '{}'))
    search = json.loads(data.get("search")) if data.get("search") else None
    search_fields = json.loads(data.get("search_fields", '[]'))
    filter_by_values = {}

    # logger.info("or_fields {0} , and_fields {1}".format(or_fields, and_fields))
    # logger.info("search={0} search_fields ={1}".format(search, search_fields))
    # logger.info("filter_by={0}".format(filter_by))

    if type(filter_by) is not dict:
        raise ValidationError(
            "{0}, filter_by must be of type key,value structure".format(filter_by))
    for field, value in and_fields.items():
        field, end_string = handle_lookup_value(field, value, fields_look_up)
        query = handle_ne(query, field, end_string, value)
        # logger.info("and_field={0}".format(field))

    # logger.info("query={0}".format(query))

    if search and search_fields:
        for field in search_fields:
            field = get_lookup_field(field, fields_look_up)
            query |= Q(**{f"{field}__icontains": search})

    if filter_by and len(filter_by) > 0:
        for field, value in filter_by.items():
            field = str(get_lookup_field(field, fields_look_up))
            # logger.info("type={0} val={1} {2}".format(type(value), value, field))
            field, end_string = handle_lookup_value(field, value, fields_look_up)
            if end_string == "__ne":
                query &= ~Q(**{f"{field}": value})
            else:
                field = f"{field}{end_string}"
                filter_by_values[field] = value
    # logger.info(f"before query {query}")

    or_applied = False
    for or_field, or_value in or_fields.items():
        or_field, or_end_string = handle_lookup_value(or_field, or_value, fields_look_up)
        # logger.info("came here second={0}{1}".format(or_field, or_end_string))
        # logger.info(f"inside query {query}")

        for flocal, value in filter_by_values.items():
            # logger.info("or_field ={0}".format(or_field))
            if flocal == or_field or str(flocal).startswith(f"{or_field}__"):
                # logger.info("matched {0}".format(flocal))
                field, end_string = handle_lookup_value(flocal, value, fields_look_up)
                query = handle_ne(query, field, end_string, value, is_and=False)
                or_applied = True
                # logger.info("del {0} {1} ".format(flocal, value))
                del filter_by_values[flocal]
                break

        # logger.info("field={0}".format(field))
        query = handle_ne(query, or_field, or_end_string, or_value, is_and=False)
        #
        if or_applied:
            break
    # logger.info(f"query {query}")
    # logger.info(f"filterby {filter_by_values}")
    return order_by_cols, query, filter_by_values


def get_lookup_field(field, fields_look_up):
    if field is None or fields_look_up is None:
        return field
    return fields_look_up.get(field, field)


def get_post_lookup_field(val, field, value, fields_look_up):
    local_field = str(field)[:-val]
    end_string = str(field)[-val:]
    field = get_lookup_field(local_field, fields_look_up)
    return field, end_string


def handle_lookup_value(field, value, fields_look_up):
    end_string = ""
    if field.endswith("__isnull"):
        field, end_string = get_post_lookup_field(8, field, value, fields_look_up)
    elif field[-5:] in ["__gte", "__lte"]:
        field, end_string = get_post_lookup_field(5, field, value, fields_look_up)
    elif field.endswith("__in") and type(value) == list:
        field, end_string = get_post_lookup_field(4, field, value, fields_look_up)
    elif field.endswith("__istartswith"):
        field, end_string = get_post_lookup_field(13, field, value, fields_look_up)
    elif field[-11:] in ["__iendswith", "__icontains"]:
        field, end_string = get_post_lookup_field(11, field, value, fields_look_up)
    elif field[-4:] in ["__ne", "__lt", "__gt"]:
        field, end_string = get_post_lookup_field(4, field, value, fields_look_up)
    elif type(value) == str or type(value) == int or type(value) == float or type(value) == bool:
        field = get_lookup_field(field, fields_look_up)
        if type(value) == str:
            if not value.isnumeric():
                end_string = "__iexact"
        # logger.info("field {0} end_string {1}".format(field, end_string))
    return field, end_string


def handle_ne(query, field, end_string, value, is_and=True):
    if is_and:
        if end_string == "__ne":
            query &= ~Q(**{f"{field}": value})
        else:
            if str(field).endswith(end_string):
                query &= Q(**{f"{field}": value})
            else:
                query &= Q(**{f"{field}{end_string}": value})
    else:
        if end_string == "__ne":
            query |= ~Q(**{f"{field}": value})
        else:
            if str(field).endswith(end_string):
                query |= Q(**{f"{field}": value})
            else:
                query |= Q(**{f"{field}{end_string}": value})
    return query


def get_filter_cols(data):
    filter_by = json.loads(data.get('filter_by', '{}'))
    # logger.info("filter_by={0}".format(filter_by))
    if type(filter_by) is not dict:
        raise ValidationError(
            "{0}, filter_by must be of type key,value structure".format(filter_by))
    return filter_by
