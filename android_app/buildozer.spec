[app]

title = AutoTrade Mobile

package.domain = org.autotrade

source.include_exts = py,png,jpg,kv,json,csv
source.exclude_dirs = tests,bin,lib,data,.git

[buildozer]

# 版本信息
version = 1.0.0

# 应用信息
author = AutoTrade Team
description = Stock trading monitoring mobile app (read-only)
website = https://www.autotrade.com

# Android 配置
android.api = 33
android.minapi = 24
android.ndk = 25b

# 权限
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# 图标
icon.filename = assets/icon.png
presplash.filename = assets/splash.png

# 方向（竖屏）
orientation = portrait

# 全屏
fullscreen = 0

# OUYA 支持
ouya.category = GAME

# 界面
android.wakelock = True
android.logcat_filters = Python:*

# Kivy 版本
requirements = python3,kivy==2.3.1,pyjnius,android,requests,pandas

# iOS 配置（暂时不需要）
ios.kivy_ios_url = 'https://github.com/kivy/kivy-ios'
ios.kivy_ios_commit = 'master'

# 构建工具
android.archs = 'armeabi-v7a,arm64-v8a'

# 布局
layout = 'internal'

# 调试
android.accept_sdk_license = True

# 黑名单（可能冲突的库）
android.blacklist = ''
android.allow_shared_libs = True

# AAR 库
android.aars = []

# Gradle
android.gradle_dependencies = ''

# AndroidManifest 模板
