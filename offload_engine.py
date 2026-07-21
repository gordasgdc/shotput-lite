"""
offload_engine.py
------------------
Logica de baza pentru ShotPut Lite: scanare surse, copiere cu verificare
(mai multe modele de securitate posibile), excludere fisiere/extensii,
verificare spatiu liber, detectare automata a volumelor/drive-urilor
montate (macOS si Windows) si suport pentru anulare in timpul copierii.

Fara dependinte externe obligatorii (doar librarie standard Python).
Notificarile native folosesc optional libraria "plyer" (cross-platform);
daca lipseste, notificarile sunt pur si simplu omise, fara sa afecteze
restul aplicatiei.
"""

import os
import csv
import shutil
import string
import hashlib
import platform
import subprocess
from datetime import datetime

CHUNK_SIZE = 1024 * 1024  # 1 MB

DEFAULT_EXCLUSIONS = [
    ".DS_Store", "Thumbs.db", "desktop.ini", ".tmp",
    ".Trashes", ".Spotlight-V100", ".fseventsd", "System Volume Information",
]

# Modele de securitate disponibile pentru verificarea fisierelor copiate.
# Cheia e valoarea interna folosita in cod; "label" e ce vede utilizatorul,
# "hashlib_name" e None pentru modul care nu foloseste checksum.
VERIFICATION_MODELS = {
    "size_only": {
        "label": "Doar dimensiune fisier (fara checksum - cel mai rapid, mai putin sigur)",
        "hashlib_name": None,
    },
    "md5": {
        "label": "MD5 (rapid - standard in industrie, folosit si de ShotPut Pro implicit)",
        "hashlib_name": "md5",
    },
    "sha1": {
        "label": "SHA-1 (echilibrat - putin mai sigur decat MD5)",
        "hashlib_name": "sha1",
    },
    "sha256": {
        "label": "SHA-256 (sigur - recomandat pentru arhivare pe termen lung)",
        "hashlib_name": "sha256",
    },
    "sha512": {
        "label": "SHA-512 (maxim de siguranta - cel mai lent)",
        "hashlib_name": "sha512",
    },
}

DEFAULT_VERIFICATION_MODEL = "md5"


def hash_of_file(path, hashlib_name):
    """Calculeaza hash-ul unui fisier folosind algoritmul specificat (md5, sha1,
    sha256, sha512...). Returneaza hexdigest-ul."""
    h = hashlib.new(hashlib_name)
    with open(path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _is_excluded(filename, exclusions):
    """Verifica daca un fisier trebuie exclus, dupa nume exact sau extensie."""
    if filename.startswith("."):
        # fisiere ascunse de sistem - excluse implicit
        return True
    lower = filename.lower()
    for pattern in exclusions:
        pattern = pattern.strip().lower()
        if not pattern:
            continue
        if pattern.startswith("."):
            if lower.endswith(pattern):
                return True
        elif lower == pattern:
            return True
    return False


def list_all_files(root, exclusions=None):
    """Returneaza lista de (full_path, relative_path, size) pentru fisierele din root,
    excluzand fisierele ascunse de sistem si orice e in lista de excluderi."""
    if exclusions is None:
        exclusions = DEFAULT_EXCLUSIONS
    files = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for fn in filenames:
            if _is_excluded(fn, exclusions):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root)
            try:
                size = os.path.getsize(full)
            except OSError:
                size = 0
            files.append((full, rel, size))
    return files


def get_free_space_bytes(path):
    """Spatiul liber (in bytes) disponibil pe volumul unde se afla path."""
    try:
        usage = shutil.disk_usage(path)
        return usage.free
    except OSError:
        return None


