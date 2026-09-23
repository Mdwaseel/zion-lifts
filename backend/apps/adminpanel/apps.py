from django.apps import AppConfig


class AdminPanelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.adminpanel"
    verbose_name = "Control room"

    def ready(self) -> None:
        # Importing the module runs the register() calls in it. Done here rather
        # than at URL-configuration time so the registry is populated before
        # anything — a management command, a test, the dashboard — asks it what
        # exists.
        from . import resources  # noqa: F401
