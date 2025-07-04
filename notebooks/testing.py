import marimo

__generated_with = "0.14.10"
app = marimo.App()


@app.cell
def _():
    import re
    import requests as rq
    from IPython.display import Image

    import urllib3
    from bs4 import BeautifulSoup
    import pandas as pd
    import json
    return BeautifulSoup, Image, json, re, rq


@app.cell
def _():
    # NZ Herald
    return


@app.cell
def _(BeautifulSoup, Image, display, json, rq):
    _temp_url = 'https://www.nzherald.co.nz/nz/time-to-have-your-say-consultation-begins-on-auckland-transports-controversial-parking-strategy/YQMPIC4PJQWJCR2SF7AHYX3BO4/'
    url = input()
    if url == '':
        url = _temp_url
    _r = rq.get(url)
    display(_r.status_code)
    soup = BeautifulSoup(_r.text, 'html.parser')
    s = soup.find(id='fusion-metadata').contents[0].split('Fusion.globalContent=')[1].split(';Fusion.globalContentConfig')[0].replace(':false', ':"False"').replace(':true', ':"True"')
    for _content in json.loads(s)['elements']:
        if _content['type'] == 'text':
            display(_content['content'])
        elif _content['type'] == 'image':
            display(Image(_content['additional_properties']['originalUrl']))
            display(_content['caption'])
        else:
            display(_content)
    return s, soup, url


@app.cell
def _():
    from markdownify import markdownify as md
    return (md,)


@app.cell
def _(display, json, md, s):
    cstr = ''
    for _content in json.loads(s)['elements']:
        if _content['type'] == 'text':
            cstr = cstr + _content['content']
        elif _content['type'] == 'image':
            cstr = cstr + _content['additional_properties']['originalUrl']
            cstr = cstr + _content['caption']
        else:
            cstr = cstr + _content
        cstr = cstr + '\n'
    display(md(cstr))
    return


@app.cell
def _(display, json, soup):
    test=(
        soup
        .find(id="fusion-metadata")
        .contents[0]
        .split('"content-by-id":')[1]
        .split(',"customFields":')[0]
        .split('{"data":')
    )

    # for t in test[1:]:
    #     display(t)

    # display(test[1].replace("\\", ""))
    display(test[1].replace("\\", "")[12360:12380])
    json.loads(test[1].replace("\\", ""))
    return


@app.cell
def _(display, re, rq, url):
    html_data=rq.get(url).text

    out=re.search(r'content-by-id= (\{.*?\});', html_data)

    display(out)
    return (html_data,)


@app.cell
def _(html_data):
    from html.parser import HTMLParser

    parser=HTMLParser()

    parser.feed(html_data)
    return


@app.cell
def _():
    # Newsroom
    return


@app.cell
def _(BeautifulSoup, display, rq):
    _temp_url = 'https://www.newsroom.co.nz/pro/governing-in-a-pandemic-and-without-a-coalition-partner'
    url_1 = input()
    if url_1 is None:
        url_1 = _temp_url
    _r = rq.get(url_1)
    display(_r.status_code)
    soup_1 = BeautifulSoup(_r.text, 'html.parser')
    return


if __name__ == "__main__":
    app.run()
