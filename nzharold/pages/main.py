import json
import re

import dash
from dash import dcc, html
import dash_bootstrap_components as dbc
from dash_extensions import enrich as dee
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from app import app


def html_to_markdown(text: str):
    # Replace all story href URLs with local URLs
    return dcc.Markdown(md(text.replace('href="https://www.nzherald.co.nz/', 'href="/')))


def html_to_caption(text: str):
    return dcc.Markdown("_" + text.strip() + "_")


def layout():
    return dbc.Container(
        [
            dbc.Row(
                dbc.Col(
                    [
                        html.P(
                            "Paste any New Zealand Herald URL below to fetch its content:"
                        ),
                        dbc.Input(id="query-url", type="url"),
                    ]
                ),
                class_name="mb-4",
            ),
            dbc.Row(
                dbc.Spinner(dbc.Col(id="story-content"), spinner_class_name="mt-5"),
            ),
        ],
        class_name="mt-4 mx-5",
    )


@app.callback(
    dee.Output("story-content", "children"),
    dee.Input("query-url", "value"),
    dee.State("location", "pathname"),
)
def update_story(query_url, pathname):
    if not query_url:
        if pathname == "/":
            raise dash.exceptions.PreventUpdate
        else:
            # Build query URL from pathname
            query_url = f"https://nzherald.co.nz{pathname}"

    content = html.P("Sorry, can't parse that URL")
    if "nzherald.co.nz" in query_url:
        r = requests.get(query_url)

        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            s = (
                soup.find(id="fusion-metadata")
                .contents[0]
                .split("Fusion.globalContent=")[1]
                .split(";Fusion.globalContentConfig")[0]
                .replace(":false", ':"False"')
                .replace(":true", ':"True"')
            )
            content = [html.H3(soup.title.contents)]
            story = json.loads(s)
            if "elements" in story:
                for el in story["elements"]:
                    if el["type"] == "text":
                        content.append(html_to_markdown(el["content"]))
                    elif el["type"] == "image":
                        content.append(
                            html.Img(
                                src=el["additional_properties"]["originalUrl"],
                                width="100%",
                            )
                        )
                        content.append(html_to_caption(el["caption"]))

    return content
