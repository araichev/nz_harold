"""
Command line tools to use with Fabric to deploy this app to MRCagney's web server.
For example ``fab deploy-app`` will deploy the app to the server for the first time.
Throughout the docstrings "locally" and "remotely" abbreviate "on your local machine"
and "on the web server", respectively.
"""

import os
import pathlib as pl
import uuid
import re
import shlex
from contextlib import contextmanager

import fabric as fr
import dotenv as de
import server_utils as su


fabfile_version = "2.3.2"

# Configure
ROOT = pl.Path(os.path.abspath(__file__)).parent.resolve()
de.load_dotenv(ROOT / ".env")
PROJECT = "nzharold"
PROJECT_MANAGER = "uv"
REMOTE_ROOT = pl.Path("/home/mrcagney")
REMOTE_DIR = REMOTE_ROOT / "webapps" / PROJECT
HOST = "mrcagney@mrcagney.works"
DOMAIN = "nzharold.mrcagney.works"
SUDO_PWD = os.getenv("SUDO_PWD")
MRCAGNEY_PWD = os.getenv("MRCAGNEY_PWD")
CONFIG = fr.Config(overrides={"sudo": {"password": SUDO_PWD}})


def check_for_passwords():
    msg = ""
    if not os.getenv("SUDO_PASSWORD"):
        msg += (
            "You must add the server's sudo password to your local .env file in the "
            "variable SUDO_PASSWORD; "
        )
    if (ROOT / PROJECT / "user_management.py").exists() and not os.getenv(
        "MRCAGNEY_PASSWORD"
    ):
        msg += (
            "You must add the default 'mrcagney' user password to your local .env file "
            "in the variable MRCAGNEY_PASSWORD"
        )
    if msg:
        raise ValueError(msg)


def sudo(connection, command, **kwargs):
    """
    Sudo with cd() fix. See https://github.com/fabric/fabric/issues/2091
    """

    @contextmanager
    def clear_prefixes():
        command_prefixes = connection.command_prefixes
        command_cwds = connection.command_cwds
        connection._set(command_prefixes=[], command_cwds=[])

        try:
            yield
        finally:
            connection._set(command_prefixes=command_prefixes, command_cwds=command_cwds)

    # use shell to execute the whole prefixed command under sudo
    # this fixes the cd issue and also fixes piped commands that require sudo
    # eg. echo "hello" | tee /etc/out.txt
    command = "%s -c %s" % (
        kwargs.get("shell", "/bin/bash"),
        shlex.quote(connection._prefix_commands(command)),
    )

    with clear_prefixes():
        return connection.sudo(command, **kwargs)


def exists(connection, path: pl.Path | str) -> bool:
    """
    Check whether a file exists on a (usually remote) connection.
    """
    try:
        connection.run(f"ls -ls {path}", hide=True)
        return True
    except Exception:
        return False


@fr.task
def list_server_ports(cxt) -> list[str, str, str]:
    """
    Print and return a sorted list of string triples
    (Gunicorn port, domain, Apache config filename) for all domains in Apache use on the
    server, where the Gunicorn port is "N/A" if the domain does not use Gunicorn.
    """
    result = []
    apache_path = "/etc/apache2/sites-available"
    domain_regex = re.compile(r"(ServerName|ServerAlias)\s+(\S+)")
    port_regex = re.compile(r"ProxyPass\s+/\s+http://127\.0\.0\.1:(\d+)")
    with fr.Connection(HOST, config=CONFIG) as c:
        # List all non-SSL Apache config files
        ls = c.run(f"ls {apache_path}/*.conf", hide=True)
        conf_files = [f for f in ls.stdout.strip().splitlines() if "-ssl" not in f]
        for conf_file in conf_files:
            content = c.run(f"cat {conf_file}", hide=True).stdout
            s = re.search(port_regex, content)
            if s:
                port = s.group(1)
            else:
                port = "N/A"
            s = re.search(domain_regex, content)
            if s:
                domain = s.group(2)
            else:
                domain = "unknown"
            result.append((port, domain, pl.Path(conf_file).name))

    result = sorted(set(result))
    print("\n".join([f"{p} : {d} : {f}" for p, d, f in result]))
    return result


@fr.task
def get_server_port(ctx) -> int:
    """
    Call :func:`list_server_ports` and return the next free port number available to
    which to deploy a Dash + Gunicorn app.
    Return that port, unless the app is already assigned to a port on the web server,
    in which case, return *that* port.
    """
    result = 6666  # Default
    for port, domain, __ in sorted(list_server_ports(ctx)):
        if domain == DOMAIN and port != "N/A":
            result = int(port)
            break
        elif port != "N/A":
            result = int(port) + 1
    return result


