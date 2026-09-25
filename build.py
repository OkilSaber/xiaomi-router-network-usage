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

def check_pip():
    """Vérifie si pip est disponible sans jamais tenter de l'installer."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False

def check_dependencies():
    """Vérifie si tous les modules requis sont déjà importables."""
    required_modules = [
        ("PyInstaller", "pyinstaller"),
        ("flask", "Flask"),
        ("requests", "requests"),
        ("urllib3", "urllib3"),
        ("mac_vendor_lookup", "mac-vendor-lookup"),
        ("webview", "pywebview"),
    ]
    missing = []
    for mod_name, pkg_name in required_modules:
        try:
            __import__(mod_name)
        except ImportError:
            missing.append(pkg_name)
    return missing

def ensure_environment():
    print("🔍 Vérification de l'environnement de build...")

    # 1. Vérification stricte de pip (PAS d'installation de pip si absent)
    if not check_pip():
        print("❌ Erreur : 'pip' n'est pas disponible dans cet environnement Python.")
        print(f"   Interpréteur utilisé : {sys.executable}")
        print("   Veuillez installer pip manuellement ou activer un environnement virtuel le contenant.")
        sys.exit(1)
    print("✅ pip détecté.")

    # 2. Vérification des dépendances et de PyInstaller
    missing = check_dependencies()
    if missing:
        print(f"📦 Dépendances manquantes détectées : {', '.join(missing)}")
        req_file = os.path.join(PROJECT_DIR, "requirements.txt")
        pip_cmd = [sys.executable, "-m", "pip", "install"]
        if os.path.exists(req_file):
            pip_cmd.extend(["-r", req_file])
        pip_cmd.append("pyinstaller")

        print("⏳ Installation automatique des dépendances manquantes via pip...")
        subprocess.check_call(pip_cmd)
        print("✅ Toutes les dépendances et PyInstaller ont été installés avec succès.")
    else:
        print("✅ Toutes les dépendances (requirements.txt + PyInstaller) sont déjà satisfaites.")

def build_executable():
    print(f"🔨 Compilation pour la plateforme : {platform.system()} ({platform.machine()})...")
    
    # Séparateur pour --add-data (';' sous Windows, ':' sous Unix)
    sep = ";" if platform.system() == "Windows" else ":"
    static_src = os.path.join(PROJECT_DIR, "static")
    add_data_arg = f"{static_src}{sep}static"

    current_os = platform.system()
    mode_arg = "--onedir" if current_os == "Darwin" else "--onefile"

    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--name", APP_NAME,
        mode_arg,
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
    icon_win = os.path.join(PROJECT_DIR, "assets", "icon.ico")
    icon_mac = os.path.join(PROJECT_DIR, "assets", "icon.icns")

    if current_os == "Windows":
        # Mode fenêtré sans invite de commande
        pyinstaller_cmd.extend(["--windowed"])
        if os.path.exists(icon_win):
            pyinstaller_cmd.extend(["--icon", icon_win])
    elif current_os == "Darwin":
        # Sur macOS, mode onedir + windowed crée un vrai bundle .app natif instantané
        pyinstaller_cmd.extend(["--windowed", "--osx-bundle-identifier", "com.xiaomi.dashboard"])
        if os.path.exists(icon_mac):
            pyinstaller_cmd.extend(["--icon", icon_mac])
    elif current_os == "Linux":
        # Sur Linux on garde la console ou windowed
        pass

    pyinstaller_cmd.append(ENTRY_POINT)

    print("Exécution de : " + " ".join(pyinstaller_cmd))
    subprocess.check_call(pyinstaller_cmd, cwd=PROJECT_DIR)

    if current_os == "Darwin":
        app_path = os.path.join(DIST_DIR, f"{APP_NAME}.app")
        info_plist_path = os.path.join(app_path, "Contents", "Info.plist")
        if os.path.exists(info_plist_path):
            import plistlib
            with open(info_plist_path, "rb") as f:
                pl = plistlib.load(f)
            pl["NSAppTransportSecurity"] = {"NSAllowsArbitraryLoads": True}
            pl["CFBundleDisplayName"] = "Xiaomi Wi-Fi Dashboard"
            with open(info_plist_path, "wb") as f:
                plistlib.dump(pl, f)

        try:
            subprocess.run(["codesign", "--force", "--deep", "--sign", "-", app_path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

        # Nettoyage et création d'un wrapper script CLI dist/xiaomi_dashboard
        cli_wrapper = os.path.join(DIST_DIR, APP_NAME)
        if os.path.isdir(cli_wrapper):
            shutil.rmtree(cli_wrapper)
        elif os.path.exists(cli_wrapper):
            os.remove(cli_wrapper)

        with open(cli_wrapper, "w") as f:
            f.write('#!/bin/bash\n')
            f.write('DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"\n')
            f.write(f'exec "$DIR/{APP_NAME}.app/Contents/MacOS/{APP_NAME}" "$@"\n')
        os.chmod(cli_wrapper, 0o755)

    print("✅ Compilation de l'exécutable terminée avec succès.")

def create_macos_dmg(app_path, dmg_path, volume_name="Xiaomi Wi-Fi Dashboard"):
    if not os.path.exists(app_path):
        print(f"⚠️ Impossible de créer le DMG : {app_path} introuvable.")
        return

    if os.path.exists(dmg_path):
        try:
            os.remove(dmg_path)
        except Exception:
            pass

    print(f"📀 Création de l'installateur DMG macOS : {dmg_path}...")

    # 1. Tentative avec create-dmg (présentation soignée et signature)
    create_dmg_bin = shutil.which("create-dmg")
    if create_dmg_bin:
        try:
            print("  Utilisation de 'create-dmg' pour une présentation optimale...")
            cmd = [
                create_dmg_bin,
                "--overwrite",
                "--no-version-in-filename",
                "--dmg-title", volume_name,
                app_path,
                DIST_DIR
            ]
            subprocess.check_call(cmd)
            default_dmg = os.path.join(DIST_DIR, f"{volume_name}.dmg")
            if os.path.exists(default_dmg):
                if os.path.abspath(default_dmg) != os.path.abspath(dmg_path):
                    shutil.move(default_dmg, dmg_path)
                print(f"🎉 Installateur DMG macOS créé avec succès : {dmg_path}")
                return
        except Exception as e:
            print(f"  ⚠️ create-dmg a échoué ({e}), basculement sur hdiutil...")

    # 2. Repli natif macOS via hdiutil
    staging_dir = os.path.join(DIST_DIR, ".dmg_staging")
    if os.path.exists(staging_dir):
        shutil.rmtree(staging_dir)
    os.makedirs(staging_dir, exist_ok=True)

    dest_app = os.path.join(staging_dir, os.path.basename(app_path))
    shutil.copytree(app_path, dest_app, symlinks=True)

    # Lien symbolique vers /Applications pour drag & drop
    try:
        os.symlink("/Applications", os.path.join(staging_dir, "Applications"))
    except Exception:
        pass

    try:
        hdiutil_cmd = [
            "hdiutil", "create",
            "-volname", volume_name,
            "-srcfolder", staging_dir,
            "-ov",
            "-format", "UDZO",
            dmg_path
        ]
        subprocess.check_call(hdiutil_cmd)
        print(f"🎉 Installateur DMG macOS créé avec succès via hdiutil : {dmg_path}")
    except Exception as e:
        print(f"❌ Échec de création du DMG : {e}")
    finally:
        if os.path.exists(staging_dir):
            shutil.rmtree(staging_dir)

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
            if os.path.exists(os.path.join(PROJECT_DIR, "assets", "icon.png")):
                tar.add(os.path.join(PROJECT_DIR, "assets", "icon.png"), arcname="icon.png")
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
            if os.path.exists(os.path.join(PROJECT_DIR, "assets", "icon.ico")):
                zipf.write(os.path.join(PROJECT_DIR, "assets", "icon.ico"), arcname="icon.ico")
            if os.path.exists(os.path.join(PROJECT_DIR, "config.example.json")):
                zipf.write(os.path.join(PROJECT_DIR, "config.example.json"), arcname="config.example.json")
            if os.path.exists(os.path.join(PROJECT_DIR, "README.md")):
                zipf.write(os.path.join(PROJECT_DIR, "README.md"), arcname="README.md")
        print(f"🎉 Release Windows créée : {archive_path}")

    elif current_os == "darwin":
        exe_path = os.path.join(DIST_DIR, APP_NAME)
        app_path = os.path.join(DIST_DIR, f"{APP_NAME}.app")
        dmg_name = f"xiaomi-dashboard-macos-{arch}.dmg"
        dmg_path = os.path.join(DIST_DIR, dmg_name)
        archive_name = f"xiaomi-dashboard-macos-{arch}.zip"
        archive_path = os.path.join(DIST_DIR, archive_name)

        # Création de l'installateur .dmg
        create_macos_dmg(app_path, dmg_path)

        # Création de l'archive .zip
        print(f"📦 Création de l'archive Release ZIP : {archive_path}...")
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
        print(f"🎉 Release macOS ZIP créée : {archive_path}")

def main():
    ensure_environment()
    build_executable()
    package_release()

if __name__ == "__main__":
    main()