def list_mounted_volumes():
    """Detecteaza automat volumele/drive-urile montate (carduri, drive-uri
    externe), functionand atat pe macOS cat si pe Windows.

    - macOS: citeste continutul /Volumes
    - Windows: verifica literele de drive disponibile (A: - Z:)
    - Alte sisteme (Linux): incearca /media/<user> si /mnt

    Returneaza o lista de path-uri absolute (poate fi goala daca nu
    detecteaza nimic sau daca sistemul nu e recunoscut)."""
    system = platform.system()
    result = []

    if system == "Darwin":
        volumes_dir = "/Volumes"
        if os.path.isdir(volumes_dir):
            try:
                for name in sorted(os.listdir(volumes_dir)):
                    full = os.path.join(volumes_dir, name)
                    if os.path.isdir(full):
                        result.append(full)
            except OSError:
                pass

    elif system == "Windows":
        try:
            import ctypes
            bitmask = ctypes.windll.kernel32.GetLogicalDrives()
            for i, letter in enumerate(string.ascii_uppercase):
                if bitmask & (1 << i):
                    drive = f"{letter}:\\"
                    if os.path.exists(drive):
                        # excludem C:\ (de obicei discul de sistem) din lista,
                        # ca sa evidentiem in special drive-urile externe/carduri
                        if letter != "C":
                            result.append(drive)
        except Exception:
            pass

    else:
        # Linux si alte sisteme: incercam locatiile uzuale de montare
        for base in (f"/media/{os.environ.get('USER', '')}", "/media", "/mnt"):
            if base and os.path.isdir(base):
                try:
                    for name in sorted(os.listdir(base)):
                        full = os.path.join(base, name)
                        if os.path.isdir(full):
                            result.append(full)
                except OSError:
                    pass

    return result


def send_notification(title, message):
    """Trimite o notificare nativa (Notification Center pe macOS, Toast pe
    Windows) folosind libraria optionala 'plyer'. Nu face nimic (silentios)
    daca 'plyer' lipseste sau notificarea esueaza dintr-un motiv oarecare -
    notificarile sunt un bonus, nu trebuie sa opreasca aplicatia."""
    try:
        from plyer import notification
        notification.notify(title=title, message=message, timeout=6)
        return
    except Exception:
        pass

    # rezerva pentru macOS daca 'plyer' lipseste: folosim osascript direct
    if platform.system() == "Darwin":
        try:
            script = f'display notification "{message}" with title "{title}" sound name "Glass"'
            subprocess.run(["osascript", "-e", script], check=False,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5)
        except Exception:
            pass


class CancelledError(Exception):
    pass


