#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
移动端监控系统 v7 — 合规只读版 + 推送通知
========================================
设计原则（合法合规）：
  ✅ 手机端只能「看」和「控制开关」
  ✅ 可查看：账户信息、持仓、自选股行情、交易记录
  ✅ 可控制：策略监控的启用/暂停开关
  ✅ 新增：自动推送交易通知（电脑端执行交易时推送消息到手机端）
  ❌ 绝对禁止：下单、执行交易、后台自动交易、挂策略
  ❌ 真正的自动交易只在电脑端运行

Tab 结构：
  [账户]  — 查看账户余额、资产信息
  [持仓]  — 查看当前持仓及盈亏
  [自选股] — 管理观察列表 + 策略开关（只控制开/关，不下单）
  [记录]  — 查看电脑端已执行的交易历史（只读）

推送通知系统：
  - 电脑端执行交易时，写入 push_notifications.csv
  - 手机端每5秒轮询该文件，自动弹出通知
  - 收到买入/卖出通知后，自动切换到"记录"Tab
"""

import sys
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
from kivy.uix.tabbedpanel import TabbedPanel, TabbedPanelItem
from kivy.uix.scrollview import ScrollView
from kivy.uix.checkbox import CheckBox
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.core.text import LabelBase
from kivy.config import Config
from kivy.graphics import Color, Rectangle
import logging

# 只导入数据管理器和凭证管理器，不导入任何交易执行模块
from trade.utils.data_manager import get_data_manager
from trade.utils.credential_manager import CredentialManager
import csv
from pathlib import Path as FSPath

# 静默日志
logging.getLogger('urllib3').setLevel(logging.ERROR)
logging.getLogger('urllib3.connectionpool').setLevel(logging.ERROR)

# ==================== 全局配置 ====================
FONT_NAME = 'SimHei'
try:
    LabelBase.register(name=FONT_NAME, fn_regular='C:/Windows/Fonts/simhei.ttf')
except:
    try:
        LabelBase.register(name=FONT_NAME, fn_regular='simhei')
    except:
        pass

Config.set('graphics', 'width',  '360')
Config.set('graphics', 'height', '640')
Config.set('graphics', 'resizable', False)

# ==================== 配色方案 ====================
C = {
    'primary':    (0.10, 0.50, 0.90, 1),   # 蓝
    'success':    (0.20, 0.72, 0.32, 1),   # 绿
    'danger':     (0.90, 0.22, 0.22, 1),   # 红
    'warning':    (0.90, 0.60, 0.10, 1),   # 橙
    'info':       (0.20, 0.65, 0.80, 1),   # 青
    'bg':         (0.96, 0.96, 0.98, 1),   # 浅灰背景
    'bg_card':    (1.00, 1.00, 1.00, 1),   # 白色卡片
    'text':       (0.12, 0.12, 0.16, 1),   # 深色文字
    'text_muted': (0.55, 0.60, 0.65, 1),   # 灰色辅助文字
    'header_bg':  (0.88, 0.93, 1.00, 1),   # 表头背景
    'row_even':   (1.00, 1.00, 1.00, 1),
    'row_odd':    (0.96, 0.97, 1.00, 1),
    'buy':        (0.20, 0.72, 0.32, 1),
    'sell':       (0.90, 0.22, 0.22, 1),
    'profit':     (0.20, 0.72, 0.32, 1),
    'loss':       (0.90, 0.22, 0.22, 1),
    'on_bg':      (0.88, 0.96, 0.88, 1),   # 策略启用行背景
    'off_bg':     (0.97, 0.97, 0.97, 1),   # 策略暂停行背景
    'badge_on':   (0.20, 0.72, 0.32, 1),   # 运行中徽标
    'badge_off':  (0.65, 0.65, 0.65, 1),   # 已暂停徽标
    'white':      (1.00, 1.00, 1.00, 1),
    'divider':    (0.88, 0.88, 0.92, 1),
}

# ==================== 字体 / 尺寸 ====================
FS = {'xl': dp(16), 'lg': dp(13), 'md': dp(11), 'sm': dp(9), 'xs': dp(8), 'xxs': dp(7)}
H  = {
    'title_bar': dp(46), 'section': dp(34), 'input': dp(34),
    'btn': dp(36), 'row': dp(36), 'thead': dp(34), 'label': dp(22),
    'banner': dp(28),
}
SP = {'xs': dp(2), 'sm': dp(4), 'md': dp(6), 'lg': dp(10), 'xl': dp(16)}


# ==================== 工具函数 ====================
def set_bg(widget, rgba):
    """canvas.before 绘制矩形背景"""
    with widget.canvas.before:
        Color(*rgba)
        rect = Rectangle(pos=widget.pos, size=widget.size)
    widget.bind(pos=lambda w, v: setattr(rect, 'pos', v),
                size=lambda w, v: setattr(rect, 'size', v))


def make_btn(text, color, font_size=None, **kwargs):
    return Button(
        text=text, font_name=FONT_NAME,
        font_size=font_size or FS['md'],
        background_color=color, background_normal='',
        color=C['white'], **kwargs
    )


def make_input(hint='', password=False, text='', input_type='text', **kwargs):
    inp = TextInput(
        hint_text=hint, text=text,
        font_name=FONT_NAME, font_size=FS['sm'],
        multiline=False, password=password,
        input_type=input_type,
        background_color=C['white'],
        foreground_color=C['text'],
        cursor_color=C['primary'],
        size_hint_y=None, height=H['input'],
        halign='center',
        **kwargs
    )
    return inp


def make_label(text, font_size=None, bold=False, color=None, height=None,
               halign='center', valign='middle', **kwargs):
    lbl = Label(
        text=text, font_name=FONT_NAME,
        font_size=font_size or FS['sm'],
        bold=bold, color=color or C['text'],
        halign=halign, valign=valign,
        size_hint_y=None, height=height or H['label'],
        **kwargs
    )
    lbl.bind(size=lambda w, v: setattr(w, 'text_size', v))
    return lbl


def make_spinner(text, values, **kwargs):
    class _Opt(SpinnerOption):
        def __init__(self, **kw):
            super().__init__(**kw)
            self.font_name = FONT_NAME; self.font_size = FS['sm']
            self.background_color = C['bg']; self.background_normal = ''
            self.color = C['text']
    return Spinner(
        text=text, values=values,
        font_name=FONT_NAME, font_size=FS['sm'],
        option_cls=_Opt,
        background_color=C['white'], background_normal='',
        color=C['text'],
        size_hint_y=None, height=H['input'], **kwargs
    )


# ==================== 合规提示横幅 ====================
class ComplianceBanner(BoxLayout):
    """顶部合规提示：手机端仅供查看与控制，不执行交易"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = H['banner']
        self.padding = (SP['md'], 0)
        set_bg(self, (0.98, 0.94, 0.82, 1))  # 淡黄提示色

        icon = make_label('⚠ ', font_size=FS['xs'], bold=True,
                          color=C['warning'], height=H['banner'],
                          size_hint_x=None, width=dp(22))
        tip  = make_label(
            '手机端仅供查看与控制开关，不执行交易',
            font_size=FS['xs'], color=(0.60, 0.40, 0.00, 1),
            height=H['banner'], halign='left'
        )
        self.add_widget(icon)
        self.add_widget(tip)


