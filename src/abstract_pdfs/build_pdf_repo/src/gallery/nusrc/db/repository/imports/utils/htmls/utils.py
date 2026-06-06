from .imports import MEDIA_ROOT,URL_ROOT
def create_bread_crumbs(path):
    path_parts = path.replace(MEDIA_ROOT,'').split('/thumbnails/')[0].split('/text/')[0].split('/')
    parts = [part for part in path_parts if part]
    path_init = URL_ROOT
    breadCrumbs = f'<nav class="breadcrumb"> › <a href="{path_init}">Home</a>'
    main = parts[-1]
    parts = parts[:-1]
    for part in parts:
        path_init = f"{path_init}/{part}"
        a_comp = f'<a href="{path_init}/">{part}</a>'
        breadCrumbs = f"{breadCrumbs} › {a_comp}"
    breadCrumbs = f"{breadCrumbs} › <span>{main}</span></nav>"
    return breadCrumbs
