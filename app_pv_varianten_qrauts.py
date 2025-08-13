
import streamlit as st
import pandas as pd
import numpy as np
import io
import matplotlib.pyplot as plt
from PIL import Image
from collections import Counter
from pathlib import Path

st.set_page_config(page_title="Qrauts · PV-Variantenvergleich", layout="wide")

# ---------- Branding helpers ----------
def rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)

def extract_palette(img: Image.Image, n=3):
    """Return up to n dominant colors from an image as hex strings (simple histogram-based)."""
    small = img.convert("RGBA").resize((64, 64))
    pixels = [p for p in small.getdata() if p[3] > 0]
    def is_noise(c):
        r,g,b,_ = c
        return (r>240 and g>240 and b>240) or (r<15 and g<15 and b<15)
    filtered = [c for c in pixels if not is_noise(c)]
    if not filtered:
        filtered = pixels
    cnt = Counter((r,g,b) for r,g,b,_ in filtered)
    common = [rgb_to_hex(c) for c,_ in cnt.most_common(n)]
    uniq = []
    for h in common:
        if h not in uniq:
            uniq.append(h)
    defaults = ["#F28C28", "#2F2F2F", "#FFFFFF"]
    i = 0
    while len(uniq) < n:
        uniq.append(defaults[i % len(defaults)])
        i += 1
    return uniq[:n]

def inject_theme_css(primary, secondary, text, bg):
    css = f"""
    <style>
    :root {{
        --primary: {primary};
        --secondary: {secondary};
        --text: {text};
        --bg: {bg};
    }}
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(180deg, var(--bg) 0%, #ffffff 100%) !important;
    }}
    h1, h2, h3, h4, h5, h6, .stMarkdown p, label {{
        color: var(--text) !important;
    }}
    .stButton > button, .stDownloadButton > button {{
        color: #ffffff !important;
        border: 0 !important;
        border-radius: 12px !important;
        padding: 0.6rem 1rem !important;
    }}
    .stButton > button {{ background: var(--primary) !important; }}
    .stDownloadButton > button {{ background: var(--secondary) !important; }}
    .stDataFrame {{
        border: 1px solid #eaeaea;
        border-radius: 12px;
    }}
    .block-container {{
        padding-top: 1rem;
    }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

# ---------- Load default logo & derive palette ----------
default_logo_path = Path("/mnt/data/image001[2925294].png")
preloaded_logo = None
palette_from_logo = ["#F28C28", "#2F2F2F", "#FFFFFF"]

if default_logo_path.exists():
    try:
        preloaded_logo = Image.open(default_logo_path)
        palette_from_logo = extract_palette(preloaded_logo, n=3)
    except Exception:
        preloaded_logo = None

# ---------- UI Header ----------
left, right = st.columns([1,3])
with left:
    if preloaded_logo is not None:
        st.image(preloaded_logo, use_column_width=True)
with right:
    st.title("PV-Variantenvergleich")
    st.caption("Qrauts · Dachpacht · Anlagenpacht · Lieferkettenmodell — mit CO₂-Gutschrift für das Gebäude")

# ---------- Sidebar: branding ----------
with st.sidebar:
    st.header("🎨 Branding")
    st.write("Logo ist **vorkonfiguriert**. Optional eigenes PNG hochladen, um Farben neu abzuleiten.")
    logo_file = st.file_uploader("Firmenlogo (PNG)", type=["png"])
    if logo_file is not None:
        try:
            uploaded = Image.open(logo_file)
            palette = extract_palette(uploaded, n=3)
            st.image(uploaded, caption="Logo-Vorschau (Upload)", use_column_width=True)
        except Exception:
            palette = palette_from_logo
    else:
        palette = palette_from_logo

    colb1, colb2 = st.columns(2)
    with colb1:
        primary = st.color_picker("Primärfarbe", palette[0])
        text_color = st.color_picker("Textfarbe", "#FFFFFF" if palette[2] == "#FFFFFF" else palette[2])
    with colb2:
        secondary = st.color_picker("Sekundärfarbe", palette[1])
        bg_color = st.color_picker("Hintergrund (Startverlauf)", "#000000")
    inject_theme_css(primary, secondary, text_color, bg_color)

with st.expander("Methodik & Annahmen", expanded=False):
    st.markdown(
        """
