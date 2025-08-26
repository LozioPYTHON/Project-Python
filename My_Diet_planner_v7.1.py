# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, Toplevel, simpledialog
import os
import sys
import json
from fpdf import FPDF
from datetime import datetime
import webbrowser
import urllib.parse
import re

# Import delle librerie AI
import openai
import google.generativeai as genai

# --- 1. CONFIGURAZIONE E GESTIONE FILE ---

CONFIG_FILE = 'config.json'
PATIENTS_DB_FILE = 'patients.json'
TEMP_REPORTS_DIR = 'temp_reports'

def load_config():
    if not os.path.exists(CONFIG_FILE):
        default_config = {"api_provider": "OpenAI", "api_key": ""}
        with open(CONFIG_FILE, 'w') as f: json.dump(default_config, f)
        return default_config
    try:
        with open(CONFIG_FILE, 'r') as f: return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"api_provider": "OpenAI", "api_key": ""}

def save_config(config_data):
    with open(CONFIG_FILE, 'w') as f: json.dump(config_data, f, indent=4)

def load_patients():
    if not os.path.exists(PATIENTS_DB_FILE):
        with open(PATIENTS_DB_FILE, 'w') as f: json.dump({}, f)
        return {}
    try:
        with open(PATIENTS_DB_FILE, 'r') as f: return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}

def save_patients(patients_data):
    with open(PATIENTS_DB_FILE, 'w') as f: json.dump(patients_data, f, indent=4)

# --- 2. CLASSE PER LA GENERAZIONE DEI PDF ---

class PDF(FPDF):
    def __init__(self, title, studio_nome="", *args, **kwargs):
        super().__init__(*args, **kwargs); self.studio_nome = studio_nome; self.doc_title = title
    def header(self):
        self.set_font('Helvetica', 'B', 14); self.cell(0, 10, self.studio_nome, 0, 1, 'C')
        self.set_font('Helvetica', 'B', 12); self.cell(0, 10, self.doc_title, 0, 1, 'C'); self.ln(5)
    def footer(self):
        self.set_y(-15); self.set_font('Helvetica', 'I', 8); self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

# --- 3. FINESTRE SECONDARIE (AGENDA E REPORT) ---