# ==================== 表格组件 ====================
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
            self.add_widget(make_label(
                h, font_size=FS['sm'], bold=True,
                color=C['text'], height=H['thead'],
                size_hint_x=w
            ))


class TableRow(BoxLayout):
    def __init__(self, data, col_keys, col_weights=None, index=0, row_bg=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.size_hint_y = None
        self.height = H['row']
        self.spacing = SP['xs']
        self.padding = (SP['sm'], 0)
        self.data = data

        bg = row_bg or (C['row_even'] if index % 2 == 0 else C['row_odd'])
        set_bg(self, bg)

        n = len(col_keys)
        weights = col_weights or [1/n] * n
        for key, w in zip(col_keys, weights):
            value = str(data.get(key, '-'))
            txt_color = C['text']
            if key == '方向':
                txt_color = C['buy'] if value in ('买入', 'buy') else C['sell']
            elif key in ('盈亏', '盈亏%'):
                try:
                    v = float(value.replace('%', ''))
                    txt_color = C['profit'] if v >= 0 else C['loss']
                except:
                    pass
            lbl = Label(
                text=value, font_name=FONT_NAME,
                font_size=FS['sm'], color=txt_color,
                halign='center', valign='middle',
                size_hint_x=w, size_hint_y=1,
                shorten=True, shorten_from='right',
            )
            lbl.bind(size=lambda w2, v: setattr(w2, 'text_size', v))
            self.add_widget(lbl)


class DataTable(BoxLayout):
    """带滚动的数据表格，支持列宽权重"""
    def __init__(self, headers, col_keys=None, col_weights=None, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'vertical'
        self.headers = headers
        self.col_keys = col_keys or headers
        self.col_weights = col_weights
        self.row_count = 0

        self.header_row = TableHeader(headers, col_weights)
        self.add_widget(self.header_row)

        self.scroll = ScrollView(do_scroll_x=False, do_scroll_y=True, bar_width=dp(4))
        self.rows_layout = BoxLayout(
            orientation='vertical', size_hint_y=None, spacing=SP['xs']
        )
        self.rows_layout.bind(minimum_height=self.rows_layout.setter('height'))
        self.scroll.add_widget(self.rows_layout)
        self.add_widget(self.scroll)

    def add_row(self, data, row_bg=None):
        row = TableRow(data, self.col_keys, self.col_weights,
                       index=self.row_count, row_bg=row_bg)
        self.rows_layout.add_widget(row)
        self.row_count += 1

    def clear_rows(self):
        self.rows_layout.clear_widgets()
        self.row_count = 0






# ==================== 登录对话框（只读模式，无交易权限） ====================
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
            color=C['primary'], height=H['section']
        ))

        # 只读提示
        notice = BoxLayout(size_hint_y=None, height=dp(48),
                           padding=(SP['md'], SP['xs']))
        set_bg(notice, (0.90, 0.95, 1.00, 1))
        notice.add_widget(make_label(
            '手机端以「只读模式」连接，\n不执行任何交易操作',
            font_size=FS['xs'], color=C['primary'],
            height=dp(48), halign='center'
        ))
        self.add_widget(notice)

        def add_field(lbl_text, widget):
            self.add_widget(make_label(lbl_text, font_size=FS['xs'],
                                       color=C['text_muted'], height=H['label'],
                                       halign='left'))
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

        self.market_spinner = make_spinner('美股', ('美股',))
        add_field('市场:', self.market_spinner)

        self.api_key_input = make_input(hint='API Key（只读权限即可）')
        add_field('API Key:', self.api_key_input)

        self.secret_key_input = make_input(hint='Secret Key', password=True)
        add_field('Secret Key:', self.secret_key_input)

        pw_row = BoxLayout(size_hint_y=None, height=H['input'], spacing=SP['sm'])
        self.save_cb = CheckBox(active=True, size_hint=(None, None), size=(dp(22), dp(22)))
        pw_row.add_widget(self.save_cb)
        pw_row.add_widget(make_label('记住账户', font_size=FS['sm'],
                                     color=C['text'], halign='left'))
        self.add_widget(pw_row)

        btn_row = BoxLayout(size_hint_y=None, height=H['btn'], spacing=SP['md'])
        conn_btn = make_btn('连接（只读）', C['primary'])
        conn_btn.bind(on_press=self._on_connect)
        skip_btn = make_btn('仅演示', C['info'])
        skip_btn.bind(on_press=self._on_demo)
        btn_row.add_widget(conn_btn); btn_row.add_widget(skip_btn)
        self.add_widget(btn_row)

        self._load_last()

    def _on_broker_change(self, inst, val):
        if 'Alpaca' in val:
            self.market_spinner.values = ('美股',); self.market_spinner.text = '美股'
        elif '富途' in val or '老虎' in val:
            self.market_spinner.values = ('港股', '美股'); self.market_spinner.text = '港股'
        else:
            self.market_spinner.values = ('A股',); self.market_spinner.text = 'A股'

    def _load_last(self):
        print(f'[登录] 正在加载上次登录信息...')
        try:
            dm = get_data_manager()
            accounts = dm.load_accounts()
            print(f'[登录] 找到 {len(accounts) if accounts else 0} 个账户')
            if accounts:
                a = accounts[0]
                broker = a.get('broker', self.broker_list[0])
                market = a.get('market', '美股')
                print(f'[登录] 上次账户: {broker} - {market}')
                self.broker_spinner.text = broker
                self.market_spinner.text = market
                try:
                    creds = CredentialManager().get_credentials(a.get('account_id', ''))
                    if creds:
                        self.api_key_input.text  = creds.get('api_key', '')
                        self.secret_key_input.text = creds.get('secret_key', '')
                        print(f'[登录] 已加载凭证')
                except Exception as e:
                    print(f'[登录] 加载凭证失败: {e}')
        except Exception as e:
            print(f'[登录] 加载上次登录信息失败: {e}')
            import traceback
            traceback.print_exc()

    def _on_connect(self, inst):
        api_key    = self.api_key_input.text.strip()
        secret_key = self.secret_key_input.text.strip()
        if not api_key or not secret_key:
            self._popup('提示', '请填写 API Key 和 Secret Key', C['warning']); return

        # 尝试从现有账户中查找匹配的账户
        try:
            dm = get_data_manager()
            existing_accounts = dm.load_accounts()
            matched_account = None

            # 提取 broker 的核心名称（去掉括号和中文）
            broker_core = self.broker_spinner.text.split('(')[0].strip().lower()

            for acc in existing_accounts:
                # 检查 broker 和 api_key 是否匹配
                acc_broker = acc.get('broker', '').lower()
                acc_market = acc.get('market', '')
                acc_api_key = acc.get('api_key', '')

                # 模糊匹配：broker 名称包含核心关键词 + API key 后6位匹配 + 市场匹配
                if (broker_core in acc_broker and
                    acc_api_key.endswith(api_key[-6:]) and
                    acc_market == self.market_spinner.text):
                    matched_account = acc
                    print(f"[登录] 找到现有账户: {acc.get('account_name')} ({acc.get('account_id')[:20]}...)")
                    break

            if matched_account:
                # 使用现有账户的 account_id
                account = matched_account.copy()
            else:
                # 创建新账户
                account = {
                    'account_id':   f"{self.broker_spinner.text}_{self.market_spinner.text}_{api_key[-6:]}",
                    'account_name': f"{self.broker_spinner.text} ({self.market_spinner.text})",
                    'broker':       self.broker_spinner.text,
                    'market':       self.market_spinner.text,
                    'mode':         '只读连接',
                    'api_type':     None,
                }
                print(f"[登录] 创建新账户: {account.get('account_name')}")

            # 更新或保存账户信息
            dm.save_account(account)
            if self.save_cb.active:
                CredentialManager().save_credentials(
                    account['account_id'], {'api_key': api_key, 'secret_key': secret_key})

        except Exception as e:
            print(f"[登录] 错误: {e}")
            import traceback
            traceback.print_exc()
            account = {
                'account_id':   f"{self.broker_spinner.text}_{self.market_spinner.text}_{api_key[-6:]}",
                'account_name': f"{self.broker_spinner.text} ({self.market_spinner.text})",
                'broker':       self.broker_spinner.text,
                'market':       self.market_spinner.text,
                'mode':         '只读连接',
            }

        # 只读模式：不创建交易引擎，只保存账户信息供展示
        self.app.on_connect_success(account, readonly=True)
        self.parent_popup.dismiss()

    def _on_demo(self, inst):
        """演示模式：不需要 API，展示界面"""
        print(f'[登录] 演示模式登录...')
        try:
            account = {
                'account_id':   'demo_account',
                'account_name': '演示账户 (无真实数据)',
                'broker':       'Demo',
                'market':       '演示',
                'mode':         '演示模式',
            }
            self.app.on_connect_success(account, readonly=True)
            print(f'[登录] 演示模式登录成功')
            self.parent_popup.dismiss()
        except Exception as e:
            print(f'[登录] 演示模式登录失败: {e}')
            import traceback
            traceback.print_exc()

    def _on_cancel(self, inst):
        self.parent_popup.dismiss()
        self.app.stop()

    def _popup(self, title, msg, color):
        content = BoxLayout(orientation='vertical', spacing=SP['md'], padding=SP['lg'])
        set_bg(content, C['bg'])
        content.add_widget(make_label(msg, font_size=FS['sm'], color=color))
        ok = make_btn('确定', C['primary'], size_hint_y=None, height=H['btn'])
        content.add_widget(ok)
        pop = Popup(title=title, title_font=FONT_NAME, title_size=FS['md'],
                    content=content, size_hint=(0.88, 0.28))
        ok.bind(on_press=pop.dismiss); pop.open()


