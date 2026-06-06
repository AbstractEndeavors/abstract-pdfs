from abstract_pdfs import *
from abstract_apis import *
from abstract_hugpy.utils.seo.pdf_utils import _analyze

import time
def get_hupy_text_data(page_text,page_number):
    return {
        "text": page_text,
        "scope": f"page:{page_number}",
        "summary_preset": "brief",
        "keyword_preset": "seo",
    }
def get_raw_text(pdf_path,i):
    return extract_single_pdf_page_text(str(pdf_path), i)
def get_raw_text_time(pdf_path,i):
    start_time = time.time()
    page_text = get_raw_text(pdf_path,i)
    end_time = time.time()
    total_time = end_time-start_time
    print(f"get_raw_text_time == {total_time}")
    return page_text
def get_clownworld_ocr_text(pdf_image):
    return requests.post("https://clownworld.biz/ocr/images/layout/to_text",data={"image_path":str(pdf_image)}).json()['result']
def get_clownworld_ocr_text_time(pdf_image):
    start_time = time.time()
    page_text = get_clownworld_ocr_text(pdf_image)
    end_time = time.time()
    total_time = end_time-start_time
    print(f"get_clownworld_ocr_text == {total_time}")
    return page_text
def get_local_ocr_text(pdf_image):
    return requests.post("http://127.0.0.1:6056/images/layout/to_text",data={"image_path":str(pdf_image)}).json()['result']
def get_local_ocr_text_time(pdf_image):
    start_time = time.time()
    page_text = get_local_ocr_text(pdf_image)
    end_time = time.time()
    total_time = end_time-start_time
    print(f"get_local_ocr_text_time == {total_time}")
    return page_text
def get_clownworld_hugpy_summate(page_text,page_number):
    data = get_hupy_text_data(page_text,page_number)
    return requests.post('https://clownworld.biz/hugpy/analyze/text', data=data).json()['result']
def get_clownworld_hugpy_summate_time(page_text,page_number):
    start_time = time.time()
    analyzed_data = get_clownworld_hugpy_summate(page_text,page_number)
    end_time = time.time()
    total_time = end_time-start_time
    print(f"get_clownworld_hugpy_summate_time == {total_time}")
    return analyzed_data
def get_local_hugpy_summate(page_text,page_number):
    data = get_hupy_text_data(page_text,page_number)
    return requests.post('http://127.0.0.1:6053/analyze/text', data=data).json()['result']
def get_local_hugpy_summate_time(page_text,page_number):
    start_time = time.time()
    analyzed_data = get_local_hugpy_summate(page_text,page_number)
    end_time = time.time()
    total_time = end_time-start_time
    print(f"get_local_hugpy_summate_time == {total_time}")
    return analyzed_data
def get_hugpy_summate(page_text,page_number):
    data = get_hupy_text_data(page_text,page_number)
    return  _analyze(**data)
def get_hugpy_summate_time(page_text,page_number):
    start_time = time.time()
    analyzed_data = get_hugpy_summate(page_text,page_number)
    end_time = time.time()
    total_time = end_time-start_time
    print(f"get_hugpy_summate_time == {total_time}")
    return analyzed_data
pdf_image = "/var/www/ABSTRACT_ENDEAVORS/media/TDD/pdfs/space/UFO Disclosure & Disclosure Project SuperPack/Giant Collection of UFO eBooks Vol. 1 of 2/The Eye of Ra Book Two - Truman Cash/pages/0004/image.png"
pdf_path = "/var/www/ABSTRACT_ENDEAVORS/media/TDD/pdfs/space/UFO Disclosure & Disclosure Project SuperPack/Giant Collection of UFO eBooks Vol. 1 of 2/The Eye of Ra Book Two - Truman Cash/The Eye of Ra Book Two - Truman Cash.pdf"
raw_text = get_raw_text(pdf_path,4)
get_clownworld_ocr_text(pdf_image)
get_local_ocr_text(pdf_image)
get_clownworld_hugpy_summate(raw_text,4)
ocr_text = get_local_hugpy_summate(raw_text,4)
get_hugpy_summate(raw_text,4)

raw_text = get_raw_text_time(pdf_path,4)
ocr_text = get_clownworld_ocr_text_time(pdf_image)
ocr_text = get_local_ocr_text_time(pdf_image)
ocr_text = get_clownworld_hugpy_summate_time(raw_text,4)
ocr_text = get_local_hugpy_summate_time(raw_text,4)
ocr_text = get_hugpy_summate_time(raw_text,4)
