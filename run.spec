from PyInstaller.utils.hooks import collect_data_files, collect_submodules
from PyInstaller.utils.hooks import copy_metadata

datas = [("C:/Users/mohse/anaconda3/envs/insights/Lib/site-packages/streamlit", "./streamlit")]
datas += collect_data_files("streamlit")
datas += copy_metadata("streamlit")
datas += [('app.py', '.')]

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=['streamlit'] + collect_submodules('streamlit'),
    hookspath=['./hooks'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MagicCSV',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)