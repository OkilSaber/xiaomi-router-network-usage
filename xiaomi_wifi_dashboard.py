import os
import sys
import time
import requests
import urllib3
import hashlib
import random
import re
import json
from flask import Flask, render_template_string, jsonify, request, send_from_directory
from mac_vendor_lookup import MacLookup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Chemins pour compatibilité binaire PyInstaller et exécution directe
if getattr(sys, 'frozen', False):
    BUNDLE_DIR = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(sys.executable)))
    EXE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BUNDLE_DIR = os.path.dirname(os.path.abspath(__file__))
    EXE_DIR = BUNDLE_DIR

STATIC_DIR = os.path.join(BUNDLE_DIR, "static")

def get_data_dir():
    """Détermine le répertoire pour les fichiers persistants (alias, config)."""
    if os.environ.get("XIAOMI_DASHBOARD_DATA_DIR"):
        path = os.environ.get("XIAOMI_DASHBOARD_DATA_DIR")
        os.makedirs(path, exist_ok=True)
        return path
    # Si le répertoire de l'exécutable est inscriptible, on l'utilise
    try:
        test_file = os.path.join(EXE_DIR, ".write_test")
        with open(test_file, 'w') as f:
            f.write("1")
        os.remove(test_file)
        return EXE_DIR
    except Exception:
        # Répertoire standard utilisateur
        if sys.platform.startswith('win'):
            base = os.environ.get('APPDATA', os.path.expanduser('~'))
        else:
            base = os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config'))
        user_dir = os.path.join(base, 'xiaomi-dashboard')
        os.makedirs(user_dir, exist_ok=True)
        return user_dir

DATA_DIR = get_data_dir()

# Stockage persistant des alias d'appareils
ALIASES_FILE = os.path.join(EXE_DIR, "device_aliases.json")
if not os.path.exists(ALIASES_FILE):
    cwd_aliases = os.path.join(os.getcwd(), "device_aliases.json")
    if os.path.exists(cwd_aliases):
        ALIASES_FILE = cwd_aliases
    else:
        ALIASES_FILE = os.path.join(DATA_DIR, "device_aliases.json")

# Chargement de la configuration
def load_config():
    config = {
        "router_ip": "192.168.31.1",
        "router_password": "SaberEtIrama213216"
    }
    
    # 1. Recherche du fichier config.json dans EXE_DIR, CWD, DATA_DIR
    for loc in [
        os.path.join(EXE_DIR, "config.json"),
        os.path.join(os.getcwd(), "config.json"),
        os.path.join(DATA_DIR, "config.json")
    ]:
        if os.path.exists(loc):
            try:
                with open(loc, 'r', encoding='utf-8') as f:
                    file_cfg = json.load(f)
                    if file_cfg.get("router_ip"):
                        config["router_ip"] = file_cfg["router_ip"]
                    if file_cfg.get("router_password"):
                        config["router_password"] = file_cfg["router_password"]
                break
            except Exception as e:
                print(f"Avertissement lors de la lecture de {loc}: {e}")

    # 2. Les variables d'environnement priment
    if os.environ.get("ROUTER_IP"):
        config["router_ip"] = os.environ["ROUTER_IP"]
    if os.environ.get("ROUTER_PASSWORD"):
        config["router_password"] = os.environ["ROUTER_PASSWORD"]

    return config

CONFIG = load_config()
ROUTER_IP = CONFIG["router_ip"]
ROUTER_PASSWORD = CONFIG["router_password"]
CURRENT_STOK = None

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path='/static')

mac_lookup = MacLookup()
VENDOR_CACHE = {}

def get_vendor(mac):
    if not mac:
        return "Inconnu"
    mac_upper = mac.upper()
    if mac_upper in VENDOR_CACHE:
        return VENDOR_CACHE[mac_upper]
    try:
        vendor = mac_lookup.lookup(mac)
    except Exception:
        vendor = "Inconnu"
    VENDOR_CACHE[mac_upper] = vendor
    return vendor

session = requests.Session()

