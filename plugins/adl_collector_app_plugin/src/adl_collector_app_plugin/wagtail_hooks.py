from django.conf import settings
from wagtail import hooks
from wagtail.admin.viewsets.chooser import ChooserViewSet


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
