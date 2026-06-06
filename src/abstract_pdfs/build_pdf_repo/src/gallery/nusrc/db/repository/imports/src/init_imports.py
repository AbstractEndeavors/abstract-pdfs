from typing import Optional
import re, unicodedata,os,logging
# your logs — INFO and up
logging.basicConfig(level=logging.INFO)

# pika — errors only
logging.getLogger("pika").setLevel(logging.ERROR)
from abstract_utilities import *
from abstract_apis import *
from pathlib import Path
from abstract_webtools import title_variants_from_domain
from abstract_react import getInfo,get_meta_info
logger = logging.getLogger(__name__)

