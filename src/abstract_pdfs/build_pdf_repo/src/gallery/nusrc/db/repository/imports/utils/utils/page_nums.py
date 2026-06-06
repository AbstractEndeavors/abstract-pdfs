def get_page_num(num):
    num = str(num)
    return '000'[:-len(num)]+num
def get_page_num_str(num):
    page_num = get_page_num(num)
    return f"page_{page_num}"
