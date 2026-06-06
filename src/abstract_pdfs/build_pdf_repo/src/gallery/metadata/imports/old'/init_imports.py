from __future__ import annotations
import shutil,logging,json,os,fitz,re,sys,hashlib,argparse
logging.getLogger("pydot").setLevel(logging.WARNING)
logging.getLogger("pypdf").setLevel(logging.WARNING)
logging.getLogger("paddle").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import *
from enum import Enum
from jinja2 import (
    Environment,
    FileSystemLoader,
    select_autoescape
    )