def get_aliases():
    if os.path.exists(ALIASES_FILE):
        try:
            with open(ALIASES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_alias(mac, name):
    aliases = get_aliases()
    aliases[mac] = name
    try:
        with open(ALIASES_FILE, 'w', encoding='utf-8') as f:
            json.dump(aliases, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde de l'alias : {e}")

def get_stok_pure_python():
    print("Authentification auprès du routeur Xiaomi (Pure Python)...")
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    res = session.get(f'https://{ROUTER_IP}/cgi-bin/luci/web', headers=headers, verify=False, timeout=5)
    
    mac_match = re.search(r"deviceId = '(.*?)'", res.text)
    mac = mac_match.group(1) if mac_match else 'f8:59:71:7d:a5:37'
    
    key_match = re.search(r"key: '(.*?)'", res.text)
    key = key_match.group(1) if key_match else 'a2ffa5c9be07488bbb04a3a47d3c5f6a'
    
    nonce = f'0_{mac}_{int(time.time())}_{int(random.random() * 10000)}'
    hash1 = hashlib.sha256((ROUTER_PASSWORD + key).encode()).hexdigest()
    pwd = hashlib.sha256((nonce + hash1).encode()).hexdigest()
    
    login_url = f'https://{ROUTER_IP}/cgi-bin/luci/api/xqsystem/login'
    resp = session.post(
        login_url,
        headers=headers,
        data={'username': 'admin', 'logtype': '2', 'password': pwd, 'nonce': nonce},
        verify=False,
        timeout=5
    )
    
    data = resp.json()
    if data.get('code') == 0:
        return data['token']
    else:
        raise Exception(f"Connexion échouée: {data}")

def fetch_devices():
    global CURRENT_STOK
    
    if not CURRENT_STOK:
        CURRENT_STOK = get_stok_pure_python()
        
    url = f"https://{ROUTER_IP}/cgi-bin/luci/;stok={CURRENT_STOK}/api/misystem/devicelist"
    resp = session.get(url, verify=False, timeout=5)
    data = resp.json()
    
    if data.get('code') == 401:
        print("Token expiré, renouvellement...")
        CURRENT_STOK = get_stok_pure_python()
        url = f"https://{ROUTER_IP}/cgi-bin/luci/;stok={CURRENT_STOK}/api/misystem/devicelist"
        resp = session.get(url, verify=False, timeout=5)
        data = resp.json()
        
    if data.get('code') != 0:
        raise Exception(f"Erreur API Routeur: {data.get('msg', 'Inconnue')}")
        
    aliases = get_aliases()
    devices = []
    total_down = 0.0
    total_up = 0.0
    
    for dev in data.get('list', []):
        ip_str = "N/A"
        down_bps = 0.0
        up_bps = 0.0
        
        ip_info = dev.get('ip', [])
        if isinstance(ip_info, list) and len(ip_info) > 0:
            if isinstance(ip_info[0], dict):
                ip_str = ip_info[0].get('ip', 'N/A')
                down_bps = float(ip_info[0].get('downspeed', 0))
                up_bps = float(ip_info[0].get('upspeed', 0))
            else:
                ip_str = str(ip_info[0])
        elif isinstance(ip_info, str):
            ip_str = ip_info
            
        if down_bps == 0.0 and up_bps == 0.0:
            stats = dev.get('statistics', {})
            if isinstance(stats, dict):
                down_bps = float(stats.get('downspeed', 0))
                up_bps = float(stats.get('upspeed', 0))
        
        total_down += down_bps
        total_up += up_bps
        
        down_mbps = round((down_bps * 8) / 1_000_000, 2)
        up_mbps = round((up_bps * 8) / 1_000_000, 2)
        
        raw_mac = dev.get('mac', '')
        vendor = get_vendor(raw_mac)
        base_name = dev.get('name', 'Appareil Inconnu')
        
        devices.append({
            'mac': raw_mac,
            'name': aliases.get(raw_mac, base_name),
            'raw_name': base_name,
            'vendor': vendor,
            'ip': ip_str,
            'downspeed': down_mbps,
            'upspeed': up_mbps
        })
        
    total_down_mbps = round((total_down * 8) / 1_000_000, 2)
    total_up_mbps = round((total_up * 8) / 1_000_000, 2)
    
    return {
        "devices": devices,
        "total_down": total_down_mbps,
        "total_up": total_up_mbps,
        "device_count": len(devices)
    }

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Xiaomi Wi-Fi Dashboard</title>
    <link rel="icon" type="image/png" href="/static/icon.png">
    <script src="/static/chart.min.js"></script>
    <script>
        if (typeof Chart === 'undefined') {
            document.write('<script src="https://cdn.jsdelivr.net/npm/chart.js"><\\/script>');
        }
    </script>
    <style>
        :root {
            --primary: #ff6900;
            --primary-hover: #e05d00;
            --primary-bg: #fff7f2;
            --down-color: #0d6efd;
            --down-bg: #edf4fe;
            --up-color: #198754;
            --up-bg: #edf8f2;
            --bg-color: #f4f6f9;
            --card-bg: #ffffff;
            --text-main: #212529;
            --text-muted: #6c757d;
            --border-color: #e9ecef;
            --shadow-sm: 0 2px 6px rgba(0,0,0,0.04);
            --shadow-md: 0 8px 24px rgba(0,0,0,0.06);
            --radius: 12px;
        }

        * { box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            margin: 0;
            padding: 24px;
            color: var(--text-main);
            user-select: none;
        }

        .container {
            max-width: 1300px;
            margin: 0 auto;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--card-bg);
            padding: 16px 24px;
            border-radius: var(--radius);
            box-shadow: var(--shadow-sm);
            margin-bottom: 20px;
        }

        .header-title {
            display: flex;
            align-items: center;
            gap: 14px;
        }

        .header-title svg {
            width: 38px;
            height: 38px;
            flex-shrink: 0;
        }

        h1 {
            font-size: 22px;
            font-weight: 700;
            margin: 0;
            color: var(--text-main);
            letter-spacing: -0.3px;
        }

        .header-controls {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .control-group {
            display: flex;
            align-items: center;
            gap: 8px;
            background: var(--bg-color);
            padding: 6px 12px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            color: var(--text-muted);
        }

        select.custom-select {
            padding: 6px 10px;
            border-radius: 6px;
            border: 1px solid var(--border-color);
            background: white;
            font-size: 13px;
            font-weight: 600;
            color: var(--text-main);
            outline: none;
            cursor: pointer;
        }

        .btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            border: none;
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .btn-primary {
            background: var(--primary);
            color: white;
        }
        .btn-primary:hover {
            background: var(--primary-hover);
        }

        .btn-secondary {
            background: #e9ecef;
            color: #495057;
        }
        .btn-secondary:hover {
            background: #dee2e6;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 18px;
            margin-bottom: 20px;
        }

        .stat-card {
            background: var(--card-bg);
            border-radius: var(--radius);
            padding: 20px 24px;
            box-shadow: var(--shadow-sm);
            border: 1px solid var(--border-color);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .stat-info h3 {
            margin: 0;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: var(--text-muted);
            font-weight: 600;
        }

        .stat-info .value {
            font-size: 30px;
            font-weight: 800;
            margin-top: 6px;
            line-height: 1.1;
        }

        .stat-info .unit {
            font-size: 15px;
            font-weight: 600;
            color: var(--text-muted);
            margin-left: 2px;
        }

        .stat-card.down .value { color: var(--down-color); }
        .stat-card.up .value { color: var(--up-color); }
        .stat-card.devices .value { color: var(--primary); }

        .stat-icon {
            width: 48px;
            height: 48px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
        }
        .stat-card.down .stat-icon { background: var(--down-bg); color: var(--down-color); }
        .stat-card.up .stat-icon { background: var(--up-bg); color: var(--up-color); }
        .stat-card.devices .stat-icon { background: var(--primary-bg); color: var(--primary); }

        .chart-card {
            background: var(--card-bg);
            border-radius: var(--radius);
            padding: 20px;
            box-shadow: var(--shadow-sm);
            border: 1px solid var(--border-color);
            margin-bottom: 20px;
        }

        .chart-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .chart-header h2 {
            font-size: 15px;
            font-weight: 700;
            margin: 0;
            color: var(--text-main);
        }

        .chart-wrapper {
            position: relative;
            height: 240px;
            width: 100%;
        }

        .table-card {
            background: var(--card-bg);
            border-radius: var(--radius);
            box-shadow: var(--shadow-sm);
            border: 1px solid var(--border-color);
            overflow: hidden;
        }

        .table-toolbar {
            padding: 16px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
        }

        .search-box {
            position: relative;
            width: 320px;
        }

        .search-box input {
            width: 100%;
            padding: 8px 12px 8px 34px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
            font-size: 13px;
            background: var(--bg-color);
            outline: none;
            transition: border 0.15s ease;
        }
        .search-box input:focus {
            border-color: var(--primary);
            background: white;
        }

        .search-box svg {
            position: absolute;
            left: 10px;
            top: 50%;
            transform: translateY(-50%);
            width: 16px;
            height: 16px;
            fill: var(--text-muted);
        }

        table {
            width: 100%;
            border-collapse: collapse;
        }

        th {
            background-color: #fafbfc;
            padding: 12px 18px;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            color: var(--text-muted);
            font-weight: 700;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }

        td {
            padding: 14px 18px;
            font-size: 13px;
            border-bottom: 1px solid var(--border-color);
            vertical-align: middle;
        }

        tr:last-child td {
            border-bottom: none;
        }

        tr:hover td {
            background-color: #fafbfc;
        }

        .device-cell {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .device-avatar {
            width: 34px;
            height: 34px;
            border-radius: 8px;
            background: #eef2f6;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            color: #495057;
            font-size: 13px;
            flex-shrink: 0;
        }

        .device-title {
            font-weight: 600;
            color: var(--text-main);
            font-size: 14px;
        }

        .badge-vendor {
            background: #eef2f5;
            color: #495057;
            font-size: 11px;
            font-weight: 600;
            padding: 3px 8px;
            border-radius: 6px;
            display: inline-block;
        }

        .mono {
            font-family: SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 12px;
            color: #555;
        }

        .speed-badge {
            display: inline-block;
            font-weight: 700;
            font-size: 13px;
        }
        .speed-badge.down { color: var(--down-color); }
        .speed-badge.up { color: var(--up-color); }

        .btn-rename {
            background: #f1f3f5;
            border: 1px solid #dee2e6;
            color: #495057;
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
        }
        .btn-rename:hover {
            background: var(--primary);
            border-color: var(--primary);
            color: white;
        }

        .footer-status {
            margin-top: 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 12px;
            color: var(--text-muted);
            padding: 0 4px;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 6px;
            background: #28a745;
            box-shadow: 0 0 0 rgba(40, 167, 69, 0.4);
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0% { box-shadow: 0 0 0 0 rgba(40, 167, 69, 0.6); }
            70% { box-shadow: 0 0 0 6px rgba(40, 167, 69, 0); }
            100% { box-shadow: 0 0 0 0 rgba(40, 167, 69, 0); }
        }

        .status-dot.error {
            background: #dc3545;
            animation: none;
        }

        .spinner {
            width: 14px;
            height: 14px;
            border: 2px solid rgba(255, 255, 255, 0.4);
            border-top: 2px solid white;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            display: none;
        }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }

        #error-banner {
            display: none;
            background: #fdf2f2;
            color: #b02a37;
            border: 1px solid #f8d7da;
            padding: 12px 18px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 13px;
        }

        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
        }

        .modal-card {
            background: white;
            border-radius: 14px;
            width: 440px;
            max-width: 90%;
            box-shadow: var(--shadow-md);
            overflow: hidden;
        }

        .modal-header {
            padding: 18px 24px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .modal-header h3 {
            margin: 0;
            font-size: 16px;
            font-weight: 700;
        }

        .modal-body {
            padding: 20px 24px;
        }

        .modal-body label {
            display: block;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-muted);
            margin-bottom: 6px;
        }

        .modal-input {
            width: 100%;
            padding: 10px 12px;
            border-radius: 8px;
            border: 1px solid #ced4da;
            font-size: 14px;
            outline: none;
            margin-bottom: 14px;
        }
        .modal-input:focus {
            border-color: var(--primary);
            box-shadow: 0 0 0 3px rgba(255, 105, 0, 0.15);
        }

        .modal-meta {
            font-size: 12px;
            color: var(--text-muted);
            background: var(--bg-color);
            padding: 8px 12px;
            border-radius: 6px;
            margin-bottom: 4px;
        }

        .modal-footer {
            padding: 14px 24px;
            border-top: 1px solid var(--border-color);
            background: #fafbfc;
            display: flex;
            justify-content: flex-end;
            gap: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-title">
                <svg viewBox="0 0 256 256">
                    <rect width="256" height="256" rx="56" fill="#ff6900"/>
                    <g fill="#FFFFFF">
                        <circle cx="128" cy="194" r="14"/>
                        <path d="M82 152a65 65 0 0 1 92 0" stroke="#FFFFFF" stroke-width="16" stroke-linecap="round" fill="none"/>
                        <path d="M48 118a113 113 0 0 1 160 0" stroke="#FFFFFF" stroke-width="16" stroke-linecap="round" fill="none"/>
                        <path d="M14 84a161 161 0 0 1 228 0" stroke="#FFFFFF" stroke-width="16" stroke-linecap="round" fill="none"/>
                    </g>
                </svg>
                <div>
                    <h1>Xiaomi Wi-Fi Dashboard</h1>
                    <div style="font-size: 12px; color: var(--text-muted); margin-top: 2px;">Routeur 192.168.31.1 &bull; Surveillance active</div>
                </div>
            </div>

            <div class="header-controls">
                <div class="control-group">
                    <span>Rafraîchissement :</span>
                    <select id="refreshRate" class="custom-select" onchange="changeRefreshRate()">
                        <option value="0">Manuel</option>
                        <option value="1">1 sec</option>
                        <option value="2">2 sec</option>
                        <option value="5">5 sec</option>
                    </select>
                </div>
                <button class="btn btn-primary" onclick="fetchDevices()">
                    <div id="loader" class="spinner"></div>
                    <span id="btn-text">Rafraîchir</span>
                </button>
            </div>
        </div>

        <div id="error-banner"></div>

        <div class="stats-grid">
            <div class="stat-card down">
                <div class="stat-info">
                    <h3>Téléchargement Total</h3>
                    <div class="value" id="total-down">0.00 <span class="unit">Mb/s</span></div>
                </div>
                <div class="stat-icon">↓</div>
            </div>

            <div class="stat-card up">
                <div class="stat-info">
                    <h3>Envoi Total</h3>
                    <div class="value" id="total-up">0.00 <span class="unit">Mb/s</span></div>
                </div>
                <div class="stat-icon">↑</div>
            </div>

            <div class="stat-card devices">
                <div class="stat-info">
                    <h3>Appareils Actifs</h3>
                    <div class="value" id="device-count">0 <span class="unit">en ligne</span></div>
                </div>
                <div class="stat-icon" style="background: var(--primary-bg); color: var(--primary);">📶</div>
            </div>
        </div>

        <div class="chart-card">
            <div class="chart-header">
                <h2>Bande Passante en Temps Réel</h2>
                <div id="chart-sub" style="font-size: 12px; color: var(--text-muted);">Mise à jour en direct (30 points)</div>
            </div>
            <div class="chart-wrapper">
                <canvas id="speedChart"></canvas>
            </div>
        </div>

        <div class="table-card">
            <div class="table-toolbar">
                <div class="search-box">
                    <svg viewBox="0 0 24 24"><path d="M15.5 14h-.79l-.28-.27A6.471 6.471 0 0 0 16 9.5 6.5 6.5 0 1 0 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
                    <input type="text" id="search-input" placeholder="Filtrer par nom, IP, MAC ou marque..." onkeyup="filterDevices()">
                </div>
                <div style="font-size: 12px; color: var(--text-muted);" id="filtered-count">Trié par débit descendant</div>
            </div>

            <table>
                <thead>
                    <tr>
                        <th>Appareil</th>
                        <th>Constructeur</th>
                        <th>Adresse IP</th>
                        <th>Adresse MAC</th>
                        <th>Téléchargement</th>
                        <th>Envoi</th>
                        <th style="text-align: right;">Action</th>
                    </tr>
                </thead>
                <tbody id="devices-body">
                    <tr><td colspan="7" style="text-align:center; padding: 30px; color: var(--text-muted);">Initialisation de la surveillance...</td></tr>
                </tbody>
            </table>
        </div>

        <div class="footer-status">
            <div>
                <span class="status-dot" id="status-indicator"></span>
                <span id="status-label">Connecté au routeur Xiaomi</span>
            </div>
            <div id="last-updated">Dernière mise à jour : En cours...</div>
        </div>
    </div>

    <!-- Rename Modal Dialog -->
    <div class="modal-overlay" id="renameModal" onclick="closeModalOnBackdrop(event)">
        <div class="modal-card">
            <div class="modal-header">
                <h3>Renommer l'appareil</h3>
                <button onclick="closeModal()" style="border:none; background:none; font-size: 18px; cursor:pointer; color: #888;">&times;</button>
            </div>
            <div class="modal-body">
                <div class="modal-meta" id="modal-mac">MAC : --</div>
                <div style="height: 12px;"></div>
                <label for="modal-input">Nom personnalisé :</label>
                <input type="text" id="modal-input" class="modal-input" placeholder="Ex: PC Bureau, iPhone Alice..." onkeydown="handleModalKey(event)">
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="closeModal()">Annuler</button>
                <button class="btn btn-primary" onclick="submitRename()">Sauvegarder</button>
            </div>
        </div>
    </div>

    <script>
        function getStoredRefreshRate() {
            try {
                if (typeof localStorage !== 'undefined' && localStorage) {
                    const saved = localStorage.getItem('refreshRate');
                    if (saved !== null && saved !== '') return saved;
                }
            } catch (e) {}
            return '2';
        }

        function setStoredRefreshRate(val) {
            try {
                if (typeof localStorage !== 'undefined' && localStorage) {
                    localStorage.setItem('refreshRate', val);
                }
            } catch (e) {}
        }

        let refreshTimer = null;
        let isFetching = false;
        let rawDevicesList = [];
        let editingMac = null;

        const select = document.getElementById('refreshRate');
        const tbody = document.getElementById('devices-body');
        const errorBanner = document.getElementById('error-banner');
        const loader = document.getElementById('loader');
        const btnText = document.getElementById('btn-text');
        const totalDownEl = document.getElementById('total-down');
        const totalUpEl = document.getElementById('total-up');
        const deviceCountEl = document.getElementById('device-count');
        const lastUpdatedEl = document.getElementById('last-updated');
        const statusIndicator = document.getElementById('status-indicator');
        const statusLabel = document.getElementById('status-label');
        const searchInput = document.getElementById('search-input');
        const filteredCountEl = document.getElementById('filtered-count');

        // Configuration du Graphique
        let speedChart = null;
        const maxDataPoints = 30;

        try {
            const ctx = document.getElementById('speedChart').getContext('2d');
            speedChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: Array(maxDataPoints).fill(''),
                    datasets: [
                        {
                            label: 'Téléchargement (Mb/s)',
                            data: Array(maxDataPoints).fill(0),
                            borderColor: '#0d6efd',
                            backgroundColor: 'rgba(13, 110, 253, 0.08)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.35,
                            pointRadius: 0
                        },
                        {
                            label: 'Envoi (Mb/s)',
                            data: Array(maxDataPoints).fill(0),
                            borderColor: '#198754',
                            backgroundColor: 'rgba(25, 135, 84, 0.08)',
                            borderWidth: 2,
                            fill: true,
                            tension: 0.35,
                            pointRadius: 0
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    animation: { duration: 0 },
                    scales: {
                        y: { 
                            beginAtZero: true, 
                            suggestedMax: 5,
                            grid: { color: 'rgba(0,0,0,0.04)' }
                        },
                        x: { display: false }
                    },
                    plugins: {
                        legend: { 
                            position: 'top',
                            labels: { boxWidth: 12, font: { weight: 600 } }
                        }
                    }
                }
            });
        } catch (e) {
            console.error('Erreur initialisation graphique:', e);
        }

        function updateChart(down, up) {
            if (!speedChart) return;
            const labels = speedChart.data.labels;
            const downData = speedChart.data.datasets[0].data;
            const upData = speedChart.data.datasets[1].data;

            const now = new Date();
            const timeStr = now.getHours().toString().padStart(2, '0') + ':' + 
                            now.getMinutes().toString().padStart(2, '0') + ':' + 
                            now.getSeconds().toString().padStart(2, '0');

            labels.push(timeStr);
            downData.push(down);
            upData.push(up);

            if (labels.length > maxDataPoints) {
                labels.shift();
                downData.shift();
                upData.shift();
            }
            speedChart.update();
        }

        // Modal Rename Logic
        function openRenameModal(mac, currentName) {
            editingMac = mac;
            document.getElementById('modal-mac').innerText = 'Adresse MAC : ' + mac;
            const input = document.getElementById('modal-input');
            input.value = currentName;
            document.getElementById('renameModal').style.display = 'flex';
            setTimeout(() => input.focus(), 50);
        }

        function closeModal() {
            document.getElementById('renameModal').style.display = 'none';
            editingMac = null;
        }

        function closeModalOnBackdrop(e) {
            if (e.target.id === 'renameModal') {
                closeModal();
            }
        }

        function handleModalKey(e) {
            if (e.key === 'Enter') {
                submitRename();
            } else if (e.key === 'Escape') {
                closeModal();
            }
        }

        async function submitRename() {
            const input = document.getElementById('modal-input');
            const newName = input.value.trim();
            if (editingMac && newName) {
                try {
                    await fetch('/api/rename', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ mac: editingMac, name: newName })
                    });
                    closeModal();
                    fetchDevices();
                } catch (e) {
                    alert("Erreur lors de la sauvegarde du nom.");
                }
            }
        }

        function renderDevices(devices) {
            tbody.innerHTML = '';
            if (!devices || devices.length === 0) {
                tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 25px; color: var(--text-muted);">Aucun appareil connecté.</td></tr>';
                return;
            }

            devices.forEach(device => {
                const tr = document.createElement('tr');
                const initial = (device.name && device.name.length > 0) ? device.name.charAt(0).toUpperCase() : '?';
                
                tr.innerHTML = `
                    <td>
                        <div class="device-cell">
                            <div class="device-avatar">${escapeHtml(initial)}</div>
                            <div>
                                <div class="device-title">${escapeHtml(device.name)}</div>
                                ${device.raw_name && device.raw_name !== device.name ? `<div style="font-size: 11px; color: var(--text-muted);">${escapeHtml(device.raw_name)}</div>` : ''}
                            </div>
                        </div>
                    </td>
                    <td><span class="badge-vendor">${escapeHtml(device.vendor)}</span></td>
                    <td class="mono">${escapeHtml(device.ip)}</td>
                    <td class="mono" style="color: #777;">${escapeHtml(device.mac)}</td>
                    <td><span class="speed-badge down">${device.downspeed} Mb/s</span></td>
                    <td><span class="speed-badge up">${device.upspeed} Mb/s</span></td>
                    <td style="text-align: right;">
                        <button class="btn-rename">Renommer</button>
                    </td>
                `;

                const btn = tr.querySelector('.btn-rename');
                btn.addEventListener('click', () => openRenameModal(device.mac, device.name));

                tbody.appendChild(tr);
            });
        }

        function filterDevices() {
            const query = (searchInput.value || '').toLowerCase().trim();
            if (!query) {
                renderDevices(rawDevicesList);
                filteredCountEl.innerText = `${rawDevicesList.length} appareils connectés`;
                return;
            }

            const filtered = rawDevicesList.filter(d => 
                (d.name && d.name.toLowerCase().includes(query)) ||
                (d.ip && d.ip.toLowerCase().includes(query)) ||
                (d.mac && d.mac.toLowerCase().includes(query)) ||
                (d.vendor && d.vendor.toLowerCase().includes(query))
            );

            renderDevices(filtered);
            filteredCountEl.innerText = `${filtered.length} sur ${rawDevicesList.length} appareil(s)`;
        }

        function escapeHtml(text) {
            if (!text) return '';
            return String(text).replace(/[&<>"']/g, function(m) {
                return {
                    '&': '&amp;',
                    '<': '&lt;',
                    '>': '&gt;',
                    '"': '&quot;',
                    "'": '&#039;'
                }[m];
            });
        }

        async function fetchDevices() {
            if (isFetching) return;
            isFetching = true;
            loader.style.display = 'inline-block';

            try {
                const response = await fetch('/api/devices');
                const result = await response.json();

                if (result.status === 'success') {
                    errorBanner.style.display = 'none';
                    statusIndicator.className = 'status-dot';
                    statusLabel.innerText = 'Connecté au routeur Xiaomi';

                    totalDownEl.innerHTML = result.data.total_down + ' <span class="unit">Mb/s</span>';
                    totalUpEl.innerHTML = result.data.total_up + ' <span class="unit">Mb/s</span>';
                    deviceCountEl.innerHTML = result.data.device_count + ' <span class="unit">en ligne</span>';

                    updateChart(result.data.total_down, result.data.total_up);

                    rawDevicesList = (result.data.devices || []).sort((a, b) => b.downspeed - a.downspeed);
                    filterDevices();

                    const now = new Date();
                    lastUpdatedEl.innerText = 'Dernière mise à jour : ' + now.toLocaleTimeString();
                } else {
                    showError(result.message || 'Erreur API routeur');
                }
            } catch (err) {
                showError('Impossible de joindre le routeur Xiaomi (192.168.31.1).');
            } finally {
                isFetching = false;
                loader.style.display = 'none';
            }
        }

        function showError(msg) {
            errorBanner.style.display = 'block';
            errorBanner.innerHTML = '<strong>Avertissement :</strong> ' + escapeHtml(msg);
            statusIndicator.className = 'status-dot error';
            statusLabel.innerText = 'Erreur de connexion';
        }

        function setRefresh() {
            if (refreshTimer) {
                clearInterval(refreshTimer);
                refreshTimer = null;
            }
            const rate = parseInt(select.value, 10);
            if (rate > 0) {
                refreshTimer = setInterval(fetchDevices, rate * 1000);
            }
        }

        function changeRefreshRate() {
            setStoredRefreshRate(select.value);
            setRefresh();
        }

        // Démarrage immédiat
        select.value = getStoredRefreshRate();
        fetchDevices();
        setRefresh();
    </script>
