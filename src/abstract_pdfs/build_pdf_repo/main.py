import logging

# Configure logging
logging.basicConfig(level=logging.ERROR)  # Change to INFO or higher to suppress DEBUG logs
logger = logging.getLogger(__name__)
from src import *
pdf_dir = "/home/op/Documents/python/test_pdfs/cancer-pdf"
pages_dir = process_pdf(pdf_dir)
