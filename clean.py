#!/usr/bin/env python3
"""
Script de nettoyage multiplateforme (Linux, macOS, Windows) pour Xiaomi Wi-Fi Dashboard.
Supprime les artefacts de build, fichiers de cache et fichiers temporaires.
"""

import os
import sys
import shutil
import glob

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))

# Dossiers à supprimer
DIRS_TO_REMOVE = [
    "build",
    "dist",
    "cache",
    ".cache",
    "__pycache__",
]

# Fichiers / motifs à supprimer
FILES_PATTERNS_TO_REMOVE = [
    "*.spec",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    "*.log",
    ".DS_Store",
    "Thumbs.db",
    "xiaomi_dashboard",
    "xiaomi_dashboard.exe",
]

def clean(deep=False):
    print("🧹 Nettoyage du projet Xiaomi Wi-Fi Dashboard...")
    deleted_count = 0

    # 1. Suppression des dossiers de premier niveau
    for dirname in DIRS_TO_REMOVE:
        dirpath = os.path.join(PROJECT_DIR, dirname)
        if os.path.exists(dirpath):
            try:
                shutil.rmtree(dirpath)
                print(f"  🗑️  Dossier supprimé : {dirname}/")
                deleted_count += 1
            except Exception as e:
                print(f"  ⚠️  Erreur suppression dossier {dirname}: {e}")

    # 2. Suppression récursive des dossiers __pycache__ (hors venv et .git)
    ignored_roots = {".git", "bin", "lib", "lib64", "venv", ".venv", "env"}
    for root, dirs, _ in os.walk(PROJECT_DIR, topdown=True):
        dirs[:] = [d for d in dirs if d not in ignored_roots]
        for d in dirs:
            if d == "__pycache__":
                full_d = os.path.join(root, d)
                try:
                    shutil.rmtree(full_d)
                    print(f"  🗑️  Cache Python supprimé : {os.path.relpath(full_d, PROJECT_DIR)}")
                    deleted_count += 1
                except Exception as e:
                    print(f"  ⚠️  Erreur suppression {full_d}: {e}")

    # 3. Suppression des fichiers selon les motifs
    for pattern in FILES_PATTERNS_TO_REMOVE:
        for filepath in glob.glob(os.path.join(PROJECT_DIR, pattern)):
            if os.path.isfile(filepath) or os.path.islink(filepath):
                try:
                    os.remove(filepath)
                    print(f"  🗑️  Fichier supprimé : {os.path.basename(filepath)}")
                    deleted_count += 1
                except Exception as e:
                    print(f"  ⚠️  Erreur suppression {filepath}: {e}")

    # 4. Nettoyage approfondi optionnel (--deep / --all)
    if deep:
        sensitive_files = ["config.json", "device_aliases.json"]
        for f in sensitive_files:
            fp = os.path.join(PROJECT_DIR, f)
            if os.path.exists(fp):
                try:
                    os.remove(fp)
                    print(f"  🗑️  [Deep Clean] Configuration supprimée : {f}")
                    deleted_count += 1
                except Exception as e:
                    print(f"  ⚠️  Erreur suppression {f}: {e}")

    if deleted_count == 0:
        print("✨ Le projet est déjà totalement propre !")
    else:
        print(f"✅ Nettoyage terminé : {deleted_count} élément(s) supprimé(s).")

if __name__ == "__main__":
    deep_mode = "--all" in sys.argv or "--deep" in sys.argv
    clean(deep=deep_mode)