# ==================== 账户面板（只读） ====================
class AccountPanel(BoxLayout):
    """只读：查看账户余额与基本信息"""
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self.spacing = SP['sm']
        self.padding = SP['md']
        set_bg(self, C['bg'])

        self.add_widget(make_label('账户概览', font_size=FS['lg'], bold=True,
                                   color=C['primary'], height=H['section']))

        # 只读徽标
        badge = make_label('● 只读模式  |  交易由电脑端执行',
                           font_size=FS['xs'], color=C['text_muted'],
                           height=dp(20))
        self.add_widget(badge)

        self.table = DataTable(
            headers=['字段', '值'],
            col_keys=['字段', '值'],
            col_weights=[0.35, 0.65]
        )
        self.add_widget(self.table)

        btn_row = BoxLayout(size_hint_y=None, height=H['btn'], spacing=SP['md'])
        r = make_btn('刷新', C['primary'])
        r.bind(on_press=lambda _: self.app.refresh_account())
        o = make_btn('断开', C['danger'])
        o.bind(on_press=self._on_disconnect)
        btn_row.add_widget(r); btn_row.add_widget(o)
        self.add_widget(btn_row)

    def update(self, info):
        self.table.clear_rows()

        def fmt_money(v):
            try: return f"${float(v):,.2f}"
            except: return str(v) if v else 'N/A'

        rows = [
            ('账户名称', info.get('account_name', 'N/A')),
            ('账户ID',   info.get('account_id',   'N/A')),
            ('连接模式', info.get('mode',          'N/A')),
            ('券商',     info.get('broker',        'N/A')),
            ('市场',     info.get('market',        'N/A')),
            ('账户余额', fmt_money(info.get('balance', 0))),
            ('可用资金', fmt_money(info.get('available', 0))),
            ('持仓市值', fmt_money(info.get('position_value', 0))),
            ('总资产',   fmt_money(info.get('total_assets', 0))),
            ('数据时间', datetime.now().strftime('%H:%M:%S')),
        ]
        for f, v in rows:
            self.table.add_row({'字段': f, '值': v})

    def _on_disconnect(self, inst):
        content = BoxLayout(orientation='vertical', spacing=SP['md'], padding=SP['lg'])
        set_bg(content, C['bg'])
        content.add_widget(make_label('确定断开账户连接？', font_size=FS['sm'], color=C['text']))
        content.add_widget(make_label('（不影响电脑端的交易运行）',
                                      font_size=FS['xs'], color=C['text_muted']))
        btn_row = BoxLayout(size_hint_y=None, height=H['btn'], spacing=SP['md'])
        cancel  = make_btn('取消', C['text_muted'])
        confirm = make_btn('断开', C['danger'])
        btn_row.add_widget(cancel); btn_row.add_widget(confirm)
        content.add_widget(btn_row)
        pop = Popup(title='断开连接', title_font=FONT_NAME, title_size=FS['md'],
                    content=content, size_hint=(0.88, 0.34))
        cancel.bind(on_press=pop.dismiss)
        confirm.bind(on_press=lambda _: (pop.dismiss(), self.app.on_disconnect()))
        pop.open()


