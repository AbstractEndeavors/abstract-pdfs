from .imports import *
def get_meta_info(info):
    data={"info":info}
    return postRequest('https://clownworld.biz/metadata/get/info',data=data)
def generate_meta_tags(meta,base_url='https://thedailydialectics.com',json_path=None):
    data={"meta":meta,"base_url":base_url,"json_path":json_path}
    return postRequest('https://clownworld.biz/metadata/get/meta_tags',data=data)
