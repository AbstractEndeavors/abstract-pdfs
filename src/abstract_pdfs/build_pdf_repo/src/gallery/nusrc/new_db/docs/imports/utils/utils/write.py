import os
from .imports import *
def write_atomic(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"
    write_to_file(file_path = tmp,contents=content)
    os.replace(tmp, path)

