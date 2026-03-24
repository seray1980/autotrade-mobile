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
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent))

# ==================== 安卓防闪退（只加这一段，别的完全不动）====================
IS_ANDROID = 'ANDROID_DATA' in os.environ
if IS_ANDROID:
    os.environ["KIVY_GL_BACKEND"] = "gl"
    os.environ["KIVY_NO_FILELOG"] = "1"
    os.environ["KIVY_NO_CONSOLELOG"] = "1"
# ==================== 结束 安卓防闪退 ====================

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

PC_SYNC_URL = "http://127.0.0.1:8899/api"
FORCE_REAL_DATA = True

# ==================== 安卓跳过本地模块（避免找不到文件闪退）====================
if not IS_ANDROID:
    from trade.utils.data_manager import get_data_manager
    from trade.utils.credential_manager import CredentialManager
    import csv
    from pathlib import Path as FSPath

logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('urllib3.connectionpool').setLevel(logging.ERROR)

# ==================== 全局配置 ====================
Config.set('graphics', 'width', 360)
Config.set('graphics', 'height', 640)
Config.set('graphics', 'resizable', False)
Config.set('graphics', 'multisamples', 0)
Config.set('kivy', 'exit_on_escape', 1)
Config.set('kivy', 'log_level', 'warning')

# ==================== 字体（安卓不读C盘）====================
FONT_NAME = 'Roboto' if IS_ANDROID else 'SimHei'
try:
    if not IS_ANDROID:
        LabelBase.register(name=FONT_NAME, fn_reg='C:/Windows/Fonts/simhei.ttf')
except:
    pass

# ==================== 配色 ====================
C = {
    'primary':    (0.15, 0.35, 0.65, 1),
    'success':    (0.18, 0.75, 0.40, 1),
    'danger':     (0.85, 0.25, 0.25, 1),
    'warning':    (0.90, 0.60, 0.05, 1),
    'info':       (0.10, 0.65, 0.75, 1),
    'bg':         (0.12, 0.12, 0.18, 1),
    'bg_card':    (0.18, 0.18, 0.24, 1),
    'text':       (1, 1, 1, 1),
    'text_muted': (0.8, 0.8, 0.85, 1),
    'header_bg':  (0.22, 0.22, 0.30, 1),
    'row_even':   (0.18, 0.18, 0.24, 1),
    'row_odd':    (0.22, 0.22, 0.28, 1),
    'buy':        (0.15, 0.75, 0.40, 1),
    'sell':       (0.85, 0.25, 0.25, 1),
    'profit':     (0.15, 0.75, 0.40, 1),
    'loss':       (0.85, 0.25, 0.25, 1),
    'on_bg':      (0.15, 0.25, 0.20, 1),
    'off_bg':     (0.25, 0.20, 0.20, 1),
    'white':      (1, 1, 1, 1),
    'tab_selected': (0.25, 0.35, 0.55, 1),
}

FS = {'xl': dp(20), 'lg': dp(18), 'md': dp(16), 'sm': dp(14), 'xs': dp(12), 'xxs': dp(10)}
H  = {
    'title_bar': dp(0), 'section': dp(40), 'input': dp(40),
    'btn': dp(44), 'row': dp(42), 'thead': dp(40), 'label': dp(28),
    'banner': dp(32), 'tab': dp(48),
}
SP = {'xs': dp(2), 'sm': dp(4), 'md': dp(6), 'lg': dp(10), 'xl': dp(16)}

# ==================== 工具函数 ====================
def set_bg(widget, rgba):
    widget.canvas.before.clear()
    with widget.canvas.before:
        Color(*rgba)
        Rectangle(pos=widget.pos, size=widget.size)

def make_btn(text, color, font_size=None, **kwargs):
    return Button(
        text=text, font_name=FONT_NAME,
        font_size=font_size or FS['md'],
        background_color=color, background_normal='',
        color=(1,1,1,1), **kwargs
    )

def make_input(hint='', password=False, text='', **kwargs):
    inp = TextInput(
        hint_text=hint, text=text,
        font_name=FONT_NAME, font_size=FS['sm'],
        multiline=False, password=password,
        background_color=(0.25,0.25,0.32,1),
        foreground_color=(1,1,1,1),
        cursor_color=(1,1,1,1),
        size_hint_y=None, height=H['input'],
        halign='left', **kwargs
    )
    inp.valign = 'middle'
    return inp