class PatientAgendaWindow(Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Agenda Pazienti"); self.geometry("900x600")
        self.transient(parent); self.grab_set()

        tree_frame = ttk.Frame(self); tree_frame.pack(expand=True, fill='both', padx=10, pady=10)
        columns = ("nome", "email", "telefono", "pagamenti")
        self.tree = ttk.Treeview(tree_frame, columns=columns, show="headings")
        self.tree.heading("nome", text="Nome Completo"); self.tree.column("nome", width=200)
        self.tree.heading("email", text="Email"); self.tree.column("email", width=250)
        self.tree.heading("telefono", text="Telefono"); self.tree.column("telefono", width=150)
        self.tree.heading("pagamenti", text="Totale Pagato (€)"); self.tree.column("pagamenti", width=120, anchor='e')
        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set); vsb.pack(side='right', fill='y'); self.tree.pack(side='left', expand=True, fill='both')
        button_frame = ttk.Frame(self); button_frame.pack(fill='x', padx=10, pady=(0,10))
        delete_btn = ttk.Button(button_frame, text="Elimina Paziente Selezionato", command=self.delete_patient); delete_btn.pack(side='right')
        self.populate_agenda()

    def populate_agenda(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for name, data in sorted(self.parent.patients_data.items()):
            total_paid = sum(p['amount'] for p in data.get('payments', []))
            self.tree.insert("", "end", values=(name, data.get('email', ''), data.get('telefono', ''), f"{total_paid:.2f}"))

    def delete_patient(self):
        selected_item = self.tree.selection()
        if not selected_item: messagebox.showwarning("Nessuna Selezione", "Selezionare un paziente da eliminare."); return
        patient_name = self.tree.item(selected_item, "values")[0]
        if messagebox.askyesno("Conferma Eliminazione", f"Sei sicuro di voler eliminare permanentemente {patient_name} e tutti i suoi dati?"):
            del self.parent.patients_data[patient_name]
            save_patients(self.parent.patients_data)
            self.parent.update_patient_dropdown()
            self.parent.clear_all_fields()
            self.populate_agenda()
            messagebox.showinfo("Successo", f"{patient_name} è stato eliminato.")

class ReportingWindow(Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.title("Report Pagamenti"); self.geometry("800x600")
        self.transient(parent); self.grab_set()

        controls_frame = ttk.Frame(self, padding=10); controls_frame.pack(fill='x')
        ttk.Label(controls_frame, text="Mese:").pack(side='left', padx=5)
        self.month_var = tk.StringVar(value=datetime.now().strftime("%B"))
        months = ["Tutti", "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
        ttk.Combobox(controls_frame, textvariable=self.month_var, values=months, state='readonly').pack(side='left', padx=5)
        ttk.Label(controls_frame, text="Anno:").pack(side='left', padx=5)
        self.year_var = tk.StringVar(value=str(datetime.now().year))
        ttk.Entry(controls_frame, textvariable=self.year_var, width=10).pack(side='left', padx=5)
        ttk.Button(controls_frame, text="Genera Report", command=self.generate_report).pack(side='left', padx=10)
        text_frame = ttk.Frame(self, padding=10); text_frame.pack(expand=True, fill='both')
        self.report_text = tk.Text(text_frame, wrap='word', font=('Courier', 10)); self.report_text.pack(expand=True, fill='both')
        ttk.Button(self, text="Esporta Report in PDF", command=self.export_pdf).pack(pady=10)

    def generate_report(self):
        try:
            year = int(self.year_var.get())
            month_str = self.month_var.get()
            month = datetime.strptime(month_str, "%B").month if month_str != "Tutti" else None
        except ValueError: messagebox.showerror("Errore", "L'anno deve essere un numero valido."); return
        report_lines = []; total = 0.0
        for patient_name, data in self.parent.patients_data.items():
            for payment in data.get('payments', []):
                payment_date = datetime.strptime(payment['date'], '%Y-%m-%d')
                if payment_date.year == year and (not month or payment_date.month == month):
                    line = f"{payment['date']} | {patient_name:<30} | {payment['note']:<25} | €{payment['amount']:>8.2f}"
                    report_lines.append(line)
                    total += payment['amount']
        period = f"{month_str} {year}" if month_str != "Tutti" else f"Anno {year}"
        header = f"RESOCONTO PAGAMENTI - {period}\n" + "="*70 + "\n"
        header += f"{'Data':<11} | {'Paziente':<30} | {'Nota':<25} | {'Importo':>9}\n" + "-"*70 + "\n"
        footer = "-"*70 + f"\nTOTALE: €{total:.2f}"
        full_report = header + "\n".join(sorted(report_lines)) + "\n\n" + footer
        self.report_text.delete('1.0', tk.END); self.report_text.insert('1.0', full_report)

    def export_pdf(self):
        report_content = self.report_text.get('1.0', tk.END).strip()
        if not report_content: messagebox.showwarning("Niente da Esportare", "Genera prima un report."); return
        file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Documents", "*.pdf")], title="Salva Report Pagamenti", initialfile=f"Report_Pagamenti_{self.month_var.get()}_{self.year_var.get()}.pdf")
        if not file_path: return
        pdf = PDF(f"Report Pagamenti - {self.month_var.get()} {self.year_var.get()}", self.parent.config.get('studio_nome'))
        pdf.add_page(); pdf.set_font("Courier", size=9)
        pdf.multi_cell(0, 5, report_content)
        pdf.output(file_path); messagebox.showinfo("Successo", "Report PDF salvato con successo.")

# --- 4. CLASSE PRINCIPALE DELL'APPLICAZIONE ---

class DietPlannerApp(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("Generatore di Diete AI v7.1 (Gestionale)"); self.geometry("1400x950"); self.minsize(1200, 900)
        self.style = ttk.Style(self); self.style.theme_use('clam'); self.primary_color = "#F0F0F0"; self.secondary_color = "#FFFFFF"; self.text_color = "#333333"
        self.accent_color = "#4CAF50"; self.whatsapp_color = "#25D366"; self.vary_color = "#007BFF"; self.manage_color = "#6c757d"
        self.configure(bg=self.primary_color)
        self.style.configure('.', background=self.primary_color, foreground=self.text_color, font=('Helvetica', 10))
        self.style.configure('TLabel', background=self.primary_color, foreground=self.text_color, font=('Helvetica', 11))
        self.style.configure('TEntry', fieldbackground=self.secondary_color, foreground=self.text_color); self.style.configure('TFrame', background=self.secondary_color)
        self.style.configure('TLabelframe.Label', background=self.secondary_color, font=('Helvetica', 11, 'bold'))
        self.style.configure('TButton', background=self.accent_color, foreground=self.secondary_color, font=('Helvetica', 10, 'bold'), borderwidth=0); self.style.map('TButton', background=[('active', '#45a049')])
        self.style.configure('WhatsApp.TButton', background=self.whatsapp_color, foreground=self.secondary_color, font=('Helvetica', 10, 'bold'), borderwidth=0); self.style.map('WhatsApp.TButton', background=[('active', '#20b859')])
        self.style.configure('Vary.TButton', background=self.vary_color, foreground=self.secondary_color, font=('Helvetica', 10, 'bold'), borderwidth=0); self.style.map('Vary.TButton', background=[('active', '#0069d9')])
        self.style.configure('Manage.TButton', background=self.manage_color, foreground=self.secondary_color, font=('Helvetica', 10, 'bold'), borderwidth=0); self.style.map('Manage.TButton', background=[('active', '#5a6268')])

        self.config = load_config(); self.patients_data = load_patients()
        self.create_widgets()

    def create_widgets(self):
        main_frame = ttk.Frame(self, padding="20", style='primary.TFrame'); main_frame.pack(expand=True, fill='both')

        # --- LAYOUT A 3 COLONNE ---
        left_column = ttk.Frame(main_frame, style='TFrame'); left_column.pack(side='left', fill='y', padx=(0, 10), ipadx=10, ipady=10)
        right_actions_column = ttk.Frame(main_frame, style='primary.TFrame'); right_actions_column.pack(side='right', fill='y', padx=(10, 0))
        center_column = ttk.Frame(main_frame, style='TFrame'); center_column.pack(side='left', expand=True, fill='both')

        # --- COLONNA SINISTRA (Dati) ---
        patient_selector_frame = ttk.LabelFrame(left_column, text="Gestione Paziente", padding=15); patient_selector_frame.pack(fill='x', pady=(0, 5))
        new_patient_btn = ttk.Button(patient_selector_frame, text="Nuovo Paziente", command=self.clear_all_fields); new_patient_btn.pack(fill='x', pady=(0, 10), ipady=4)
        self.search_var = tk.StringVar(); self.search_entry = ttk.Entry(patient_selector_frame, textvariable=self.search_var, font=('Helvetica', 9), foreground='grey')
        self.search_entry.insert(0, "Cerca per nome..."); self.search_entry.bind("<KeyRelease>", self.filter_patients); self.search_entry.bind("<FocusIn>", self.on_search_focus_in); self.search_entry.bind("<FocusOut>", self.on_search_focus_out)
        self.search_entry.pack(fill='x', pady=(0,5))
        self.patient_var = tk.StringVar(); self.patient_dropdown = ttk.Combobox(patient_selector_frame, textvariable=self.patient_var, state="readonly"); self.patient_dropdown.pack(expand=True, fill='x')
        self.patient_dropdown.bind("<<ComboboxSelected>>", self.on_patient_select); self.update_patient_dropdown()
        
        notebook = ttk.Notebook(left_column)
        notebook.pack(fill='both', pady=5, expand=True)
        paziente_frame_container = ttk.Frame(notebook, padding=15); notebook.add(paziente_frame_container, text='Dati Paziente')
        studio_frame = ttk.Frame(notebook, padding=15); notebook.add(studio_frame, text='Impostazioni')

        # Dati Paziente
        self.paziente_nome = self.crea_campo(paziente_frame_container, "Nome:"); self.paziente_eta = self.crea_campo(paziente_frame_container, "Età:")
        self.paziente_telefono = self.crea_campo(paziente_frame_container, "Telefono:"); self.paziente_email = self.crea_campo(paziente_frame_container, "Email:")
        self.paziente_peso = self.crea_campo(paziente_frame_container, "Peso (kg):"); self.paziente_calorie = self.crea_campo(paziente_frame_container, "Calorie (kcal):")
        self.paziente_intolleranze = self.crea_campo(paziente_frame_container, "Intolleranze:"); self.paziente_cibi_preferiti = self.crea_campo(paziente_frame_container, "Cibi Preferiti:")
        self.paziente_cibi_non_preferiti = self.crea_campo(paziente_frame_container, "Cibi Non Graditi:")
        ttk.Separator(paziente_frame_container, orient='horizontal').pack(fill='x', pady=10)
        ttk.Label(paziente_frame_container, text="Misure Corporee (cm)", font=('Helvetica', 9, 'italic')).pack(anchor='w')
        self.paziente_vita = self.crea_campo(paziente_frame_container, "Vita:"); self.paziente_cosce = self.crea_campo(paziente_frame_container, "Cosce:")
        self.paziente_spalle = self.crea_campo(paziente_frame_container, "Spalle:"); self.paziente_braccia = self.crea_campo(paziente_frame_container, "Braccia:")
        ttk.Separator(paziente_frame_container, orient='horizontal').pack(fill='x', pady=10)
        self.trains_var = tk.BooleanVar(); self.trains_checkbox = ttk.Checkbutton(paziente_frame_container, text="Il Paziente si Allena", variable=self.trains_var, command=self.toggle_training_fields); self.trains_checkbox.pack(anchor='w')
        self.training_days_frame = ttk.Frame(paziente_frame_container); self.training_days_frame.pack(fill='x', pady=5)
        days = ["Lunedì", "Martedì", "Mercoledì", "Giovedì", "Venerdì", "Sabato", "Domenica"]; self.training_days_vars = {day: tk.BooleanVar() for day in days}; self.training_days_checkboxes = {}
        for i, day in enumerate(days): cb = ttk.Checkbutton(self.training_days_frame, text=day[:3], variable=self.training_days_vars[day]); cb.grid(row=0, column=i, padx=2, sticky='w'); self.training_days_checkboxes[day] = cb
        self.toggle_training_fields()
        patient_buttons_frame = ttk.Frame(paziente_frame_container); patient_buttons_frame.pack(fill='x', pady=(10,0)); patient_buttons_frame.columnconfigure((0,1), weight=1)
        save_patient_btn = ttk.Button(patient_buttons_frame, text="Salva Dati Paziente", command=self.save_patient_data); save_patient_btn.grid(row=0, column=0, sticky='ew', padx=2)
        add_payment_btn = ttk.Button(patient_buttons_frame, text="Aggiungi Pagamento", command=self.add_payment); add_payment_btn.grid(row=0, column=1, sticky='ew', padx=2)
        
        # Dati Studio
        self.studio_nome = self.crea_campo(studio_frame, "Nome Studio:"); self.studio_indirizzo = self.crea_campo(studio_frame, "Indirizzo:")
        self.studio_telefono = self.crea_campo(studio_frame, "Telefono:"); self.studio_email = self.crea_campo(studio_frame, "Email:")
        ttk.Separator(studio_frame, orient='horizontal').pack(fill='x', pady=10)
        self.api_provider_var = tk.StringVar(value=self.config.get("api_provider", "OpenAI")); self.crea_campo_dropdown(studio_frame, "Provider AI:", self.api_provider_var, ["OpenAI", "Google Gemini"])
        self.api_key_entry = self.crea_campo(studio_frame, "Chiave API:", show_char='*'); self.api_key_entry.insert(0, self.config.get("api_key", ""))
        save_api_btn = ttk.Button(studio_frame, text="Salva Impostazioni", command=self.save_all_configs); save_api_btn.pack(fill='x', pady=(10,0), ipady=4)
        
        # --- COLONNA CENTRALE (Dieta) ---
        dieta_frame = ttk.LabelFrame(center_column, text="Dieta Elaborata", padding=15); dieta_frame.pack(expand=True, fill='both')
        self.dieta_output = tk.Text(dieta_frame, height=20, width=80, wrap='word', font=('Helvetica', 11), relief='sunken', borderwidth=1, bg=self.secondary_color, fg=self.text_color); self.dieta_output.pack(expand=True, fill='both', pady=(5, 10))

        # --- COLONNA DESTRA (Azioni) ---
        actions_frame = ttk.Frame(right_actions_column, style='primary.TFrame', padding=10); actions_frame.pack(fill='x')
        actions_frame.columnconfigure(0, weight=1)
        ttk.Label(actions_frame, text="Azioni Dieta", font=('Helvetica', 10, 'bold')).grid(row=0, column=0, pady=(0,5), sticky='w')
        self.genera_btn = ttk.Button(actions_frame, text="Genera Dieta", command=lambda: self.genera_dieta(is_variation=False)); self.genera_btn.grid(row=1, column=0, sticky='ew', padx=2, pady=2, ipady=4)
        self.varia_btn = ttk.Button(actions_frame, text="Varia Dieta", command=lambda: self.genera_dieta(is_variation=True), style='Vary.TButton'); self.varia_btn.grid(row=2, column=0, sticky='ew', padx=2, pady=2, ipady=4)
        ttk.Label(actions_frame, text="Gestione", font=('Helvetica', 10, 'bold')).grid(row=3, column=0, pady=(15,5), sticky='w')
        ttk.Button(actions_frame, text="Agenda Pazienti", command=self.open_agenda, style='Manage.TButton').grid(row=4, column=0, sticky='ew', padx=2, pady=2, ipady=4)
        ttk.Button(actions_frame, text="Report Pagamenti", command=self.open_reports, style='Manage.TButton').grid(row=5, column=0, sticky='ew', padx=2, pady=2, ipady=4)
        ttk.Label(actions_frame, text="Condividi", font=('Helvetica', 10, 'bold')).grid(row=6, column=0, pady=(15,5), sticky='w')
        self.esporta_pdf_btn = ttk.Button(actions_frame, text="Esporta PDF", command=lambda: self.esporta_pdf()); self.esporta_pdf_btn.grid(row=7, column=0, sticky='ew', padx=2, pady=2, ipady=4)
        self.condividi_email_btn = ttk.Button(actions_frame, text="Invia Email", command=self.share_via_email); self.condividi_email_btn.grid(row=8, column=0, sticky='ew', padx=2, pady=2, ipady=4)
        self.condividi_wa_btn = ttk.Button(actions_frame, text="Invia WhatsApp", command=self.share_via_whatsapp, style='WhatsApp.TButton'); self.condividi_wa_btn.grid(row=9, column=0, sticky='ew', padx=2, pady=2, ipady=4)
        
        self.load_studio_data()

    def on_search_focus_in(self, event):
        if self.search_var.get() == "Cerca per nome...": self.search_entry.delete(0, tk.END); self.search_entry.config(foreground='black')
    def on_search_focus_out(self, event):
        if not self.search_var.get(): self.search_entry.insert(0, "Cerca per nome..."); self.search_entry.config(foreground='grey')

    def filter_patients(self, event=None):
        search_term = self.search_var.get().lower()
        if not search_term or search_term == "cerca per nome...": self.update_patient_dropdown(filtered_list=None)
        else:
            filtered = [name for name in self.patients_data.keys() if search_term in name.lower()]
            self.update_patient_dropdown(filtered_list=filtered)

    def open_agenda(self): PatientAgendaWindow(self)
    def open_reports(self): ReportingWindow(self)
    def add_payment(self):
        patient_name = self.paziente_nome.get()
        if not patient_name or patient_name not in self.patients_data: messagebox.showwarning("Nessun Paziente", "Selezionare o salvare un paziente prima di aggiungere un pagamento."); return
        amount = simpledialog.askfloat("Aggiungi Pagamento", f"Importo pagato da {patient_name}:", parent=self, minvalue=0.0)
        if amount is not None:
            note = simpledialog.askstring("Aggiungi Pagamento", "Nota (opzionale):", parent=self)
            new_payment = {'date': datetime.now().strftime('%Y-%m-%d'), 'amount': amount, 'note': note or ''}
            if 'payments' not in self.patients_data[patient_name]: self.patients_data[patient_name]['payments'] = []
            self.patients_data[patient_name]['payments'].append(new_payment)
            save_patients(self.patients_data); messagebox.showinfo("Successo", f"Pagamento di €{amount:.2f} registrato per {patient_name}.")

    def update_patient_dropdown(self, filtered_list=None):
        all_patients = sorted(list(self.patients_data.keys()))
        display_list = filtered_list if filtered_list is not None else all_patients
        self.patient_dropdown['values'] = display_list
        if not self.patient_var.get() in display_list: self.patient_var.set("")

    def on_patient_select(self, event=None):
        selected_name = self.patient_var.get();
        if not selected_name: return
        self.on_search_focus_in(None); self.search_var.set(selected_name)
        if selected_name in self.patients_data:
            patient_data = self.patients_data[selected_name]
            all_fields = [
                (self.paziente_nome, 'nome'),
                (self.paziente_eta, 'eta'),
                (self.paziente_telefono, 'telefono'),
                (self.paziente_email, 'email'),
                (self.paziente_peso, 'peso'),
                (self.paziente_calorie, 'calorie'),
                (self.paziente_intolleranze, 'intolleranze'),
                (self.paziente_cibi_preferiti, 'cibi_preferiti'),
                (self.paziente_cibi_non_preferiti, 'cibi_non_graditi'),
                (self.paziente_vita, 'vita'),
                (self.paziente_cosce, 'cosce'),
                (self.paziente_spalle, 'spalle'),
                (self.paziente_braccia, 'braccia')
            ]
            for field, key in all_fields:
                self.populate_fields(field, patient_data, key)
            training_data = patient_data.get('training', {'trains': False, 'days': []})
            self.trains_var.set(training_data.get('trains', False))
            for day, var in self.training_days_vars.items(): var.set(day in training_data.get('days', []))
            self.toggle_training_fields()

    def save_patient_data(self):
        nome = self.paziente_nome.get().strip();
        if not nome: messagebox.showerror("Errore", "'Nome Paziente' è obbligatorio."); return
        existing_payments = self.patients_data.get(nome, {}).get('payments', [])
        all_fields_keys = [('nome', self.paziente_nome), ('eta', self.paziente_eta), ('telefono', self.paziente_telefono), ('email', self.paziente_email), ('peso', self.paziente_peso), ('calorie', self.paziente_calorie), ('intolleranze', self.paziente_intolleranze), ('cibi_preferiti', self.paziente_cibi_preferiti), ('cibi_non_graditi', self.paziente_cibi_non_preferiti), ('vita', self.paziente_vita), ('cosce', self.paziente_cosce), ('spalle', self.paziente_spalle), ('braccia', self.paziente_braccia)]
        patient_data = {key: field.get() for key, field in all_fields_keys}
        patient_data['training'] = {'trains': self.trains_var.get(), 'days': [day for day, var in self.training_days_vars.items() if var.get()]}
        patient_data['payments'] = existing_payments
        self.patients_data[nome] = patient_data; save_patients(self.patients_data); messagebox.showinfo("Successo", f"Dati di '{nome}' salvati.")
        self.update_patient_dropdown(); self.patient_dropdown.set(nome)
    
    def toggle_training_fields(self): state = 'normal' if self.trains_var.get() else 'disabled'; [cb.config(state=state) for cb in self.training_days_checkboxes.values()]
    def crea_campo(self, parent, label_text, show_char=None): frame = ttk.Frame(parent); frame.pack(fill='x', pady=2); label = ttk.Label(frame, text=label_text, width=13); label.pack(side='left'); entry = ttk.Entry(frame, show=show_char); entry.pack(side='right', expand=True, fill='x'); return entry
    def crea_campo_dropdown(self, parent, label_text, variable, options): frame = ttk.Frame(parent); frame.pack(fill='x', pady=2); label = ttk.Label(frame, text=label_text, width=13); label.pack(side='left'); dropdown = ttk.Combobox(frame, textvariable=variable, values=options, state="readonly"); dropdown.pack(side='right', expand=True, fill='x'); return dropdown
    def save_all_configs(self): self.config['api_provider'] = self.api_provider_var.get(); self.config['api_key'] = self.api_key_entry.get(); self.config['studio_nome'] = self.studio_nome.get(); self.config['studio_indirizzo'] = self.studio_indirizzo.get(); self.config['studio_telefono'] = self.studio_telefono.get(); self.config['studio_email'] = self.studio_email.get(); save_config(self.config); messagebox.showinfo("Successo", "Impostazioni salvate.")
    def load_studio_data(self): self.populate_fields(self.studio_nome, self.config, 'studio_nome'); self.populate_fields(self.studio_indirizzo, self.config, 'studio_indirizzo'); self.populate_fields(self.studio_telefono, self.config, 'studio_telefono'); self.populate_fields(self.studio_email, self.config, 'studio_email')
    def populate_fields(self, field, data, key): field.delete(0, tk.END); field.insert(0, data.get(key, ''))
    def clear_patient_fields(self):
        all_fields = [self.paziente_nome, self.paziente_eta, self.paziente_telefono, self.paziente_email, self.paziente_peso, self.paziente_calorie, self.paziente_intolleranze, self.paziente_cibi_preferiti, self.paziente_cibi_non_preferiti, self.paziente_vita, self.paziente_cosce, self.paziente_spalle, self.paziente_braccia]
        [field.delete(0, tk.END) for field in all_fields]
        self.trains_var.set(False); [var.set(False) for var in self.training_days_vars.values()]; self.toggle_training_fields()
    def clear_all_fields(self): self.clear_patient_fields(); self.patient_dropdown.set(''); self.on_search_focus_out(None); self.update_patient_dropdown()
    
    def genera_dieta(self, is_variation=False):
        api_key = self.config.get("api_key"); api_provider = self.config.get("api_provider");
        if not api_key: messagebox.showerror("Errore API", "Chiave API non configurata."); return
        paziente_nome = self.paziente_nome.get(); paziente_calorie = self.paziente_calorie.get();
        if not all([paziente_nome, paziente_calorie]): messagebox.showwarning("Dati Mancanti", "Inserire almeno Nome e Calorie."); return
        
        variation_instruction = "L'obiettivo è fornire una valida alternativa a una dieta precedente, quindi utilizza alimenti e ricette differenti." if is_variation else ""
        training_instruction = ""
        if self.trains_var.get():
            training_days = [day for day, var in self.training_days_vars.items() if var.get()]
            if training_days: training_instruction = f"ALLENAMENTO: Il paziente si allena nei giorni: {', '.join(training_days)}. In questi giorni specifici, modifica la dieta per includere un pasto pre-allenamento e un pasto post-allenamento, adeguati per supportare lo sforzo e il recupero."
        
        measurements = { "Vita": self.paziente_vita.get(), "Cosce": self.paziente_cosce.get(), "Spalle": self.paziente_spalle.get(), "Braccia": self.paziente_braccia.get()}
        valid_measurements = {k: v for k, v in measurements.items() if v.strip()}
        measurements_instruction = ""
        if valid_measurements:
            measures_str = ", ".join([f"{k}: {v} cm" for k, v in valid_measurements.items()])
            measurements_instruction = f"OBIETTIVI DI RICOMPOSIZIONE CORPOREA: Le misure attuali del paziente sono {measures_str}. Tieni conto di questi dati per formulare una dieta che supporti la riduzione del grasso e il mantenimento/aumento della massa magra."

        prompt = f"""Sei un nutrizionista professionista. Crea un piano dietetico settimanale dettagliato, suddividendo ogni giorno in pasti principali e spuntini. Elenca alimenti e quantità in grammi. L'apporto calorico deve avvicinarsi a {paziente_calorie} kcal. {variation_instruction} {training_instruction} {measurements_instruction} Alla fine, aggiungi note su idratazione e cottura.
        Dati paziente: Nome: {paziente_nome}, Età: {self.paziente_eta.get()}, Peso: {self.paziente_peso.get()} kg, Intolleranze: {self.paziente_intolleranze.get()}, Cibi preferiti: {self.paziente_cibi_preferiti.get()}, Cibi da escludere: {self.paziente_cibi_non_preferiti.get()}.
        Inizia con "Piano Alimentare per {paziente_nome}"."""
        
        self.dieta_output.delete("1.0", tk.END); self.dieta_output.insert(tk.END, f"Elaborazione con {api_provider}, attendere..."); self.update_idletasks()
        try:
            risposta_dieta = ""
            if api_provider == 'OpenAI': openai.api_key = api_key; response = openai.chat.completions.create(model="gpt-4o-mini", messages=[{"role": "system", "content": "Sei un esperto nutrizionista."}, {"role": "user", "content": prompt}]); risposta_dieta = response.choices[0].message.content
            elif api_provider == 'Google Gemini': genai.configure(api_key=api_key); model = genai.GenerativeModel('gemini-1.5-flash'); response = model.generate_content(prompt); risposta_dieta = response.text
            self.dieta_output.delete("1.0", tk.END); self.dieta_output.insert(tk.END, risposta_dieta.strip())
        except Exception as e: self.dieta_output.delete("1.0", tk.END); messagebox.showerror("Errore API", f"Impossibile generare la dieta.\nDettagli: {e}")
    
    def esporta_pdf(self, file_path=None):
        contenuto_dieta = self.dieta_output.get("1.0", tk.END).strip()
        if not contenuto_dieta or "Elaborazione" in contenuto_dieta: messagebox.showwarning("Nessuna Dieta", "Genera prima una dieta."); return None
        if not file_path: file_path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF Documents", "*.pdf")], title="Salva Report", initialfile=f"Dieta_{self.paziente_nome.get().replace(' ', '_')}.pdf")
        if not file_path: return None
        try:
            pdf = PDF(f"Piano Alimentare per {self.paziente_nome.get()}", self.config.get('studio_nome'))
            pdf.add_page(); pdf.set_font('Helvetica', '', 10); pdf.multi_cell(0, 6, contenuto_dieta); pdf.output(file_path)
            if TEMP_REPORTS_DIR not in str(file_path): messagebox.showinfo("Successo", f"File PDF salvato.")
            return file_path
        except Exception as e: messagebox.showerror("Errore PDF", f"Impossibile generare il PDF.\nDettagli: {e}"); return None
    
    def _prepare_share(self):
        if not os.path.exists(TEMP_REPORTS_DIR): os.makedirs(TEMP_REPORTS_DIR)
        file_name = f"Dieta_{self.paziente_nome.get().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        temp_file_path = os.path.join(TEMP_REPORTS_DIR, file_name); return self.esporta_pdf(file_path=temp_file_path)
    
    def share_via_email(self):
        patient_email = self.paziente_email.get();
        if not patient_email: messagebox.showerror("Email Mancante", "Inserire l'email del paziente."); return
        pdf_path = self._prepare_share();
        if not pdf_path: return
        subject = f"Piano Alimentare da {self.config.get('studio_nome', 'Studio Medico')}"
        body = f"Gentile {self.paziente_nome.get()},\n\nin allegato trovi il tuo piano alimentare.\n\nCordiali saluti,\n{self.config.get('studio_nome', '')}"
        mailto_url = f"mailto:{patient_email}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(body)}"
        webbrowser.open(mailto_url); messagebox.showinfo("Apri Client Email", f"Il tuo programma di posta è stato aperto.\n\nAllega manualmente il file:\n{os.path.abspath(pdf_path)}")
    
    def share_via_whatsapp(self):
        patient_phone = self.paziente_telefono.get()
        if not patient_phone: messagebox.showerror("Telefono Mancante", "Inserire il telefono del paziente."); return
        pdf_path = self._prepare_share();
        if not pdf_path: return
        cleaned_phone = re.sub(r'\D', '', patient_phone)
        if not cleaned_phone.startswith(('39', '+39')) and len(cleaned_phone) <= 11: cleaned_phone = f'39{cleaned_phone}'
        message = f"Gentile {self.paziente_nome.get()}, ecco il tuo piano alimentare. Saluti, {self.config.get('studio_nome', 'Studio Medico')}."
        whatsapp_url = f"https://wa.me/{cleaned_phone}?text={urllib.parse.quote(message)}"
        webbrowser.open(whatsapp_url); messagebox.showinfo("Apri WhatsApp", f"WhatsApp è stato aperto.\n\nAllega manualmente il file:\n{os.path.abspath(pdf_path)}")

if __name__ == "__main__":
    app = DietPlannerApp()
    app.mainloop()