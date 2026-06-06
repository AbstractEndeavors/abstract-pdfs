from .init_imports import *
from .module_imports import *
SITE_NAME = "thedailydialectics"
DOMAIN = f"{SITE_NAME}.com"
TDD_ROOT_URL = SITE_ROOT = URL_ROOT = ROOT_URL = f"https://{DOMAIN}"
TDD_IMGS_URL = f"{TDD_ROOT_URL}/imgs"
TDD_PDFS_URL = PDFS_PUBLIC_URL = f"{TDD_ROOT_URL}/pdfs"
TDD_PUBLIC_URL = f"{TDD_ROOT_URL}/public"
VARIANTS=title_variants_from_domain(DOMAIN)
TITLE_VARIANTS=title_variants_from_domain(DOMAIN)
TENANT_NAME = "The Daily Dialectics"
TENANT_SLUG = "thedailydialectics"

TDD_ROOT_DIR = "/srv/thedailydialectics/app"
TDD_SRC_DIR = os.path.join(TDD_ROOT_DIR,"src")
TDD_PUBLIC_DIR = os.path.join(TDD_ROOT_DIR,"public")
TDD_PAGES_DIR = os.path.join(TDD_ROOT_DIR,"pages")

TDD_MEDIA_ROOT_DIR = MEDIA_ROOT = "/srv/media/thedailydialectics"
TDD_IMGS_DIR = os.path.join(TDD_MEDIA_ROOT_DIR,"imgs")
TDD_PDFS_DIR = PDF_MEDIA_ROOT = PDF_DIR = os.path.join(TDD_MEDIA_ROOT_DIR,"pdfs")
TDD_VIDEOS_DIR = os.path.join(TDD_MEDIA_ROOT_DIR,"videos")
TDD_MEDIA_PAGES_DIR = os.path.join(TDD_MEDIA_ROOT_DIR,"pages")

TDD_IMGS_PDF_IMAGES_DIR = os.path.join(TDD_IMGS_DIR,"pdf_images")
TDD_IMGS_PDF_IMAGES_WIPOW_DIR= os.path.join(TDD_IMGS_PDF_IMAGES_DIR,"wipow")
TDD_PDF_IMAGES_WIPOW_PATENTS_DIR = os.path.join(TDD_IMGS_PDF_IMAGES_WIPOW_DIR,"patents")

TDD_PDFS_WIPOW_DIR = os.path.join(TDD_PDFS_DIR,"wipow")
TDD_PDFS_WIPOW_PATENTS_DIR = os.path.join(TDD_PDFS_WIPOW_DIR,"patents")

IMAGE_EXTS = list(MIME_TYPES.get('image').keys())

SKIP_DIRS = {
    "text", "pages", "images", "thumbnails", "pdf_pages",
    "preprocessed_images", "preprocessed_text",
    "node_modules", ".git", "__pycache__",
}

TEST_DIR = os.path.join(get_caller_dir(), "test")

REGISTRY_PATH_JSON = "/srv/media/thedailydialectics/registry.json"
REGISTRY_DATA = safe_load_from_json(REGISTRY_PATH_JSON)
IMAGE_EXTS = list(MIME_TYPES.get('image').keys())
MIN_TEXT_CHARS = 100    # avg chars/page below which we consider the PDF scanned
MAX_FITZ_PAGES = 2000   # safety ceiling — don't OCR enormous PDFs without explicit override

TENANT_ID = "c16c16fd-e86e-4727-952c-dcb569c52f0d"
POOL_SIZE = 8

