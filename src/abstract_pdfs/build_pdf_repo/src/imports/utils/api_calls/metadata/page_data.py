from .imports import *
MAX_FITZ_PAGES = 2000   # safety ceiling — don't OCR enormous PDFs without explicit override
def path_to_url(path):
    return path.replace(MEDIA_ROOT,ROOT_URL)
def url_to_path(path):
    return path.replace(ROOT_URL,MEDIA_ROOT)

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
def get_parsed_url(domain, **kwargs):
    parsed_url = dict(kwargs)
    post_variants = []
    # http / www
    http_www = get_http_www(domain)
    parsed_url.update(http_www)
    http = http_www.get('http')
    # basic domain pieces
    domain_paths = get_domain_paths(domain, http=http)
    if 'path' not in parsed_url:
        parsed_url['path']=[]
    parsed_url['path']+=domain_paths
    domain_name_ext = get_domain_name_ext(domain, http=http)
    parsed_url.update(domain_name_ext)

    domain_name = parsed_url.get('name',"") or ""
    domain = parsed_url.get('domain',"") or ""
        # tokenization
    tokenized_domain = tokenize_domain(domain)
    parsed_url["tokenized_domain"] = tokenized_domain
    app_name = " ".join(tokenized_domain)
    
    parsed_url["app_name"] = app_name
    # author / "i_url"
    parsed_url["author"] = f"@{domain_name.lower()}"
    parsed_url["i_url"] = f"{domain_name}://"

    # combine with domain
    # compute final title
    title = get_title(parsed_url)
    
    post_variants=[title,app_name,domain]
    variants = title_variants_from_domain(domain)
    base_variants = list(set([variant for variant in variants if variant not in post_variants]))
    # update the organized variants
    parsed_url["title_variants"] = get_all_title_variants(variants=base_variants,page=title,name=app_name,domain=domain)

    parsed_url["title"] = pad_or_trim(
        "title",
        string=title,
        title_variants=parsed_url["title_variants"],
        page=title,
        domain=domain,
        name = app_name
    )
    # get keywords
    keywords_info = get_keywords(parsed_url,page=title,domain=domain,name = app_name)
    parsed_url.update(keywords_info)
    keywords = parsed_url.get("keywords", [])
    # FINAL: longest→shortest list with TITLE first, DOMAIN second
    domain = parsed_url.get("domain")
    if domain:
        final_variants = [title,page_data ]
        # remove title/domain from pool
        pool = set(keywords + variants)
        pool.discard(title)
        pool.discard(parsed_url.get("domain"))

        # sort longest → shortest
        final_variants += sort_longest_first(pool)

        parsed_url["title_variants"] = final_variants
   
    return parsed_url
def init_page_data():
    page_data = {}
    variants=title_variants_from_domain(DOMAIN)
    title_variants=title_variants_from_domain(DOMAIN) 
    site_name=SITE_NAME
    domain=DOMAIN
    root_url=ROOT_URL
    page_data = getInfo(domain=DOMAIN)
    page_data = get_parsed_url(**page_data)
    page_data['domain']=domain
    page_data['variants']=variants
    page_data['site'] = root_url
    page_data['site_name'] = site_name
    page_data['creator'] = site_name
    page_data['author'] = f'@{site_name}'
    return page_data

def get_page_data(
    title,
    href,
    summary,
    keywords,
    keywords_str,
    thumbnail_url,
    alt=None,
    caption=None,
    ):
    page_data = init_page_data()
    page_data["title"] = title
    page_data['href'] = href
    page_data["page_url"] = href
    page_data['share_url'] = href
    page_data['thumbnail'] = url_to_path(thumbnail_url)
    page_data['thumbnail_link'] = thumbnail_url
    page_data['description'] = summary
    page_data['keywords'] = keywords
    page_data['keywords_str']= ','.join(keywords)
    page_data["alt"] = alt or title
    page_data["caption"] = caption or summary
    
    meta_info = get_meta_info(info=page_data,base_image_dir=PDF_MEDIA_ROOT,base_image_url=PDFS_PUBLIC_URL)
    meta_info['thumbnail_resized'] = path_to_url(meta_info.get('thumbnail_resized',thumbnail_url) or thumbnail_url)
    meta_info['thumbnail_url_resized'] = path_to_url(meta_info.get('thumbnail_url_resized',thumbnail_url) or thumbnail_url)
    meta_info['thumbnail'] = path_to_url(meta_info.get('thumbnail',thumbnail_url) or thumbnail_url)
    meta_info['og']['image'] = path_to_url(meta_info.get('og',{}).get('image',thumbnail_url) or thumbnail_url)
    meta_info['twitter']['image'] = path_to_url(meta_info.get('twitter',{}).get('image',thumbnail_url) or thumbnail_url)

    return meta_info
##    page_data["alt"] = alt or title
##    page_data["caption"] = caption or summary
##    page_data["schema"] = meta.get("og", {})
##    page_data["schema"]['site_name'] = SITE_NAME
##    page_data["social_meta"] = meta.get("twitter", {})
##    page_data["other"] = meta.get("other")
##    page_data['meta']= meta
##    return page_data
def get_metadata_info(pdf_path,page_number):
    page_dir = get_page_dir_from_pdf_path(pdf_path, page_number)
    info_path  = get_page_info_path_from_pdf_path(pdf_path, page_number)
    image_path = get_page_image_path_from_pdf_path(pdf_path, page_number)
    analyzed_data = safe_load_from_json(info_path) 
    meta_path = get_page_meta_path_from_pdf_path(pdf_path, page_number)
    if not image_path:
       dirs,files = get_files_and_dirs(page_dir,allwed_exts=list(MIME_TYPES.get('image').keys()))
       if files:
           image_path = files[0]
    if not analyzed_data.get("image_path"):
        analyzed_data["image_path"]=image_path
        safe_dump_to_json(data=analyzed_data,file_path=info_path)
    summary = get_info_summary_from_pdf_path(pdf_path, page_number)
    keywords = get_info_keywords_from_pdf_path(pdf_path, page_number)
    keywords_str = ', '.join(keywords)
    pdf_title = get_pdf_title_from_pdf_path(pdf_path, page_number)
    page_title = get_page_title_from_pdf_path(pdf_path, page_number)
    alt = get_page_alt_from_pdf_path(pdf_path, page_number)
    caption = get_caption_from_pdf_path(pdf_path, page_number)
    href = path_to_url(page_dir)
    thumbnail_url = path_to_url(image_path)
    meta_info = get_page_data(page_title,
                href=href,
                summary=summary,
                keywords=keywords,
                keywords_str=keywords_str,
                thumbnail_url=thumbnail_url,
                alt=alt,
                caption=caption)
 
    
    return meta_info
