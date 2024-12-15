# Project:      Agent
# Author:       yomu
# Time:         2024/12/12
# Version:      0.1
# Description:  agent Windows client

"""
    agent的windows客户端
    # TODO 还未完全实现，等写完了再上传
    在外面修改，此处仅做保存
"""

import os
import json
import requests
import logging
import tkinter as tk
from tkinter.ttk import Combobox
from tkinter import messagebox
from tkinter import Listbox
from tkinter import scrolledtext
from typing import Tuple, Optional, Literal
from functools import partial
from dotenv import dotenv_values

'''记得.env文件里的相关内容'''

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class ClientWindow():
    
    def __init__(self):
        self.env_vars = dotenv_values('./.env')
        self.agent_server_url = self.env_vars.get("APP_SERVER_URL", "")
        if self.agent_server_url == "":
            raise ValueError(f"Agent server url is not set.Please set it in Init/config.yml")
        self.current_usr_info = ()
        
        self.login_window: tk.Tk = None
        self.signup_window: tk.Toplevel = None
        self.usr_main_window: tk.Toplevel = None
        
    def run(self):
        """入口函数"""
        self.init_window()
            
    def init_window(self):
        """初始化登陆窗口"""
        self.login_window = self.init_login_window()
        self.login_window.mainloop()

    def init_login_window(self)->tk.Tk:
        """初始化登陆界面, 返回一个主窗口对象"""
        login_window = tk.Tk()
        login_window.title(self.env_vars.get("APP_NAME"))
        login_window.iconbitmap(self.env_vars.get("APP_ICON_PATH"))
        login_window.geometry(self.env_vars.get("APP_LOGIN_WINDOW_SIZE"))
        login_window.resizable(width=False, height=False)
        
        def login_exit():
            if messagebox.askokcancel(title="退出程序", message="确认退出？"):
                login_window.destroy()
        
        login_window.protocol('WM_DELETE_WINDOW', func=login_exit)
        
        # 登录界面背景图
        # background_login_image = tk.PhotoImage(file=env_vars.get("APP_LOGIN_BACKGROUND_IMAGE_PATH"))
        # background_login_label = tk.Label(login_window, image=background_login_image)
        # background_login_label.pack(side='top')
        
        """登陆相关"""
        login_username_label = tk.Label(login_window, text="账号:")
        login_username_label.place(x=560, y=420, width=30)
        login_password_label = tk.Label(login_window, text="密码:")
        login_password_label.place(x=560, y=460, width=30)
        
        # 登陆输入框
        login_username = tk.StringVar(value="yomu")
        login_password = tk.StringVar(value="123456")
        
        login_username_entry = tk.Entry(login_window, textvariable=login_username, width=30)
        login_username_entry.place(x=560+30+20, y=420)
        login_password_entry = tk.Entry(login_window, textvariable=login_password, width=30,show="*")
        login_password_entry.place(x=560+30+20, y=460)
        
        def login_window_login():
            """登陆界面的登陆按钮触发函数，如果登录成功，会进入用户主界面并隐藏登录界面"""
            username = login_username.get()
            password = login_password.get()
            succeed, message = self.usr_login(username, password)
            
            if succeed:
                messagebox.showinfo(title="Login", message="登录成功")
                self.current_usr_info = (username, password)
                # 隐藏登录窗口
                self.login_window.withdraw()
                # 
                self.usr_main_window = self.init_usr_main_window()
            else:
                messagebox.showinfo(message="账号或密码错误! " + message)
    
        def login_window_signup():
            """登录界面的注册按钮触发函数，会进入一个新的注册界面"""
            # 初始化注册界面
            self.signup_window =  self.init_signup_window()   
        
        def test_server():
            """登陆界面的测试按钮触发函数"""
            pass
        
        def clear_login_window_info_box():
            """登陆界面的更新按钮触发函数"""
            pass
        
        # 登陆与注册按钮
        login_login_button = tk.Button(login_window, text="登录", command=login_window_login, width=8)
        login_login_button.place(x=560+30+20+220, y=420)
        login_signup_button = tk.Button(login_window, text="注册", command=login_window_signup, width=8)
        login_signup_button.place(x=560+30+20+220, y=460)
        
        """服务器信息相关"""
        # 信息框
        login_info_box = tk.Listbox(login_window, width=70, height=10)
        login_info_box.place(x=20, y=300)
        
        # 信息框按钮
        login_info_test_button = tk.Button(login_window, text="测试", command=test_server, width=8)
        login_info_test_button.place(x=40, y=500)
        login_info_update_button = tk.Button(login_window, text="清空", command=clear_login_window_info_box, width=8)
        login_info_update_button.place(x=140, y=500)
        
        return login_window    
    
        
    def init_usr_main_window(self)->tk.Toplevel:
        """初始化用户主界面, 返回一个tk.Toplevel对象"""
        usr_main_window = tk.Toplevel()
        usr_main_window.title(self.env_vars.get("APP_NAME"))
        usr_main_window.iconbitmap(self.env_vars.get("APP_ICON_PATH"))
        usr_main_window.geometry(self.env_vars.get("APP_USR_MAIN_WINDOW_SIZE"))
        usr_main_window.resizable(width=False, height=False)
        
        def usr_main_window_exit():
            if messagebox.askokcancel(title="退出程序", message="确认退出？"):
                self.usr_main_window.destroy()
                self.usr_main_window = None
                self.login_window.deiconify()
        
        usr_main_window.protocol('WM_DELETE_WINDOW', func=usr_main_window_exit)
        
        # 窗口背景
        # background_usr_main_window_image = tk.PhotoImage(file=self.env_vars.get("APP_USR_MAIN_WINDOW_IMAGE_PATH"))
        # background_label = tk.Label(usr_main_window, image=background_usr_main_window_image)
        # background_label.pack(side='top')
                    
        """菜单栏"""  
        # 顶层菜单栏
        usr_main_menu = tk.Menu(usr_main_window)
        
        def app_exit():
            self.usr_main_window.destroy()
            self.usr_main_window = None
            self.login_window.deiconify() 
            
        ## 开始菜单
        usr_start_menu = tk.Menu(usr_main_menu, tearoff=0)
        usr_start_menu.add_command(label="退出", command=app_exit)
        
        usr_main_menu.add_cascade(label="开始", menu=usr_start_menu)
        
        ## 账户菜单
        usr_account_menu = tk.Menu(usr_main_menu, tearoff=0)
        
        def account_change_password():
            self.signup_window = self.init_change_pwd_window()

        
        #### 添加下拉菜单内的按钮
        usr_account_menu.add_command(label="切换账号",command=self.account_logout)
        usr_account_menu.add_command(label="注销",command=self.account_logout)
        usr_account_menu.add_command(label="修改密码",command=account_change_password)
        
        #### 将下拉菜单绑定到主菜单
        usr_main_menu.add_cascade(label="账户", menu=usr_account_menu)
        
        ## 设置菜单
        usr_setting_menu = tk.Menu(usr_start_menu, tearoff=0)
        
        def setting_test():
            messagebox.showinfo(message="setting")
        
        def open_setting_menu():
            self.init_setting_menu()
            
        usr_setting_menu.add_command(label="测试", command=setting_test)
        usr_setting_menu.add_command(label="更多设置", command=open_setting_menu)
        
        usr_main_menu.add_cascade(label="设置", menu=usr_setting_menu)
        
        # 将主菜单绑定到主界面上
        usr_main_window.config(menu=usr_main_menu)
        
        """选项子界面"""
        
        options = tk.Label(usr_main_window, text="选项")
        options.place(x=0, y=0)
        
        # 大模型类型选项(本地还是云端)
        llm_model_type_select = tk.StringVar()
        llm_model_type_candidate = ["Local", "Cloud"]
        llm_model_type_combobox = Combobox(usr_main_window, textvariable=llm_model_type_select, values=llm_model_type_candidate, state="readonly", width=10)
        llm_model_type_combobox.current(newindex=0)
        llm_model_type_combobox.place(x=50,y=0)
        
        # 大模型选项
        llm_model_label =tk.Label(usr_main_window, text="LLM模型")
        llm_model_label.place(x=150, y=0)
        llm_model_select = tk.StringVar(value="llama 3.2")
        llm_model_candidate = ['llama 3.2', 'qwen2.5']
        llm_model_select_combobox = Combobox(usr_main_window, textvariable=llm_model_select, values=llm_model_candidate, state='readonly', width=20)
        llm_model_select_combobox.current(newindex=0)
        llm_model_select_combobox.place(x=210,y=0)
        
        # 语音合成选项TTS
        tts_model_label =tk.Label(usr_main_window, text="语音合成模型", width=13)
        tts_model_label.place(x=375,y=0)
        tts_model_select = tk.StringVar()
        tts_model_candidate = ['GPTSoVits','CosyVoice']
        tts_model_select_combobox = Combobox(usr_main_window, textvariable=tts_model_select, values=tts_model_candidate, state='readonly', width=15)
        tts_model_select_combobox.current(newindex=0)
        tts_model_select_combobox.place(x=470,y=0)
        
        # 语音识别选项STT
        stt_model_label = tk.Label(usr_main_window, text="语音识别模型", width=13)
        stt_model_label.place(x=600,y=0)
        stt_model_select = tk.StringVar()
        stt_model_candidate = ['SenseVoice','Whisper']
        stt_model_select_combobox = Combobox(usr_main_window, textvariable=stt_model_select, values=stt_model_candidate, state='readonly', width=15)
        stt_model_select_combobox.current(newindex=0)
        stt_model_select_combobox.place(x=700,y=0)
        
        
        """聊天界面"""
        
        # 聊天窗口
        chat_message_display = scrolledtext.ScrolledText(usr_main_window, wrap=tk.WORD, state='disabled')
        chat_message_display.place(x=200,y=100)
        
        # 聊天输入框
        chat_message_input_box = tk.Frame(usr_main_window)
        chat_message_input_box.place(x=200,y=450)
        
        chat_message_input_box = tk.Text(chat_message_input_box,height=6)
        chat_message_input_box.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        default_chat_message=f""

        # 聊天发送按钮
        chat_message_submit_button = tk.Button(usr_main_window, text="发送", command=self.chat_message_submit, width=8, height=3)
        chat_message_submit_button.place(x=780,y=450)
        
        """左侧功能栏"""
        function_box = tk.Listbox(usr_main_window, width=25, height=17)
        function_box.place(x=10, y=100)
        
        
        """虚拟人物展示界面"""
        # 待实现
        character_show = ""
        
        """agent信息展示界面"""
        agent_info_box = tk.Listbox(usr_main_window, width=25, height=4)
        agent_info_box.place(x=10,y=450)
        
        return usr_main_window

    
    def init_signup_window(self)->tk.Toplevel:
        """初始化注册界面,返回一个tk.Toplevel对象"""
        signup_window = tk.Toplevel()
        signup_window.title(self.env_vars.get("APP_NAME") + "Sign Up")
        signup_window.iconbitmap(self.env_vars.get("APP_ICON_PATH"))
        signup_window.geometry(self.env_vars.get("APP_SIGN_UP_WINDOW_SIZE"))
        signup_window.resizable(width=False, height=False)
        signup_window.focus_set()
        
        # 账号密码输入标签
        signup_username_label = tk.Label(signup_window, text="账号: ", width=10)
        signup_username_label.place(x=100,y=25)
        signup_password_label = tk.Label(signup_window, text="密码: ", width=10)
        signup_password_label.place(x=100,y=65)
        signup_password_confirm_label = tk.Label(signup_window, text="确认密码: ",width=10)
        signup_password_confirm_label.place(x=90,y=105)
        
        # 账号密码
        signup_username = tk.StringVar(value="yomu")
        signup_password = tk.StringVar(value="123456")
        signup_password_confirm = tk.StringVar(value="123456")
        
        def default_username_cmd():
            """默认用户账号逻辑"""
            pass
        
        def default_password_cmd():
            """默认用户密码逻辑"""
            pass
        
        def signup_password_confirm_validate():
            """再次确认密码逻辑"""
            pass
        
        # 账号密码输入框
        signup_account_entry = tk.Entry(signup_window, width=25, textvariable=signup_username, state='normal' , validate='key', validatecommand=default_username_cmd)
        signup_account_entry.place(x=165,y=25)
        signup_password_entry = tk.Entry(signup_window, width=25, textvariable=signup_password, show="*", validate='key', validatecommand=default_password_cmd)
        signup_password_entry.place(x=165,y=65)
        signup_password_confirm_entry = tk.Entry(signup_window, width=25, textvariable=signup_password_confirm, show="*", validate='key', validatecommand=signup_password_confirm_validate)
        signup_password_confirm_entry.place(x=165,y=105)
        
        def signup_window_exit():
            signup_window.destroy()
            
        def signup_window_signup():
            """注册界面的注册按钮触发函数，会检测账号密码是否符合规定，并向服务器发送注册请求"""
            username = signup_username.get()
            password = signup_password.get()
            confirm_pwd = signup_password_confirm.get()
            # 账号密码初步校验
            if not username:
                messagebox.showinfo(message="请输入账号")
            elif not password or not confirm_pwd:
                messagebox.showinfo(message="请输入密码")
            elif len(password) < 6:
                messagebox.showinfo(message="密码至少6位")
            elif password != confirm_pwd:
                messagebox.showinfo(message="两次密码不一致！")  
            else:    
                # 向服务器注册
                success, message = self.usr_signup(username, password)
                if success:
                    messagebox.showinfo(message="注册成功")    
                    self.signup_window.destroy()
                    self.signup_window = None
                else:
                    messagebox.showerror(title="Error", message=message)
        
        # 功能按钮    
        signup_signup_button = tk.Button(signup_window, text="注册" , width=15, command=signup_window_signup)
        signup_signup_button.place(x=125,y=200)
        signup_cancel_button = tk.Button(signup_window, text="取消", width=15, command=signup_window_exit)
        signup_cancel_button.place(x=255,y=200)
        
        return signup_window
        
        
    def init_change_pwd_window(self)->tk.Toplevel:
        """初始化修改密码界面,返回一个tk.Toplevel对象"""
        # self.change_pwd_window_submit
        change_pwd_window = tk.Toplevel()
        change_pwd_window.title(self.env_vars.get("APP_NAME") + "Sign Up")
        change_pwd_window.iconbitmap(self.env_vars.get("APP_ICON_PATH"))
        change_pwd_window.geometry(self.env_vars.get("APP_SIGN_UP_WINDOW_SIZE"))
        change_pwd_window.resizable(width=False, height=False)
        change_pwd_window.focus_set()
        
        # 账号密码输入标签
        change_pwd_username_label = tk.Label(change_pwd_window, text="账号: ", width=10)
        change_pwd_username_label.place(x=100,y=25)
        change_pwd_password_label = tk.Label(change_pwd_window, text="新密码: ", width=10)
        change_pwd_password_label.place(x=100,y=65)
        change_pwd_password_confirm_label = tk.Label(change_pwd_window, text="确认密码: ",width=10)
        change_pwd_password_confirm_label.place(x=90,y=105)
        
        # 密码
        print(f"current usr:{self.current_usr_info}")
        change_pwd_username = tk.StringVar(value=self.current_usr_info[0])
        change_pwd_password = tk.StringVar()
        change_pwd_password_confirm = tk.StringVar()
        
        def default_password_cmd():
            """默认用户密码逻辑"""
            pass
        
        def change_pwd_password_confirm_validate():
            """再次确认密码逻辑"""
            pass
        
        # 账号密码输入框
        change_pwd_account_entry = tk.Entry(change_pwd_window, width=25, textvariable=change_pwd_username,  state='readonly')
        change_pwd_account_entry.place(x=165,y=25)
        change_pwd_password_entry = tk.Entry(change_pwd_window, width=25, textvariable=change_pwd_password, show="*", validate='key', validatecommand=default_password_cmd)
        change_pwd_password_entry.place(x=165,y=65)
        change_pwd_password_confirm_entry = tk.Entry(change_pwd_window, width=25, textvariable=change_pwd_password_confirm, show="*", validate='key', validatecommand=change_pwd_password_confirm_validate)
        change_pwd_password_confirm_entry.place(x=165,y=105)
        
        def change_pwd_window_exit():
            change_pwd_window.destroy()
            
        def change_pwd_window_submit():
            """修改密码界面的修改密码按钮触发函数"""
            # 获取用户输入
            username, old_pwd =self.current_usr_info
            new_pwd = change_pwd_password.get()
            confirm_pwd = change_pwd_password_confirm.get()
            
            if not new_pwd or not confirm_pwd:
                messagebox.showinfo(message="请输入新密码！")
            elif len(new_pwd) < 6:
                messagebox.showinfo(message="新密码至少6位！")
            elif new_pwd == old_pwd:
                messagebox.showinfo(message="不能与旧密码相同！")
            else:
                # 修改密码逻辑
                success, message = self.usr_pwd_change(username, new_pwd)
                if success:
                    messagebox.showinfo(message="修改密码成功,请重新登录！")    
                    self.signup_window.destroy()
                    self.signup_window = None
                    self.account_logout()
                else:
                    messagebox.showerror(title="Error", message=message)
        
        # 功能按钮    
        change_pwd_change_pwd_button = tk.Button(change_pwd_window, text="修改密码" , width=15, command=change_pwd_window_submit)
        change_pwd_change_pwd_button.place(x=123,y=200)
        change_pwd_cancel_button = tk.Button(change_pwd_window, text="取消", width=15, command=change_pwd_window_exit)
        change_pwd_cancel_button.place(x=255,y=200)
        
        return change_pwd_window
        
   
    def init_setting_menu(self):
        """用户界面的设置选项中打开的菜单窗口"""
        self.usr_setting_window = tk.Toplevel()
        self.usr_setting_window.title("设置")
        self.usr_setting_window.iconbitmap(self.env_vars.get("APP_ICON_PATH"))
        self.usr_setting_window.geometry(self.env_vars.get("APP_USR_SETTING_WINDOW_SIZE"))
        self.usr_setting_window.resizable(width=False, height=False)
        
        self.usr_setting_label = tk.Label(self.usr_setting_window, text="Setting").pack()
        # 各种设置选项
        
        self.usr_setting_window.focus_set()
    
    
    """按钮相关触发函数"""
    
    def account_logout(self):
            # 退出当前用户主界面
            self.usr_main_window.destroy()
            self.usr_main_window = None
            # 恢复登录窗口
            self.login_window.deiconify() 
    
    def chat_message_submit(self):
        """用户界面的聊天框发送按钮触发函数"""
        pass
    
    def agent_info_update(self):
        """用户界面的agent信息更新按钮触发函数"""
        pass
    
    """内部使用函数"""
    
    def usr_login(self, username: str, password: str)->Tuple[bool, str]:
        """验证账户密码的逻辑"""
        response = self._send_usr_account_info(username, password, op='login')
        logging.info(f"User login: {response}")
        return response['result'], response['message']

    def usr_signup(self, username: str, password: str)->Tuple[bool, str]:
        """用户注册函数"""
        response = self._send_usr_account_info(username, password, op='signup')
        logging.info(f"User sign up: {response}")
        return response['result'], response['message']
    
    def usr_pwd_change(self, username: str, new_password: str)->Tuple[bool, str]:
        """用户修改密码函数"""
        response = self._send_usr_account_info(username, new_password, op='change_pwd')
        logging.info(f"User change pwd: {response}")
        return response['result'], response['message']
    
    
    def _send_usr_account_info(self, username: str, password: str, op: Literal['login', 'signup', 'change_pwd']):
        """负责根据操作类型发送用户账号和密码给服务端"""
        if op == 'login':
            api_url = self.agent_server_url + '/usr/login/'
        elif op == 'signup':
            api_url = self.agent_server_url + '/usr/signup/'
        elif op == 'change_pwd':
            api_url = self.agent_server_url + '/usr/change_pwd/'
        else:
            raise ValueError(f"Unsupported operation: {op}")
        
        # 检查 URL 是否安全
        # if not api_url.startswith("https://"):
        #     logging.warning("The API URL is not secure (HTTPS is recommended).")
        
        try:
            form_data = {
                "username": username,
                "password": password
            }
            response = requests.post(url=api_url, data=form_data, timeout=10)
            response.raise_for_status()  # 检查请求是否成功
            return response.json()
        except requests.HTTPError as http_err:
            logging.error(f"HTTP error occurred: {http_err} (Status Code: {response.status_code})")
            return {
                "error": "HTTPError",
                "details": str(http_err),
                "status_code": response.status_code
            }
        except requests.RequestException as req_err:
            logging.error(f"Request error occurred: {req_err}")
            return {"error": "RequestException", "details": str(req_err)}
        except Exception as err:
            logging.error(f"An error occurred: {err}")
            return f"An error occurred: {err}"
        
        
    def _send_chat_message(self, ):
        """"""
    
    def _send_option_message(self):
        pass
    
    def _get_server_info(self):
        pass
    
    def _get_agent_info(self):
        pass
    
    def __del__(self):
        pass

if __name__ == '__main__':
    window = ClientWindow()
    window.run()

