from BBulkSmash import __version__, __release_date__, __app_name__, __author__

def version_context(request):
    """
    Make version info available to all templates
    """
    return {
        'APP_VERSION': __version__,
        'APP_RELEASE_DATE': __release_date__,
        'APP_NAME': __app_name__,
        'APP_AUTHOR': __author__,
    }