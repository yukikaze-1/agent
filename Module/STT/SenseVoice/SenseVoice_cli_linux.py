# Project:      Agent
# Author:       yomu
# Time:         2024/11/28
# Version:      0.1
# Description:  agent STT SenseVoice Liunx client class

# TODO 待实现，思考linux版应该提供什么功能

"""
    SenseVoice的Linux client agent
    
    Linux 版本：
        1. 后台运行，无窗口
        2. 支持音频文件推理
        3. 支持麦克风实时语音流推理
        
"""

"""
import requests
import os
import tkinter as tk
from tkinter import filedialog, messagebox
import sounddevice as sd
import numpy as np
import wave
from scipy.io.wavfile import write
import time
from tkinter import ttk
import threading
import pyaudio
import io
from dotenv import load_dotenv

load_dotenv()

# ASR API 的 URL
API_URL = "http://192.168.1.17:50000/predict/sentences/"
STREAM_API_URL = "http://192.168.1.17:50000/predict/stream/"
# 存放音频文件的目录
AUDIO_DIR = "./audio_files"

# 全局变量定义
recording = None  # 录音流对象
audio_data = []  # 存储录音数据
start_time = None  # 录音开始时间
timer_label = None  # 计时器标签
start_record_button = None  # 开始录音按钮
stop_record_button = None  # 停止录音按钮
record_button = None  # 处理录制音频按钮
real_time_button = None  # 实时录音按钮
recorded_filename = None  # 录制的音频文件名
real_time_running = False  # 实时录音运行状态
real_time_threads = []  # 实时录音线程列表
audio_queue = []  # 实时音频数据队列
real_time_result_text = None  # 实时推理结果显示框

# 实时音频采集参数
CHUNK = 16000  # 帧大小 (每秒16000采样点, 1秒一帧)
FORMAT = pyaudio.paInt16  # 16位音频格式
CHANNELS = 1  # 单声道
RATE = 16000  # 采样率

# 更新计时器
def update_timer():
    if start_time is not None:
        elapsed_time = time.time() - start_time
        timer_label.config(text=f"录音时间: {elapsed_time:.2f} 秒")
        timer_label.after(100, update_timer)

# 发送音频文件到 ASR API
def send_audio_files(audio_files, keys, lang="auto"):
    files = [("files", open(file, "rb")) for file in audio_files]
    form_data = {
        "keys": keys,
        "lang": lang,
    }
    response = requests.post(API_URL, files=files, data=form_data)
    return response.json()

# 处理音频文件，发送到 ASR API
def process_audio_files(audio_files, lang="auto"):
    keys = ",".join([os.path.basename(file) for file in audio_files])
    try:
        result = send_audio_files(audio_files, keys, lang)
        result_text = "ASR API 的响应：\n"
        for res in result.get("result", []):
            result_text += f"音频键: {res['key']}\n"
            result_text += f"清理后的文本: {res['clean_text']}\n"
            result_text += "-\n"
        return result_text
    except requests.RequestException as e:
        return f"与服务器通信时出错: {e}"

# 开始录音
def start_recording():
    global recording, audio_data, start_time
    fs = 16000
    messagebox.showinfo("录音", "开始录音，请说话...")
    try:
        audio_data = []
        recording = sd.InputStream(samplerate=fs, channels=1, dtype=np.int16, callback=callback)
        recording.start()
        record_button.config(state=tk.DISABLED)
        start_record_button.config(state=tk.DISABLED)
        stop_record_button.config(state=tk.NORMAL)
        start_time = time.time()
        update_timer()
    except Exception as e:
        messagebox.showerror("录音错误", f"录音失败: {e}")

# 录音回调函数
def callback(indata, frames, time, status):
    global audio_data
    if status:
        print(status)
    audio_data.append(indata.copy())

# 停止录音
def stop_recording():
    global recording, audio_data, start_time, recorded_filename
    if recording is not None:
        recording.stop()
        recording.close()
        recording = None
        audio_data = np.concatenate(audio_data, axis=0)
        recorded_filename = time.strftime("%Y%m%d_%H%M%S.wav", time.localtime())
        write(recorded_filename, 16000, audio_data)
        elapsed_time = time.time() - start_time
        start_time = None
        timer_label.config(text="录音时间: 0.00 秒")
        messagebox.showinfo("录音完成", f"录音文件: {recorded_filename}\n录音时长: {elapsed_time:.2f} 秒")
        start_record_button.config(state=tk.NORMAL)
        stop_record_button.config(state=tk.DISABLED)
        record_button.config(state=tk.NORMAL)
    else:
        messagebox.showwarning("警告", "未开始录音。")

# 实时录音线程
def real_time_record():
    global real_time_running, audio_queue
    real_time_running = True
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)

    while real_time_running:
        data = stream.read(CHUNK)
        audio_queue.append(data)
        time.sleep(0.1)

    stream.stop_stream()
    stream.close()
    p.terminate()

# 发送实时录音数据到服务器
def send_real_time_audio():
    global real_time_running, audio_queue, real_time_result_text
    while real_time_running:
        if audio_queue:
            audio_data = audio_queue.pop(0)
            wav_io = io.BytesIO()
            with wave.open(wav_io, 'wb') as wav_file:
                wav_file.setnchannels(CHANNELS)
                wav_file.setsampwidth(pyaudio.get_sample_size(FORMAT))
                wav_file.setframerate(RATE)
                wav_file.writeframes(audio_data)
            wav_io.seek(0)
            try:
                response = requests.post(STREAM_API_URL, files={"file": ("audio.wav", wav_io, "audio/wav")})
                if response.status_code == 200:
                    result = response.json()["result"]
                    if isinstance(result, list):
                        result = ' '.join([r['text'] for r in result])
                    print(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()), result)
                    real_time_result_text.insert(tk.END, f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}: {result}\n")
                    real_time_result_text.see(tk.END)
            except requests.RequestException as e:
                print(f"与服务器通信时出错: {e}")
        time.sleep(0.1)

# 切换实时录音的状态（开始/停止）
def toggle_real_time():
    global real_time_running, real_time_threads
    if not real_time_running:
        real_time_running = True
        real_time_threads = [
            threading.Thread(target=real_time_record),
            threading.Thread(target=send_real_time_audio)
        ]
        for thread in real_time_threads:
            thread.start()
        real_time_button.config(text="停止实时录音")
    else:
        real_time_running = False
        for thread in real_time_threads:
            thread.join()
        real_time_button.config(text="开始实时录音")

# 主函数，创建 GUI
def main():
    global timer_label, start_record_button, stop_record_button, record_button, real_time_button, recorded_filename, real_time_result_text
    root = tk.Tk()
    root.title("ASR 音频处理客户端")
    root.geometry("800x900")
    root.configure(bg="#f0f0f0")

    # 设置样式
    style = ttk.Style()
    style.configure("TButton", font=("Helvetica", 12), padding=10)
    style.configure("TLabel", font=("Helvetica", 12))
    style.configure("TListbox", font=("Helvetica", 12))

    # 顶部框架，包含选择文件按钮和文件列表
    frame_top = ttk.Frame(root, padding="10 10 10 5")
    frame_top.pack(fill=tk.X)

    frame_middle = ttk.Frame(root, padding="10 10 10 5")
    frame_middle.pack(fill=tk.X)

    frame_bottom = ttk.Frame(root, padding="10 10 10 5")
    frame_bottom.pack(fill=tk.BOTH, expand=True)

    frame_real_time = ttk.Frame(root, padding="10 10 10 5")
    frame_real_time.pack(fill=tk.BOTH, expand=True)

    # 选择音频文件
    def select_files():
        files = filedialog.askopenfilenames(filetypes=[("音频文件", "*.wav *.mp3")])
        if files:
            file_list.delete(0, tk.END)
            for file in files:
                file_list.insert(tk.END, file)

    # 处理选中的音频文件
    def process_files():
        audio_files = list(file_list.get(0, tk.END))
        if not audio_files:
            messagebox.showwarning("警告", "请选择音频文件。")
            return
        lang = lang_var.get()
        result = process_audio_files(audio_files, lang)
        result_text.delete(1.0, tk.END)
        result_text.insert(tk.END, result)

    # 处理录制的音频文件
    def record_and_process():
        global recorded_filename
        if recorded_filename:
            audio_files = [recorded_filename]
            result = process_audio_files(audio_files)
            result_text.delete(1.0, tk.END)
            result_text.insert(tk.END, result)

    # 创建 GUI 元素
    select_button = ttk.Button(frame_top, text="选择音频文件", command=select_files)
    select_button.pack(pady=5, side=tk.LEFT)

    file_list = tk.Listbox(frame_top, selectmode=tk.MULTIPLE, width=50, height=5, font=("Helvetica", 12))
    file_list.pack(pady=5, side=tk.LEFT, fill=tk.X, expand=True)

    lang_var = tk.StringVar(value="auto")
    lang_label = ttk.Label(frame_middle, text="选择语言：")
    lang_label.pack(side=tk.LEFT, padx=(0, 5))
    lang_options = ["auto", "zh", "en", "yue", "ja", "ko", "nospeech"]
    lang_menu = ttk.OptionMenu(frame_middle, lang_var, *lang_options)
    lang_menu.pack(side=tk.LEFT, fill=tk.X, expand=True)

    timer_label = ttk.Label(frame_middle, text="录音时间: 0.00 秒")
    timer_label.pack(side=tk.RIGHT)

    start_record_button = ttk.Button(frame_middle, text="开始录音", command=start_recording)
    start_record_button.pack(side=tk.LEFT, padx=5)

    stop_record_button = ttk.Button(frame_middle, text="结束录音", command=stop_recording, state=tk.DISABLED)
    stop_record_button.pack(side=tk.LEFT, padx=5)

    record_button = ttk.Button(frame_middle, text="处理录制音频", command=record_and_process, state=tk.DISABLED)
    record_button.pack(side=tk.LEFT, padx=5)

    real_time_button = ttk.Button(frame_middle, text="开始实时录音", command=toggle_real_time)
    real_time_button.pack(side=tk.LEFT, padx=5)

    process_button = ttk.Button(frame_bottom, text="处理音频文件", command=process_files)
    process_button.pack(pady=10, fill=tk.X)

    result_text = tk.Text(frame_bottom, wrap=tk.WORD, width=80, height=15, font=("Helvetica", 12))
    result_text.pack(pady=10, fill=tk.BOTH, expand=True)

    real_time_result_text = tk.Text(frame_real_time, wrap=tk.WORD, width=80, height=10, font=("Helvetica", 12))
    real_time_result_text.pack(pady=10, fill=tk.BOTH, expand=True)

    root.mainloop()

# 程序入口
if __name__ == "__main__":
    main()
"""