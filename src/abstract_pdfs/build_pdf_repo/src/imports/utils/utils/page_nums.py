def get_page_num(num):
    num = str(num)
    return '000'[:-len(num)]+num
def get_page_num_str(num):
    page_num = get_page_num(num)
    return f"page_{page_num}"
def zero_it(i):
    i_str = str(i)
    i_len = len(i_str)
    return '000'[:-i_len]+i_str
def elim_zeros(num):
    return eatInner(num,['0'])
