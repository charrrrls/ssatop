# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['main.py',
    'Controllers/FileUploadWidgetController.py',
    'Controllers/SettingsWidgetController.py',
    'Controllers/SourceDetectionWidgetController.py',
    'Controllers/WaveDisplayWidgetController.py',
    'Models/Config.py',
    'Models/TaskRunner.py',
    'Models/TraceFile.py',
    'Services/find_time.py',
    'Services/ssatop.py',
    'Views/FileUploadWidget.py',
    'Views/SettingsWidget.py',
    'Views/SourceDetectionWidget.py',
    'Views/WaveDisplayWidget.py',],
    pathex=[],
    binaries=[],
    datas=[('config.yaml','.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='main',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='main',
)
