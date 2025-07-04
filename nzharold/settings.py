# -*- coding: utf-8 -*-
"""Application configuration."""

import os
import pathlib as pl

import dotenv as de

# Load environment variables from .dotenv
# Pipenv does this automatically, so the following code line is
# redundant if you are using Pipenv
ROOT = pl.Path(os.path.abspath(__file__)).parent.parent
de.load_dotenv(dotenv_path=ROOT / ".env")


class BaseConfig(object):
    ROOT = pl.Path(os.path.abspath(__file__)).parent.parent
    APP_DIR = ROOT / "nzherald"
    DATA_DIR = ROOT / "data"
    ASSETS_DIR = APP_DIR / "assets"
    CACHE_DIR = ROOT / "cache"

    SECRET_KEY = os.getenv("SECRET_KEY")
    BCRYPT_LOG_ROUNDS = 13
    DEBUG_TB_ENABLED = False  # Disable Debug toolbar
    DEBUG_TB_INTERCEPT_REDIRECTS = False
    CACHE_TYPE = "simple"  # Can be "memcached", "redis", etc.
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{ROOT / 'users.sqlite'}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class DevConfig(BaseConfig):
    MODE = "development"
    DEBUG = True
    DEBUG_TB_ENABLED = True


class ProdConfig(BaseConfig):
    MODE = "production"
    DEBUG = False


# Choose configuration from environment variable MODE
mode = os.getenv("MODE")
if mode == "development":
    config = DevConfig
else:
    config = ProdConfig
