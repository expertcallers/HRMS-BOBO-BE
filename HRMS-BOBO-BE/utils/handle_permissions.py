from importlib import import_module
import inspect
from pathlib import Path
import importlib.util

from django.conf import settings
from django.contrib.admin.options import ModelAdmin
from django.urls import URLResolver, URLPattern
from django.urls import get_resolver
from mapping.models import HrmsPermission, HrmsPermissionGroup
import re
import logging

logger = logging.getLogger(__name__)


def is_modeladmin_view(view):
    """Return True if the view is an admin view."""
    view = inspect.unwrap(view)  # In case this is a decorated view
    self = getattr(view, "__self__", None)
    return self is not None and isinstance(self, ModelAdmin)


def get_all_views(urlpatterns):
    """Given a URLconf, return a set of all view objects."""
    views = set()
    for pattern in urlpatterns:
        if hasattr(pattern, "url_patterns"):
            views |= get_all_views(pattern.url_patterns)
        else:
            if hasattr(pattern.callback, "cls"):
                view = pattern.callback.cls
            elif hasattr(pattern.callback, "view_class"):
                view = pattern.callback.view_class
            else:
                view = pattern.callback
            if not is_modeladmin_view(view):
                views.add(view)
    return views


def get_module_path(module_name):
    """Return the path for a given module name."""
    spec = importlib.util.find_spec(module_name)
    if spec is None:
        raise ImportError(f"Module '{module_name}' not found")
    return Path(spec.origin).resolve()


def is_subpath(path, directory):
    """Return True if path is below directory and isn't within a "venv"."""
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    else:
        # Return True if view isn't under a directory ending in "venv"
        return not any(p.endswith("venv") for p in path.parts)


def update_or_create_permission(url_name):
    route = get_resolver().reverse_dict[url_name][0][0][0]
    route = re.sub(r'%\((\w+)\)s', r'<str:\1>', route)
    perm_data = {'url_name': url_name, 'url_route': route, 'module_name': route.split("/")[0]}
    permission, created = HrmsPermission.objects.update_or_create(url_name=url_name, defaults=perm_data)
    return permission, created, perm_data


def get_all_local_views():
    """Return a set of all local views in this project."""
    root_urlconf = import_module(settings.ROOT_URLCONF)
    all_urlpatterns = root_urlconf.urlpatterns
    try:
        root_directory = settings.ROOT_DIR
    except AttributeError:
        root_directory = Path.cwd()  # Assume we're in the root directory

    perm = {}
    for view in get_all_views(all_urlpatterns):
        if is_subpath(get_module_path(view.__module__), root_directory) and type(view).__name__ != 'function':
            print(view.__name__, "___", view)
            cl_name = view.__module__.split(".")[0]
            if cl_name in perm:
                perm[cl_name].append(view.__name__)
            else:
                perm[cl_name] = [view.__name__]
    print(perm)

    # print(urlset)

    # print('api_views=', api_views)
    # print("api_class_views=", api_classes)


def get_all_local_url_names():
    url_names = []
    for i in get_resolver().reverse_dict:
        if type(i) == str:
            url_names.append(i)
    return url_names


handle_permissions = None


class HandlePermissions:
    url_names = []

    def __init__(self):
        self.url_names = get_all_local_url_names()
        print("executed")

    def add_permissions(self):
        # print(get_resolver().reverse_dict)
        for i in get_resolver().reverse_dict:
            if type(i) == str:
                permission, created, perm_data = update_or_create_permission(i)
                if created:
                    print("created ", perm_data.get('url_route'), i)
                    # hrmsgroup = HrmsPermissionGroup.objects.all()
                    # for group in hrmsgroup:
                    #     group.permissions.add(permission)
                    #     group.save()

    def get_default_permissions(self):
        url_names = ['get_all_leave_balance_history', 'get_leave_balance', 'appeal_leave_request_by_escalating',
                     'get_all_applied_leaves', 'get_all_leave_history_of_employee', 'apply_for_leave', 'get_new_hires',
                     'get_attendance_by_emp_id', 'get_all_birthdays']

    def clean_up_permissions(self):
        all_urls = get_all_local_url_names()
        permissions = HrmsPermission.objects.all()
        for i in permissions:
            if i.url_name not in self.url_names:
                print("deleting ", i.url_name)
                i.delete()


def get_handle_permissions():
    global handle_permissions
    if handle_permissions is None:
        handle_permissions = HandlePermissions()
    return handle_permissions


def print_views():
    get_all_local_views()
    # all_views = get_all_local_views()
    # print("all_views", all_views)
    # print("Number of local views: ", len(all_views))
