import click
import flask_sqlalchemy as fsa
import sqlalchemy as sa
import sqlalchemy.sql as sas
import werkzeug.security as ws

import settings as st

engine = sa.create_engine(st.config.SQLALCHEMY_DATABASE_URI)
db = fsa.SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    email = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(50))

    def __repr__(self):
        return "<User %r>" % self.username


user_table = sa.Table("user", User.metadata)


# Add a command line interface
@click.group()
def cli():
    """
    A basic set of command for managing users in the database.
    """
    pass


@cli.command()
def create_user_table():
    User.metadata.create_all(engine)
    click.echo("Created User table")


@cli.command()
@click.argument("username")
@click.argument("password")
@click.argument("email")
def add_user(username: str, password: str, email: str) -> None:
    """
    Add a user with the given username, password, and email address to the database.
    """
    hashed_password = ws.generate_password_hash(password)
    ins = user_table.insert().values(
        username=username, email=email, password=hashed_password
    )
    with engine.connect() as conn:
        conn.execute(ins)
        conn.commit()

    click.echo(f"Added user {username}")


@cli.command()
@click.argument("username")
def remove_user(username: str) -> None:
    """
    Remove the user with the given username from the database.
    """
    delete = user_table.delete().where(user_table.c.username == username)
    with engine.connect() as conn:
        conn.execute(delete)
        conn.commit()

    click.echo(f"Removed user {username}")


@cli.command()
def list_users() -> str:
    """
    Show the users (username, email address) registered in the database.
    """
    select_st = sas.select(user_table.c.username, user_table.c.email)
    with engine.connect() as conn:
        rs = conn.execute(select_st)
        for row in rs:
            print(row)


if __name__ == "__main__":
    cli()
