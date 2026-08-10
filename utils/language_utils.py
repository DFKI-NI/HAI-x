"""
Utility functions for language handling.
"""
from utils import variables as var


def get_language_module(request=None):
    """
    Returns the appropriate language module based on the current language
    preference.  Checks the Django session first (when a request is given),
    then falls back to the default value in var.language.

    Returns:
        module: The language module containing all text variables.
    """
    language = var.language
    if request is not None and hasattr(request, "session"):
        language = request.session.get("language", var.language)

    if language == 'german':
        from utils import language_variables_german as lang_module
    else:
        from utils import language_variables_english as lang_module

    return lang_module
