"""
Utility functions for language handling.
"""
from flask import session
from utils import variables as var

def get_language_module():
    """
    Returns the appropriate language module based on the current language preference.
    Checks the session first, then falls back to the default value in var.language.

    Returns:
        module: The language module containing all text variables.
    """
    # Get language preference from session if available, otherwise use default
    language = session.get('language', var.language)

    language = var.language

    if language == 'german':
        from utils import language_variables_german as lang_module
    else:
        from utils import language_variables_english as lang_module

    return lang_module
