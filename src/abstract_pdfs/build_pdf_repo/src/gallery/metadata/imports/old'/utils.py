from .constants import *
from .init_imports import *
def save_info(data,file_path):
    if data:
        safe_dump_to_json(data=data,file_path=file_path)
def zero_it(i):
    i_str = str(i)
    i_len = len(i_str)
    return '000'[:-i_len]+i_str
def elim_zeros(num):
    return eatInner(num,['0'])
def get_img_exts():
    return list(MIME_TYPES.get('image').keys())
def humanize(name: str) -> str:
    return name.replace("-", " ").replace("_", " ").title()
def clean_text(s: str, max_len: int = 200) -> str:
    if isinstance(s,list):
        s = str(s[0])
    s = re.sub(r'\s+', ' ', s).strip()
    if len(s) > max_len:
        s = s[:max_len].rsplit(' ', 1)[0] + '…'
    return s
def getPath(path):
    if path and isinstance(path,str):
        path = Path(path)
    return path
