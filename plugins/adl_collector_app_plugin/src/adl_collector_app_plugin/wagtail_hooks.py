from django.conf import settings
from django.urls import path
from wagtail import hooks
from wagtail.admin.viewsets.chooser import ChooserViewSet

from .views import view_test_collector_submissions


class UserChooserViewSet(ChooserViewSet):
    model = settings.AUTH_USER_MODEL
    icon = "form"
    choose_one_text = "Choose User"
    choose_another_text = "Choose different User"
    edit_item_text = "Edit this User"
    per_page = 50


@hooks.register("register_admin_viewset")
def register_viewsets():
    return [
        UserChooserViewSet("user_chooser"),
    ]


@hooks.register('register_admin_urls')
def urlconf_adl_collector_app_plugin():
    return [
        path(
            "adl-collector-app-plugin/test-collector-submissions/",
            view_test_collector_submissions,
            name="view_test_collector_submissions",
        ),
    ]
