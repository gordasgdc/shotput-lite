#!/usr/bin/env python3
"""
ShotPut Lite
------------
Aplicatie personala/echipa pentru offload verificat de fisiere media,
inspirata de ShotPut Pro: copiere catre mai multe destinatii simultan,
verificare (MD5/SHA-1/SHA-256/SHA-512/doar-dimensiune, la alegere),
denumire automata de foldere, rapoarte CSV + PDF, notificari native
(macOS si Windows), detectare automata a cardurilor/drive-urilor
montate, excludere de fisiere/extensii, verificare spatiu liber si
anulare in timpul rularii. Functioneaza pe macOS si Windows.

Ruleaza cu: python3 main.py
Dependinte externe: reportlab (rapoarte PDF), tkinterdnd2 (drag-and-drop),
                    plyer (notificari, optional)
"""

import os
import threading
import queue
from datetime import datetime

import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    _DND_AVAILABLE = True
    _BASE_CLASS = TkinterDnD.Tk
except ImportError:
    _DND_AVAILABLE = False
    DND_FILES = None
    _BASE_CLASS = tk.Tk

from offload_engine import (
    list_all_files, list_mounted_volumes, get_free_space_bytes,
    send_notification, DestinationJob, DEFAULT_EXCLUSIONS,
    VERIFICATION_MODELS, DEFAULT_VERIFICATION_MODEL,
)
import config as cfg


def format_size(num_bytes):
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if num_bytes < 1024.0:
            return f"{num_bytes:.1f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} PB"


