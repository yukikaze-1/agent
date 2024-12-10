# Project:      Agent
# Author:       yomu
# Time:         2024/12/10
# Version:      0.1
# Description:  agent client window

"""
    用户端操作的对话界面等等
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel, QPushButton, QLineEdit
from PyQt6.QtCore import Qt
import socket

# TODO 只是按照gpt给的框架，还没修改
class AgentClientWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # 设置主窗口属性
        self.setWindowTitle("客户端界面")
        self.setGeometry(100, 100, 400, 300)

        # 设置中心窗口
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建垂直布局
        layout = QVBoxLayout()

        # 添加标签
        self.label = QLabel("输入服务器地址：")
        self.label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.label)

        # 添加文本输入框
        self.server_input = QLineEdit(self)
        layout.addWidget(self.server_input)

        # 添加连接按钮
        self.connect_button = QPushButton("连接")
        self.connect_button.clicked.connect(self.connect_to_server)
        layout.addWidget(self.connect_button)

        # 添加状态标签
        self.status_label = QLabel("状态：未连接")
        layout.addWidget(self.status_label)

        # 设置布局
        central_widget.setLayout(layout)

    def connect_to_server(self):
        server_address = self.server_input.text().strip()
        if server_address:
            try:
                # 使用 socket 尝试连接服务器
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                client_socket.connect((server_address, 9880))  # 假设端口号是 9880
                self.status_label.setText(f"状态：已连接到 {server_address}")
                client_socket.close()
            except Exception as e:
                self.status_label.setText(f"状态：连接失败 - {str(e)}")
        else:
            self.status_label.setText("状态：请输入有效的服务器地址")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AgentClientWindow()
    window.show()
    sys.exit(app.exec())