- **Ziel:** Wirtschaftlicher Vergleich dreier Modelle aus Sicht der WG UNITAS.
- **Lastdeckung:** PV-Erzeugung bedient zuerst die **Mieterstrom-Nachfrage**, danach **Allgemeinstrom/Wärmepumpe**. Überschüsse werden konservativ **nicht** bepreist (optional erweiterbar).
- **Einnahmen WG UNITAS je Modell:**
  - **Dachpachtmodell:** Fixe Dachpacht (€/a).
  - **Anlagenpachtmodell:** Erlöse aus Stromverkauf (Mieterarbeitspreis + Grundpreise + Allgemeinstrom/WP) minus Anlagenpacht.
  - **Lieferkettenmodell:** Vergütung in ct/kWh auf intern gelieferte kWh (Mieter + Allgemein), keine Pachtzahlung.
- **CO₂-Gutschrift:** Erzeugte kWh × CO₂-Faktor (kg/kWh).
        """
    )

# ---------- Inputs ----------
st.sidebar.header("🔧 Grundparameter")
col1, col2 = st.sidebar.columns(2)
with col1:
    kWp = st.number_input("Anlagengröße (kWp)", min_value=10, value=150, step=10)
    specific_yield = st.number_input("Spez. Ertrag (kWh/kWp·a)", min_value=600, value=950, step=10)
    units = st.number_input("Anzahl Wohneinheiten (WE)", min_value=1, value=40, step=1)
    cons_per_unit = st.number_input("Verbrauch je WE (kWh/a)", min_value=500, value=1500, step=100)
with col2:
    participant_rate = st.slider("Teilnehmerquote (%)", 0, 100, 45, step=1)
    general_kwh = st.number_input("Allgemeinstrom inkl. WP (kWh/a)", min_value=0, value=10000, step=500)
    co2_factor = st.number_input("CO₂-Faktor (kg/kWh)", min_value=0.0, value=0.40, step=0.01, format="%.2f")

st.sidebar.header("💶 Preise & Vergütungen")
colp1, colp2 = st.sidebar.columns(2)
with colp1:
    price_tenant_ct = st.number_input("Mieter: Arbeitspreis (ct/kWh)", min_value=0.0, value=28.0, step=0.1)
    base_tenant_eur = st.number_input("Mieter: Grundpreis (€/Monat)", min_value=0.0, value=8.0, step=0.5)
with colp2:
    price_general_ct = st.number_input("Allgemeinstrom/WP: Arbeitspreis (ct/kWh)", min_value=0.0, value=26.0, step=0.1)
    base_general_eur = st.number_input("Allgemeinstrom/WP: Grundpreis (€/Monat)", min_value=0.0, value=0.0, step=0.5)

st.sidebar.header("📄 Modell-spezifisch (WG-Sicht)")
pacht_dach_eur = st.sidebar.number_input("Dachpacht (€/a) → Einnahme WG", min_value=0.0, value=3000.0, step=100.0)
pacht_anlage_eur = st.sidebar.number_input("Anlagenpacht (€/a) → Ausgabe WG", min_value=0.0, value=6000.0, step=100.0)
verg_ct_per_kwh = st.sidebar.number_input("Lieferkette: Vergütung (ct/kWh)", min_value=0.0, value=4.0, step=0.1)

st.sidebar.header("🧾 Sonstige Kosten")
other_costs_eur = st.sidebar.number_input("Sonstige Kosten WG (€/a)", min_value=0.0, value=0.0, step=100.0)

# ---------- Calculations ----------
generation = kWp * specific_yield
participants = int(np.floor(units * participant_rate / 100.0))

tenant_demand = participants * cons_per_unit
deliv_tenant = min(generation, tenant_demand)

remaining = max(generation - deliv_tenant, 0.0)
deliv_general = min(remaining, general_kwh)

total_internal_kwh = deliv_tenant + deliv_general  # Basis für Lieferkettenvergütung
co2_savings_tons = (generation * co2_factor) / 1000.0

# Einnahmen-Komponenten (€/a)
tenant_revenue_eur = (deliv_tenant * price_tenant_ct / 100.0) + (participants * base_tenant_eur * 12.0)
general_revenue_eur = (deliv_general * price_general_ct / 100.0) + (base_general_eur * 12.0)

# Modell-Ergebnisse (€/a)
res_dach_eur = pacht_dach_eur - other_costs_eur
gross_anlagen_eur = tenant_revenue_eur + general_revenue_eur
res_anlagen_eur = gross_anlagen_eur - pacht_anlage_eur - other_costs_eur
res_lieferkette_eur = (total_internal_kwh * verg_ct_per_kwh / 100.0) - other_costs_eur

# ---------- Result tables ----------
summary = pd.DataFrame({
    "Parameter": [
        "Anlagengröße (kWp)",
        "Erzeugung (kWh/a)",
        "Teilnehmer (WE)",
        "Mieterstrom geliefert (kWh/a)",
        "Allgemeinstrom/WP geliefert (kWh/a)",
        "CO₂-Gutschrift (t/a)",
        "Einnahmen Mieter (€/a)",
        "Einnahmen Allgemeinstrom/WP (€/a)",
        "Dachpacht Einnahme (€/a)",
        "Anlagenpacht Ausgabe (€/a)",
        "Lieferkette Vergütung (ct/kWh)",
        "Sonstige Kosten WG (€/a)",
        "Gesamtergebnis WG (€/a)"
    ],
    "Dachpachtmodell": [
        kWp,
        generation,
        participants,
        deliv_tenant,
        deliv_general,
        round(co2_savings_tons, 2),
        0.0,
        0.0,
        pacht_dach_eur,
        0.0,
        0.0,
        other_costs_eur,
        round(res_dach_eur, 2)
    ],
    "Anlagenpachtmodell": [
        kWp,
        generation,
        participants,
        deliv_tenant,
        deliv_general,
        round(co2_savings_tons, 2),
        round(tenant_revenue_eur, 2),
        round(general_revenue_eur, 2),
        0.0,
        pacht_anlage_eur,
        0.0,
        other_costs_eur,
        round(res_anlagen_eur, 2)
    ],
    "Lieferkettenmodell": [
        kWp,
        generation,
        participants,
        deliv_tenant,
        deliv_general,
        round(co2_savings_tons, 2),
        0.0,
        0.0,
        0.0,
        0.0,
        verg_ct_per_kwh,
        other_costs_eur,
        round(res_lieferkette_eur, 2)
    ]
})

st.subheader("Ergebnisübersicht (WG-Sicht)")
st.dataframe(summary, use_container_width=True)

# ---------- Chart (matplotlib, no explicit colors) ----------
st.subheader("Vergleich: Gesamtergebnis (€/a)")
fig, ax = plt.subplots()
models = ["Dachpacht", "Anlagenpacht", "Lieferkette"]
values = [res_dach_eur, res_anlagen_eur, res_lieferkette_eur]
ax.bar(models, values)
ax.set_ylabel("Ergebnis (€/a)")
ax.set_xlabel("Modell")
ax.set_title("Gesamtergebnis der WG pro Jahr")
st.pyplot(fig)

# ---------- Export ----------
st.subheader("Export")
export_df = summary.copy()
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
    export_df.to_excel(writer, index=False, sheet_name="Variantenvergleich")
    ws = writer.sheets["Variantenvergleich"]
    for i, width in enumerate([28, 20, 14, 26, 30, 18, 22, 26, 24, 24, 26, 22, 24]):
        ws.set_column(i, i, width)

st.download_button(
    label="📥 Excel herunterladen",
    data=buffer.getvalue(),
    file_name="variantenvergleich_pv_modelle.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
