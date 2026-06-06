from .imports import *
def analyze_page(pdf_dir,page_index):
    filtered_text = get_filtered_text(pdf_dir,'pages',zero_it(int(page_index)))
    text = truncate_to_word_limit(filtered_text, max_words=510)
    data={"text":text,
    "scope":f"page:{page_index}",
    "summary_preset":"brief",         # one page ≠ article-length
    "keyword_preset":"seo"}
    logger.info(f"analyze_page data = {data}")
    response = postRequest('https://hugpy.abstractendeavors.com/analyze/text',data=data)
    logger.info(f"response = {response}")
    return response
def analyze_full(pdf_dir):
    filtered_text = get_unfiltered_text(pdf_dir)
    text = truncate_to_word_limit(filtered_text, max_words=510)
    data={"text":text,
    "scope":f"full",
    "summary_preset":"article",         # one page ≠ article-length
    "keyword_preset":"seo"}
    return postRequest('https://hugpy.abstractendeavors.com/analyze/text',data=data)
def refine_keywords(text, preset="seo"):
    data={"text":text,"preset":preset}
    return postRequest('https://hugpy.abstractendeavors.com/keybert/refine_keywords',data=data)
def summarize(text, preset="article"):
    data={"text":text,"preset":preset}
    return postRequest('https://hugpy.abstractendeavors.com/summarizer/summarize',data=data)
