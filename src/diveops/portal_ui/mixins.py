"""Portal UI mixins for view access control."""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class StaffPortalMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin for staff portal views."""

    required_module = None
    required_action = "view"

    def test_func(self):
        user = self.request.user

        # Superusers always have access
        if user.is_superuser:
            return True

        # Must be staff
        if not user.is_staff:
            return False

        # If no module required, staff is enough
        if not self.required_module:
            return True

        # Check module permission via django-modules if available
        if hasattr(user, "has_module_permission"):
            return user.has_module_permission(self.required_module, self.required_action)

        return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_staff_portal"] = True
        return context


class CustomerPortalMixin(LoginRequiredMixin):
    """Mixin for customer portal views."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_customer_portal"] = True
        return context


class PublicViewMixin:
    """Mixin for public views (no authentication required)."""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["is_public"] = True
        return context


class SuperadminMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Mixin for superadmin-only views."""

    def test_func(self):
        return self.request.user.is_superuser
