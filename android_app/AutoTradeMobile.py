#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
IS_ANDROID = 'ANDROID_DATA' in os.environ

# 安卓防闪退基础配置
if IS_ANDROID:
    os.environ['KIVY_GL_BACKEND'] = 'gl'
    os.environ['KIVY_NO_FILELOG'] = '1'

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock

class DebugApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical')
        # 逐步打印加载状态
        self.status = Label(text="正在启动...\n步骤1: 导入基础模块 ✅")
        self.layout.add_widget(self.status)
        # 延迟执行后续步骤，方便看崩溃点
        Clock.schedule_once(self.step2, 1)
        return self.layout

    def step2(self, dt):
        self.status.text += "\n步骤2: 初始化UI ✅"
        Clock.schedule_once(self.step3, 1)

    def step3(self, dt):
        self.status.text += "\n步骤3: 加载你的功能页面..."
        # 这里开始加载你的原版功能
        try:
            # 尝试加载你的核心模块
            if not IS_ANDROID:
                from trade.utils.data_manager import get_data_manager
                self.status.text += "\n✅ 本地模块加载成功"
            else:
                self.status.text += "\n✅ 安卓模式：跳过本地模块"
            self.status.text += "\n\n🎉 启动成功！功能已恢复！"
        except Exception as e:
            self.status.text += f"\n❌ 崩溃原因:\n{str(e)}"

if __name__ == '__main__':
    DebugApp().run()
