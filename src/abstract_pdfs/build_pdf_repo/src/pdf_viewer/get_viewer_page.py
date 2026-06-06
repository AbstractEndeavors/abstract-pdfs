from __future__ import annotations

from abstract_utilities import *
import json
import os

from ..image_page import get_image_page
from ..imports import *

VIEWER_TEMPLATE_NAME = "pdf_viewer/viewer_base/viewer_base.html"
def path_to_url(path: str, media_root: str = PDF_MEDIA_ROOT, site_root: str = SITE_ROOT) -> str:
    rel = os.path.realpath(path).replace(os.path.realpath(media_root), "").lstrip(os.sep)
    return f"{site_root}/{rel.replace(os.sep, '/')}"


def clean_text(value: str, max_len: int = 180) -> str:
    value = (value or "").strip()
    value = " ".join(value.split())
    if len(value) <= max_len:
        return value
    return value[:max_len].rsplit(" ", 1)[0] + "…"


def dedupe_keywords(values: list[str], limit: int = 20) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for raw in values:
        kw = str(raw or "").strip()
        key = kw.lower()
        if not kw or key in seen:
            continue
        seen.add(key)
        output.append(kw)
        if len(output) >= limit:
            break
    return output


def ensure_public_url(value: str | None, media_root: str = PDF_MEDIA_ROOT, site_root: str = SITE_ROOT) -> str:
    if not value:
        return ""
    value = str(value).strip()
    if not value:
        return ""
    if value.startswith("http://") or value.startswith("https://"):
        return value
    if value.startswith("/"):
        if os.path.exists(value):
            return path_to_url(value, media_root=media_root, site_root=site_root)
        return f"{site_root.rstrip('/')}/{value.lstrip('/')}"
    return value


def viewer_canonical_url(pdf_dir: str, metadata: dict) -> str:
    canonical = str(metadata.get("canonical") or "").strip()
    if canonical.endswith((".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf")):
        return path_to_url(pdf_dir)
    if canonical:
        return ensure_public_url(canonical)
    return path_to_url(pdf_dir)


def normalize_keywords(metadata: dict, page_keywords: list[str], limit: int = 20) -> list[str]:
    metadata_keywords = metadata.get("keywords") or []
    if isinstance(metadata_keywords, str):
        metadata_keywords = [item.strip() for item in metadata_keywords.split(",") if item.strip()]
    elif not isinstance(metadata_keywords, list):
        metadata_keywords = []

    combined: list[str] = []
    combined.extend(metadata_keywords)
    combined.extend(page_keywords)
    return dedupe_keywords(combined, limit=limit)


def build_meta_bundle(
    *,
    metadata: dict,
    title: str,
    description: str,
    canonical_url: str,
    first_thumb: str,
    keywords_list: list[str],
) -> dict:
    og = metadata.get("og") or {}
    twitter = metadata.get("twitter") or {}
    other = metadata.get("other") or {}

    published_time = (
        ((og.get("article") or {}).get("published_time"))
        or metadata.get("published_time")
        or ""
    )
    modified_time = (
        ((og.get("article") or {}).get("modified_time"))
        or og.get("updated_time")
        or metadata.get("modified_time")
        or ""
    )

    thumbnail_url = (
        ensure_public_url(metadata.get("thumbnail_link"))
        or ensure_public_url(metadata.get("thumbnail_url_resized"))
        or ensure_public_url(metadata.get("thumbnail_resized"))
        or ensure_public_url(metadata.get("thumbnail"))
        or ensure_public_url(og.get("image"))
        or ensure_public_url(twitter.get("image"))
        or first_thumb
    )

    resolved_og = {
        "type": og.get("type") or "article",
        "title": og.get("title") or title,
        "description": og.get("description") or description,
        "url": viewer_canonical_url(metadata.get("source_dir", ""), metadata) if metadata.get("source_dir") else canonical_url,
        "image": thumbnail_url,
        "image_alt": og.get("image_alt") or title,
        "image_width": og.get("image_width") or "",
        "image_height": og.get("image_height") or "",
        "image_type": og.get("image_type") or "",
        "locale": og.get("locale") or "en_US",
        "site_name": og.get("site_name") or "thedailydialectics",
        "article": {
            "published_time": published_time,
            "modified_time": modified_time,
            "section": ((og.get("article") or {}).get("section")) or "",
            "tag": ((og.get("article") or {}).get("tag")) or keywords_list,
        },
    }

    twitter_card = twitter.get("card") or "summary_large_image"
    if twitter_card == "app":
        twitter_card = "summary_large_image"

    resolved_twitter = {
        "card": twitter_card,
        "title": twitter.get("title") or title,
        "description": twitter.get("description") or description,
        "site": twitter.get("site") or "@thedailydialectics",
        "creator": twitter.get("creator") or "@thedailydialectics",
        "image": thumbnail_url,
        "image_alt": twitter.get("image_alt") or title,
        "domain": twitter.get("domain") or "thedailydialectics.com",
    }

    resolved_other = {
        "robots": other.get("robots") or "index, follow",
        "googlebot": other.get("googlebot") or "index, follow",
        "author": other.get("author") or "@thedailydialectics",
        "viewport": other.get("viewport") or "width=device-width, initial-scale=1",
        "theme_color": other.get("theme_color") or "#FFFFFF",
        "referrer": other.get("referrer") or "origin-when-cross-origin",
    }

    return {
        "thumbnail_url": thumbnail_url,
        "published_time": published_time,
        "modified_time": modified_time,
        "og": resolved_og,
        "twitter": resolved_twitter,
        "other": resolved_other,
    }
