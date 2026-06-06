from .init_imports import *
SITE_NAME ="thedailydialectics"
DOMAIN= f"{SITE_NAME}.com"
VARIANTS=title_variants_from_domain(DOMAIN)
TITLE_VARIANTS=title_variants_from_domain(DOMAIN)
TENANT_NAME = "The Daily Dialectics"
TENANT_SLUG = "thedailydialectics"
ROOT_URL=URL_ROOT=f"https://{DOMAIN}"
PDFS_PUBLIC_URL='https://thedailydialectics.com/pdfs'
IMGS_PUBLIC_URL='https://thedailydialectics.com/imgs'
MEDIA_ROOT='/var/www/ABSTRACT_ENDEAVORS/media/TDD'
PDF_MEDIA_ROOT = f"{MEDIA_ROOT}/pdfs"
IMG_MEDIA_ROOT = f"{MEDIA_ROOT}/imgs"
REGISTRY_PATH_JSON = "/srv/media/thedailydialectics/registry.json"
REGISTRY_DATA = safe_load_from_json(REGISTRY_PATH_JSON)
IMAGE_EXTS = list(MIME_TYPES.get('image').keys())
MIN_TEXT_CHARS = 100    # avg chars/page below which we consider the PDF scanned
MAX_FITZ_PAGES = 2000   # safety ceiling — don't OCR enormous PDFs without explicit override