# ==================== 持仓面板（只读） ====================
class PositionPanel(BoxLayout):
    """只读：查看当前持仓及盈亏，不提供操作入口"""
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self.spacing = SP['sm']
        self.padding = SP['md']
        set_bg(self, C['bg'])

        hdr = BoxLayout(size_hint_y=None, height=H['section'])
        hdr.add_widget(make_label('当前持仓', font_size=FS['lg'], bold=True,
                                  color=C['primary'], height=H['section'],
                                  halign='left'))
        hdr.add_widget(make_label('（只读）', font_size=FS['xs'],
                                  color=C['text_muted'], height=H['section'],
                                  size_hint_x=None, width=dp(50)))
        self.add_widget(hdr)

        self.table = DataTable(
            headers=['代码', '数量', '成本', '现价', '盈亏%'],
            col_keys=['代码', '数量', '成本', '现价', '盈亏%'],
            col_weights=[0.25, 0.15, 0.18, 0.18, 0.24]
        )
        self.add_widget(self.table)

        r = make_btn('刷新持仓', C['primary'], size_hint_y=None, height=H['btn'])
        r.bind(on_press=lambda _: self.app.refresh_positions())
        self.add_widget(r)

    def update(self, positions):
        self.table.clear_rows()
        if not positions:
            self.table.add_row({'代码': '暂无持仓', '数量': '-', '成本': '-',
                                '现价': '-', '盈亏%': '-'})
            return
        for p in positions:
            pct = p.get('pnl_percent', 0)
            try:    pct_f = float(pct)
            except: pct_f = 0
            row_bg = C['on_bg'] if pct_f >= 0 else (1.00, 0.94, 0.94, 1)
            self.table.add_row({
                '代码':  p.get('symbol', '-'),
                '数量':  str(p.get('quantity', 0)),
                '成本':  f"{float(p.get('avg_price', 0)):.2f}",
                '现价':  f"{float(p.get('current_price', 0)):.2f}",
                '盈亏%': f"{pct_f:+.2f}%",
            }, row_bg=row_bg)