class ShotPutLiteApp(_BASE_CLASS):
    def __init__(self):
        super().__init__()
        self.title("ShotPut Lite")
        self.geometry("820x680")
        self.minsize(720, 560)

        self.settings = cfg.load_config()

        self.source_var = tk.StringVar()
        self.project_var = tk.StringVar(value=self.settings.get("project", ""))
        self.card_var = tk.StringVar(value=self.settings.get("card", ""))
        self.exclusions_var = tk.StringVar(value=self.settings.get("exclusions", ", ".join(DEFAULT_EXCLUSIONS)))
        self.skip_existing_var = tk.BooleanVar(value=self.settings.get("skip_existing_identical", False))
        self.verification_model_var = tk.StringVar(
            value=self.settings.get("verification_model", DEFAULT_VERIFICATION_MODEL)
        )
        self.destinations = list(self.settings.get("destinations", []))

        self.log_queue = queue.Queue()
        self.progress_counter = [0]
        self.bytes_counter = [0]
        self.progress_lock = threading.Lock()
        self.total_units = 0
        self.total_bytes = 0
        self.running = False
        self.cancel_event = threading.Event()
        self.jobs = []
        self.start_time = None

        self._build_ui()
        self._refresh_volumes()
        for d in self.destinations:
            self.dest_listbox.insert("end", d)

        self.after(150, self._poll_log_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------------- UI ----------------

    def _build_ui(self):
        pad = {"padx": 10, "pady": 6}

        # Sursa
        frame_src = ttk.LabelFrame(self, text="Sursa (card / drive de offload)")
        frame_src.pack(fill="x", **pad)

        row1 = ttk.Frame(frame_src)
        row1.pack(fill="x", padx=8, pady=(8, 4))
        ttk.Label(row1, text="Volume detectate automat:").pack(side="left")
        self.volume_combo = ttk.Combobox(row1, state="readonly", width=40)
        self.volume_combo.pack(side="left", padx=8)
        self.volume_combo.bind("<<ComboboxSelected>>", self._on_volume_selected)
        ttk.Button(row1, text="Reimprospateaza", command=self._refresh_volumes).pack(side="left")

        row2 = ttk.Frame(frame_src)
        row2.pack(fill="x", padx=8, pady=(0, 4))
        self.source_entry = ttk.Entry(row2, textvariable=self.source_var)
        self.source_entry.pack(side="left", fill="x", expand=True)
        ttk.Button(row2, text="Alege manual...", command=self._choose_source).pack(side="left", padx=8)

        dnd_hint_src = "(sau trage un folder aici din Finder)" if _DND_AVAILABLE else \
            "(drag-and-drop indisponibil - vezi CITESTE-MA.md pentru activare)"
        ttk.Label(frame_src, text=dnd_hint_src, foreground="#777777").pack(
            anchor="w", padx=8, pady=(0, 8))

        if _DND_AVAILABLE:
            self.source_entry.drop_target_register(DND_FILES)
            self.source_entry.dnd_bind("<<Drop>>", self._on_source_drop)
            frame_src.drop_target_register(DND_FILES)
            frame_src.dnd_bind("<<Drop>>", self._on_source_drop)

        # Proiect / Card
        frame_meta = ttk.LabelFrame(self, text="Denumire automata folder (Data_Proiect_Card)")
        frame_meta.pack(fill="x", **pad)
        ttk.Label(frame_meta, text="Nume proiect:").grid(row=0, column=0, padx=8, pady=6, sticky="e")
        ttk.Entry(frame_meta, textvariable=self.project_var, width=25).grid(row=0, column=1, padx=8, pady=6, sticky="w")
        ttk.Label(frame_meta, text="Eticheta card:").grid(row=0, column=2, padx=8, pady=6, sticky="e")
        ttk.Entry(frame_meta, textvariable=self.card_var, width=20).grid(row=0, column=3, padx=8, pady=6, sticky="w")

        # Excluderi + optiuni
        frame_opts = ttk.LabelFrame(self, text="Optiuni de copiere")
        frame_opts.pack(fill="x", **pad)

        ttk.Label(frame_opts, text="Model de securitate (verificare):").grid(
            row=0, column=0, padx=8, pady=6, sticky="e")
        self.verification_labels = {v["label"]: k for k, v in VERIFICATION_MODELS.items()}
        self.verification_combo = ttk.Combobox(
            frame_opts, state="readonly", width=58,
            values=[v["label"] for v in VERIFICATION_MODELS.values()]
        )
        current_label = VERIFICATION_MODELS.get(
            self.verification_model_var.get(), VERIFICATION_MODELS[DEFAULT_VERIFICATION_MODEL]
        )["label"]
        self.verification_combo.set(current_label)
        self.verification_combo.grid(row=0, column=1, padx=8, pady=6, sticky="w", columnspan=2)
        self.verification_combo.bind("<<ComboboxSelected>>", self._on_verification_selected)

        ttk.Label(frame_opts, text="Exclude fisiere/extensii (separate prin virgula):").grid(
            row=1, column=0, padx=8, pady=6, sticky="w")
        ttk.Entry(frame_opts, textvariable=self.exclusions_var, width=50).grid(
            row=1, column=1, padx=8, pady=6, sticky="w", columnspan=2)
        ttk.Checkbutton(
            frame_opts, text="Sari peste fisiere deja identice la destinatie (economiseste timp la re-rulari)",
            variable=self.skip_existing_var
        ).grid(row=2, column=0, columnspan=3, padx=8, pady=(0, 6), sticky="w")

        # Destinatii
        frame_dest = ttk.LabelFrame(self, text="Destinatii (poti adauga oricate, copiere simultana)")
        frame_dest.pack(fill="both", expand=True, **pad)

        list_frame = ttk.Frame(frame_dest)
        list_frame.pack(fill="both", expand=True, padx=8, pady=8)

        self.dest_listbox = tk.Listbox(list_frame, height=5)
        self.dest_listbox.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.dest_listbox.yview)
        scrollbar.pack(side="left", fill="y")
        self.dest_listbox.config(yscrollcommand=scrollbar.set)

        btn_frame = ttk.Frame(frame_dest)
        btn_frame.pack(fill="x", padx=8, pady=(0, 4))
        ttk.Button(btn_frame, text="Adauga destinatie...", command=self._add_destination).pack(side="left")
        ttk.Button(btn_frame, text="Sterge selectia", command=self._remove_destination).pack(side="left", padx=8)

        dnd_hint_dest = "(sau trage unul sau mai multe foldere aici din Finder)" if _DND_AVAILABLE else \
            "(drag-and-drop indisponibil - vezi CITESTE-MA.md pentru activare)"
        ttk.Label(frame_dest, text=dnd_hint_dest, foreground="#777777").pack(
            anchor="w", padx=8, pady=(0, 8))

        if _DND_AVAILABLE:
            self.dest_listbox.drop_target_register(DND_FILES)
            self.dest_listbox.dnd_bind("<<Drop>>", self._on_dest_drop)
            frame_dest.drop_target_register(DND_FILES)
            frame_dest.dnd_bind("<<Drop>>", self._on_dest_drop)

        # Progres
        frame_progress = ttk.Frame(self)
        frame_progress.pack(fill="x", **pad)
        self.progress = ttk.Progressbar(frame_progress, orient="horizontal", mode="determinate")
        self.progress.pack(fill="x", side="top")
        info_row = ttk.Frame(frame_progress)
        info_row.pack(fill="x", pady=(4, 0))
        self.progress_label = ttk.Label(info_row, text="Inactiv")
        self.progress_label.pack(side="left")
        self.speed_label = ttk.Label(info_row, text="")
        self.speed_label.pack(side="right")

        # Butoane start/anuleaza
        action_row = ttk.Frame(self)
        action_row.pack(pady=(0, 6))
        self.start_btn = ttk.Button(action_row, text="Incepe offload-ul", command=self._start_offload)
        self.start_btn.pack(side="left", padx=6)
        self.cancel_btn = ttk.Button(action_row, text="Anuleaza", command=self._cancel_offload, state="disabled")
        self.cancel_btn.pack(side="left", padx=6)

        # Log
        frame_log = ttk.LabelFrame(self, text="Jurnal")
        frame_log.pack(fill="both", expand=True, **pad)
        self.log_text = tk.Text(frame_log, height=12, state="disabled", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)

    # ---------------- Volume / sursa ----------------

    def _refresh_volumes(self):
        volumes = list_mounted_volumes()
        self.volume_combo["values"] = volumes
        if volumes:
            self._append_log(f"Volume detectate: {len(volumes)} ({', '.join(os.path.basename(v) for v in volumes)})")
        else:
            self._append_log("Nu am detectat volume/drive-uri montate automat "
                              "(sau niciun card/drive extern nu e conectat). Poti alege manual sursa.")

    def _on_volume_selected(self, _event):
        self.source_var.set(self.volume_combo.get())

    def _on_verification_selected(self, _event):
        label = self.verification_combo.get()
        key = self.verification_labels.get(label, DEFAULT_VERIFICATION_MODEL)
        self.verification_model_var.set(key)

    def _choose_source(self):
        path = filedialog.askdirectory(title="Alege folderul sursa (cardul sau drive-ul)")
        if path:
            self.source_var.set(path)

    def _parse_dropped_paths(self, raw_data):
        """Finder trimite caile ca lista in format Tcl; foloseste tk.splitlist,
        care stie sa gestioneze corect caile cu spatii (acolade) sau ghilimele."""
        try:
            paths = self.tk.splitlist(raw_data)
        except Exception:
            paths = [raw_data]
        return [p for p in paths if p]

    def _on_source_drop(self, event):
        paths = self._parse_dropped_paths(event.data)
        if not paths:
            return
        folders = [p for p in paths if os.path.isdir(p)]
        if not folders:
            messagebox.showwarning("Atentie", "Te rog trage un folder (nu un fisier individual).")
            return
        if len(folders) > 1:
            self._append_log(f"Ai tras {len(folders)} foldere - folosesc doar primul ca sursa: {folders[0]}")
        self.source_var.set(folders[0])
        self._append_log(f"Sursa setata prin drag-and-drop: {folders[0]}")

    def _on_dest_drop(self, event):
        paths = self._parse_dropped_paths(event.data)
        if not paths:
            return
        added = 0
        for p in paths:
            if os.path.isdir(p) and p not in self.destinations:
                self.destinations.append(p)
                self.dest_listbox.insert("end", p)
                added += 1
            elif not os.path.isdir(p):
                self._append_log(f"Ignorat (nu e folder): {p}")
        if added:
            self._append_log(f"Adaugate {added} destinatie(i) prin drag-and-drop.")
        else:
            messagebox.showwarning("Atentie", "Te rog trage unul sau mai multe foldere (nu fisiere individuale).")

    # ---------------- Destinatii ----------------

    def _add_destination(self):
        path = filedialog.askdirectory(title="Alege un folder destinatie")
        if path and path not in self.destinations:
            self.destinations.append(path)
            self.dest_listbox.insert("end", path)

    def _remove_destination(self):
        sel = list(self.dest_listbox.curselection())
        for idx in reversed(sel):
            self.dest_listbox.delete(idx)
            del self.destinations[idx]

    # ---------------- Log / progres ----------------

    def _append_log(self, text):
        self.log_text.config(state="normal")
        self.log_text.insert("end", text + "\n")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _poll_log_queue(self):
        try:
            while True:
                line = self.log_queue.get_nowait()
                self._append_log(line)
        except queue.Empty:
            pass

        if self.running and self.total_units > 0:
            with self.progress_lock:
                done = self.progress_counter[0]
                bytes_done = self.bytes_counter[0]
            pct = int(done * 100 / self.total_units)
            self.progress["value"] = pct
            self.progress_label.config(text=f"{pct}%  ({done}/{self.total_units} fisiere)")

            if self.start_time:
                elapsed = (datetime.now() - self.start_time).total_seconds()
                if elapsed > 0:
                    speed = bytes_done / elapsed
                    self.speed_label.config(text=f"{format_size(speed)}/s")

            if done >= self.total_units:
                self._finish_session()

        self.after(150, self._poll_log_queue)

    def _finish_session(self):
        self.running = False
        self.start_btn.config(state="normal")
        self.cancel_btn.config(state="disabled")

        any_cancelled = any(j.cancelled for j in self.jobs)
        total_ok = sum(j.ok_count for j in self.jobs)
        total_fail = sum(j.fail_count for j in self.jobs)
        total_skip = sum(j.skip_count for j in self.jobs)

        if any_cancelled:
            self._append_log(">>> Sesiune anulata de utilizator.")
            send_notification("ShotPut Lite", "Offload anulat de utilizator.")
            messagebox.showwarning("ShotPut Lite", "Offload-ul a fost anulat.")
        else:
            self._append_log(
                f">>> Toate destinatiile au fost finalizate. Total: {total_ok} OK, "
                f"{total_skip} sarite, {total_fail} probleme."
            )
            send_notification(
                "ShotPut Lite",
                f"Offload complet: {total_ok} OK, {total_fail} probleme pe "
                f"{len(self.jobs)} destinatie(i)."
            )
            if total_fail > 0:
                messagebox.showwarning(
                    "ShotPut Lite",
                    f"Offload complet, dar cu {total_fail} probleme. Verifica jurnalul si rapoartele PDF/CSV."
                )
            else:
                messagebox.showinfo("ShotPut Lite", "Offload complet, toate fisierele verificate cu succes.")

    # ---------------- Logica principala ----------------

    def _parse_exclusions(self):
        raw = self.exclusions_var.get()
        return [p.strip() for p in raw.split(",") if p.strip()]

    def _save_settings(self):
        cfg.save_config({
            "project": self.project_var.get().strip(),
            "card": self.card_var.get().strip(),
            "destinations": self.destinations,
            "exclusions": self.exclusions_var.get(),
            "skip_existing_identical": self.skip_existing_var.get(),
            "verification_model": self.verification_model_var.get(),
        })

    def _start_offload(self):
        source = self.source_var.get().strip()
        if not source or not os.path.isdir(source):
            messagebox.showerror("Eroare", "Alege un folder sursa valid.")
            return
        if not self.destinations:
            messagebox.showerror("Eroare", "Adauga cel putin o destinatie.")
            return

        project = self.project_var.get().strip() or "Proiect"
        card = self.card_var.get().strip() or "Card"
        date_str = datetime.now().strftime("%Y-%m-%d")
        folder_name = f"{date_str}_{project}_{card}".replace(" ", "_")
        exclusions = self._parse_exclusions()

        current_label = VERIFICATION_MODELS.get(
            self.verification_model_var.get(), VERIFICATION_MODELS[DEFAULT_VERIFICATION_MODEL]
        )["label"]
        self._append_log(f"Model de verificare folosit: {current_label}")
        self._append_log(f"Se scaneaza sursa: {source} ...")
        files = list_all_files(source, exclusions=exclusions)
        if not files:
            messagebox.showwarning("Atentie", "Nu am gasit niciun fisier relevant in sursa selectata "
                                               "(sau toate au fost excluse).")
            return

        total_size = sum(size for _f, _r, size in files)

        # verificare spatiu liber pe fiecare destinatie
        insufficient = []
        for dest in self.destinations:
            free = get_free_space_bytes(dest)
            if free is not None and free < total_size:
                insufficient.append(f"{dest} (liber: {format_size(free)}, necesar: {format_size(total_size)})")
        if insufficient:
            proceed = messagebox.askyesno(
                "Spatiu insuficient",
                "Spatiu liber insuficient pe urmatoarele destinatii:\n\n" +
                "\n".join(insufficient) +
                "\n\nVrei sa continui oricum?"
            )
            if not proceed:
                return

        self._append_log(
            f"Am gasit {len(files)} fisiere ({format_size(total_size)}). "
            f"Se incepe copierea catre {len(self.destinations)} destinatie(i)..."
        )

        self._save_settings()

        self.progress_counter = [0]
        self.bytes_counter = [0]
        self.total_units = len(files) * len(self.destinations)
        self.total_bytes = total_size * len(self.destinations)
        self.running = True
        self.start_time = datetime.now()
        self.progress["value"] = 0
        self.progress_label.config(text="Se pregateste...")
        self.speed_label.config(text="")
        self.start_btn.config(state="disabled")
        self.cancel_btn.config(state="normal")
        self.cancel_event = threading.Event()

        self.jobs = [
            DestinationJob(
                dest, folder_name, files, self.log_queue,
                self.progress_counter, self.bytes_counter, self.progress_lock,
                skip_existing_identical=self.skip_existing_var.get(),
                cancel_event=self.cancel_event,
                verification_model=self.verification_model_var.get(),
            )
            for dest in self.destinations
        ]

        for job in self.jobs:
            t = threading.Thread(target=job.run, daemon=True)
            t.start()

    def _cancel_offload(self):
        if self.running:
            confirmed = messagebox.askyesno("Anuleaza", "Sigur vrei sa anulezi offload-ul in curs?")
            if confirmed:
                self.cancel_event.set()
                self._append_log(">>> Se anuleaza... (fisierul curent se termina de copiat, apoi se opreste)")
                self.cancel_btn.config(state="disabled")

    def _on_close(self):
        if self.running:
            if not messagebox.askyesno(
                "Iesire", "Un offload este in curs. Sigur vrei sa inchizi aplicatia? "
                          "Copierea in desfasurare va fi intrerupta."
            ):
                return
            self.cancel_event.set()
        self._save_settings()
        self.destroy()


if __name__ == "__main__":
    app = ShotPutLiteApp()
    app.mainloop()
