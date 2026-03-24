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
import requests
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).parent.parent))

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

FONT_NAME = 'SimHei'
try:
    LabelBase.register(name=FONT_NAME, fn_reg='C:/Windows/Fonts/simhei.ttf')
except:
    try:
        LabelBase.register(name=FONT_NAME, fn_sim='simhei')
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

# ==================== 字体尺寸 ====================
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
        halign='left',
        **kwargs
    )
    inp.valign = 'middle'
    return inp

def make_label(text, font_size=None, bold=False, color=None, halign='left', **kwargs):
    lbl = Label(
        text=text, font_name=FONT_NAME,
        font_size=font_size or FS['sm'],
        bold=bold, color=color or (1,1,1,1),
        halign=halign, valign='middle',
        size_hint_y=None, height=kwargs.get('height', H['label']),
    )
    return lbl

def make_spinner(text, values, **kwargs):
    class _Opt(SpinnerOption):
        def __init__(self, **kw):
            super().__init__(**kw)
            self.font_name = FONT_NAME
            self.font_size = FS['sm']
            self.background_color = (0.25,0.25,0.32,1)
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
            lbl = Label(
                text=value, font_name=FONT_NAME, font_size=FS['sm'],
                color=txt_color, halign='right', size_hint_x=w
            )
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
                broker = a.get('broker', self.broker_list[0])
                market = a.get('market', '美股')
                self.broker_spinner.text = broker
                self.market_spinner.text = market
                try:
                    creds = CredentialManager().get_credentials(a.get('account_id', ''))
                    if creds:
                        self.api_key_input.text = creds.get('api_key', '')
                        self.secret_key_input.text = creds.get('secret_key', '')
                except:
                    pass
        except:
            pass

    def _on_connect(self, inst):
        api_key = self.api_key_input.text.strip()
        secret_key = self.secret_key_input.text.strip()
        if not api_key or not secret_key:
            return
        try:
            dm = get_data_manager()
            existing_accounts = dm.load_accounts()
            matched_account = None
            broker_core = self.broker_spinner.text.split('(')[0].strip().lower()
            for acc in existing_accounts:
                acc_broker = acc.get('broker', '').lower()
                acc_market = acc.get('market', '')
                acc_api_key = acc.get('api_key', '')
                if (broker_core in acc_broker and
                    acc_api_key.endswith(api_key[-6:]) and
                    acc_market == self.market_spinner.text):
                    matched_account = acc
                    break
            if matched_account:
                account = matched_account.copy()
            else:
                account = {
                    'account_id': f"{self.broker_spinner.text}_{self.market_spinner.text}_{api_key[-6:]}",
                    'account_name': f"{self.broker_spinner.text} ({self.market_spinner.text})",
                    'broker': self.broker_spinner.text,
                    'market': self.market_spinner.text,
                    'mode': '只读连接',
                }
            dm.save_account(account)
            if self.save_cb.active:
                CredentialManager().save_credentials(
                    account['account_id'], {'api_key': api_key, 'secret_key': secret_key})
        except:
            account = {
                'account_id': f"{self.broker_spinner.text}_{self.market_spinner.text}_{api_key[-6:]}",
                'account_name': f"{self.broker_spinner.text} ({self.market_spinner.text})",
                'broker': self.broker_spinner.text,
                'market': self.market_spinner.text,
                'mode': '只读连接',
            }
        self.app.on_connect_success(account, readonly=True)
        self.parent_popup.dismiss()

    def _on_demo(self, inst):
        account = {
            'account_id': 'demo_account',
            'account_name': '演示账户 (无真实数据)',
            'broker': 'Demo',
            'market': '演示',
            'mode': '演示模式',
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
        
        self.table = DataTable(
            headers=['字段','值'], 
            col_keys=['字段','值'], 
            col_weights=[0.3, 0.7]
        )
        self.add_widget(self.table)
        
        btn_row = BoxLayout(size_hint_y=None, height=H['btn'], spacing=SP['md'])
        r = make_btn('刷新', C['primary'])
        r.bind(on_press=lambda _: self.app.refresh_account())
        o = make_btn('断开', C['danger'])
        o.bind(on_press=self._on_disconnect)
        btn_row.add_widget(r)
        btn_row.add_widget(o)
        self.add_widget(btn_row)

    def update(self, info):
        self.table.clear_rows()
        def fmt_money(v):
            try:
                return f"${float(v):,.2f}"
            except:
                return str(v) if v else 'N/A'
        rows = [
            ('账户名称', info.get('account_name', 'N/A')),
            ('账户ID', info.get('account_id', 'N/A')),
            ('连接模式', info.get('mode', 'N/A')),
            ('券商', info.get('broker', 'N/A')),
            ('市场', info.get('market', 'N/A')),
            ('账户余额', fmt_money(info.get('balance', 0))),
            ('可用资金', fmt_money(info.get('available', 0))),
            ('持仓市值', fmt_money(info.get('position_value', 0))),
            ('总资产', fmt_money(info.get('total_assets', 0))),
            ('数据时间', datetime.now().strftime('%H:%M:%S')),
        ]
        for f, v in rows:
            self.table.add_row({'字段': f, '值': v})

    def _on_disconnect(self, inst):
        content = BoxLayout(orientation='vertical', spacing=SP['md'], padding=SP['lg'])
        set_bg(content, C['bg'])
        content.add_widget(make_label('确定断开账户连接？', font_size=FS['sm'], color=C['text']))
        btn_row = BoxLayout(size_hint_y=None, height=H['btn'], spacing=SP['md'])
        cancel = make_btn('取消', C['text_muted'])
        confirm = make_btn('断开', C['danger'])
        btn_row.add_widget(cancel)
        btn_row.add_widget(confirm)
        content.add_widget(btn_row)
        pop = Popup(title='断开连接', title_font=FONT_NAME, title_size=FS['md'],
                    content=content, size_hint=(0.88, 0.34))
        cancel.bind(on_press=pop.dismiss)
        confirm.bind(on_press=lambda _: (pop.dismiss(), self.app.on_disconnect()))
        pop.open()


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
            pct = p.get('pnl_percent', 0)
            try:
                pct_f = float(pct)
            except:
                pct_f = 0
            row_bg = C['on_bg'] if pct_f >= 0 else (1.00, 0.94, 0.94, 1)
            self.table.add_row({
                '代码': p.get('symbol', '-'),
                '数量': str(p.get('quantity', 0)),
                '成本': f"{float(p.get('avg_price',0)):.2f}",
                '现价': f"{float(p.get('current_price',0)):.2f}",
                '盈亏%': f"{pct_f:+.2f}%",
            }, row_bg=row_bg)


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
        row = BoxLayout(
            orientation='horizontal', size_hint_y=None, height=H['row'],
            spacing=SP['xs'], padding=(SP['sm'],0)
        )
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
        date = self.date_input.text.strip()
        try:
            dm = get_data_manager()
            logs = dm.get_trade_logs(date)
            if not logs:
                self.table.add_row({'时间':'暂无记录','代码':'-','方向':'-','价格':'-','数量':'-','状态':'-'})
                self.summary_lbl.text = f'{date}  共 0 笔'
                return
            buy_cnt = sell_cnt = 0
            for log in logs:
                action = log.get('action','')
                direction = '买入' if action in ('buy','买入') else '卖出'
                if direction == '买入':
                    buy_cnt +=1
                else:
                    sell_cnt +=1
                status = log.get('status','-')
                row_bg = C['on_bg'] if status in ('filled','已成交') else None
                t = log.get('time','-')[-8:]
                self.table.add_row({
                    '时间':t,'代码':log.get('symbol','-'),'方向':direction,
                    '价格':log.get('price','-'),'数量':log.get('quantity','-'),'状态':status
                }, row_bg=row_bg)
            self.summary_lbl.text = f'{date}  共 {len(logs)} 笔  买入{buy_cnt}  卖出{sell_cnt}'
        except Exception as e:
            print(f'[历史] 加载失败: {e}')
            self.summary_lbl.text = '加载失败'


class PushNotificationManager:
    def __init__(self, app):
        self.app = app
        self.notif_file = FSPath(__file__).parent.parent / 'push_notifications.csv'
        self.notif_file.touch(exist_ok=True)
        self.shown_ids = set()

    def check_notifications(self, dt):
        try:
            if not self.notif_file.exists(): return
            with open(self.notif_file,'r',encoding='utf-8') as f:
                rows = list(csv.DictReader(f))
            for row in rows:
                nid = row.get('id','')
                if nid and nid not in self.shown_ids:
                    self.shown_ids.add(nid)
        except:
            pass


class MonitorApp(App):
    def build(self):
        root = BoxLayout(orientation='vertical')
        set_bg(root, C['bg'])

        # 顶部栏：顶到最上，无空白
        top_bar = BoxLayout(orientation='vertical', size_hint_y=None, height=H['tab'])
        set_bg(top_bar, C['bg_card'])

        tab_bar = BoxLayout(size_hint_y=None, height=H['tab'])
        set_bg(tab_bar, C['bg_card'])

        class TabButton(BoxLayout):
            def __init__(self, text, is_monitor=False, **kwargs):
                super().__init__(**kwargs)
                self.orientation = 'vertical'
                self.size_hint_x = 0.25
                self.padding = (0, 0)
                self.tab_text = text
                self.label = make_label(text, font_size=FS['md'], bold=True, halign='center')
                self.add_widget(self.label)
                self.is_selected = False
                self.is_monitor = is_monitor
                self.set_normal()

            def set_selected(self):
                self.is_selected = True
                color = C['tab_selected'] if self.is_monitor else C['primary']
                set_bg(self, color)
                self.label.color = C['white']

            def set_normal(self):
                self.is_selected = False
                set_bg(self, C['bg_card'])
                self.label.color = C['text_muted']

        self.tabs = {}
        tab_names = ['账户', '持仓', '监控', '记录']
        for name in tab_names:
            tab = TabButton(text=name, is_monitor=(name == '监控'))
            tab.bind(on_touch_down=lambda w, t: self._switch_tab(w.tab_text) if w.collide_point(*t.pos) else None)
            self.tabs[name] = tab
            tab_bar.add_widget(tab)
        self.tabs['账户'].set_selected()

        top_bar.add_widget(tab_bar)
        root.add_widget(top_bar)

        # ====================== 退出按钮 → 放到 右上角 ======================
        self.logout_btn = make_btn(
            '退出', C['danger'],
            font_size=FS['xs'],
            size_hint=(None, None),
            size=(dp(46), dp(26))
        )
        self.logout_btn.bind(on_press=self.on_disconnect)
        
        # 右上角、贴边、在顶部栏内
        self.logout_btn.pos_hint = {'right': 0.99, 'top': 0.99}
        root.add_widget(self.logout_btn)

        self.content = BoxLayout()
        root.add_widget(self.content)

        self.account_panel = AccountPanel(self)
        self.position_panel = PositionPanel(self)
        self.watchlist_panel = WatchlistPanel(self)
        self.history_panel = TradeHistoryPanel(self)

        self.current_panel = self.account_panel
        self.content.add_widget(self.current_panel)

        self.current_account = None
        self.push_manager = None
        Clock.schedule_once(self._show_login, 0)
        return root

    def _switch_tab(self, tab_name):
        for name, tab in self.tabs.items():
            if name == tab_name:
                tab.set_selected()
            else:
                tab.set_normal()
        self.content.clear_widgets()
        if tab_name == '账户':
            self.current_panel = self.account_panel
        elif tab_name == '持仓':
            self.current_panel = self.position_panel
        elif tab_name == '监控':
            self.current_panel = self.watchlist_panel
        elif tab_name == '记录':
            self.current_panel = self.history_panel
        self.content.add_widget(self.current_panel)

    def _show_login(self, dt):
        dlg = LoginDialog(self)
        pop = Popup(
            title='', title_font=FONT_NAME, title_size=FS['lg'],
            title_color=(1,1,1,1),
            background_color=(0.1,0.1,0.15,1),
            content=dlg, size_hint=(0.92,0.92), auto_dismiss=False
        )
        dlg.parent_popup = pop
        pop.open()

    def on_connect_success(self, account, readonly=True):
        self.current_account = account
        self.push_manager = PushNotificationManager(self)
        Clock.schedule_interval(self.push_manager.check_notifications, 5)
        Clock.schedule_once(lambda dt: self._load_all(), 0.2)

    def _load_all(self):
        try:
            res = requests.get(f"{PC_SYNC_URL}/positions", timeout=2)
            real_positions = res.json()
        except:
            real_positions = []
        
        self.position_panel.update(real_positions)

        try:
            res = requests.get(f"{PC_SYNC_URL}/account", timeout=2)
            info = res.json()
        except:
            info = {
                'account_name': '同步失败',
                'account_id': 'error',
                'mode': '离线',
                'broker': '-',
                'market': '-',
                'balance': 0,
                'available': 0,
                'position_value': 0,
                'total_assets': 0
            }
        
        self.account_panel.update(info)
        self.watchlist_panel._load()

    def refresh_account(self):
        self._load_all()

    def refresh_positions(self):
        try:
            res = requests.get(f"{PC_SYNC_URL}/positions", timeout=2)
            real_positions = res.json()
        except:
            real_positions = []
        self.position_panel.update(real_positions)

    def on_disconnect(self, instance=None):
        self.current_account = None
        Clock.schedule_once(lambda dt: self._show_login(0), 0.5)


if __name__ == '__main__':
    MonitorApp().run()
