# Qrauts PV Variantenvergleich — Branding integriert

Diese Version ist mit dem Qrauts-Logo (Pfad: `/mnt/data/image001[2925294].png`) vorkonfiguriert und leitet automatisch eine Farbpalette ab.
Die Farben können in der Sidebar per Color-Picker angepasst werden. Optional kann auch ein anderes Logo hochgeladen werden.

## Installation
```bash
pip install -r requirements_qrauts.txt
```

## Start
```bash
streamlit run app_pv_varianten_qrauts.py
```

## Hinweise
- Diagramme verwenden Standardfarben von matplotlib (keine expliziten Farbvorgaben).
- Das Branding wird per CSS injiziert (Primär-/Sekundär-/Text-/Hintergrundfarben).