# ==================== 监控台面板 ====================
class WatchlistPanel(BoxLayout):
    """
    监控台 - 只读监控列表
    ─────────────────────────────
    手机端可以：
      ✅ 查看监控列表（只读）
      ✅ 查看策略运行状态
    手机端不能：
      ❌ 添加/删除监控标的
      ❌ 修改策略开关
      ❌ 执行任何交易操作
    所有操作由电脑端完成。
    """
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self.spacing = SP['sm']
        self.padding = SP['md']
        set_bg(self, C['bg'])

        # 标题行 - 字体放大
        hdr = BoxLayout(size_hint_y=None, height=H['section'])
        hdr.add_widget(make_label('监控台', font_size=FS['xl'], bold=True,
                                  color=C['primary'], height=H['section'], halign='center'))
        self.add_widget(hdr)

        # 说明文字 - 字体放大
        tip = make_label(
            '监控列表由电脑端管理，手机端仅查看',
            font_size=FS['sm'], color=C['text_muted'],
            height=dp(26), halign='center'
        )
        self.add_widget(tip)

        # 表格：代码 | 备注 | 状态（只读）
        self.table = DataTable(
            headers=['代码', '备注', '状态'],
            col_keys=['代码', '备注', '状态'],
            col_weights=[0.25, 0.50, 0.25]
        )
        self.add_widget(self.table)

        # 刷新按钮
        r = make_btn('刷新监控列表', C['primary'], size_hint_y=None, height=H['btn'])
        r.bind(on_press=lambda _: self._load())
        self.add_widget(r)

        Clock.schedule_once(lambda dt: self._load(), 0.5)

    def _load(self):
        """加载监控列表（只读）"""
        try:
            dm = get_data_manager()
            mons = dm.load_monitors(
                self.app.current_account.get('account_id') if self.app.current_account else None
            )
            self.table.clear_rows()
            for m in mons:
                sym = m.get('symbol', '')
                if not sym: continue
                # 读取状态（存储在 status 字段）
                status = m.get('status', '启用')
                if status in ('暂停', '已暂停', 'paused', 'off'):
                    status_text = '已暂停'
                else:
                    status_text = '运行中'
                self._add_watchlist_row(sym, m.get('name', sym), status_text)
        except Exception as e:
            print(f'[监控台] 加载失败: {e}')

    def _add_watchlist_row(self, sym, note, status_text):
        """添加一行（只读状态显示）"""
        row = BoxLayout(
            orientation='horizontal',
            size_hint_y=None, height=H['row'],
            spacing=SP['xs'], padding=(SP['sm'], 0)
        )
        # 根据状态设置背景色
        bg = C['on_bg'] if status_text == '运行中' else C['off_bg']
        set_bg(row, bg)

        # 代码列 - 字体放大，居中
        lbl_sym = Label(
            text=sym, font_name=FONT_NAME, font_size=FS['md'],
            color=C['text'], halign='center', valign='middle',
            size_hint_x=0.25, size_hint_y=1,
        )
        lbl_sym.bind(size=lambda w, v: setattr(w, 'text_size', v))

        # 备注列 - 字体放大，居中
        lbl_note = Label(
            text=note, font_name=FONT_NAME, font_size=FS['sm'],
            color=C['text_muted'], halign='center', valign='middle',
            size_hint_x=0.50, size_hint_y=1,
            shorten=True, shorten_from='right',
        )
        lbl_note.bind(size=lambda w, v: setattr(w, 'text_size', v))

        # 状态列 - 字体放大，居中
        lbl_status = Label(
            text=status_text, font_name=FONT_NAME, font_size=FS['md'],
            color=C['success'] if status_text == '运行中' else C['text_muted'],
            halign='center', valign='middle',
            size_hint_x=0.25, size_hint_y=1,
        )
        lbl_status.bind(size=lambda w, v: setattr(w, 'text_size', v))

        row.add_widget(lbl_sym)
        row.add_widget(lbl_note)
        row.add_widget(lbl_status)
        self.table.rows_layout.add_widget(row)
        self.table.row_count += 1

    def _on_toggle(self, btn):
        """切换策略开关——仅写入标志位，不执行任何交易"""
        sym = btn._sym
        row = btn._row
        is_on = self._strategy_states.get(sym, True)
        new_state = not is_on
        self._strategy_states[sym] = new_state

        # 更新按钮文字与颜色
        btn.text = '运行中' if new_state else '已暂停'
        btn.background_color = C['badge_on'] if new_state else C['badge_off']



