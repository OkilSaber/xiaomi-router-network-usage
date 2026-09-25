# 🚀 Xiaomi Router Network Usage & Dashboard

Application de surveillance en temps réel du trafic réseau et des appareils connectés pour les routeurs Xiaomi (Mi WiFi).

Disponible sous forme d'application de bureau autonome (GUI native) avec basculement automatique en serveur Web local.

---

## ✨ Fonctionnalités

- 📊 **Graphique de bande passante en temps réel** : suivi live des débits montant (upload) et descendant (download) via Chart.js.
- 📱 **Gestion des appareils connectés** :
  - Détection automatique des adresses MAC, IP et débits instantanés.
  - Identification automatique des constructeurs (base OUI IEEE).
  - Attribution et sauvegarde d'**alias personnalisés** par appareil.
- 🖥️ **Multiplateforme** : compatible **Linux**, **macOS** et **Windows**.
- 🌐 **Double mode d'affichage** :
  - Fenêtre applicative native légère via `pywebview`.
  - Mode serveur web (`http://localhost:5000`) avec option `--server` ou repli automatique headless.
- 🔒 **Gestion sécurisée des identifiants** : configuration séparée via variables d'environnement ou fichier `config.json`.

---

## ⚙️ Configuration

Copiez le fichier exemple de configuration :

```bash
cp config.example.json config.json
```

Modifiez `config.json` avec l'adresse IP et le mot de passe de votre routeur :

```json
{
  "router_ip": "192.168.31.1",
  "router_password": "VOTRE_MOT_DE_PASSE"
}
```

> **Astuce** : Vous pouvez également utiliser les variables d'environnement `ROUTER_IP` et `ROUTER_PASSWORD` :
> ```bash
> export ROUTER_IP="192.168.31.1"
> export ROUTER_PASSWORD="votre_mot_de_passe"
> ```

---

## 🚀 Utilisation

### Option 1 : Lancement depuis les sources Python

1. **Installer les dépendances** :
   ```bash
   pip install -r requirements.txt
   ```

2. **Lancer l'application** :
   ```bash
   python xiaomi_wifi_dashboard.py
   ```

3. **Options en ligne de commande** :
   ```bash
   # Lancer uniquement en serveur web (sans fenêtre native)
   python xiaomi_wifi_dashboard.py --server

   # Afficher l'aide
   python xiaomi_wifi_dashboard.py --help
   ```

---

## 🔨 Compilation / Build

Le projet inclut un script de build universel ainsi que des raccourcis par plateforme.

### Prérequis de compilation

```bash
pip install -r requirements.txt
pip install pyinstaller
```

### Linux
```bash
./build_linux.sh
# ou
python build.py
```
L'exécutable autonome `xiaomi_dashboard` ainsi que l'archive `dist/xiaomi-dashboard-linux-x86_64.tar.gz` seront générés.

### macOS
```bash
./build_macos.sh
# ou
python build.py
```
Génère l'archive `dist/xiaomi-dashboard-macos-x86_64.zip`.

### Windows
```cmd
build_windows.bat
rem ou
python build.py
```
Génère l'archive `dist/xiaomi-dashboard-windows-x86_64.zip`.

---

## 🧹 Nettoyage du projet

Pour supprimer les dossiers temporaires de build (`dist/`, `build/`, `*.spec`, caches Python) :

```bash
# Linux / macOS
./clean.sh

# Windows
clean.bat

# Multiplateforme (Python)
python clean.py
```

> **Astuce** : Ajoutez `--all` pour nettoyer également les fichiers de configuration locaux (`config.json`, `device_aliases.json`).

---

## 📄 Licence

Ce projet est sous licence GPLv3. Voir le fichier [LICENSE](LICENSE) pour plus de détails.
