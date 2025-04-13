import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QTextEdit, QSystemTrayIcon, QMenu, QDialog, 
                           QLabel, QLineEdit, QPushButton, QGridLayout, QMessageBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QFont, QAction, QActionGroup
import requests
import random
from hashlib import md5
import keyboard
import time
import pyperclip as cb
import os
import pygame
import json
import youdao

# 添加资源路径处理
def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 创建临时文件夹，将路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, "resources", relative_path)

class TranslateThread(QThread):
    # 定义信号
    translation_done = pyqtSignal(str, str)
    api_config_required = pyqtSignal(str)  # 发送需要配置的API类型
    
    def __init__(self):
        super().__init__()
        self.current_api = "BaiduAPI"  # 默认使用百度API
        
        self.load_api_config()  # 加载API配置
        
    def load_api_config(self):
        """加载API配置"""
        config_path = os.path.join(os.environ.get('PROGRAMDATA', 'C:\\ProgramData'), 'FloatTrans', 'config.json')
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                self.current_api = config["src"]
                self.baidu_config = config["BaiduAPI"]
                self.youdao_config = config["YoudaoAPI"]
                
                # 检查当前API的配置是否为空
                if self.current_api == "BaiduAPI" and (not self.baidu_config["apppid"] or not self.baidu_config["apikey"]):
                    self.api_config_required.emit("BaiduAPI")
                elif self.current_api == "YoudaoAPI" and (not self.youdao_config["apppid"] or not self.youdao_config["apikey"]):
                    self.api_config_required.emit("YoudaoAPI")
                    
        except Exception as e:
            print(f"加载配置文件失败: {e}")

    def run(self):
        while True:
            # 获取原始文本并处理换行
            query = self.keywatch_loop().replace('\r\n', ' ')
            
            # 根据当前API选择调用对应的翻译方法
            if self.current_api == "BaiduAPI":
                result = self.trans_(query, 'en', 'zh')
            else:  # YoudaoAPI
                result = youdao.createRequest(query, 'en', 'zh')
                
            if result:
                self.translation_done.emit(result, query)

    def keywatch_loop(self):
        press_count = 0
        last_press_time = 0

        while True:
            keyboard.wait('ctrl+c')
            current_time = time.time()
            
            if current_time - last_press_time > 1:
                press_count = 1
            else:
                press_count += 1
            
            last_press_time = current_time
            
            if press_count >= 3:
                break
        return cb.paste()

    def trans_(self, query, from_lang, to_lang):
        # 使用配置文件中的百度API认证信息
        appid = self.baidu_config["apppid"]
        appkey = self.baidu_config["apikey"]
        
        if not appid or not appkey:
            print("百度API认证信息未配置")
            return None
            
        endpoint = 'http://api.fanyi.baidu.com'
        path = '/api/trans/vip/translate'
        url = endpoint + path

        salt = random.randint(32768, 65536)
        sign = md5((appid + query + str(salt) + appkey).encode('utf-8')).hexdigest()

        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        payload = {'appid': appid, 'q': query, 'from': from_lang, 
                  'to': to_lang, 'salt': salt, 'sign': sign}

        try:
            r = requests.post(url, params=payload, headers=headers)
            result = r.json()['trans_result'][0]['dst']
            return result
        except Exception as e:
            print(f"翻译错误: {e}")
            return None
        


class TranslatorWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.existFile()
        self.initUI()
        self.initTray()  # 添加托盘初始化
        self.initThread()
        self.playSound()


    def initUI(self):
        # 设置窗口基本属性
        self.setWindowTitle('翻翻译译')
        self.setMinimumSize(300, 150)
        # 使用默认的窗口标志，只添加置顶
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)

        # 设置窗口图标
        icon_path = get_resource_path("images/xb32.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建垂直布局
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建文本显示区域
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setFont(QFont("黑体", 12))
        self.text_display.setFrameStyle(0)  # 移除边框
        self.text_display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_display.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout.addWidget(self.text_display)

    def initTray(self):
        # 创建托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        
        # 设置托盘图标
        icon_path = get_resource_path("images/xb32.ico")
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            print(f"找不到图标文件：{icon_path}")
        
        # 创建托盘菜单
        self.tray_menu = QMenu()
        
        # 添加显示/隐藏动作
        show_action = QAction("显示", self)
        show_action.triggered.connect(self.show)
        self.tray_menu.addAction(show_action)
        
        # 添加分隔线
        self.tray_menu.addSeparator()
        
        # 添加API选择子菜单
        api_menu = QMenu("通道选择", self)
        
        # 创建API选择动作组
        self.api_group = QActionGroup(self)
        self.api_group.setExclusive(True)  # 确保只能选择一个
        
        # 添加百度API选项
        baidu_action = QAction("百度API", self.api_group, checkable=True)
        baidu_action.setChecked(True)  # 默认选中百度API
        baidu_action.triggered.connect(lambda: self.selectAPI("BaiduAPI"))
        api_menu.addAction(baidu_action)
        
        # 添加有道API选项
        youdao_action = QAction("有道API", self.api_group, checkable=True)
        youdao_action.triggered.connect(lambda: self.selectAPI("YoudaoAPI"))
        api_menu.addAction(youdao_action)
        
        # 将API菜单添加到托盘菜单
        self.tray_menu.addMenu(api_menu)
        
        # 添加分隔线
        self.tray_menu.addSeparator()
        
        # 添加配置按钮
        config_action = QAction("配置", self)
        config_action.triggered.connect(self.configure_current_api)
        self.tray_menu.addAction(config_action)
        
        # 添加分隔线
        self.tray_menu.addSeparator()
        
        # 添加退出动作
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_app)
        self.tray_menu.addAction(quit_action)
        
        # 设置托盘菜单
        self.tray_icon.setContextMenu(self.tray_menu)
        
        # 显示托盘图标
        self.tray_icon.show()
        
        # 连接托盘图标的点击事件
        self.tray_icon.activated.connect(self.tray_icon_activated)
        
        # 连接API选择事件
        self.api_group.triggered.connect(self.on_api_changed)

    def tray_icon_activated(self, reason):
        # 处理托盘图标的点击事件
        if reason == QSystemTrayIcon.ActivationReason.Trigger:  # 单击
            if self.isHidden():
                self.show()
            else:
                self.hide()

    def closeEvent(self, event):
        # 重写关闭事件，点击关闭按钮时最小化到托盘
        event.ignore()
        self.hide()
        # self.tray_icon.showMessage(
        #     "翻翻译译",
        #     "应用程序已最小化到系统托盘",
        #     QSystemTrayIcon.MessageIcon.Information,
        #     2000
        # )

    def quit_app(self):
        # 完全退出应用程序
        self.tray_icon.hide()
        QApplication.quit()

    def initThread(self):
        # 创建并启动翻译线程
        self.translate_thread = TranslateThread()
        self.translate_thread.translation_done.connect(self.updateText)
        self.translate_thread.api_config_required.connect(self.show_api_config_dialog)
        self.translate_thread.start()

    def updateText(self, result, query):
        # 更新显示文本，不使用wrap_text方法
        formatted_text = (
            f'原文：\n    {query}\n'
            f'译文：\n    {result}\n'
        )
        self.text_display.setText(formatted_text)
        
        # 设置自动换行模式
        self.text_display.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        # 设置文字对齐方式
        self.text_display.setAlignment(Qt.AlignmentFlag.AlignLeft)

    def existFile(self):
        """检查并创建必要的文件和目录"""
        # 创建配置目录
        config_dir = os.path.join(os.environ.get('PROGRAMDATA', 'C:\\ProgramData'), 'FloatTrans')
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
            
        # 检查配置文件是否存在
        config_path = os.path.join(config_dir, 'config.json')
        if not os.path.exists(config_path):
            # 创建默认配置文件
            default_config = {
                "src": "BaiduAPI",
                "BaiduAPI": {
                    "apppid": "",
                    "apikey": ""
                },
                "YoudaoAPI": {
                    "apppid": "",
                    "apikey": ""
                }
            }
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(default_config, f, ensure_ascii=False, indent=4)

    def selectAPI(self, nameapi):
        """切换API通道"""
        config_path = os.path.join(os.environ.get('PROGRAMDATA', 'C:\\ProgramData'), 'FloatTrans', 'config.json')
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                
            # 检查新选择的API配置是否为空
            if nameapi == "BaiduAPI" and (not config["BaiduAPI"]["apppid"] or not config["BaiduAPI"]["apikey"]):
                self.show_api_config_dialog("BaiduAPI")
                return
            elif nameapi == "YoudaoAPI" and (not config["YoudaoAPI"]["apppid"] or not config["YoudaoAPI"]["apikey"]):
                self.show_api_config_dialog("YoudaoAPI")
                return
                
            # 更新配置
            config["src"] = nameapi
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
                
            # 更新当前API
            self.translate_thread.current_api = nameapi
            
            # 显示切换成功提示
            if os.path.exists(get_resource_path("images/xb32.ico")):
                self.tray_icon.setIcon(QIcon(get_resource_path("images/xb32.ico")))
                self.setWindowTitle(f"翻翻译译:{nameapi}")
            self.tray_icon.showMessage(
                "翻翻译译",
                f"已切换到{nameapi}",
                QSystemTrayIcon.MessageIcon.Information,
                2000
            )

    def on_api_changed(self, action):
        """处理API选择变更"""
        api_name = action.text()
        print(f"切换到 {api_name}")
        # TODO: 在这里添加API切换的具体实现


    def playSound(self):
        # 播放音效
        try:
            pygame.init()
            pygame.mixer.init()
            sound_path = get_resource_path("sound/xb1.wav")
            if os.path.exists(sound_path):
                sound = pygame.mixer.Sound(sound_path)
                sound.play()
        except Exception as e:
            print(f"播放音效失败: {e}")

    def show_api_config_dialog(self, api_type):
        """显示API配置对话框"""
        dialog = APIConfigDialog(api_type, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 配置已更新，重新加载配置
            self.translate_thread.load_api_config()

    def configure_current_api(self):
        """配置当前选择的API"""
        # 获取当前API类型
        current_api = self.translate_thread.current_api
        
        # 显示配置对话框
        dialog = APIConfigDialog(current_api, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            app_id, api_key = dialog.get_values()
            
            # 更新配置
            config_path = os.path.join(os.environ.get('PROGRAMDATA', 'C:\\ProgramData'), 'FloatTrans', 'config.json')
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                
                # 更新配置
                config[current_api]["apppid"] = app_id
                config[current_api]["apikey"] = api_key
                
                # 保存配置
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump(config, f, ensure_ascii=False, indent=4)
                
                # 重新加载配置
                self.translate_thread.load_api_config()
                
                # 显示成功提示
                self.tray_icon.showMessage(
                    "翻翻译译",
                    f"{current_api}配置已更新",
                    QSystemTrayIcon.MessageIcon.NoIcon,
                    2000
                )
            except Exception as e:
                print(f"更新配置失败: {e}")

# 添加API配置对话框类
class APIConfigDialog(QDialog):
    def __init__(self, api_type, parent=None):
        super().__init__(parent)
        self.api_type = api_type
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle(f'配置{self.api_type}')
        # 设置对话框图标
        icon_path = get_resource_path("images/xb32.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            
        layout = QGridLayout()
        
        # 创建输入框和标签
        appid_label = QLabel("AppID:")
        self.appid_edit = QLineEdit()
        apikey_label = QLabel("API Key:")
        self.apikey_edit = QLineEdit()
        
        # 添加按钮
        save_button = QPushButton("保存")
        save_button.clicked.connect(self.save_config)
        cancel_button = QPushButton("取消")
        cancel_button.clicked.connect(self.reject)
        
        # 添加到布局
        layout.addWidget(appid_label, 0, 0)
        layout.addWidget(self.appid_edit, 0, 1)
        layout.addWidget(apikey_label, 1, 0)
        layout.addWidget(self.apikey_edit, 1, 1)
        layout.addWidget(save_button, 2, 0)
        layout.addWidget(cancel_button, 2, 1)
        
        self.setLayout(layout)
        
        # 加载现有配置
        self.load_config()
        
    def load_config(self):
        """加载现有配置"""
        config_path = os.path.join(os.environ.get('PROGRAMDATA', 'C:\\ProgramData'), 'FloatTrans', 'config.json')
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                if self.api_type == "BaiduAPI":
                    self.appid_edit.setText(config["BaiduAPI"]["apppid"])
                    self.apikey_edit.setText(config["BaiduAPI"]["apikey"])
                else:
                    self.appid_edit.setText(config["YoudaoAPI"]["apppid"])
                    self.apikey_edit.setText(config["YoudaoAPI"]["apikey"])
                    
    def save_config(self):
        """保存配置"""
        appid = self.appid_edit.text().strip()
        apikey = self.apikey_edit.text().strip()
        
        if not appid or not apikey:
            QMessageBox.warning(self, "警告", "AppID和API Key不能为空！")
            return
            
        config_path = os.path.join(os.environ.get('PROGRAMDATA', 'C:\\ProgramData'), 'FloatTrans', 'config.json')
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
                
            if self.api_type == "BaiduAPI":
                config["BaiduAPI"]["apppid"] = appid
                config["BaiduAPI"]["apikey"] = apikey
            else:
                config["YoudaoAPI"]["apppid"] = appid
                config["YoudaoAPI"]["apikey"] = apikey
                
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
                
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败：{str(e)}")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 设置退出时清理
    app.setQuitOnLastWindowClosed(False)
    window = TranslatorWindow()
    window.show()
    sys.exit(app.exec())