@fr.task
def get_local_port(ctx) -> int:
    """
    Return the port listed in the local 'gunicorn_config.py' file.
    """
    path = ROOT / PROJECT / "gunicorn_config.py"
    with path.open() as src:
        content = src.read()

    # Guaranteed a match by original construction of `gunicorn_config.py`
    s = re.search(r"127\.0\.0\.1:(\d+)", content)
    return int(s.group(1))


@fr.task
def update_local_port(ctx):
    """
    Locally, update the port in ``gunicorn.py`` to the port obtained from
    :func:`get_server_port`.
    """
    print("-" * 10, "Setting the port in local file 'gunicorn_config.py'...")
    port = get_server_port(ctx)
    path = ROOT / PROJECT / "gunicorn_config.py"
    with path.open() as src:
        content = src.read()

    content = re.sub(r"127\.0\.0\.1:(\d+)", f"127.0.0.1:{port}", content)

    with path.open("w") as tgt:
        tgt.write(content)


@fr.task
def init_local_env(ctx):
    """
    Locally, initialise the project environment as follows.
    Install Git and Git flow, add the web server as a remote called
    'production', install the precommit hooks, create a user database, add a 'test' user
    with password 'test', create a .env file, and set the correct port in
    ``gunicorn_config.py``.
    """
    print("-" * 40, "Initialising the local project environment...")
    with ctx.cd(ROOT):
        # Init Git and Git Flow
        ctx.run("git init")
        ctx.run("git flow init")
        ctx.run(
            f"git config remote.production.url >&- || "
            f"git remote add production "
            f"mrcagney@mrcagney.works:/home/mrcagney/git_repos/{PROJECT}.git"
        )
        # Install pre-commit hooks
        ctx.run("uv run pre-commit install")
        ctx.run("uv run pre-commit autoupdate")
        # Create the user database and add a test user
        if (ROOT / PROJECT / "user_management.py").exists() and not (
            ROOT / "users.sqlite"
        ).exists():
            ctx.run(f"uv run python {PROJECT}/user_management.py create-user-table")
            ctx.run(f"uv run python {PROJECT}/user_management.py add-user test test test")

    # Create local .env file
    if not (ROOT / ".env").exists():
        su.make_dotenv(
            {
                "MODE": "development",
                "SECRET_KEY": "sssssh",
            },
            ROOT / ".env",
        )
    update_local_port(ctx)


@fr.task
def init_project_folder(ctx):
    """
    Remotely, make the necessary project folders for the app and make a
    default .env file that contains the (random) secret key required by Dash.
    """
    print("-" * 10, "Making project folders on server...")
    with fr.Connection(HOST, config=CONFIG) as c:
        c.run(f"mkdir -p {REMOTE_DIR / 'site' / 'logs'}")
        c.run(f"mkdir -p {REMOTE_DIR / PROJECT}")


@fr.task
def init_dotenv(
    ctx, ignore_keys=("MODE", "SECRET_KEY", "SUDO_PASSWORD", "MRCAGNEY_PASSWORD")
):
    """
    Copy the local environment variables in the ``.env`` file to the web server,
    ignoring the given keys.
    Also, add the line 'MODE=production' and a random secret key in 'SECRET_KEY'.
    """
    print("-" * 10, "Copying local .env file to server with some tweeks...")
    local = de.dotenv_values(ROOT / ".env")
    env = {
        "MODE": "production",
        "SECRET_KEY": uuid.uuid4().hex,
    } | {k: v for k, v in local.items() if k not in ignore_keys}
    tmp_path = ROOT / "tmp"
    su.make_dotenv(env, out_path=tmp_path)
    with fr.Connection(HOST, config=CONFIG) as c:
        c.put(tmp_path, remote=str(REMOTE_DIR / PROJECT))
        c.run(
            f"mv {REMOTE_DIR / PROJECT / tmp_path.name} {REMOTE_DIR / PROJECT / '.env'}"
        )
    # Remove tmp file
    tmp_path.unlink()


