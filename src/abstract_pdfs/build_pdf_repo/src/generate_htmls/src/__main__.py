"""
Example entry point.

Demonstrates explicit config wiring — no hidden globals.
"""
import sys
from generate_htmls import get_viewer_page, get_image_page, get_gallery_page, SiteConfig


def process_pdf(pdf_path, cfg=None):
    """Generate viewer page for a single PDF."""
    cfg = cfg or SiteConfig()
    url = get_viewer_page(pdf_path, cfg=cfg)
    print("wrote viewer → {}".format(url))
    return url


def main():
    if len(sys.argv) < 2:
        print("usage: python -m generate_htmls <pdf_path>")
        sys.exit(1)

    pdf_path = sys.argv[1]

    # explicit config — swap in a test config by changing this one line
    cfg = SiteConfig(
        site_name="thedailydialectics",
        domain="thedailydialectics.com",
        root_url="https://thedailydialectics.com",
        media_root="/srv/media/thedailydialectics",
    )

    process_pdf(pdf_path, cfg)


if __name__ == "__main__":
    main()
