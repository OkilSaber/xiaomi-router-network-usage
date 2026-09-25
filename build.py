#!/usr/bin/env python3
"""
Script de compilation multiplateforme (Linux, macOS, Windows) pour Xiaomi Wi-Fi Dashboard.
Utilise PyInstaller pour générer un exécutable autonome et un package d'archive de release.
"""

import os
import sys
import shutil
import platform
import subprocess
import tarfile
import zipfile

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DIST_DIR = os.path.join(PROJECT_DIR, "dist")
BUILD_DIR = os.path.join(PROJECT_DIR, "build")
ENTRY_POINT = os.path.join(PROJECT_DIR, "xiaomi_wifi_dashboard.py")
APP_NAME = "xiaomi_dashboard"

def check_pyinstaller():
    try:
        import PyInstaller
        print(f"✅ PyInstaller {PyInstaller.__version__} détecté.")
    except ImportError:
        print("❌ PyInstaller n'est pas installé dans l'environnement Python courant.")
        print("Installation via: pip install pyinstaller")
        sys.exit(1)

def build_executable():
    print(f"🔨 Compilation pour la plateforme : {platform.system()} ({platform.machine()})...")
    
    # Séparateur pour --add-data (';' sous Windows, ':' sous Unix)
    sep = ";" if platform.system() == "Windows" else ":"
    static_src = os.path.join(PROJECT_DIR, "static")
    add_data_arg = f"{static_src}{sep}static"

    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        "--onefile",
        "--noconfirm",
        "--clean",
        "--add-data", add_data_arg,
        "--hidden-import", "mac_vendor_lookup",
        "--hidden-import", "requests",
        "--hidden-import", "urllib3",
        "--hidden-import", "flask",
        "--hidden-import", "webview",
    ]

    # Options spécifiques selon l'OS
    current_os = platform.system()
    if current_os == "Windows":
        # Mode fenêtré sans invite de commande
        pyinstaller_cmd.extend(["--windowed"])
    elif current_os == "Darwin":
        pyinstaller_cmd.extend(["--windowed"])
    elif current_os == "Linux":
        # Sur Linux on garde la console ou windowed
        pass

    pyinstaller_cmd.append(ENTRY_POINT)

    print("Exécution de : " + " ".join(pyinstaller_cmd))
    subprocess.check_call(pyinstaller_cmd, cwd=PROJECT_DIR)
    print("✅ Compilation de l'exécutable terminée avec succès.")

def package_release():
    current_os = platform.system().lower()
    machine = platform.machine().lower()
    if machine in ["x86_64", "amd64"]:
        arch = "x86_64"
    elif machine in ["aarch64", "arm64"]:
        arch = "arm64"
    else:
        arch = machine

    os.makedirs(DIST_DIR, exist_ok=True)

    if current_os == "linux":
        exe_path = os.path.join(DIST_DIR, APP_NAME)
        archive_name = f"xiaomi-dashboard-linux-{arch}.tar.gz"
        archive_path = os.path.join(DIST_DIR, archive_name)
        
        print(f"📦 Création de l'archive Release : {archive_path}...")
        with tarfile.open(archive_path, "w:gz") as tar:
            if os.path.exists(exe_path):
                tar.add(exe_path, arcname=APP_NAME)
            if os.path.exists(os.path.join(PROJECT_DIR, "xiaomi-dashboard.desktop")):
                tar.add(os.path.join(PROJECT_DIR, "xiaomi-dashboard.desktop"), arcname="xiaomi-dashboard.desktop")
            if os.path.exists(os.path.join(PROJECT_DIR, "static")):
                tar.add(os.path.join(PROJECT_DIR, "static"), arcname="static")
            if os.path.exists(os.path.join(PROJECT_DIR, "config.example.json")):
                tar.add(os.path.join(PROJECT_DIR, "config.example.json"), arcname="config.example.json")
            if os.path.exists(os.path.join(PROJECT_DIR, "README.md")):
                tar.add(os.path.join(PROJECT_DIR, "README.md"), arcname="README.md")
        print(f"🎉 Release Linux créée : {archive_path}")

    elif current_os == "windows":
        exe_name = f"{APP_NAME}.exe"
        exe_path = os.path.join(DIST_DIR, exe_name)
        archive_name = f"xiaomi-dashboard-windows-{arch}.zip"
        archive_path = os.path.join(DIST_DIR, archive_name)

        print(f"📦 Création de l'archive Release : {archive_path}...")
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            if os.path.exists(exe_path):
                zipf.write(exe_path, arcname=exe_name)
            if os.path.exists(os.path.join(PROJECT_DIR, "config.example.json")):
                zipf.write(os.path.join(PROJECT_DIR, "config.example.json"), arcname="config.example.json")
            if os.path.exists(os.path.join(PROJECT_DIR, "README.md")):
                zipf.write(os.path.join(PROJECT_DIR, "README.md"), arcname="README.md")
        print(f"🎉 Release Windows créée : {archive_path}")

    elif current_os == "darwin":
        exe_path = os.path.join(DIST_DIR, APP_NAME)
        app_path = os.path.join(DIST_DIR, f"{APP_NAME}.app")
        archive_name = f"xiaomi-dashboard-macos-{arch}.zip"
        archive_path = os.path.join(DIST_DIR, archive_name)

        print(f"📦 Création de l'archive Release : {archive_path}...")
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            if os.path.exists(app_path):
                for root, dirs, files in os.walk(app_path):
                    for file in files:
                        full_path = os.path.join(root, file)
                        rel_path = os.path.relpath(full_path, DIST_DIR)
                        zipf.write(full_path, arcname=rel_path)
            elif os.path.exists(exe_path):
                zipf.write(exe_path, arcname=APP_NAME)
            if os.path.exists(os.path.join(PROJECT_DIR, "config.example.json")):
                zipf.write(os.path.join(PROJECT_DIR, "config.example.json"), arcname="config.example.json")
            if os.path.exists(os.path.join(PROJECT_DIR, "README.md")):
                zipf.write(os.path.join(PROJECT_DIR, "README.md"), arcname="README.md")
        print(f"🎉 Release macOS créée : {archive_path}")

def main():
    check_pyinstaller()
    build_executable()
    package_release()

if __name__ == "__main__":
    main()