def get_meta_info(analyzed_data,page_dir,metadata_path,href=None):
    image_path = analyzed_data.get("image_path")
    if not image_path:
       dirs,files = get_files_and_dirs(page_dir,allwed_exts=list(MIME_TYPES.get('image').keys()))
       if files:
           image_path = files[0]
    summary = analyzed_data.get("summary", "")
    keywords = analyzed_data.get("keywords", {})
    dirname = os.path.dirname(page_dir)
    dirbase = os.path.basename(dirname)
    parent_dirname = os.path.dirname(dirname)
    parent_dirbase = os.path.basename(parent_dirname)
    pdf_title = parent_dirbase.replace('_','-').replace('_','-').replace('--','-')
    page_title = f"{pdf_title}-{dirbase}"
    alt = f"{pdf_title}-{dirbase} pdf Image"
    capt = summary[:67] if len(summary) >67 else summary
    caption = f"{alt} {capt}..." 
    
    href = path_to_url(href or image_path)
    meta_info = get_page_data(page_title,
                href,
                summary,
                keywords,
                href,
                alt=alt,
                caption=caption)
 
    safe_dump_to_json(file_path=str(metadata_path), data=meta_info)
    return meta_info
def get_image_candidate(page_dir,candidates=None):
    candidates = make_list(candidates or []) +  ["image.webp", "image.png", "image.jpg", "image.jpeg"]
    for candidate in candidates:
        candidate_path = os.path.join(page_dir, candidate)
        if os.path.isfile(candidate_path):
            return path_to_url(candidate_path)
                    
def get_safe_read(file_path:str):
    data = safe_load_from_json(file_path) if os.path.isfile(file_path) else {}
    return data or {}
def get_safe_file_read(file_path:str):
    contents = read_from_file(file_path) if os.path.isfile(file_path) else ""
    return contents or {}
def get_text_info(text_path):
    if not os.path.isfile(text_path):
        file_parts = get_file_parts(text_path)
        page_num = file_parts.get('dirbase')
        pdf_dir = file_parts.get('super_dirname')
        pdf_paths = [os.path.join(pdf_dir,item) for item in os.listdir(pdf_dir) if item.endswith('.pdf')]
        if pdf_paths:
            pdf_path = pdf_paths[0]
            text = extract_single_pdf_page_text(pdf_path=pdf_path, page_index=int(page_num))
            write_to_file(file_path=text_path,contents=text)
    return read_from_file(text_path)
def get_info_data(info_path):

    if not os.path.isfile(info_path) or read_from_file(info_path)== "":
        text_path = info_path.replace('info.json','text.txt')
        text_info = get_text_info(text_path)        
def build_page_payload(page_dir: str, pdf_slug: str) -> dict:
##    try:
        page_num = int(os.path.basename(page_dir))
        info_path = os.path.join(page_dir, "info.json")
        meta_path = os.path.join(page_dir, "metadata.json")
        text_path = os.path.join(page_dir, "text.txt")

        info = get_safe_read(info_path)
#        print(f"info == {info}")
        text = get_safe_file_read(text_path)
#        print(f"text == {text}")
        meta = get_safe_read(meta_path)
#        print(f"meta == {meta}")
  
        summary = info.get('summary')
#        print(f"summary == {summary}")
        page_keywords = (info.get('keywords',{}).get('primary') or info.get('keywords',{}).get('meta_keywords') or []) if isinstance(info, dict) else []
#        print(f"page_keywords == {page_keywords}")
        title = meta.get('title')
#        print(f"title == {title}")
        image_alt = meta.get('og',{}).get('image_alt') or meta.get('twitter',{}).get('image_alt') or meta.get('twitter',{}).get('html_description') or title or ''
#        print(f"image_alt == {image_alt}")
        image_url = meta.get('thumbnail') or meta.get('thumbnail_link')
#        print(f"image_url == {image_url}")
        thumb = meta.get('thumbnail_resized') or meta.get('thumbnail_url_resized')
        if 'https://thedailydialectics/None' in str(meta):
            href = viewer_canonical_url(pdf_dir, meta)
            meta_info = get_meta_info(info,page_dir,meta_path,href=href)
            input(meta_info)
