# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

# Collect all Textual submodules + CSS/theme data files
_textual_datas, _textual_binaries, _textual_hiddenimports = collect_all("textual")

# Collect rich (dynamic unicode data submodules)
_rich_datas, _rich_binaries, _rich_hiddenimports = collect_all("rich")

a = Analysis(
    ["burnBot.py"],
    pathex=[],
    binaries=_textual_binaries + _rich_binaries,
    datas=_textual_datas + _rich_datas,
    hiddenimports=[
        *_textual_hiddenimports,
        *_rich_hiddenimports,
        "keyrings.alt",
        "keyrings.alt.file",
        "selenium.webdriver.chrome.webdriver",
        "selenium.webdriver.chrome.service",
        "selenium.webdriver.chrome.options",
        "selenium.webdriver.common.service",
        "selenium.webdriver.common.utils",
        "selenium.webdriver.remote.remote_connection",
        "selenium.webdriver.support.ui",
        "selenium.webdriver.support.expected_conditions",
        "selenium.webdriver.support.wait",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pyautogui", "pygetwindow"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="slowburnbot",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
