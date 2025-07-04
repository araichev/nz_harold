import dash_bootstrap_components as dbc
from dash import html


def layout():
    return dbc.Container(
        html.P(
            ["Logged out. ", html.A("Log in again?", href="/login")],
        ),
        className="mt-3 g-5",
        fluid=True,
    )
