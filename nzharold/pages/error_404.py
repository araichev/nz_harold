import dash_bootstrap_components as dbc
from dash import html


def layout():
    return dbc.Container(
        html.P("Whoops, that's an error!"),
        class_name="mt-3 g-5",
        fluid=True,
    )
