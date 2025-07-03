import requests
import os
from typing import List, Tuple

audio_path = "${AGENT_HOME}/Module/Chat/1_301.wav"
url = "http://127.0.0.1:20060/agent/chat/input/audio"  # 确保URL路径与服务端一致

# 以二进制方式打开音频文件
with open(audio_path, "rb") as f:
    # 使用文件名作为上传的键值对，MIME类型设为audio/wav
    files = {"file": (os.path.basename(audio_path), f, "audio/wav")}

    # 使用POST请求发送文件
    res = requests.post(url=url, files=files, timeout=300)

# 输出返回的响应信息
print(f"Status Code: {res.status_code}")
# print(f"Response: {res.json()}")