# ==================== 交易记录面板（只读） ====================

class TradeHistoryPanel(BoxLayout):
    """
    只读：查看电脑端已执行的交易历史
    手机端无法在此发起任何新订单
    """
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app
        self.orientation = 'vertical'
        self.spacing = SP['sm']
        self.padding = SP['md']
        set_bg(self, C['bg'])

        hdr = BoxLayout(size_hint_y=None, height=H['section'])
        hdr.add_widget(make_label('交易记录', font_size=FS['lg'], bold=True,
                                  color=C['primary'], height=H['section'], halign='left'))
        hdr.add_widget(make_label('（电脑端执行）', font_size=FS['xs'],
                                  color=C['text_muted'], height=H['section'],
                                  size_hint_x=None, width=dp(90)))
        self.add_widget(hdr)

        # 日期选择
        date_row = BoxLayout(size_hint_y=None, height=H['input'], spacing=SP['sm'])
        self.date_input = make_input(
            hint='日期 YYYYMMDD', text=datetime.now().strftime('%Y%m%d')
        )
        load_btn = make_btn('查询', C['primary'],
                            size_hint=(None, None), size=(dp(58), H['input']))
        load_btn.bind(on_press=self._on_load)
        date_row.add_widget(self.date_input); date_row.add_widget(load_btn)
        self.add_widget(date_row)

        self.table = DataTable(
            headers=['时间', '代码', '方向', '价格', '数量', '状态'],
            col_keys=['时间', '代码', '方向', '价格', '数量', '状态'],
            col_weights=[0.18, 0.18, 0.14, 0.18, 0.16, 0.16]
        )
        self.add_widget(self.table)

        # 统计摘要行
        self.summary_lbl = make_label('', font_size=FS['xs'],
                                      color=C['text_muted'], height=dp(20))
        self.add_widget(self.summary_lbl)

        Clock.schedule_once(lambda dt: self._load_logs(), 0.8)

    def _on_load(self, inst):
        self._load_logs()

    def _load_logs(self):
        self.table.clear_rows()
        date = self.date_input.text.strip()
        try:
            dm   = get_data_manager()
            logs = dm.get_trade_logs(date)
            if not logs:
                self.table.add_row({
                    '时间': '暂无记录', '代码': '-', '方向': '-',
                    '价格': '-', '数量': '-', '状态': '-'
                })
                self.summary_lbl.text = f'{date}  共 0 笔'
                return
            buy_cnt = sell_cnt = 0
            for log in logs:
                action = log.get('action', '')
                direction = '买入' if action in ('buy', '买入') else '卖出'
                if direction == '买入': buy_cnt += 1
                else: sell_cnt += 1
                status = log.get('status', '-')
                row_bg = C['on_bg'] if status in ('filled', '已成交') else None
                t = log.get('time', '-')
                if len(t) > 8: t = t[-8:]   # 只显示时间部分
                self.table.add_row({
                    '时间': t,
                    '代码': log.get('symbol', '-'),
                    '方向': direction,
                    '价格': log.get('price', '-'),
                    '数量': log.get('quantity', '-'),
                    '状态': status,
                }, row_bg=row_bg)
            self.summary_lbl.text = (f'{date}  共 {len(logs)} 笔  '
                                     f'买入 {buy_cnt}  卖出 {sell_cnt}')
        except Exception as e:
            print(f'[History] 加载失败: {e}')
            self.summary_lbl.text = '加载失败，请重试'


