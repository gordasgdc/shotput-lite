# ShotPut Lite

O aplicație personală/echipă pentru offload verificat de fișiere media —
inspirată de ShotPut Pro. Copiază fișiere de pe un card/drive către una
sau mai multe destinații **simultan**, verifică fiecare fișier (checksum
configurabil), denumește automat folderul de destinație, și generează
rapoarte profesionale **CSV + PDF**.

Funcționează pe **macOS** și pe **Windows**.

## Funcții

- **Iconiță personalizată** — inclusă pentru `.app` (Mac) și `.exe` (Windows), generată automat la compilare
- **Drag-and-drop** — tragi direct folderul sursă (cardul) peste aplicație, la fel și pentru destinații (poți trage mai multe foldere deodată); butoanele "Alege manual..." rămân disponibile ca alternativă
- **Copiere simultană** către oricâte destinații (drive extern, NAS, folder local etc.)
- **Model de securitate selectabil** — alegi între MD5 (rapid, standard), SHA-1, SHA-256, SHA-512 (maxim de siguranță) sau doar verificare de dimensiune (cel mai rapid, fără checksum) — compromis viteză/siguranță, la fel ca la ShotPut Pro
- **Verificare** pentru fiecare fișier, conform modelului ales — te asiguri că datele au ajuns intacte
- **Denumire automată a folderului** de destinație: `Data_Proiect_Card` (ex: `2026-07-21_NuntaAna_CardA`)
- **Rapoarte CSV + PDF** per destinație, cu status colorat (OK / Nepotrivire / Eroare / Sărit) și sumar
- **Notificări native** (Notification Center pe macOS, Toast pe Windows) când se termină fiecare destinație și la finalul întregii sesiuni
- **Detectare automată a cardurilor/drive-urilor montate** (pe Mac citește `/Volumes`; pe Windows detectează literele de drive `D:\`, `E:\` etc.), cu buton de reîmprospătare
- **Excludere fișiere/extensii** (implicit: `.DS_Store`, `Thumbs.db`, `desktop.ini`, `.tmp` etc., plus orice adaugi tu)
- **Verificare spațiu liber** înainte de start — te avertizează dacă o destinație nu are loc suficient
- **Buton de anulare** — poți opri copierea în siguranță în orice moment
- **"Sări peste fișiere identice"** — la re-rulări, nu recopiază ce e deja verificat corect la destinație
- **Setările se salvează automat** (proiect, card, destinații, excluderi) — nu mai retastezi de fiecare dată
- **Viteză de transfer și progres în timp real** (MB/s, fișiere copiate/total)

## Structura fișierelor

```
ShotPutLite/
├── main.py                                 <- interfata grafica
├── offload_engine.py                       <- logica de copiere/verificare/scanare
├── pdf_report.py                            <- generarea rapoartelor PDF
├── config.py                                <- salvarea automata a setarilor
├── Porneste ShotPut Lite.command            <- lansator pentru Mac (dublu-click)
├── Porneste ShotPut Lite (Windows).bat      <- lansator pentru Windows (dublu-click)
├── setup.py                                 <- optional, pentru pachetare .app (Mac)
├── ShotPutLite.icns                         <- iconita gata de folosit pentru Mac
├── ShotPutLite.ico                          <- iconita gata de folosit pentru Windows
├── icon_master.png                          <- iconita la rezolutie mare (referinta/arhiva)
├── .github/workflows/build-windows.yml      <- optional, compileaza .exe automat in cloud
├── .github/workflows/build-mac.yml          <- optional, compileaza .app automat in cloud
└── CITESTE-MA.md                            <- acest fisier
```

Toate cele 4 fișiere `.py` trebuie să rămână împreună, în același folder,
indiferent de sistemul de operare. Fișierele de iconiță (`ShotPutLite.icns`,
`ShotPutLite.ico`, `icon_master.png`) sunt folosite automat de workflow-urile
GitHub Actions și de `setup.py` — nu trebuie să faci nimic manual cu ele
dacă folosești build-ul din cloud.

**Notă despre descărcare:** dacă descarci fișierele individual din chat
(nu ca o arhivă unică), verifică după copiere că toate fișierele de mai
sus există local — unele browsere/Finder pot omite fișiere dacă le tragi
unul câte unul. Cel mai sigur e să le descarci pe rând și să confirmi cu
`ls -la` în Terminal că regăsești fiecare nume exact ca mai sus.

---

## Instalare pe Mac

**Cerințe:**
- macOS (orice versiune recentă)
- Python 3 (majoritatea Mac-urilor moderne îl au deja; altfel:
  https://www.python.org/downloads/macos/)
- Dacă la pornire apare eroare legată de "tkinter": `brew install python-tk`

**Pornire:**
1. Copiază tot folderul `ShotPutLite` pe Mac.
2. Dublu-click pe **"Porneste ShotPut Lite.command"**.
   - Dacă macOS blochează fișierul ("nu poate fi deschis pentru că vine de
     la un dezvoltator neidentificat"): click-dreapta pe fișier → Open →
     confirmă "Open" în fereastra de avertizare. Se face o singură dată.
3. La prima rulare, aplicația își creează automat un mediu Python izolat
   (`.venv`, în interiorul folderului) și instalează acolo `reportlab`
   (rapoarte PDF), `tkinterdnd2` (drag-and-drop) și `plyer` (notificări) —
   fără să atingă Python-ul de sistem. Asta evită complet eroarea
   `externally-managed-environment`, întâlnită pe Mac-urile cu Python
   instalat prin Homebrew. Durează câteva secunde, e nevoie de internet
   doar în acel moment.
4. Se deschide fereastra aplicației.

Dacă vreo librărie opțională nu se instalează (rar, ex. probleme de
rețea), aplicația pornește oricum — funcția respectivă (PDF, drag-and-drop
sau notificări) e pur și simplu dezactivată, restul merge normal.

### Opțional: transformare într-un `.exe` — compilat automat în cloud (de pe Mac, fără Windows)

`py2app` (folosit pe Mac) și `PyInstaller` construiesc doar pentru sistemul
pe care rulează — deci nu poți crea un `.exe` direct de pe Mac local. Dar
poți folosi **GitHub Actions**: un calculator Windows temporar, gratuit,
în cloud, care compilează `.exe`-ul pentru tine. Fișierul de configurare
(`.github/workflows/build-windows.yml`) e deja inclus în acest folder.

**Pași (totul se face de pe Mac, din Terminal sau din aplicația GitHub Desktop):**

1. **Cont GitHub** — dacă nu ai deja, creează unul gratuit pe github.com.

2. **Creează un repository nou** pe github.com (buton verde "New"). Poate
   fi *Public* (nelimitat, gratuit) sau *Private* (gratuit, cu minute
   Actions limitate lunar — suficient pentru un proiect ca acesta). Nu
   bifa "Add a README" (avem deja unul).

3. **Trimite codul pe GitHub** — în Terminal, în folderul `ShotPutLite`:
   ```bash
   git init
   git add .
   git commit -m "Prima versiune ShotPut Lite"
   git branch -M main
   git remote add origin https://github.com/NUMELE_TAU/NUMELE_REPO.git
   git push -u origin main
   ```
   (Înlocuiește URL-ul cu cel afișat de GitHub după ce creezi repo-ul —
   îl găsești pe pagina repo-ului, sub "…or push an existing repository".
   La primul push, GitHub îți va cere autentificare — urmează instrucțiunile
   afișate în Terminal.)

4. **Build-ul pornește automat** — de îndată ce faci `git push`, GitHub
   deschide un Windows temporar în cloud și rulează compilarea. Mergi pe
   pagina repo-ului → tab-ul **"Actions"** → vezi rularea în curs (un cerc
   galben care se învârte, apoi ✅ verde când termină — durează ~2-3 minute).

5. **Descarcă `.exe`-ul** — click pe rularea terminată → în josul paginii,
   la secțiunea **"Artifacts"**, apeși pe `ShotPut-Lite-Windows` — se
   descarcă o arhivă `.zip` care conține `ShotPut Lite.exe`.

6. Trimite acel `.exe` colegilor cu Windows — îl pot rula direct cu
   dublu-click, fără să mai instaleze Python sau altceva (PyInstaller
   `--onefile` include tot ce e necesar în interiorul `.exe`-ului).

**De reținut:** de fiecare dată când modifici codul (`main.py` etc.) și
faci din nou `git push`, se generează automat o versiune nouă de `.exe`
— nu trebuie să repeți pașii 1-3, doar `git add . && git commit -m "..." && git push`.

### Alternativ: `.app` pentru Mac (fără Windows, direct local)

```bash
cd ShotPutLite
python3 -m venv .venv-build
source .venv-build/bin/activate
pip install py2app reportlab tkinterdnd2 plyer
python3 setup.py py2app
deactivate
```

Rezultatul apare în `dist/ShotPut Lite.app`, cu iconița inclusă. Îl poți
muta în `/Applications`. Neavând cont Apple Developer, la prima rulare pe
fiecare Mac va trebui aprobat o dată prin click-dreapta → Open.

---

## Instalare pe Windows

**Cerințe:**
- Windows 10 sau 11
- Python 3, instalat de pe https://www.python.org/downloads/windows/
  - **Important la instalare:** bifează opțiunea **"Add python.exe to PATH"**
    din primul ecran al instalatorului — altfel scriptul de pornire nu va
    găsi Python.
  - `tkinter` vine deja inclus în instalatorul oficial de Python pentru
    Windows (nu e nevoie de nimic suplimentar, spre deosebire de unele
    distribuții Linux/Homebrew).

**Pornire:**
1. Copiază tot folderul `ShotPutLite` pe calculator.
2. Dublu-click pe **"Porneste ShotPut Lite (Windows).bat"**.
   - Dacă Windows SmartScreen avertizează ("Windows protected your PC"):
     click pe "More info" → "Run anyway". Se face o singură dată.
3. La prima rulare, aplicația își creează automat un mediu Python izolat
   (folderul `.venv`) și instalează acolo `reportlab`, `tkinterdnd2` și
   `plyer`. Durează câteva secunde, e nevoie de internet doar atunci.
4. Se deschide fereastra aplicației (fără fereastră neagră de consolă in fundal).

### Note specifice Windows

- Detectarea automată a "volumelor" arată literele de drive disponibile
  (ex. `D:\`, `E:\`) — de obicei cardul de memorie sau drive-ul extern
  apare acolo după ce îl conectezi; apasă "Reîmprospătează" dacă tocmai
  l-ai băgat.
- Discul `C:\` (de obicei discul de sistem) e exclus automat din lista de
  volume detectate, ca să nu-l alegi din greșeală ca sursă sau destinație.
- Notificările folosesc Windows Toast Notifications (colțul din dreapta-jos).

### Opțional: transformare într-un `.exe`

Dacă vrei un `.exe` compilat, fără să ai nevoie de un Windows fizic,
folosește **GitHub Actions** — vezi secțiunea detaliată "transformare
într-un `.exe` — compilat automat în cloud" din partea de Mac de mai sus
(pașii sunt identici, indiferent de pe ce sistem pornești).

Dacă totuși ai acces direct la un Windows (fizic sau VM) și preferi să
compilezi local, fără GitHub:

```bat
cd ShotPutLite
python -m venv .venv-build
.venv-build\Scripts\activate
pip install pyinstaller reportlab tkinterdnd2 plyer
pyinstaller --onefile --windowed --name "ShotPut Lite" --icon=ShotPutLite.ico main.py
deactivate
```

Rezultatul apare în `dist\ShotPut Lite.exe`.

---

## Cum îl folosești (identic pe Mac și Windows)

1. **Sursa** — trei variante: tragi folderul cardului/drive-ului direct
   peste câmpul de sursă, alegi din lista "Volume detectate automat"
   (cardul apare acolo dacă e conectat), sau apeși "Alege manual...".
   Butonul "Reîmprospătează" recitește lista dacă tocmai ai conectat cardul.
2. **Nume proiect / Etichetă card** — ex: `NuntaAna` / `CardA`. Folderul
   rezultat pe fiecare destinație va fi `2026-07-21_NuntaAna_CardA`.
3. **Opțiuni de copiere** — alegi **modelul de securitate** (verificare)
   din listă:
   - *Doar dimensiune fișier* — cel mai rapid, doar compară mărimea (fără garanție criptografică)
   - *MD5* — rapid, standard în industrie (setat implicit)
   - *SHA-1* — puțin mai lent, ceva mai sigur decât MD5
   - *SHA-256* — recomandat pentru arhivare pe termen lung
   - *SHA-512* — maxim de siguranță, cel mai lent

   Poți edita și lista de excluderi (ex: adaugă `.wav` dacă nu vrei să
   copiezi și sunetul separat) și poți bifa "Sări peste fișiere identice"
   pentru re-rulări rapide.
4. **Destinații** — adaugi oricâte ai nevoie: tragi unul sau mai multe
   foldere deodată direct peste lista de destinații, sau apeși
   "Adaugă destinație...". Toate se completează simultan, în paralel.
5. Apeși **"Începe offload-ul"**. Dacă o destinație nu are spațiu
   suficient, primești o avertizare înainte de start.
6. Jurnalul arată status per fișier. Bara de progres arată procent,
   fișiere copiate și viteza curentă (MB/s).
7. Poți apăsa **"Anulează"** oricând — copierea fișierului curent se
   termină, apoi se oprește (nu lasă fișiere pe jumătate scrise).
8. Când se termină, primești o notificare nativă și un rezumat. În
   fiecare folder de destinație găsești `offload_report_*.csv` și
   `offload_report_*.pdf` cu toate detaliile.

## Pentru echipă

Distribuie folderul `ShotPutLite` fiecărui membru al echipei — Mac sau
Windows, fiecare folosește lansatorul potrivit sistemului lui
(`.command` sau `.bat`). Nu există licențe sau activări — rulează local,
fără cont, fără internet (cu excepția instalării unice a dependințelor).

## Idei de extindere pe viitor

Dacă vrei mai mult: suport pentru formate specifice de cameră (ARRI, RED,
etc.), rapoarte agregate pentru o sesiune întreagă cu mai multe carduri,
un istoric al tuturor sesiunilor anterioare căutabil, sau o variantă
companion pe telefon pentru a urmări progresul de la distanță — spune-mi
ce prioritizezi și le adaug.
