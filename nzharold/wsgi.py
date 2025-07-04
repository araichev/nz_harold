#!/usr/bin/python3
import os
import sys

ROOT = os.path.abspath(os.path.join(__file__, ".."))
sys.path.append(ROOT)

from index import server as application