</body>
</html>
"""

@app.route('/')
def dashboard():
    return render_template_string(HTML_TEMPLATE)

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(STATIC_DIR, filename)

@app.route('/api/devices')
def api_devices():
    try:
        data = fetch_devices()
        return jsonify({"status": "success", "data": data})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/api/rename', methods=['POST'])
def api_rename():
    data = request.json or {}
    mac = data.get('mac')
    name = data.get('name')
    if mac and name:
        save_alias(mac, name)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Données invalides"})

def main():
    if "-h" in sys.argv or "--help" in sys.argv:
        print("Xiaomi Wi-Fi Dashboard")
        print("Usage:")
        print("  python xiaomi_wifi_dashboard.py             # Lance l'application avec interface graphique")
        print("  python xiaomi_wifi_dashboard.py --server    # Lance uniquement le serveur web (http://localhost:5000)")
        print("  python xiaomi_wifi_dashboard.py --help      # Affiche cette aide")
        sys.exit(0)

    if "--server" in sys.argv or "--web" in sys.argv:
        print("🚀 Lancement du dashboard Wi-Fi en mode serveur web...")
        print("👉 Ouvre ton navigateur à l'adresse : http://localhost:5000")
        app.run(host='0.0.0.0', port=5000, debug=False)
    else:
        try:
            import webview
            print("🖥️  Ouverture de la fenêtre graphique Xiaomi Wi-Fi Dashboard...")
            window = webview.create_window(
                title='Xiaomi Wi-Fi Dashboard',
                url=app,
                width=1280,
                height=850,
                min_size=(950, 650)
            )
            def bring_to_front():
                if sys.platform == 'darwin':
                    try:
                        from AppKit import NSApplication, NSApplicationActivationPolicyRegular
                        ns_app = NSApplication.sharedApplication()
                        ns_app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
                        ns_app.activateIgnoringOtherApps_(True)
                    except Exception:
                        pass

            if sys.platform.startswith('linux'):
                try:
                    webview.start(gui='gtk')
                except Exception:
                    webview.start()
            else:
                webview.start(bring_to_front)
        except Exception as e:
            print(f"⚠️  Impossible d'ouvrir l'interface graphique native ({e}).")
            print("🚀 Basculement automatique en mode serveur web...")
            print("👉 Ouvre ton navigateur à l'adresse : http://localhost:5000")
            app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    main()
