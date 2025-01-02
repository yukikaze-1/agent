"""
    工具函数
"""
from starlette.datastructures import Headers

def filter_headers(headers: Headers):
        """过滤请求头，移除不必要的头"""
        excluded_headers = {"host", "content-length", "transfer-encoding", "connection"}
        return {k: v for k, v in headers.items() if k.lower() not in excluded_headers}
    
    
def filter_response_headers(headers: Headers):
    """过滤响应头，移除不必要的头"""
    excluded_response_headers = {"content-encoding", "transfer-encoding", "connection"}
    return {k: v for k, v in headers.items() if k.lower() not in excluded_response_headers}