@fr.task
def set_apache_permissions(ctx, dirname: str):
    """
    Remotely and recursively change the  permissions of the directory
    ``REMOTE_DIR / PROJECT / dirname``, if it exists, so Apache owns
    it and can write to it.
    Commands taken from https://serverfault.com/a/357109.

    To run this from the command line on folder 'data', do
    ``fab set-apache-permissions --dirname data``.
    """
    path = REMOTE_DIR / PROJECT / dirname
    print("-" * 10, f"Giving Apache write permisions to {path}...")
    with fr.Connection(HOST, config=CONFIG) as c:
        if exists(c, path):
            c.sudo(f"chgrp -R www-data {path}")
            c.sudo(f"chmod -R 750 {path}")
            c.sudo(f"chmod g+w {path}")


@fr.task
def delete_project_folder(ctx):
    """
    Remotely, delete the project folder.
    """
    print("-" * 10, "Deleting project folder on server...")
    with fr.Connection(HOST, config=CONFIG) as c:
        path = REMOTE_DIR / PROJECT
        if exists(c, path):
            c.run(f"rm -rf {path}")


@fr.task
def rsync_push(ctx):
    """
    Push files in local Git branch 'master' to remote 'production'
    using Rsync and ignoring all Git-ignored and Git-related files.
    If Git LFS is detected (if '.gitattributes' file is presest), download LFS
    files from remote 'origin' before pushing.
    """
    print("Pushing files to production via Rsync...")
    if (ROOT / ".gitattributes").exists():
        # Get LFS files
        print("Found '.gitattributes', so pulling Git LFS files from origin first...")
        with ctx.cd(ROOT):
            ctx.run("git checkout master")
            ctx.run("git lfs pull")

    with ctx.cd(ROOT):
        rsync_cmd = f"rsync -av --delete --exclude-from='.gitignore' --exclude='.git*' --exclude='.pre-commit*' {ROOT} {HOST}:{REMOTE_DIR}"
        ctx.run(rsync_cmd)


@fr.task
def init_virtualenv(ctx):
    """
    Remotley, create a virtual environment and into it Poetry install the main
    dependencies, assuming the app's ``pyproject.toml`` file exists.
    """
    print("-" * 10, "Creating virtual environment and installing main dependencies...")
    with fr.Connection(HOST, config=CONFIG) as c:
        with c.cd(REMOTE_DIR / PROJECT):
            c.run("bash -ic 'uv sync --no-dev --frozen'")


@fr.task
def init_apache(ctx):
    """
    Remotely, configure Apache for the app and its domain, install an SSL
    certificate via Let's Encrypt, which requires you to answer two questions
    interactively, then restart Apache.
    """
    print("-" * 10, f"Configuring Apache for domain {DOMAIN}...")

    # Get local port and use that in Apache conf
    port = get_local_port(ctx)

    # Make the Apache conf file locally, then copy it to the server
    filename = f"{DOMAIN}.conf"
    su.make_apache_conf("dash", DOMAIN, PROJECT, port, out_path=ROOT / filename)
    with fr.Connection(HOST, config=CONFIG) as c:
        apache_dir = pl.Path("/etc/apache2/sites-available")
        conf_path = apache_dir / filename
        if not exists(c, conf_path):
            # Can't use sudo with put :(, so copy to remote root then sudo move it
            # to the proper folder
            c.put(ROOT / filename)
            sudo(c, f"mv {filename} {apache_dir}")
            with c.cd(apache_dir):
                sudo(c, f"a2ensite {filename}")
                # Enable SSL
                sudo(c, f"certbot --apache -d {DOMAIN}")
                output = sudo(c, "apachectl configtest")
                if "Syntax OK" in output.stdout:
                    sudo(c, "service apache2 restart")

    # Delete local conf file
    (ROOT / filename).unlink()


