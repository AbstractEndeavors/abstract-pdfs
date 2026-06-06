from src import *
def process_pdf(pdf_path, cfg=None):
    """Generate viewer page for a single PDF."""
    cfg = cfg or SiteConfig()
    url = get_viewer_page(pdf_path, cfg=cfg)
    print("wrote viewer → {}".format(url))
    return url

pdf_path = "/home/op/Documents/python/modules/src/modules/abstract_pdfs/src/abstract_pdfs/generate_htmls/test_pdfs/ch102practiceexam2/ch102practiceexam2.pdf"
process_pdf(pdf_path)
