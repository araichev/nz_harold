import dash
import dash_bootstrap_components as dbc
import flask_login as fl
from dash import dcc
from dash_extensions import enrich as dee
from dash_extensions.enrich import html

import settings as st
from app import app
from pages import main, login, logout, error_404

# -------
# Layout
# -------
server = app.server
app.title = "NZ Harold"
app.layout = html.Div(
    [
        dcc.Location(id="location", refresh=False),
        dbc.NavbarSimple(
            children=[
                dbc.NavItem(
                    dbc.NavLink(
                        id="logout",
                        href="/logout",
                    )
                ),
            ],
            brand=[
                html.H4("NZ Harold 🗞️", style={"display": "inline-block"}),
            ],
            color="black",
            dark=True,
            fluid=True,
            class_name="py-0 my-navbar",
        ),
        html.Div(id="page-content"),
    ]
)


@dash.callback(
    dash.Output("logout", "children"),
    dash.Input("page-content", "children"),
)
def set_logout_link(input1):
    if fl.current_user.is_authenticated:
        result = f"Logout {fl.current_user.username}"
    else:
        result = None

    return result


@dash.callback(
    dee.Output("page-content", "children"),
    dee.Input("location", "pathname"),
)
def display_page(pathname):
    """
    Display the page corresponding to the given URL.
    """
    if not fl.current_user.is_authenticated or pathname == "/login":
        result = login.layout()
    elif pathname == "/logout":
        if fl.current_user.is_authenticated:
            fl.logout_user()
        result = logout.layout()
    else:
        result = main.layout()

    return result


if __name__ == "__main__":
    app.run(debug=st.config.DEBUG)
