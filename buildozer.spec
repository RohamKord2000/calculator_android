[app]
title = Calculator
package.name = calculator
package.domain = org.example
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1
requirements = python3,kivy==2.3.0
orientation = portrait
fullscreen = 0

# Android
android.api = 33
android.minapi = 21
android.ndk = 25b
android.ndk_api = 21
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

# Pin python-for-android to a release that works with Kivy 2.3.0 / Python 3.11
# (the newest p4a uses Python 3.14, which Kivy 2.3.0 does not support)
p4a.branch = v2024.01.21

[buildozer]
log_level = 2
warn_on_root = 1