def make_label(text, font_size=None, bold=False, color=None, halign='left', **kwargs):
    return Label(
        text=text, font_name=FONT_NAME,
        font_size=font_size or FS['sm'],
        bold=bold, color=color or (1,1,1,1),
        halign=halign, valign='middle',
        size_hint_y=None, height=kwargs.get('height', H['label']),
    )

def make_spinner(text, values, **kwargs):
    class _Opt(SpinnerOption):
        def __init__(self, **kw):
            super().__init__(**kw)
            self.font_name = FONT_NAME
            self.font_size = FS['sm']
            self.background_color=(0.25,0.25,0.32,1)
            self.color=(1,1,1,1)
    return Spinner(
        text=text, values=values,
        font_name=FONT_NAME, font_size=FS['sm'],
        option_cls=_Opt,
        background_color=(0.25,0.25,0.32,1),
        color=(1,1,1,1),
        size_hint_y=None, height=H['input'], **kwargs
    )

class TableHeader(BoxLayout):
    def __init__(self, headers, col_weights=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = H['thead']
        self.spacing = SP['xs']
        self.padding = (SP['sm'], 0)
        set_bg(self, C['header_bg'])
        n = len(headers)
        weights = col_weights or [1/n] * n
        for h, w in zip(headers, weights):
            self.add_widget(make_label(h, font_size=FS['sm'], bold=True, height=H['thead'], size_hint_x=w))

class TableRow(BoxLayout):
    def __init__(self, data, col_keys, col_weights=None, index=0, row_bg=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = H['row']
        self.spacing = SP['xs']
        self.padding = (SP['sm'], 0)
        bg = row_bg or (C['row_even'] if index % 2 == 0 else C['row_odd'])
        set_bg(self, bg)
        n = len(col_keys)
        weights = col_weights or [1/n] * n
        for key, w in zip(col_keys, weights):
            value = str(data.get(key, '-'))
            txt_color = C['text']
            if key == '方向' or key == '买卖方式':
                txt_color = C['buy'] if '买' in value else C['sell']
            elif key in ('盈亏%'):
                try:
                    txt_color = C['profit'] if float(value.replace('%',''))>=0 else C['loss']
                except:
                    pass
            lbl = Label(text=value, font_name=FONT_NAME, font_size=FS['sm'], color=txt_color, halign='right', size_hint_x=w)
            self.add_widget(lbl)

class DataTable(BoxLayout):
    def __init__(self, headers, col_keys=None, col_weights=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.headers = headers
        self.col_keys = col_keys or headers
        self.col_weights = col_weights
        self.row_count = 0
        self.header_row = TableHeader(headers, col_weights)
        self.add_widget(self.header_row)
        self.scroll = ScrollView(do_scroll_x=False, do_scroll_y=True)
        self.rows_layout = BoxLayout(orientation='vertical', size_hint_y=None, spacing=SP['xs'])
        self.rows_layout.bind(minimum_height=self.rows_layout.setter('height'))
        self.scroll.add_widget(self.rows_layout)
        self.add_widget(self.scroll)

    def add_row(self, data, row_bg=None):
        row = TableRow(data, self.col_keys, self.col_weights, index=self.row_count, row_bg=row_bg)
        self.rows_layout.add_widget(row)
        self.row_count += 1

    def clear_rows(self):
        self.rows_layout.clear_widgets()
        self.row_count = 0

class LoginDialog(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self.spacing = SP['sm']
        self.padding = (SP['lg'], SP['sm'])
        set_bg(self, C['bg'])

        self.add_widget(make_label(
            '连接交易账户', font_size=FS['xl'], bold=True,
            color=C['white'], height=H['section'], halign='center'
        ))

        def add_field(lbl_text, widget):
            self.add_widget(make_label(lbl_text, font_size=FS['sm'], color=C['white'], halign='center'))
            self.add_widget(widget)

        self.broker_list = [
            'Alpaca (美股)', 'Interactive Brokers (全球)', '富途 (港股)',
            '老虎证券 (港股)', '东方财富 (A股)', '华泰证券 (A股)',
            '中金财富 (A股)', '国泰君安 (A股)', '招商证券 (A股)',
            '中信证券 (A股)', '海通证券 (A股)', '广发证券 (A股)',
            '申万宏源 (A股)', '银河证券 (A股)', '光大证券 (A股)'
        ]
        self.broker_spinner = make_spinner(self.broker_list[0], self.broker_list)
        self.broker_spinner.bind(text=self._on_broker_change)
        add_field('券商:', self.broker_spinner)

        self.market_spinner = make_spinner('美股', ('美股','港股','A股'))
        add_field('市场:', self.market_spinner)

        self.api_key_input = make_input(hint='API Key')
        add_field('API Key:', self.api_key_input)

        self.secret_key_input = make_input(hint='Secret Key', password=True)
        add_field('Secret Key:', self.secret_key_input)

        row_save = BoxLayout(size_hint_y=None, height=H['input'], spacing=SP['xs'])
        self.save_cb = CheckBox(active=True, size_hint=(None, None), size=(dp(24), dp(24)), color=(1,1,1,1))
        row_save.add_widget(self.save_cb)
        row_save.add_widget(make_label('记住账户', font_size=FS['sm'], color=C['white']))
        self.add_widget(row_save)

        btn_row = BoxLayout(size_hint_y=None, height=H['btn'], spacing=SP['md'])
        conn_btn = make_btn('连接（只读）', C['primary'])
        conn_btn.bind(on_press=self._on_connect)
        skip_btn = make_btn('仅演示', C['info'])
        skip_btn.bind(on_press=self._on_demo)
        btn_row.add_widget(conn_btn)
        btn_row.add_widget(skip_btn)
        self.add_widget(btn_row)
        if not IS_ANDROID:
            self._load_last()

    def _on_broker_change(self, inst, val):
        if 'Alpaca' in val:
            self.market_spinner.values = ('美股',)
            self.market_spinner.text = '美股'
        elif '富途' in val or '老虎' in val:
            self.market_spinner.values = ('港股', '美股')
            self.market_spinner.text = '港股'
        else:
            self.market_spinner.values = ('A股',)
            self.market_spinner.text = 'A股'

    def _load_last(self):
        try:
            dm = get_data_manager()
            accounts = dm.load_accounts()
            if accounts:
                a = accounts[0]
                self.broker_spinner.text = a.get('broker', self.broker_list[0])
                self.market_spinner.text = a.get('market', '美股')
        except:
            pass

    def _on_connect(self, inst):
        self.app.on_connect_success({}, readonly=True)
        self.parent_popup.dismiss()

    def _on_demo(self, inst):
        account = {
            'account_id': 'demo_account', 'account_name': '演示账户',
            'broker': 'Demo', 'market': '演示', 'mode': '演示模式'
        }
        self.app.on_connect_success(account, readonly=True)
        self.parent_popup.dismiss()

class AccountPanel(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self.spacing = SP['sm']
        self.padding = SP['md']
        set_bg(self, C['bg'])
        self.table = DataTable(headers=['字段','值'], col_keys=['字段','值'], col_weights=[0.3, 0.7])
        self.add_widget(self.table)
        btn_row = BoxLayout(size_hint_y=None, height=H['btn'], spacing=SP['md'])
        r = make_btn('刷新', C['primary'])
        r.bind(on_press=lambda _: self.app.refresh_account())
        o = make_btn('断开', C['danger'])
        o.bind(on_press=self.app.on_disconnect)
        btn_row.add_widget(r)
        btn_row.add_widget(o)
        self.add_widget(btn_row)

    def update(self, info):
        self.table.clear_rows()
        rows = [
            ('账户名称', info.get('account_name', 'N/A')),
            ('账户ID', info.get('account_id', 'N/A')),
            ('连接模式', info.get('mode', 'N/A')),
            ('券商', info.get('broker', 'N/A')),
            ('市场', info.get('market', 'N/A')),
            ('数据时间', datetime.now().strftime('%H:%M:%S')),
        ]
        for f, v in rows:
            self.table.add_row({'字段': f, '值': v})

class PositionPanel(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self.spacing = SP['sm']
        self.padding = SP['md']
        set_bg(self, C['bg'])
        self.table = DataTable(
            headers=['代码','数量','成本','现价','盈亏%'],
            col_keys=['代码','数量','成本','现价','盈亏%'],
            col_weights=[0.1, 0.225, 0.225, 0.225, 0.225]
        )
        self.add_widget(self.table)
        r = make_btn('刷新持仓', C['primary'], size_hint_y=None, height=H['btn'])
        r.bind(on_press=lambda _: self.app.refresh_positions())
        self.add_widget(r)

    def update(self, positions):
        self.table.clear_rows()
        if not positions:
            self.table.add_row({'代码':'暂无持仓','数量':'-','成本':'-','现价':'-','盈亏%':'-'})
            return
        for p in positions:
            self.table.add_row({
                '代码': p.get('symbol', '-'),
                '数量': str(p.get('quantity', 0)),
                '成本': f"{float(p.get('avg_price',0)):.2f}",
                '现价': f"{float(p.get('current_price',0)):.2f}",
                '盈亏%': f"{p.get('pnl_percent', 0):+.2f}%",
            })

class WatchlistPanel(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self.spacing = SP['sm']
        self.padding = SP['md']
        set_bg(self, C['bg'])
        self.table = DataTable(
            headers=['代码','现价','下单价','买卖方式','状态'],
            col_keys=['代码','现价','下单价','买卖方式','状态'],
            col_weights=[0.15, 0.18, 0.18, 0.24, 0.25]
        )
        self.add_widget(self.table)
        r = make_btn('刷新监控列表', C['primary'], size_hint_y=None, height=H['btn'])
        r.bind(on_press=lambda _: self._load())
        self.add_widget(r)
        Clock.schedule_once(lambda dt: self._load(), 0.5)

    def _load(self):
        self.table.clear_rows()
        try:
            res = requests.get(f"{PC_SYNC_URL}/monitors", timeout=2)
            real_monitors = res.json()
        except:
            real_monitors = []
        for m in real_monitors:
            self._add_row(m["symbol"], m["current_price"], m["entry_price"], m["direction"], m["status"])

    def _add_row(self, sym, price, entry, direct, status_text):
        row = BoxLayout(orientation='horizontal', size_hint_y=None, height=H['row'], spacing=SP['xs'], padding=(SP['sm'],0))
        bg = C['on_bg'] if status_text == '运行中' else C['off_bg']
        set_bg(row, bg)
        lbl_sym   = Label(text=sym, font_name=FONT_NAME, font_size=FS['sm'], color=C['text'], halign='center', size_hint_x=0.15)
        lbl_price = Label(text=f"{float(price):.2f}", font_name=FONT_NAME, font_size=FS['sm'], color=C['text'], halign='right', size_hint_x=0.18)
        lbl_entry = Label(text=f"{float(entry):.2f}", font_name=FONT_NAME, font_size=FS['sm'], color=C['text'], halign='right', size_hint_x=0.18)
        lbl_dir   = Label(text=direct, font_name=FONT_NAME, font_size=FS['sm'], color=C['buy'] if '买' in direct else C['sell'], halign='center', size_hint_x=0.24)
        lbl_st    = Label(text=status_text, font_name=FONT_NAME, font_size=FS['sm'], color=C['success'] if status_text=='运行中' else C['text_muted'], halign='center', size_hint_x=0.25)
        row.add_widget(lbl_sym)
        row.add_widget(lbl_price)
        row.add_widget(lbl_entry)
        row.add_widget(lbl_dir)
        row.add_widget(lbl_st)
        self.table.rows_layout.add_widget(row)
        self.table.row_count += 1

class TradeHistoryPanel(BoxLayout):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self.spacing = SP['sm']
        self.padding = SP['md']
        set_bg(self, C['bg'])
        date_row = BoxLayout(size_hint_y=None, height=H['input'], spacing=SP['sm'])
        self.date_input = make_input(hint='日期 YYYYMMDD', text=datetime.now().strftime('%Y%m%d'))
        load_btn = make_btn('查询', C['primary'], size_hint=(None,None), size=(dp(58), H['input']))
        load_btn.bind(on_press=self._on_load)
        date_row.add_widget(self.date_input)
        date_row.add_widget(load_btn)
        self.add_widget(date_row)
        self.table = DataTable(
            headers=['时间','代码','方向','价格','数量','状态'],
            col_keys=['时间','代码','方向','价格','数量','状态'],
            col_weights=[0.09, 0.20, 0.17, 0.20, 0.17, 0.17]
        )
        self.add_widget(self.table)
        self.summary_lbl = make_label('', font_size=FS['xs'], color=C['text_muted'], height=dp(20))
        self.add_widget(self.summary_lbl)
        Clock.schedule_once(lambda dt: self._load_logs(), 0.8)

    def _on_load(self, inst):
        self._load_logs()

    def _load_logs(self):
        self.table.clear_rows()
        if IS_ANDROID:
            self.table.add_row({'时间':'暂无记录','代码':'-','方向':'-','价格':'-','数量':'-','状态':'-'})
            self.summary_lbl.text = '共 0 笔'
            return

class MonitorApp(App):
    def build(self):
        root = BoxLayout(orientation='vertical')
        set_bg(root, C['bg'])

        top_bar = BoxLayout(orientation='vertical', size_hint_y=None, height=H['tab'])
        set_bg(top_bar, C['bg_card'])
        tab_bar = BoxLayout(size_hint_y=None, height=H['tab'])
        set_bg(tab_bar, C['bg_card'])

        class TabButton(BoxLayout):
            def __init__(self, text, **kwargs):
                super().__init__(**kwargs)
                self.orientation = 'vertical'
                self.size_hint_x = 0.25
                self.label = make_label(text, font_size=FS['md'], bold=True, halign='center')
                self.add_widget(self.label)
                self.set_normal()
            def set_selected(self):
                set_bg(self, C['primary'])
                self.label.color = C['white']
            def set_normal(self):
                set_bg(self, C['bg_card'])
                self.label.color = C['text_muted']

        self.tabs = {}
        for name in ['账户', '持仓', '监控', '记录']:
            tab = TabButton(text=name)
            self.tabs[name] = tab
            tab_bar.add_widget(tab)
        self.tabs['账户'].set_selected()
        top_bar.add_widget(tab_bar)
        root.add_widget(top_bar)

        self.logout_btn = make_btn('退出', C['danger'], font_size=FS['xs'], size_hint=(None, None), size=(dp(46), dp(26)))
        root.add_widget(self.logout_btn)
        self.content = BoxLayout()
        root.add_widget(self.content)

        self.account_panel = AccountPanel(self)
        self.position_panel = PositionPanel(self)
        self.watchlist_panel = WatchlistPanel(self)
        self.history_panel = TradeHistoryPanel(self)
        self.current_panel = self.account_panel
        self.content.add_widget(self.current_panel)
        Clock.schedule_once(self._show_login, 0)
        return root

    def _switch_tab(self, tab_name):
        for t in self.tabs.values(): t.set_normal()
        self.tabs[tab_name].set_selected()
        self.content.clear_widgets()
        if tab_name == '账户': self.content.add_widget(self.account_panel)
        elif tab_name == '持仓': self.content.add_widget(self.position_panel)
        elif tab_name == '监控': self.content.add_widget(self.watchlist_panel)
        elif tab_name == '记录': self.content.add_widget(self.history_panel)

    def _show_login(self, dt):
        dlg = LoginDialog(self)
        self.pop = Popup(content=dlg, size_hint=(0.92,0.92), auto_dismiss=False)
        dlg.parent_popup = self.pop
        self.pop.open()

    def on_connect_success(self, account, readonly=True):
        self._load_all()

    def _load_all(self):
        try:
            self.position_panel.update(requests.get(f"{PC_SYNC_URL}/positions", timeout=2).json())
        except:
            self.position_panel.update([])
        self.account_panel.update({
            'account_name':'同步版','account_id':'mobile','mode':'只读','broker':'远程','market':'PC同步'
        })
        self.watchlist_panel._load()

    def refresh_account(self): self._load_all()
    def refresh_positions(self): self._load_all()
    def on_disconnect(self, *args): self.pop.open()

if __name__ == '__main__':
    MonitorApp().run()
