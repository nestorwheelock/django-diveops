"""Portal UI mixins for DiveOps."""

__all__ = ["StaffPortalMixin", "CustomerPortalMixin", "PublicViewMixin"]


def __getattr__(name):
    """Lazy import to avoid AppRegistryNotReady errors."""
    if name in __all__:
        from . import mixins
        return getattr(mixins, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