def add_bot_block_rules(apache_conf: str) -> str:
    """
    Add/update AI bot blocking rules to the text of an Apache SSL conf file.
    Blocking rules taken from https://github.com/ai-robots-txt.
    """
    import httpx

    # Get update bot block rules from Github
    r = httpx.get(
        "https://raw.githubusercontent.com/ai-robots-txt/ai.robots.txt/refs/heads/main/.htaccess"
    )
    if r.status_code != httpx.codes.OK:
        print(
            f"Update bot-blocking rules failed: {r.json()}. Falling back to default rules"
        )
        rule_block = (
            r"RewriteCond %{HTTP_USER_AGENT} (AI2Bot|Ai2Bot\-Dolma|Amazonbot|anthropic\-ai|Applebot|Applebot\-Extended|Brightbot\ 1\.0|Bytespider|CCBot|ChatGPT\-User|Claude\-Web|ClaudeBot|cohere\-ai|cohere\-training\-data\-crawler|Crawlspace|Diffbot|DuckAssistBot|FacebookBot|FriendlyCrawler|Google\-Extended|GoogleOther|GoogleOther\-Image|GoogleOther\-Video|GPTBot|iaskspider/2\.0|ICC\-Crawler|ImagesiftBot|img2dataset|ISSCyberRiskCrawler|Kangaroo\ Bot|Meta\-ExternalAgent|Meta\-ExternalFetcher|OAI\-SearchBot|omgili|omgilibot|PanguBot|PerplexityBot|Perplexity‑User|PetalBot|Scrapy|SemrushBot\-OCOB|SemrushBot\-SWA|Sidetrade\ indexer\ bot|Timpibot|VelenPublicWebCrawler|Webzio\-Extended|YouBot) [NC]"
            r"RewriteRule !^/?robots\.txt$ - [F,L]"
        )
    else:
        rule_block = r.text

    # Add comments as markers
    rule_block = (
        f"\n# Start blocking AI bots with the help of https://github.com/ai-robots-txt\n"
        f"{rule_block}"
        f"# End blocking AI bots\n"
    )

    # Find the <VirtualHost *:443> block
    vh_pattern = r"(<VirtualHost\s+\*:443>)(.*?)(</VirtualHost>)"
    vh_match = re.search(vh_pattern, apache_conf, re.DOTALL | re.IGNORECASE)
    if not vh_match:
        raise ValueError("No <VirtualHost *:443> block found in the config.")

    vh_open, vh_body, vh_close = vh_match.groups()

    # Remove any existing block between the markers
    # "# Start blocking bots" and "# End blocking bots"
    rule_pattern = r"\s*# Start blocking AI bots.*?# End blocking AI bots\s*"
    vh_body_cleaned = re.sub(rule_pattern, "", vh_body, flags=re.DOTALL | re.IGNORECASE)

    # Append the new rule block to the VirtualHost body.
    new_vh_body = vh_body_cleaned.rstrip() + "\n" + rule_block + "\n"
    new_vh_block = vh_open + new_vh_body + vh_close

    # Replace old <VirtualHost *:443> block with updated block
    new_apache_conf = apache_conf.replace(vh_match.group(0), new_vh_block)

    return new_apache_conf


@fr.task
def add_apache_bot_blocking(ctx):
    """ """
    filename = f"{DOMAIN}-le-ssl.conf"
    print("-" * 10, f"Adding bot blocking to Apache conf {filename}...")

    with fr.Connection(HOST, config=CONFIG) as c:
        apache_dir = pl.Path("/etc/apache2/sites-available")
        conf_path = apache_dir / filename
        if exists(c, conf_path):
            # Get old conf
            conf = c.run(f"cat {conf_path}", hide=True).stdout
            # Make new conf
            new_conf = add_bot_block_rules(conf)
            # Upload new conf
            tmp_path = conf_path.parent / (conf_path.name + ".tmp")
            sudo(c, f"echo {shlex.quote(new_conf)} > {tmp_path}")
            # Replace old conf with new conf
            sudo(c, f"mv {tmp_path} {conf_path}")
            with c.cd(apache_dir):
                output = sudo(c, "apachectl configtest")
                if "Syntax OK" in output.stdout:
                    sudo(c, "service apache2 restart")


def delete_apache(ctx):
    """
    Remotely, disable and delete the Apache setup for the app on its domain.
    """
    print("-" * 10, f"Deleting Apache config files for {DOMAIN}...")
    filename = f"{DOMAIN}.conf"
    filename_ssl = f"{DOMAIN}-le-ssl.conf"
    with fr.Connection(HOST, config=CONFIG) as c:
        with c.cd("/etc/apache2/sites-available"):
            if exists(c, filename):
                sudo(c, f"a2dissite {filename}")
                sudo(c, f"rm {filename}")
                sudo(c, "service apache2 restart")
            if exists(c, filename_ssl):
                sudo(c, f"a2dissite {filename_ssl}")
                sudo(c, f"rm {filename_ssl}")
                sudo(c, "service apache2 restart")


