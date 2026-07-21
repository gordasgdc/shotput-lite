"""
DOAR PENTRU MAC. Optional: foloseste acest fisier daca vrei un ".app" real,
cu iconita, in loc de fisierul "Porneste ShotPut Lite.command".
Pentru Windows, vezi sectiunea despre PyInstaller din CITESTE-MA.md.

Pasi (in Terminal, pe Mac, in acest folder):
    python3 -m venv .venv-build
    source .venv-build/bin/activate
    pip install py2app reportlab tkinterdnd2 plyer
    python3 setup.py py2app
    deactivate

Rezultatul apare in folderul "dist/ShotPut Lite.app" - il poti muta apoi
in Applications si il lansezi cu dublu-click ca orice alta aplicatie Mac.
"""

from setuptools import setup

APP = ["main.py"]
DATA_FILES = ["offload_engine.py", "pdf_report.py", "config.py"]
OPTIONS = {
    "argv_emulation": False,
    "packages": ["reportlab", "tkinterdnd2", "plyer"],
    "includes": ["offload_engine", "pdf_report", "config"],
    "plist": {
        "CFBundleName": "ShotPut Lite",
        "CFBundleDisplayName": "ShotPut Lite",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleIdentifier": "personal.shotputlite",
    },
}

setup(
    app=APP,
    name="ShotPut Lite",
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)

