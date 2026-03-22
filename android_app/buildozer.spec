[app]

title = AutoTrade Mobile
package.domain = org.autotrade
source.include_exts = py,png,jpg,kv,json,csv
source.exclude_dirs = tests,bin,lib,data,.git

[buildozer]

# Version
version = 1.0.0

# App info
author = AutoTrade Team
description = Stock trading monitoring mobile app (read-only)

# Android
android.api = 33
android.minapi = 24
android.ndk = 25b
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WRITE_EXTERNAL_STORAGE,READ_EXTERNAL_STORAGE

# Orientation
orientation = portrait
fullscreen = 0

# Kivy
requirements = python3,kivy==2.3.1,pyjnius,android,requests,pandas

# Icon
icon.filename = assets/icon.png
presplash.filename = assets/splash.png