@fr.task
def init_gunicorn(ctx):
    """
    Remotely, create and start a Gunicorn service for the app.
    """
    print("-" * 10, "Creating Gunicorn service...")
    # Make the Gunicorn conf file locally, then copy it to the server
    filename = f"dash.{PROJECT}.service"
    su.make_gunicorn_service("uv", PROJECT, out_path=ROOT / filename)
    with fr.Connection(HOST, config=CONFIG) as c:
        gunicorn_dir = pl.Path("/etc/systemd/system/")
        path = gunicorn_dir / filename
        if not exists(c, path):
            # Can't use sudo with put :(, so copy to remote root then sudo move it
            # to the proper folder
            c.put(ROOT / filename)
            sudo(c, f"mv {filename} {gunicorn_dir}")
            sudo(c, f"systemctl enable {filename}")
            sudo(c, f"systemctl start {filename}")
            sudo(c, f"systemctl status {filename}")

    # Delete local conf file
    (ROOT / filename).unlink()


@fr.task
def gunicorn_status(ctx):
    """
    Return the status of the server's Gunicorn service for the app.
    """
    filename = f"dash.{PROJECT}.service"
    with fr.Connection(HOST, config=CONFIG) as c:
        sudo(c, f"systemctl status {filename}").stdout


@fr.task
def delete_gunicorn(ctx):
    """
    Remotely, delete the app's Gunicorn service.
    """
    print("-" * 10, "Deleting Gunicorn service...")
    filename = f"dash.{PROJECT}.service"
    path = pl.Path("/etc/systemd/system/") / filename
    with fr.Connection(HOST, config=CONFIG) as c:
        if exists(c, path):
            sudo(c, f"systemctl stop {filename}")
            sudo(c, f"rm {path}")


@fr.task
def init_user_db(ctx):
    """
    Remotely, if the app has a ``user_management.py`` file, then create a user database,
    initialise it with user 'mrcagney' and the password in the `MRCAGNEY_PASSWORD`
    environment variable.
    Running this task twice will not destroy the original database, but it will recreate
    the 'mrcagney' user.
    So you could change `MRCAGNEY_PASSWORD`, then run this task to update the password
    on the production database.
    """
    if not (ROOT / PROJECT / "user_management.py").exists():
        return

    if not os.getenv("MRCAGNEY_PASSWORD"):
        raise ValueError(
            "You must add the MRCagney user password to the .env file as MRCAGNEY_PASSWORD"
        )

    print("-" * 10, "Initialising user database and adding user 'mrcagney'")
    with fr.Connection(HOST, config=CONFIG) as c:
        with c.cd(REMOTE_DIR / PROJECT):
            c.run(
                f"bash -ic 'uv run python {PROJECT}/user_management.py create-user-table && "
                f"uv run python {PROJECT}/user_management.py remove-user mrcagney && "
                f"uv run python {PROJECT}/user_management.py add-user "
                f"mrcagney {os.getenv('MRCAGNEY_PASSWORD')} mrcagney@mrcagney.com'"
            )


@fr.task
def update_virtualenv(ctx):
    print("-" * 10, "Updating virtualenv...")
    with fr.Connection(HOST, config=CONFIG) as c:
        with c.cd(REMOTE_DIR / PROJECT):
            c.run("bash -ic 'uv sync --no-dev --frozen'")


@fr.task
def restart_gunicorn(ctx):
    print("-" * 10, "Restarting Gunicorn service...")
    filename = f"dash.{PROJECT}.service"
    with fr.Connection(HOST, config=CONFIG) as c:
        sudo(c, f"/usr/bin/systemctl restart {filename}")
        sudo(c, f"/usr/bin/systemctl status {filename}")


@fr.task
def deploy_app(ctx):
    """
    Deploy the app to the web server for the first time.

    If you have app folders that Apache needs to write to, such as a cache folder,
    then run ``fab set-apache-permissions --dirname <folder name>`` after this command
    for each such folder.
    """
    check_for_passwords()
    init_project_folder(ctx)
    rsync_push(ctx)
    init_dotenv(ctx)
    init_virtualenv(ctx)
    init_user_db(ctx)
    init_apache(ctx)
    add_apache_bot_blocking(ctx)
    init_gunicorn(ctx)
    print("-" * 10, f"The app should be working now at {DOMAIN}")


@fr.task
def update_app(ctx):
    """
    Update the app after you've made a new release.
    This entails locally pushing the master branch to 'production',
    remotely Poetry installing the main dependencies, and remotely restarting Gunicorn.
    """
    print("-" * 10, "Updating app...")
    rsync_push(ctx)
    update_virtualenv(ctx)
    restart_gunicorn(ctx)


@fr.task
def delete_app(ctx):
    """
    Delete the app from the web server.
    """
    delete_project_folder(ctx)
    delete_apache(ctx)
    delete_gunicorn(ctx)
