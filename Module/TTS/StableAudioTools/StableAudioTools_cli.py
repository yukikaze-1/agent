# Project:      Agent
# Author:       yomu
# Time:         2024/11/09
# Version:      0.1
# Description:  agent TTS StableAudioTools client

# TODO 抽离环境变量，配环境，优化代码

from gradio_client import Client, handle_file

client = Client("http://192.168.1.17:7860/")

class test():
    def __init__(self):
        pass


result = client.predict(
		prompt="cat",
		negative_prompt=None,
		seconds_start=0,
		seconds_total=10,
		cfg_scale=7,
		steps=100,
		preview_every=0,
		seed="-1",
		sampler_type="dpmpp-3m-sde",
		sigma_min=0.03,
		sigma_max=500,
		cfg_rescale=0,
		use_init=False,
		init_audio=None,
		init_noise_level=0.1,
		api_name="/generate"
)
print(result)