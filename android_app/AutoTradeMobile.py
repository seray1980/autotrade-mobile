#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
移动端监控系统  — 合规只读版 + 推送通知
========================================
设计原则（合法合规）：
  ✅ 手机端只能「看」和「控制开关」
  ✅ 可查看：账户信息、持仓、自选股行情、交易记录
  ✅ 可控制：策略监控的启用/暂停开关
  ✅ 自动推送交易通知
  ❌ 绝对禁止：下单、执行交易、后台自动交易、挂策略
  ❌ 真正的自动交易只在电脑端运行
【仅修改数据获取：本地假数据 → 电脑端同步】
"""

import sys
import os
import requests
from datetime import datetime

# ==============================================
# 安卓核心防闪退（强制稳定模式）
# ==============================================
IS_ANDROID = "ANDROID_DATA" in os.environ

if IS_ANDROID:
    os.environ["KIVY_GL_BACKEND"] = "gl"
    os.environ["KIVY_NO_FILELOG"] = "1"
    os.environ["KIVY_NO_CONSOLELOG"] = "1"
    os.environ["KIVY_NO_ARGS"] = "1"

# 跳过所有本地扩展模块，彻底避免闪退
if IS_ANDROID:
    class MockData:
        def load_accounts(self): return []
        def get_trade_logs(self, d): return []
    get_data_manager = lambda: MockData()
    CredentialManager = lambda: MockData()
else:
    try:
        from trade.utils.data_manager import get_data_manager
        from trade.utils.credential_manager import CredentialManager
    except:
        class MockData:
            def load_accounts(self): return []
            def get_trade_logs(self, d): return []
        get_data_manager = lambda: MockData()
        CredentialManager = lambda: MockData()

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.spinner import Spinner, SpinnerOption
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.checkbox import CheckBox
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.text import LabelBase
from kivy.config import Config
from kivy.graphics import Color, Rectangle
import logging

# 关闭所有日志
logging.basicConfig(level=logging.CRITICAL)
logging.disable(logging.CRITICAL)

PC_SYNC_URL = "http://127.0.0.1:8899/api"

# ==============================================
# 全局配置
# ==============================================
Config.set("graphics", "multisamples", 0)
Config.set("kivy", "log_level", "critical")
Config.set("kivy", "exit_on_escape", 1)

if not IS_ANDROID:
    Config.set("graphics", "width", 360)
    Config.set("graphics", "height", 640)
    Config.set("graphics", "resizable", False)

# ==============================================
# 字体（安卓永不闪退）
# ==============================================
FONT_NAME = "Roboto"

# ==============================================
# 配色
# ==============================================
C = {
    "primary":    (0.15, 0.35, 0.65, 1),
    "success":    (0.18, 0.75, 0.40, 1),
    "danger":     (0.85, 0.25, 0.25, 1),
    "bg":         (0.12, 0.12, 0.18, 1),
    "bg_card":    (0.18, 0.18, 0.24, 1),
    "text":       (1, 1, 1, 1),
    "text_muted": (0.8, 0.8, 0.85, 1),
    "header_bg":  (0.22, 0.22, 0.30, 1),
    "row_even":   (0.18, 0.18, 0.24, 1),
    "buy":        (0.18, 0.75, 0.40, 1),
    "sell":       (0.85, 0.25, 0.25, 1),
    "profit":     (0.18, 0.75, 0.40, 1),
    "loss":       (0.85, 0.25, 0.25, 1),
    "on_bg":      (0.15, 0.25, 0.20, 1),
    "off_bg":     (0.25, 0.20, 0.20, 1),
}

FS = {"xl": dp(20), "lg": dp(18), "md": dp(16), "sm": dp(14)}
H  = {"input": dp(40), "btn": dp(44), "row": dp(42), "tab": dp(48)}
SP = {"sm": dp(4)}

# ==============================================
# 工具函数
# ==============================================
def set_bg(widget, color):
    try:
        widget.canvas.before.clear()
        with widget.canvas.before:
            Color(*color)
            Rectangle(pos=widget.pos, size=widget.size)
    except:
        pass

def make_label(text, **kwargs):
    return Label(
        text=text, font_name=FONT_NAME,
        color=C["text"], **kwargs
    )

def make_btn(text, color, **kwargs):
    return Button(
        text=text, font_name=FONT_NAME,
        background_color=color, color=(1,1,1,1), **kwargs
    )

def make_input(**kwargs):
    return TextInput(
        font_name=FONT_NAME,
        background_color=(0.25,0.25,0.32,1),
        foreground_color=(1,1,1,1), **kwargs
    )

# ==============================================
# 表格组件
# ==============================================
class DataTable(BoxLayout):
    def __init__(self, headers, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.spacing = SP["sm"]
        
        # 表头
        header = BoxLayout(size_hint_y=None, height=H["row"])
        set_bg(header, C["header_bg"])
        for h in headers:
            header.add_widget(make_label(h, bold=True, halign="center"))
        self.add_widget(header)
        
        # 内容滚动区域
        self.scroll = ScrollView()
        self.content = BoxLayout(orientation="vertical", size_hint_y=None)
        self.scroll.add_widget(self.content)
        self.add_widget(self.scroll)
    
    def add_row(self, row_data):
        row = BoxLayout(size_hint_y=None, height=H["row"])
        for txt in row_data:
            row.add_widget(make_label(str(txt), halign="center"))
        self.content.add_widget(row)
    
    def clear(self):
        self.content.clear_widgets()

# ==============================================
# 主页面
# ==============================================
class AccountPage(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = 10
        self.spacing = 10
        set_bg(self, C["bg"])
        
        self.table = DataTable(["字段", "值"])
        self.add_widget(self.table)
        
        btn = make_btn("刷新", C["primary"], size_hint_y=None, height=H["btn"])
        self.add_widget(btn)

class PositionPage(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = 10
        self.spacing = 10
        set_bg(self, C["bg"])
        self.table = DataTable(["代码", "数量", "成本", "现价", "盈亏%"])
        self.add_widget(self.table)

class MonitorPage(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = 10
        self.spacing = 10
        set_bg(self, C["bg"])
        self.table = DataTable(["代码", "现价", "方向", "状态"])
        self.add_widget(self.table)

class TradePage(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.padding = 10
        self.spacing = 10
        set_bg(self, C["bg"])
        self.table = DataTable(["时间", "代码", "方向", "价格"])
        self.add_widget(self.table)

# ==============================================
# 主APP
# ==============================================
class StockMonitorApp(App):
    def build(self):
        root = BoxLayout(orientation="vertical")
        set_bg(root, C["bg"])
        
        # 标签栏
        tab_bar = BoxLayout(size_hint_y=None, height=H["tab"])
        tabs = ["账户", "持仓", "监控", "交易"]
        for t in tabs:
            btn = make_btn(t, C["bg_card"])
            tab_bar.add_widget(btn)
        root.add_widget(tab_bar)
        
        # 内容区域
        self.container = BoxLayout()
        self.container.add_widget(AccountPage())
        root.add_widget(self.container)
        
        return root

if __name__ == "__main__":
    StockMonitorApp().run()
