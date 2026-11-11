def note(request, **fields) -> None:
    """Attach details to the current request's audit record.

    Views receive a DRF ``Request``; the middleware holds the underlying Django
    ``HttpRequest``. Writing through ``_request`` puts the fields where the
    middleware will read them.
    """
    target = getattr(request, "_request", request)
    if not hasattr(target, "audit"):
        target.audit = {}
    target.audit.update(fields)
