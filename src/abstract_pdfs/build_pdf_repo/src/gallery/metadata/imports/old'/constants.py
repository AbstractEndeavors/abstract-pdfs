from .module_imports import MIME_TYPES,os
DOMAIN = "thedailydialectics.com"
SITE_ROOT_DEFAULT = f"https://{DOMAIN}"

SKIP_DIRS = frozenset({
    "text", "pages", "pdf_pages",
    "preprocessed_images", "preprocessed_text",
    "node_modules", ".git", "__pycache__",
})

IMAGE_EXTS = frozenset({".webp", ".jpg", ".jpeg", ".png", ".gif"})

VARIANTS=title_variants_from_domain(DOMAIN)
TITLE_VARIANTS=title_variants_from_domain(DOMAIN)
TDD_ROOT_URL = "https://thedailydialectics.com"
TDD_IMGS_URL = f"{TDD_ROOT_URL}/imgs"
TDD_PDFS_URL = f"{TDD_ROOT_URL}/pdfs"
TDD_PUBLIC_URL = f"{TDD_ROOT_URL}/public"

TDD_ROOT_DIR = "/var/www/presites/thedailydialectics/react/main"
TDD_SRC_DIR = os.path.join(TDD_ROOT_DIR,"src")
TDD_PUBLIC_DIR = os.path.join(TDD_ROOT_DIR,"public")
TDD_PAGES_DIR = os.path.join(TDD_ROOT_DIR,"pages")

TDD_MEDIA_ROOT_DIR = "/srv/media/thedailydialectics"
TDD_IMGS_DIR = os.path.join(TDD_MEDIA_ROOT_DIR,"imgs")
TDD_PDFS_DIR = os.path.join(TDD_MEDIA_ROOT_DIR,"pdfs")
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
SITE_ROOT = TDD_ROOT_URL
