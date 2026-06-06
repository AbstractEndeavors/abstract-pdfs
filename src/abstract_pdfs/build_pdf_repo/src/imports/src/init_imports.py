from __future__ import annotations
import shutil,logging,json,os,fitz,re,sys,hashlib,argparse
import json, sys,re, unicodedata,os,logging,shutil,PyPDF2
logging.getLogger("pydot").setLevel(logging.WARNING)
logging.getLogger("pypdf").setLevel(logging.WARNING)
logging.getLogger("paddle").setLevel(logging.WARNING)
logging.basicConfig(level=logging.INFO)
logging.getLogger("pika").setLevel(logging.ERROR)
logger = logging.getLogger(__name__)
from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from multiprocessing import Pool
from typing import *
from pathlib import Path
from jinja2 import Template
from typing import Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import *
import html as html_mod
from enum import Enum
from jinja2 import (
    Environment,
    FileSystemLoader,
    select_autoescape
    )

