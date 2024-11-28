# Project:      Agent
# Author:       yomu
# Time:         2024/11/28
# Version:      0.1
# Description:  agent STT SenseVoice Windows client class


"""
    SenseVoice客户端的windows版本，带GUI界面
    SenseVoice服务器是linux
    
    Windows 版本：
        1. 前台运行，GUI窗口
        2. 支持音频文件推理
        3. 支持麦克风实时语音流推理
        4. 支持音频录制推理
        
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
import logging

load_dotenv()

# 初始化日志记录
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class SenseVoiceClient:
    """
        SenseVoice Windows 客户端 后端
    """
    def __init__(self):
        """初始化 SenseVoice 客户端"""
        self.api_url = os.getenv("SENTENCES_API_URL", "http://192.168.1.17:50000/predict/sentences/")
        self.stream_api_url = os.getenv("STREAM_API_URL", "http://192.168.1.17:50000/predict/stream/")
        self.audio_dir = os.getenv("AUDIO_DIR", "./audio_files")
        self.recording = None
        self.audio_data = []
        self.start_time = None
        self.recorded_filename = None
        self.real_time_running = False
        self.real_time_threads = []
        self.audio_queue = []
        self.chunk = 16000
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.real_time_button = None  # 实时录音按钮
        self.real_time_result_text = None  # 实时推理结果显示框
        self.start_record_button = None  # 开始录音按钮
        self.stop_record_button = None  # 结束录音按钮

    def send_audio_files(self, audio_files, keys, lang="auto"):
        """发送音频文件到 ASR API"""
        files = [("files", open(file, "rb")) for file in audio_files]
        try:
            form_data = {
                "keys": keys,
                "lang": lang,
            }
            response = requests.post(self.api_url, files=files, data=form_data)
            response.raise_for_status()  # 检查请求是否成功
            return response.json()
        except requests.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err}")
            return f"HTTP error occurred: {http_err}"
        except Exception as err:
            logging.error(f"An error occurred: {err}")
            return f"An error occurred: {err}"
        finally:
            for _, file in files:
                file.close()

    def process_audio_files(self, audio_files, lang="auto"):
        """处理音频文件，发送到 ASR API"""
        keys = ",".join([os.path.basename(file) for file in audio_files])
        try:
            result = self.send_audio_files(audio_files, keys, lang)
            result_text = "ASR API 的响应：\n"
            for res in result.get("result", []):
                result_text += f"音频键: {res['key']}\n"
                result_text += f"清理后的文本: {res['clean_text']}\n"
                result_text += "-\n"
            return result_text
        except requests.RequestException as e:
            return f"与服务器通信时出错: {e}"

    def start_recording(self):
        """开始录音"""
        fs = 16000
        messagebox.showinfo("录音", "开始录音，请说话...")
        try:
            self.audio_data = []
            self.recording = sd.InputStream(samplerate=fs, channels=1, dtype=np.int16, callback=self.callback)
            self.recording.start()
            self.start_time = time.time()
            # 更新按钮状态
            self.start_record_button.config(state=tk.DISABLED)
            self.stop_record_button.config(state=tk.NORMAL)
        except Exception as e:
            messagebox.showerror("录音错误", f"录音失败: {e}")

    def callback(self, indata, frames, time, status):
        """录音回调函数"""
        if status:
            print(status)
        self.audio_data.append(indata.copy())

    def stop_recording(self):
        """停止录音"""
        if self.recording is not None:
            self.recording.stop()
            self.recording.close()
            self.recording = None
            self.audio_data = np.concatenate(self.audio_data, axis=0)
            self.recorded_filename = time.strftime("%Y%m%d_%H%M%S.wav", time.localtime())
            write(self.recorded_filename, 16000, self.audio_data)
            elapsed_time = time.time() - self.start_time
            self.start_time = None
            messagebox.showinfo("录音完成", f"录音文件: {self.recorded_filename}\n录音时长: {elapsed_time:.2f} 秒")
            # 更新按钮状态
            self.start_record_button.config(state=tk.NORMAL)
            self.stop_record_button.config(state=tk.DISABLED)
            self.record_button.config(state=tk.NORMAL)  # 启用“处理录制音频”按钮
        else:
            messagebox.showwarning("警告", "未开始录音。")

    def real_time_record(self):
        """实时录音线程"""
        self.real_time_running = True
        p = pyaudio.PyAudio()
        stream = p.open(format=self.format,
                        channels=self.channels,
                        rate=self.rate,
                        input=True,
                        frames_per_buffer=self.chunk)

        while self.real_time_running:
            data = stream.read(self.chunk)
            self.audio_queue.append(data)
            time.sleep(0.1)

        stream.stop_stream()
        stream.close()
        p.terminate()

    def send_real_time_audio(self):
        """发送实时录音数据到服务器"""
        lock = threading.Lock()
        while self.real_time_running:
            if self.audio_queue:
                with lock:
                    audio_data = self.audio_queue.pop(0)
                wav_io = io.BytesIO()
                with wave.open(wav_io, 'wb') as wav_file:
                    wav_file.setnchannels(self.channels)
                    wav_file.setsampwidth(pyaudio.get_sample_size(self.format))
                    wav_file.setframerate(self.rate)
                    wav_file.writeframes(audio_data)
                wav_io.seek(0)
                try:
                    response = requests.post(self.stream_api_url, files={"file": ("audio.wav", wav_io, "audio/wav")})
                    if response.status_code == 200:
                        result = response.json()["result"]
                        if isinstance(result, list):
                            result = ' '.join([r['text'] for r in result])
                        logging.info(f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}: {result}")
                        # 在GUI中显示结果
                        self.real_time_result_text.insert(tk.END, f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}: {result}\n")
                        self.real_time_result_text.see(tk.END)
                except requests.RequestException as e:
                    logging.error(f"与服务器通信时出错: {e}")
            time.sleep(0.1)

    def toggle_real_time(self):
        """切换实时录音的状态（开始/停止）"""
        if not self.real_time_running:
            self.real_time_running = True
            self.real_time_threads = [
                threading.Thread(target=self.real_time_record),
                threading.Thread(target=self.send_real_time_audio)
            ]
            for thread in self.real_time_threads:
                thread.start()
            self.real_time_button.config(text="停止实时录音")  # 更新按钮文本
        else:
            self.real_time_running = False
            for thread in self.real_time_threads:
                thread.join()
            self.real_time_button.config(text="开始实时录音")  # 恢复按钮文本

class SenseVoiceGUI:
    """
        SenseVoice Windows 客户端 前端
    """
    def __init__(self, client: SenseVoiceClient):
        """初始化 GUI"""
        self.client = client
        self.root = tk.Tk()
        self.root.title("ASR 音频处理客户端")
        self.root.geometry("800x900")
        self.root.configure(bg="#f0f0f0")
        self.setup_gui()

    def setup_gui(self):
        """设置 GUI 元素"""
        # 设置样式
        style = ttk.Style()
        style.configure("TButton", font=("Helvetica", 12), padding=10)
        style.configure("TLabel", font=("Helvetica", 12))
        style.configure("TListbox", font=("Helvetica", 12))

        # 顶部框架，包含选择文件按钮和文件列表
        frame_top = ttk.Frame(self.root, padding="10 10 10 5")
        frame_top.pack(fill=tk.X)

        frame_middle = ttk.Frame(self.root, padding="10 10 10 5")
        frame_middle.pack(fill=tk.X)

        frame_bottom = ttk.Frame(self.root, padding="10 10 10 5")
        frame_bottom.pack(fill=tk.BOTH, expand=True)

        frame_real_time = ttk.Frame(self.root, padding="10 10 10 5")
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
            result = self.client.process_audio_files(audio_files, lang)
            result_text.delete(1.0, tk.END)
            result_text.insert(tk.END, result)

        # 处理录制的音频文件
        def record_and_process():
            if self.client.recorded_filename:
                audio_files = [self.client.recorded_filename]
                result = self.client.process_audio_files(audio_files)
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

        start_record_button = ttk.Button(frame_middle, text="开始录音", command=self.client.start_recording)
        start_record_button.pack(side=tk.LEFT, padx=5)

        stop_record_button = ttk.Button(frame_middle, text="结束录音", command=self.client.stop_recording, state=tk.DISABLED)
        stop_record_button.pack(side=tk.LEFT, padx=5)

        record_button = ttk.Button(frame_middle, text="处理录制音频", command=record_and_process, state=tk.DISABLED)
        record_button.pack(side=tk.LEFT, padx=5)

        real_time_button = ttk.Button(frame_middle, text="开始实时录音", command=self.client.toggle_real_time)
        real_time_button.pack(side=tk.LEFT, padx=5)

        process_button = ttk.Button(frame_bottom, text="处理音频文件", command=process_files)
        process_button.pack(pady=10, fill=tk.X)

        result_text = tk.Text(frame_bottom, wrap=tk.WORD, width=80, height=15, font=("Helvetica", 12))
        result_text.pack(pady=10, fill=tk.BOTH, expand=True)

        real_time_result_text = tk.Text(frame_real_time, wrap=tk.WORD, width=80, height=10, font=("Helvetica", 12))
        real_time_result_text.pack(pady=10, fill=tk.BOTH, expand=True)

        self.client.timer_label = timer_label
        self.client.start_record_button = start_record_button
        self.client.stop_record_button = stop_record_button
        self.client.record_button = record_button
        self.client.real_time_button = real_time_button
        self.client.real_time_result_text = real_time_result_text

    def run(self):
        """运行 GUI 主循环"""
        self.root.mainloop()

class SenseVoiceWindowsClient:
    """
        SenseVoice Windows 客户端 封装
    """
    def __init__(self):
        """初始化 SenseVoice 应用程序"""
        self.client = SenseVoiceClient()
        self.gui = SenseVoiceGUI(self.client)

    def run(self):
        """运行应用程序"""
        self.gui.run()


def main():
    app = SenseVoiceWindowsClient()
    app.run()
    
# 程序入口
if __name__ == "__main__":
    print("Now in Linux,please run in Windows!Do nothing")
