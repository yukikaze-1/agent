# Project:      Agent
# Author:       yomu
# Time:         2024/10/24
# Version:      0.1
# Description:  agent STT SenseVoice server

import os
import os.path
import time
import datetime

from gradio_client import Client, handle_file
from dotenv import load_dotenv

load_dotenv("./.env")

# TODO SenseVoice部署在本地，采用C/S方式