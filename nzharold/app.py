import dash_bootstrap_components as dbc
import flask_login as fl
from dash_extensions import enrich as dee

import settings as st
import user_management as um

# --------------
# Configuration
# --------------
# fs = dee.FileSystemStore(cache_dir=st.config.CACHE_DIR)
app = dee.DashProxy(
    __name__,
    # transforms=[
    #     dee.ServersideOutputTransform(backend=fs),
    # ],
    suppress_callback_exceptions=True,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        dbc.icons.BOOTSTRAP,
    ],
    meta_tags=[{"name": "viewport", "content": "width=device-width"}],
)
app.server.config.from_object(st.config)
server = app.server

# Add 'lang' attribute to html tag

app.index_string = """
<!DOCTYPE html>
<html lang='en-NZ' role='main'>
    <head>
        {%metas%}
        <title>{%title%}</title>
        {%favicon%}
        {%css%}
    </head>
    <body>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
"""


# Connect the database
um.db.init_app(server)

# Set up the login manager
login_manager = fl.LoginManager()
login_manager.init_app(server)
login_manager.login_view = "/login"


class User(fl.UserMixin, um.User):
    pass


@login_manager.user_loader
def load_user(user_id):
    """
    Callback to reload the user object
    """
    return User.query.get(int(user_id))