# ==================== 推送通知管理器 ====================
class PushNotificationManager:
    """
    推送通知系统：
    - 电脑端执行交易时写入 push_notifications.csv
    - 手机端定期轮询该文件，显示未读通知
    """
    def __init__(self, app):
        self.app = app
        self.notif_file = FSPath(__file__).parent.parent / 'push_notifications.csv'
        self.notif_file.touch(exist_ok=True)  # 确保文件存在
        self.shown_ids = set()  # 已显示的通知ID

    def check_notifications(self, dt):
        """
        检查新通知（由 Clock 轮询调用）
        推送通知弹窗功能已禁用，仅记录日志

        Args:
            dt: 距离上次调用的时间间隔（Kivy Clock 回调参数）
        """
        try:
            if not self.notif_file.exists():
                return

            with open(self.notif_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)

            new_notifs = []
            for row in rows:
                notif_id = row.get('id', '')
                if notif_id and notif_id not in self.shown_ids:
                    self.shown_ids.add(notif_id)
                    new_notifs.append(row)

            if new_notifs:
                # 推送通知弹窗已禁用，仅打印日志
                latest = new_notifs[-1]
                print(f'[推送通知] 收到新通知: {latest.get("message", "")}')
                # 不再调用 self._show_popup(latest)

        except Exception as e:
            print(f'[推送通知] 检查失败: {e}')

    def _show_popup(self, notif):
        """显示通知弹窗"""
        msg_type = notif.get('type', 'info')
        title = notif.get('title', '交易通知')
        message = notif.get('message', '')
        timestamp = notif.get('timestamp', '')

        # 根据类型选择颜色
        color_map = {
            'buy': C['buy'],
            'sell': C['sell'],
            'error': C['danger'],
            'warning': C['warning'],
            'info': C['primary']
        }
        color = color_map.get(msg_type, C['primary'])

        # 构建弹窗内容
        content = BoxLayout(orientation='vertical', spacing=SP['md'], padding=SP['lg'])
        set_bg(content, C['bg'])

        # 时间戳
        if timestamp:
            time_lbl = make_label(timestamp, font_size=FS['xs'], color=C['text_muted'])
            content.add_widget(time_lbl)

        # 消息内容
        msg_lbl = Label(
            text=message,
            font_name=FONT_NAME,
            font_size=FS['sm'],
            color=color,
            halign='left',
            valign='middle',
            size_hint_y=None,
            height=dp(80),
            text_size=(dp(300), None)
        )
        content.add_widget(msg_lbl)

        # 确定按钮
        ok = make_btn('确定', C['primary'], size_hint_y=None, height=H['btn'])
        content.add_widget(ok)

        pop = Popup(
            title=title,
            title_font=FONT_NAME,
            title_size=FS['md'],
            content=content,
            size_hint=(0.88, 0.48),
            title_color=C['primary']
        )
        ok.bind(on_press=pop.dismiss)
        pop.open()

        # 切换到"记录"Tab，方便用户查看
        if msg_type in ('buy', 'sell'):
            Clock.schedule_once(lambda dt: self._switch_to_history(), 0.5)

    def _switch_to_history(self):
        """切换到交易记录Tab"""
        try:
            self.app.tabs.tab_list[3].content._on_load(None)  # 索引3是"记录"Tab
            self.app.tabs.tab_list[3].trigger_action()
        except:
            pass


