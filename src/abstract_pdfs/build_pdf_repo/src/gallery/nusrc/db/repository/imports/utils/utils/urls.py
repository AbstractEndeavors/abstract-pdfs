import os
from .imports import MEDIA_ROOT,ROOT_URL,eatOuter,eatInner
def join_pathlike(path,rel):
    path = eatOuter(path,'/')
    rel = eatInner(rel,'/')
    return f"{path}/{rel}"
def path_to_url(path):
    rel_path = str(path).replace(MEDIA_ROOT,"")
    return join_pathlike(ROOT_URL,rel_path)
def url_to_path(url):
    rel_path = url.replace(ROOT_URL,"")
    return join_pathlike(MEDIA_ROOT,rel_path)
def path_to_url_info(path):
    dirname = os.path.dirname(path)       
    return path_to_url(dirname)
def convert_paths_to_urls(data,base_url=None):
    base_url = base_url or ROOT_URL
    return join_pathlike(MEDIA_ROOT,base_url)
