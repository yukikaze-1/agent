import requests
import os
from typing import List, Tuple

audio_path = "${AGENT_HOME}/Module/Chat/1_301.wav"
url = "http://127.0.0.1:20041/audio/recognize"  # 确保URL路径与服务端一致

# 以二进制方式打开音频文件
with open(audio_path, "rb") as f:
    # 使用文件名作为上传的键值对，MIME类型设为audio/wav
    files = {"file": (os.path.basename(audio_path), f, "audio/wav")}
    data = {
        "audio_path": audio_path
    }
    # 使用POST请求发送文件
    res:List[Tuple[str,str]] = requests.post(url=url, json=data, timeout=30)

# 输出返回的响应信息
print(f"Status Code: {res.status_code}")
print(f"Response: {res.json()}")
for _,ret in res.json():
    print(ret)
