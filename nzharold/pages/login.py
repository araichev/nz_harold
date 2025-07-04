import time

import dash
import dash.dependencies as dd
import dash_bootstrap_components as dbc
import flask_login as fl
import werkzeug.security as ws
from dash import dcc, html
from loguru import logger

from app import User


def layout():
    return dbc.Container(
        [
            dbc.Row(
                dbc.Col(
                    [
                        dbc.Label("Username", class_name="mr-2"),
                        dbc.Input(id="username", n_submit=0),
                    ],
                    width={"size": 6, "offset": 3},
                ),
                class_name="mb-3",
            ),
            dbc.Row(
                dbc.Col(
                    [
                        dbc.Label("Password", class_name="mr-2"),
                        dbc.Input(id="password", type="password", n_submit=0),
                    ],
                    width={"size": 6, "offset": 3},
                ),
                class_name="mb-3",
            ),
            dbc.Row(
                dbc.Col(
                    dbc.Button("Submit", id="submit", color="primary"),
                    width={"size": 3, "offset": 3},
                ),
            ),
            dbc.Row(
                dbc.Col(
                    [
                        dcc.Location(id="login-url", refresh=True),
                        dcc.Store(id="is-authenticated", data=False),
                        html.Div(id="message"),
                    ],
                    width={"size": 6, "offset": 3},
                ),
                class_name="mt-3",
            ),
        ],
        class_name="mt-5",
    )


@dash.callback(
    dd.Output("message", "children"),
    dd.Output("is-authenticated", "data"),
    dd.Input("submit", "n_clicks"),
    dd.Input("username", "n_submit"),
    dd.Input("password", "n_submit"),
    dd.State("username", "value"),
    dd.State("password", "value"),
)
def check_login(n_clicks, n_submit_username, n_submit_password, username, password):
    result = None, False
    if n_clicks or n_submit_username or n_submit_password:
        user = User.query.filter_by(username=username).first()
        logger.info(password)
        logger.info(user)
        if user and ws.check_password_hash(user.password, password):
            fl.login_user(user)
            result = (
                dbc.Alert(
                    "Success!",
                    color="success",
                    duration="5000",
                ),
                True,
            )
        else:
            result = (
                dbc.Alert(
                    "Unrecognized username-password combination.",
                    color="danger",
                    duration="5000",
                ),
                False,
            )

    return result


@dash.callback(
    dd.Output("login-url", "href"),
    dd.Input("is-authenticated", "data"),
)
def redirect_home(is_authenticated):
    if is_authenticated:
        time.sleep(1)
        return "/"
