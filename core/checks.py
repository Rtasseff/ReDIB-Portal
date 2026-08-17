"""
System checks for the core app.
"""
from django.core.checks import Error, register


@register()
def user_guide_file_check(app_configs, **kwargs):
    """
    The user guide page (/help/user-guide/) renders docs/USER_GUIDE.md at
    request time, so the file has to ship inside the Docker image. `docs/` is
    excluded by .dockerignore with a trailing `!docs/USER_GUIDE.md` exception;
    if that exception is ever dropped the page would 404 silently in
    production. The container entrypoint runs `migrate`, which runs system
    checks, so this turns that into a loud deploy failure instead.
    """
    from .views import USER_GUIDE_PATH

    if not USER_GUIDE_PATH.is_file():
        return [
            Error(
                f'User guide source file not found at {USER_GUIDE_PATH}.',
                hint=(
                    'The /help/user-guide/ page renders this file at request '
                    'time. In Docker builds, check that .dockerignore still '
                    'ends with the `!docs/USER_GUIDE.md` exception.'
                ),
                id='core.E001',
            )
        ]
    return []