# ==================== 主应用 ====================
class MonitorApp(App):
    """手机端监控应用 — 合规只读版"""

    def build(self):
        root = BoxLayout(orientation='vertical')
        set_bg(root, C['bg'])

        # 顶部标题栏
        title_bar = BoxLayout(size_hint_y=None, height=H['title_bar'],
                              padding=(SP['lg'], 0))
        set_bg(title_bar, C['primary'])
        # 左侧标题
        title_lbl = Label(
            text='交易监控  v7',
            font_name=FONT_NAME, font_size=FS['lg'],
            bold=True, color=C['white'],
            halign='left', valign='middle',
            size_hint_x=0.6,
        )
        title_lbl.bind(size=lambda w, v: setattr(w, 'text_size', v))
        # 右侧只读徽标
        readonly_badge = Label(
            text='📱 只读模式',
            font_name=FONT_NAME, font_size=FS['xs'],
            color=(0.90, 0.95, 1.00, 1),
            halign='right', valign='middle',
            size_hint_x=0.4,
        )
        readonly_badge.bind(size=lambda w, v: setattr(w, 'text_size', v))
        title_bar.add_widget(title_lbl)
        title_bar.add_widget(readonly_badge)
        root.add_widget(title_bar)

        # 合规提示横幅
        root.add_widget(ComplianceBanner())

        # Tab 面板
        class _TabItem(TabbedPanelItem):
            def __init__(self, **kw):
                super().__init__(**kw)
                self.font_name = FONT_NAME; self.font_size = FS['sm']

        self.tabs = TabbedPanel(do_default_tab=False, tab_pos='top_left')

        def add_tab(name, panel):
            tab = _TabItem(text=name)
            tab.add_widget(panel)
            self.tabs.add_widget(tab)
            return panel

        self.account_panel   = add_tab('账户',  AccountPanel(self))
        self.position_panel  = add_tab('持仓',  PositionPanel(self))
        self.watchlist_panel = add_tab('监控台', WatchlistPanel(self))
        self.history_panel   = add_tab('记录',  TradeHistoryPanel(self))

        root.add_widget(self.tabs)

        self.current_account = None
        self.push_manager = None  # 推送通知管理器

        self.current_account = None
        self.push_manager = None  # 推送通知管理器

        Clock.schedule_once(self._show_login, 0)
        return root

    def _show_login(self, dt):
        dlg = LoginDialog(self)
        pop = Popup(title='连接账户', title_font=FONT_NAME, title_size=FS['lg'],
                    content=dlg, size_hint=(0.92, 0.92), auto_dismiss=False)
        dlg.parent_popup = pop
        pop.open()

    def on_connect_success(self, account, readonly=True):
        print(f'[连接成功] 开始处理登录...')
        self.current_account = account
        name = account.get('account_name', 'N/A')
        print(f'[连接成功] {name}  只读模式={readonly}')

        try:
            # 初始化推送通知管理器，并开始轮询（每5秒检查一次）
            self.push_manager = PushNotificationManager(self)
            Clock.schedule_interval(self.push_manager.check_notifications, 5)
            print(f'[连接成功] 推送通知管理器已初始化')

            Clock.schedule_once(lambda dt: self._load_all(), 0.2)
            print(f'[连接成功] 已调度数据加载')
        except Exception as e:
            print(f'[连接成功] 错误: {e}')
            import traceback
            traceback.print_exc()

    def _load_all(self):
        """加载所有只读数据"""
        print(f'[加载] 开始加载数据...')

        # 持仓（从 CSV 读取，电脑端负责写入）
        # 先加载持仓，因为账户的总资产需要持仓市值
        position_value = 0
        try:
            print(f'[加载] 正在加载持仓...')
            dm   = get_data_manager()
            account_id = self.current_account.get('account_id', '')
            print(f'[加载] 账户ID: {account_id}')
            rows = dm.load_positions(account_id)
            print(f'[加载] 持仓记录数: {len(rows) if rows else 0}')

            positions = [{
                'symbol':        r.get('symbol', '-'),
                'quantity':      r.get('quantity', 0),
                'avg_price':     r.get('avg_cost', 0),
                'current_price': r.get('current_price', 0),
                'pnl':           r.get('profit_loss', 0),
                'pnl_percent':   r.get('profit_ratio', 0),
            } for r in (rows or [])]

            # 计算持仓市值
            for r in (rows or []):
                qty = r.get('quantity', 0)
                price = r.get('current_price', 0)
                try:
                    position_value += float(qty) * float(price)
                except:
                    pass

            self.position_panel.update(positions)
            print(f'[持仓] 加载 {len(positions)} 条记录，持仓市值: ${position_value:,.2f}')
        except Exception as e:
            print(f'[持仓] 加载失败: {e}')
            import traceback
            traceback.print_exc()
            self.position_panel.update([])
            positions = []

        # 账户信息（直接从 CSV 构建，不调用交易引擎）
        try:
            print(f'[加载] 正在加载账户信息...')
            dm = get_data_manager()
            accs = dm.load_accounts()
            print(f'[加载] 账户列表长度: {len(accs) if accs else 0}')

            acc_data = {}
            if accs:
                for a in accs:
                    if a.get('account_id') == self.current_account.get('account_id'):
                        acc_data = a
                        print(f'[加载] 找到匹配账户: {a.get("account_name")}')
                        break

            if not acc_data:
                print(f'[加载] 警告: 未找到匹配账户，使用默认值')
                acc_data = {
                    'total_balance': 0,
                    'available_balance': 0,
                }

            balance = float(acc_data.get('total_balance', 0))
            available = float(acc_data.get('available_balance', 0))
            total_assets = balance + position_value

            info = {
                'account_name':   self.current_account.get('account_name', 'N/A'),
                'account_id':     self.current_account.get('account_id', 'N/A'),
                'mode':           self.current_account.get('mode', '只读连接'),
                'broker':         self.current_account.get('broker', 'N/A'),
                'market':         self.current_account.get('market', 'N/A'),
                'balance':        balance,
                'available':      available,
                'position_value': position_value,
                'total_assets':   total_assets,
            }
            self.account_panel.update(info)
            print(f'[账户] 余额: ${balance:,.2f}, 持仓市值: ${position_value:,.2f}, 总资产: ${total_assets:,.2f}')
        except Exception as e:
            print(f'[账户] 加载失败: {e}')
            import traceback
            traceback.print_exc()
            # 即使失败也显示基本信息
            try:
                info = {
                    'account_name':   self.current_account.get('account_name', 'N/A'),
                    'account_id':     self.current_account.get('account_id', 'N/A'),
                    'mode':           self.current_account.get('mode', '只读连接'),
                    'broker':         self.current_account.get('broker', 'N/A'),
                    'market':         self.current_account.get('market', 'N/A'),
                    'balance':        0,
                    'available':      0,
                    'position_value': position_value,
                    'total_assets':   position_value,
                }
                self.account_panel.update(info)
            except Exception as e2:
                print(f'[账户] 更新UI失败: {e2}')

        # 监控台列表
        try:
            print(f'[加载] 正在加载监控台...')
            self.watchlist_panel._load()
            print(f'[加载] 监控台加载完成')
        except Exception as e:
            print(f'[监控台] 加载失败: {e}')
            import traceback
            traceback.print_exc()

        print(f'[加载] 数据加载完成')

    def refresh_account(self):
        self._load_all()

    def refresh_positions(self):
        try:
            dm   = get_data_manager()
            rows = dm.load_positions(self.current_account.get('account_id'))
            positions = [{
                'symbol':        r.get('symbol', '-'),
                'quantity':      r.get('quantity', 0),
                'avg_price':     r.get('avg_cost', 0),
                'current_price': r.get('current_price', 0),
                'pnl':           r.get('profit_loss', 0),
                'pnl_percent':   r.get('profit_ratio', 0),
            } for r in rows]
            self.position_panel.update(positions)
        except Exception as e:
            print(f'[持仓] 刷新失败: {e}')

    def on_disconnect(self):
        self.current_account = None
        Clock.schedule_once(lambda dt: self._show_login(0), 0.5)


if __name__ == '__main__':
    print('=' * 60)
    print('交易监控系统 v7  手机端合规只读版  360×640')
    print('本版本绝对不执行任何交易操作')
    print('真正的自动交易由电脑端独立运行')
    print('=' * 60)
    MonitorApp().run()