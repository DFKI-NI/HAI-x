from flask import render_template_string, session
from utils import variables as var, language_utils

def init_layout(path, **kwargs):
    var_lang = language_utils.get_language_module()

    with open(path, "r") as f:
        html_layout = render_template_string(f.read(), version=var.version, new_area_lang=var_lang.NEW_AREA, new_path_lang=var_lang.NEW_PATH, tables_lang=var_lang.TABLES, language_lang=var_lang.LANGUAGE, english_lang=var_lang.ENGLISH, german_lang=var_lang.GERMAN, **kwargs)
    comments_to_replace = ("app_entry", "config", "scripts", "renderer")
    for comment in comments_to_replace:
        html_layout = html_layout.replace(f"<!-- {comment} -->", "{%" + comment + "%}")
    return html_layout
