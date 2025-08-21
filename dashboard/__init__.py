"""Instantiate all Dash apps."""
import dash
from .init_haix_dash import init_haix_dash
import dash_bootstrap_components as dbc


def dash_init(server):
    haix_dash = dash.Dash(
        server=server,
        routes_pathname_prefix="/",
        external_stylesheets=[
            dbc.themes.BOOTSTRAP
        ],
    )

    init_haix_dash(haix_dash)

    return server