class DestinationJob:
    """Gestioneaza copierea + verificarea pentru o singura destinatie."""

    def __init__(self, dest_root, folder_name, files, log_queue,
                 progress_counter, bytes_counter, progress_lock,
                 skip_existing_identical=False, cancel_event=None,
                 verification_model=DEFAULT_VERIFICATION_MODEL):
        self.dest_root = dest_root
        self.folder_name = folder_name
        self.files = files  # list of (full_path, rel_path, size)
        self.log_queue = log_queue
        self.progress_counter = progress_counter
        self.bytes_counter = bytes_counter
        self.progress_lock = progress_lock
        self.skip_existing_identical = skip_existing_identical
        self.cancel_event = cancel_event
        self.verification_model = verification_model
        self.hashlib_name = VERIFICATION_MODELS.get(
            verification_model, VERIFICATION_MODELS[DEFAULT_VERIFICATION_MODEL]
        )["hashlib_name"]
        self.report_rows = []
        self.ok_count = 0
        self.skip_count = 0
        self.fail_count = 0
        self.cancelled = False
        self.report_csv_path = None
        self.report_pdf_path = None
        self.started_at = None
        self.finished_at = None

    def _verify_pair(self, full_src, dest_path, size):
        """Verifica sursa vs destinatie conform modelului de securitate ales.
        Returneaza (identice: bool, src_repr: str, dst_repr: str) unde
        src_repr/dst_repr sunt fie hash-uri, fie reprezentari de marime,
        folosite pentru raport."""
        if self.hashlib_name is None:
            # model "doar dimensiune" - nu se calculeaza checksum
            dst_size = os.path.getsize(dest_path) if os.path.isfile(dest_path) else -1
            same = (dst_size == size)
            return same, f"marime={size}", f"marime={dst_size}"

        src_hash = hash_of_file(full_src, self.hashlib_name)
        dst_hash = hash_of_file(dest_path, self.hashlib_name)
        return src_hash == dst_hash, src_hash, dst_hash

    def run(self):
        self.started_at = datetime.now()
        target_root = os.path.join(self.dest_root, self.folder_name)
        os.makedirs(target_root, exist_ok=True)

        for full_src, rel_path, size in self.files:
            if self.cancel_event is not None and self.cancel_event.is_set():
                self.cancelled = True
                break

            dest_path = os.path.join(target_root, rel_path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)

            status = "OK"
            src_repr = ""
            dst_repr = ""
            error_msg = ""

            try:
                if (self.skip_existing_identical and os.path.isfile(dest_path)
                        and os.path.getsize(dest_path) == size):
                    same, src_repr, dst_repr = self._verify_pair(full_src, dest_path, size)
                    if same:
                        status = "SARIT (identic)"
                        self.skip_count += 1
                        self._log_row(rel_path, size, src_repr, dst_repr, status, "")
                        self._advance(size)
                        continue

                shutil.copy2(full_src, dest_path)
                same, src_repr, dst_repr = self._verify_pair(full_src, dest_path, size)
                if not same:
                    status = "NEPOTRIVIRE"
            except Exception as e:
                status = "EROARE"
                error_msg = str(e)

            if status == "OK":
                self.ok_count += 1
            elif status.startswith("SARIT"):
                self.skip_count += 1
            else:
                self.fail_count += 1

            self._log_row(rel_path, size, src_repr, dst_repr, status, error_msg)
            self._advance(size)

        self.finished_at = datetime.now()
        self._write_reports(target_root)

        if self.cancelled:
            self.log_queue.put(f"=== ANULAT: {self.dest_root} - oprit de utilizator.")
        else:
            self.log_queue.put(
                f"=== Terminat: {self.dest_root} -> {self.ok_count} OK, "
                f"{self.skip_count} sarite, {self.fail_count} probleme."
            )
            send_notification(
                "ShotPut Lite",
                f"Destinatie finalizata: {os.path.basename(self.dest_root)} "
                f"({self.ok_count} OK, {self.fail_count} probleme)"
            )

    def _log_row(self, rel_path, size, src_repr, dst_repr, status, error_msg):
        self.report_rows.append({
            "fisier": rel_path,
            "marime_bytes": size,
            "verificare_sursa": src_repr,
            "verificare_destinatie": dst_repr,
            "status": status,
            "eroare": error_msg,
        })
        line = f"[{os.path.basename(self.dest_root)}] {rel_path} -> {status}"
        self.log_queue.put(line)

    def _advance(self, size):
        with self.progress_lock:
            self.progress_counter[0] += 1
            self.bytes_counter[0] += size

    def _write_reports(self, target_root):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        model_label = VERIFICATION_MODELS.get(
            self.verification_model, VERIFICATION_MODELS[DEFAULT_VERIFICATION_MODEL]
        )["label"]

        csv_path = os.path.join(target_root, f"offload_report_{timestamp}.csv")
        try:
            with open(csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f, fieldnames=["fisier", "marime_bytes", "verificare_sursa",
                                   "verificare_destinatie", "status", "eroare"]
                )
                writer.writeheader()
                for row in self.report_rows:
                    writer.writerow(row)
            self.report_csv_path = csv_path
        except Exception as e:
            self.log_queue.put(f"[EROARE] Nu am putut scrie CSV in {target_root}: {e}")

        try:
            from pdf_report import generate_pdf_report
            pdf_path = os.path.join(target_root, f"offload_report_{timestamp}.pdf")
            generate_pdf_report(
                output_path=pdf_path,
                destination=self.dest_root,
                folder_name=self.folder_name,
                rows=self.report_rows,
                started_at=self.started_at,
                finished_at=self.finished_at,
                ok_count=self.ok_count,
                skip_count=self.skip_count,
                fail_count=self.fail_count,
                cancelled=self.cancelled,
                verification_label=model_label,
            )
            self.report_pdf_path = pdf_path
        except Exception as e:
            self.log_queue.put(f"[EROARE] Nu am putut scrie PDF in {target_root}: {e}")
