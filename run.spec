import os
import site
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# Get the site-packages directory
site_packages = site.getsitepackages()[0]

# Define the path to the textcomplete package
textcomplete_path = os.path.join(site_packages, 'textcomplete')

# Print debugging information
print(f"Python version: {sys.version}")
print(f"Site packages directory: {site_packages}")
print(f"Expected textcomplete path: {textcomplete_path}")
print(f"textcomplete path exists: {os.path.exists(textcomplete_path)}")

if not os.path.exists(textcomplete_path):
    import textcomplete
    print(f"Actual textcomplete path: {os.path.dirname(textcomplete.__file__)}")

datas = [("C:/Users/mohse/anaconda3/envs/insights/Lib/site-packages/streamlit", "./streamlit")]
datas += collect_data_files("streamlit")
datas += collect_data_files("textcomplete")

# Only add textcomplete path if it exists
if os.path.exists(textcomplete_path):
    datas += [(textcomplete_path, 'textcomplete')]
else:
    print("Warning: textcomplete path not found. It will not be included in the bundle.")

datas += [('app.py', '.')]

# Add streamlit metadata
from PyInstaller.utils.hooks import copy_metadata
datas += copy_metadata("streamlit")

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=['streamlit', 'textcomplete'] + 
                   collect_submodules('streamlit') + 
                   collect_submodules('textcomplete'),
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