#        print(f"thumb == {thumb}")
        if not not thumb:
    #        print(f"get_image_candidate == thumb < {thumb}")
            thumb = get_image_candidate(page_dir,candidates="image_627x1200.png") or image_url
        if not image_url:
    #        print(f"get_image_candidate == image_url < {image_url}")
            image_url = get_image_candidate(page_dir) or thumb
        if thumb and os.path.isfile(thumb):
            thumb = path_to_url(thumb)
        if image_url and os.path.isfile(image_url):
            image_url = path_to_url(image_url)
        keywords = ((info.get("keywords") or {}).get("primary") or []) if isinstance(info, dict) else []
#        print(f"keywords == {keywords}")
        return {
            "n": page_num,
            "thumb": path_to_url(thumb) if thumb else "",
            "image": image_url,
            "text": text,
            "alt": title,
            "page_title": (title or info.get("scope", "")) if isinstance(info, dict) else "",
            "page_keywords": page_keywords,
        }
##    except Exception as e:
##        input(f"{e}")

def get_viewer_page(pdf_path: str) -> str:
    file_parts = get_file_parts(pdf_path)
    pdf_dir = file_parts.get("dirname")
    pdf_slug = file_parts.get("dirbase")
    pages_dir = os.path.join(pdf_dir, "pages")
    html_path = os.path.join(pdf_dir, "index.html")
    meta_path = os.path.join(pdf_dir, "meta", "metadata.json")
    
    metadata = {}
    if os.path.isfile(meta_path):
        metadata = safe_load_from_json(meta_path) or {}

    metadata["source_dir"] = pdf_dir
    correct_meta_datas(pdf_path)
    title = metadata.get("title") or humanize(pdf_slug)
    description = clean_text(
        metadata.get("summary")
        or metadata.get("summary_html")
        or f"Read {title} in image, text, or PDF view."
    )
    canonical_url = viewer_canonical_url(pdf_dir, metadata)
    pdf_url = path_to_url(pdf_path)
    download_url = pdf_url

    pages: list[dict] = []
    page_keywords: list[str] = []
    if os.path.isdir(pages_dir):
        
        for page_dir_name in sorted(os.listdir(pages_dir)):
            page_dir = os.path.join(pages_dir, page_dir_name)
            
            if not os.path.isdir(page_dir) or not page_dir_name.isdigit():
                continue

            page = build_page_payload(page_dir=page_dir, pdf_slug=pdf_slug)
            pages.append(page)
            page_keywords.extend(page["page_keywords"])
            
    if not pages:
        pages = [{
            "n": 1,
            "thumb": "",
            "image": "",
            "text": "",
            "alt": pdf_slug,
            "page_title": "",
            "page_keywords": [],
        }]

    keywords_list = normalize_keywords(metadata, page_keywords, limit=20)
    keywords_str = ", ".join(keywords_list)
    first_thumb = pages[0]["thumb"] if pages else ""

    meta_bundle = build_meta_bundle(
        metadata=metadata,
        title=title,
        description=description,
        canonical_url=canonical_url,
        first_thumb=first_thumb,
        keywords_list=keywords_list,
    )

    schema = metadata.get("schema") or {
        "@context": "https://schema.org",
        "@type": "ScholarlyArticle",
        "name": title,
        "headline": title,
        "description": description,
        "url": canonical_url,
        "thumbnailUrl": meta_bundle["thumbnail_url"],
        "image": meta_bundle["thumbnail_url"],
        "fileFormat": "application/pdf",
        "datePublished": meta_bundle["published_time"],
        "dateModified": meta_bundle["modified_time"],
        "keywords": keywords_list,
    }

    viewer_config = {
        "title": title,
        "description": description,
        "canonicalUrl": canonical_url,
        "siteRoot": SITE_ROOT,
        "pdfUrl": pdf_url,
        "downloadUrl": download_url,
        "defaultMode": "images",
        "total": len(pages),
        "keywords": keywords_list,
        "pages": pages,
    }

    env = get_jinja_env()
    template = env.get_template(VIEWER_TEMPLATE_NAME)
    thumbnail = meta_bundle["thumbnail_url"] or first_thumb
    
    html = template.render(
        title=title,
        description=description,
        keywords=keywords_str,
        canonical_url=canonical_url,
        first_thumb=thumbnail,
        schema_json=json.dumps(schema, ensure_ascii=False),
        site_root=SITE_ROOT,
        pdf_url=pdf_url,
        download_url=download_url,
        total=len(pages),
        viewer_config_json=json.dumps(viewer_config, ensure_ascii=False),
        meta_bundle=meta_bundle,
        breadcrumbs=breadcrumbs(pdf_url),
        viewer_css_url="/assets/css/pdf-viewer/viewer.css",
        viewer_js_url="/assets/js/pdf-viewer/page-viewer.js",
        viewer_theme_vars="",
    )

    write_to_file(file_path=html_path, contents=html)
    return pdf_url
