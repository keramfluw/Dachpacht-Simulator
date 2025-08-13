
import streamlit as st
import pandas as pd
import numpy as np
import io
import matplotlib.pyplot as plt

st.set_page_config(page_title="PV-Variantenvergleich", layout="wide")

st.title("PV-Variantenvergleich")
st.caption("Dachpachtmodell · Anlagenpachtmodell · Lieferkettenmodell — mit CO₂-Gutschrift für das Gebäude")

with st.expander("Methodik & Annahmen", expanded=False):
    st.markdown(
        """
- **Ziel:** Wirtschaftlicher Vergleich dreier Modelle aus Sicht der WG UNITAS.
- **Lastdeckung:** PV-Erzeugung bedient zuerst die **Mieterstrom-Nachfrage**, danach **Allgemeinstrom/Wärmepumpe**. Etwaige Überschüsse werden hier konservativ **nicht** bepreist (erweiterbar).
- **Einnahmen WG UNITAS je Modell:**
  - **Dachpachtmodell:** Fixe Dachpacht (€/a).
  - **Anlagenpachtmodell:** WG erzielt **Erlöse** aus Stromverkauf (Mieterarbeitspreis + Grundpreise + Allgemeinstrom/WP) und zahlt **Anlagenpacht (€/a)**.
  - **Lieferkettenmodell:** WG erhält **Vergütung in ct/kWh** (auf die intern verbrauchten kWh für Mieter + Allgemeinstrom/WP), anstatt einer Pachtzahlung.
- **CO₂-Gutschrift:** Erzeugte kWh × CO₂-Faktor (kg/kWh).
        """
    )

# ============== Eingaben ==============
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

# ============== Ableitungen ==============
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

# ============== Modell-Ergebnisse (WG-Sicht) ==============
# Dachpacht: fixe Einnahme
res_dach_eur = pacht_dach_eur - other_costs_eur

# Anlagenpacht: Erlöse aus Stromverkauf minus Pacht
gross_anlagen_eur = tenant_revenue_eur + general_revenue_eur
res_anlagen_eur = gross_anlagen_eur - pacht_anlage_eur - other_costs_eur

# Lieferkette: Vergütung in ct/kWh (auf intern verbrauchte kWh: Mieter + Allgemein)
res_lieferkette_eur = (total_internal_kwh * verg_ct_per_kwh / 100.0) - other_costs_eur

# Tabellenaufbereitung
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

# ============== Visualisierung (matplotlib, ohne Styles/Farben) ==============
st.subheader("Vergleich: Gesamtergebnis (€/a)")
fig, ax = plt.subplots()
models = ["Dachpacht", "Anlagenpacht", "Lieferkette"]
values = [res_dach_eur, res_anlagen_eur, res_lieferkette_eur]
ax.bar(models, values)
ax.set_ylabel("Ergebnis (€/a)")
ax.set_xlabel("Modell")
ax.set_title("Gesamtergebnis der WG pro Jahr")
st.pyplot(fig)

# ============== Export ==============
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

with st.expander("Eingabedaten (für Dokumentation)", expanded=False):
    st.json({
        "kWp": kWp,
        "specific_yield_kWh_per_kWp_a": specific_yield,
        "units_WE": units,
        "participants_WE": participants,
        "participant_rate_percent": participant_rate,
        "consumption_per_WE_kWh_a": cons_per_unit,
        "general_kWh_a": general_kwh,
        "prices": {
            "tenant_ct_per_kWh": price_tenant_ct,
            "tenant_base_eur_per_month": base_tenant_eur,
            "general_ct_per_kWh": price_general_ct,
            "general_base_eur_per_month": base_general_eur
        },
        "model_params": {
            "dachpacht_eur_a": pacht_dach_eur,
            "anlagenpacht_eur_a": pacht_anlage_eur,
            "lieferkette_ct_per_kWh": verg_ct_per_kwh,
            "other_costs_eur_a": other_costs_eur
        },
        "derived": {
            "generation_kWh_a": generation,
            "delivered_tenant_kWh_a": deliv_tenant,
            "delivered_general_kWh_a": deliv_general,
            "co2_tons_a": round(co2_savings_tons, 2),
            "revenues": {
                "tenant_revenue_eur_a": round(tenant_revenue_eur, 2),
                "general_revenue_eur_a": round(general_revenue_eur, 2)
            },
            "results": {
                "dachpacht_eur_a": round(res_dach_eur, 2),
                "anlagenpacht_eur_a": round(res_anlagen_eur, 2),
                "lieferkette_eur_a": round(res_lieferkette_eur, 2)
            }
        }
    })
