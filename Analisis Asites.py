"""
=============================
TUTORIAL MENJALANKAN APLIKASI
=============================

1. **Install Python**
   - Download dari: https://www.python.org/downloads/
   - Saat install di Windows, centang "Add Python to PATH".

2. **Install VS Code (editor)**
   - Download dari: https://code.visualstudio.com/download

3. **Buat folder proyek**, misalnya: `ascites-helper`
   - Simpan file ini sebagai `app.py` di folder tersebut.

4. **Buka terminal** di VS Code atau Command Prompt/Terminal, lalu masuk ke folder proyek.
   - Windows: `cd Desktop\\ascites-helper`
   - macOS/Linux: `cd ~/Desktop/ascites-helper`

5. **(Opsional) Buat virtual environment**
   - Windows:
     ```
     python -m venv .venv
     .venv\\Scripts\\activate
     ```
   - macOS/Linux:
     ```
     python3 -m venv .venv
     source .venv/bin/activate
     ```

6. **Install Streamlit**
   ```
   python -m pip install --upgrade pip
   python -m pip install streamlit
   ```
   (Gunakan `python3` bila di macOS/Linux)

7. **Jalankan aplikasi**
   ```
   python -m streamlit run app.py
   ```
   Browser akan terbuka di `http://localhost:8501`.

8. **Masukkan data laboratorium** di sidebar kiri sesuai kolom yang tersedia.
   Aplikasi otomatis menghitung **Albumin Asites (rumus)**, **SAAG**, serta interpretasi **SAAG**.

=============================
"""

import streamlit as st
from typing import Optional

st.set_page_config(page_title="Ascites Analysis Helper", layout="wide")
st.title("Ascites Analysis Helper")

st.caption("Interpretasi asites berbasis SAAG (dengan albumin asites dihitung dari rumus: Alb asites = (Alb serum / Protein serum) × Protein asites), ditambah Kriteria Light (adaptasi asites), alert SBP (PMN ≥250), serta catatan makroskopis/sitologi opsional.")

# Fungsi perhitungan
@st.cache_data(show_spinner=False)
def compute(
    sa: Optional[float],               # serum albumin (g/dL)
    sp: Optional[float],               # serum total protein (g/dL)
    atp: Optional[float],              # ascites total protein (g/dL)
    override_aa: Optional[float],      # optional measured ascites albumin (g/dL)
    pmn: Optional[float],              # PMN cells/µL
    serum_ldh: Optional[float],        # serum LDH (U/L)
    ldh_uln: Optional[float],          # serum LDH ULN (U/L)
    asc_ldh: Optional[float],          # ascites LDH (U/L)
    serum_glucose: Optional[float],    # serum glucose (mg/dL)
    asc_glucose: Optional[float],      # ascites glucose (mg/dL)
    rivalta_positive: Optional[bool],  # Rivalta result
    color: Optional[str], turbidity: Optional[str], mn_count: Optional[float], rbc_count: Optional[float]
):
    out: dict = {}

    # --- 1) Hitung Albumin Asites (derived) ---
    ascites_albumin_derived = None
    if sa is not None and sp is not None and sp > 0 and atp is not None:
        ascites_albumin_derived = (sa / sp) * atp

    # Pilih albumin asites yang dipakai (override bila tersedia)
    ascites_albumin_used = override_aa if override_aa is not None else ascites_albumin_derived

    # --- 2) Hitung SAAG ---
    saag = None
    if sa is not None and ascites_albumin_used is not None:
        saag = sa - ascites_albumin_used
        out["SAAG"] = saag
        out["Ascites albumin (used)"] = ascites_albumin_used
        out["Ascites albumin (derived)"] = ascites_albumin_derived

    impressions = []
    flags = []

    # --- SBP Alert ---
    if pmn is not None:
        if pmn >= 250:
            flags.append("PMN ≥250 sel/µL → **Curiga SBP**; tata laksana sesuai pedoman dan lakukan kultur botol darah di bedside.")
        elif 100 <= pmn < 250:
            flags.append("PMN 100–249 sel/µL → borderline; pertimbangkan ulang pungsi/monitor gejala.")

    # --- 3) Alur interpretasi SAAG sesuai diagram ---
    if saag is not None:
        if saag >= 1.1:
            if atp is not None and atp < 2.5:
                impressions.append("SAAG ≥1,1 g/dL & Protein asites <2,5 g/dL → **Cirrhosis, Late Budd–Chiari, Massive liver metastases**.")
            elif atp is not None and atp >= 2.5:
                impressions.append("SAAG ≥1,1 g/dL & Protein asites ≥2,5 g/dL → **Heart failure/Constrictive pericarditis, Early Budd–Chiari, IVC obstruction, Sinusoidal obstruction syndrome**.")
            else:
                impressions.append("SAAG ≥1,1 g/dL → **Portal hipertensi** (butuh nilai protein asites untuk sub‑klasifikasi).")
        else:
            impressions.append("SAAG <1,1 g/dL → **Non‑portal**: Biliary leak, Nephrotic syndrome, Pancreatitis, Peritoneal carcinomatosis, Tuberculosis.")

    # --- 4) Kriteria Light (adaptasi untuk asites) ---
    light_details = []
    exudate = False

    # a) Protein ratio > 0.5
    if sp is not None and sp > 0 and atp is not None:
        pr = atp / sp
        cond = pr > 0.5
        light_details.append(f"Protein asites/serum = {pr:.2f} {'>' if cond else '≤'} 0,5")
        exudate = exudate or cond

    # b) LDH ratio > 0.6
    if serum_ldh is not None and serum_ldh > 0 and asc_ldh is not None:
        lr = asc_ldh / serum_ldh
        cond = lr > 0.6
        light_details.append(f"LDH asites/serum = {lr:.2f} {'>' if cond else '≤'} 0,6")
        exudate = exudate or cond

    # c) Ascites LDH > 2/3 ULN serum
    if ldh_uln is not None and ldh_uln > 0 and asc_ldh is not None:
        cutoff = (2/3) * ldh_uln
        cond = asc_ldh > cutoff
        light_details.append(f"LDH asites = {asc_ldh:.0f} {'>' if cond else '≤'} 2/3 ULN serum ({cutoff:.0f})")
        exudate = exudate or cond

    # Rivalta & Glucose (pendukung eksudat)
    if rivalta_positive is not None:
        light_details.append(f"Rivalta: {'Positif' if rivalta_positive else 'Negatif'} (positif → mendukung eksudat)")
    if asc_glucose is not None and asc_glucose < 50:
        light_details.append("Glukosa asites <50 mg/dL (mendukung proses inflamasi/eksudat: infeksi/TB/malignansi)")
    if asc_glucose is not None and serum_glucose is not None and asc_glucose < 0.5 * serum_glucose:
        light_details.append("Glukosa asites jauh lebih rendah dari serum (mendukung eksudat/inflamasi)")

    if any([sp, atp, serum_ldh, asc_ldh, ldh_uln]):
        impressions.append("**Kriteria Light (adaptasi asites):** " + ("Eksudat" if exudate else "Transudat") + ". Gunakan bersama SAAG & konteks klinis.")
    out["Light_details"] = light_details

    # --- 5) Catatan makroskopis/sitologi opsional ---
    extra_notes = []
    if color:
        c = color.lower()
        if any(k in c for k in ["milky", "chylous", "susu"]):
            extra_notes.append("Warna milky/chylous → curiga **chylous ascites**; periksa trigliserida asites (≥200 mg/dL).")
        if any(k in c for k in ["bloody", "darah", "serosanguinous"]):
            extra_notes.append("Warna berdarah → **hemoragik/traumatic**; korelasikan dengan RBC & klinis.")
        if any(k in c for k in ["green", "hijau", "bile"]):
            extra_notes.append("Warna kehijauan/bile‑stained → curiga **bile leak**; pertimbangkan bilirubin asites.")
    if turbidity:
        t = turbidity.lower()
        if any(k in t for k in ["cloudy", "keruh", "turbid", "hazy"]):
            extra_notes.append("Cairan keruh → mendukung proses inflamasi/infeksi; korelasikan dengan sel & kultur.")
        if any(k in t for k in ["chylous", "milky", "susu"]):
            extra_notes.append("Tampak chylous → curiga **chylous ascites** (TG ≥200 mg/dL).")
    if rbc_count is not None and rbc_count > 10000:
        extra_notes.append("RBC >10.000/µL → **hemoragik/traumatic tap**; interpretasi indeks lain dengan hati‑hati.")
    if mn_count is not None and mn_count >= 500:
        extra_notes.append("MN ≥500/µL → dominansi mononuklear/limfosit; pertimbangkan **TB peritonitis** atau **malignansi** (lihat ADA, sitologi, kultur).")

    out["flags"] = flags
    out["impressions"] = impressions
    out["extra_notes"] = extra_notes
    return out

# Sidebar input
st.sidebar.header("Input Data — Utama")
serum_albumin = st.sidebar.number_input("Albumin serum (g/dL)", 0.0, 8.0, 3.0, 0.1)
serum_protein = st.sidebar.number_input("Protein total serum (g/dL)", 0.0, 12.0, 6.5, 0.1)
ascites_protein = st.sidebar.number_input("Protein asites (g/dL)", 0.0, 10.0, 2.0, 0.1)
ascites_albumin_override = None
if st.sidebar.checkbox("Input albumin asites terukur (override)"):
    ascites_albumin_override = st.sidebar.number_input("Albumin asites (g/dL)", 0.0, 8.0, 1.5, 0.1)

st.sidebar.header("Input Data — SBP & Light")
pmn = st.sidebar.number_input("PMN (sel/µL)", 0.0, 100000.0, 0.0, 10.0)
serum_ldh = st.sidebar.number_input("LDH serum (U/L)", 0.0, 10000.0, 220.0, 1.0)
ldh_uln = st.sidebar.number_input("LDH serum ULN (U/L)", 0.0, 10000.0, 250.0, 1.0)
ascites_ldh = st.sidebar.number_input("LDH asites (U/L)", 0.0, 5000.0, 180.0, 1.0)
serum_glucose = st.sidebar.number_input("Gula darah serum (mg/dL)", 0.0, 1000.0, 100.0, 1.0)
ascites_glucose = st.sidebar.number_input("Glukosa asites (mg/dL)", 0.0, 500.0, 80.0, 1.0)
rivalta = st.sidebar.checkbox("Rivalta positif?", value=False)

with st.sidebar.expander("Makroskopis & Sitologi (opsional)"):
    color = st.selectbox("Warna", ["—", "jernih/straw", "kuning", "keruh/cloudy", "milky/chylous", "hijau/bile‑stained", "berdarah/bloody", "lainnya"], index=0)
    turbidity = st.selectbox("Kekeruhan", ["—", "jernih", "hazy", "cloudy", "turbid", "chylous"], index=0)
    mn_count = st.number_input("MN (mononuklear) (sel/µL)", 0.0, 100000.0, 0.0, 10.0)
    rbc_count = st.number_input("Eritrosit (RBC) (sel/µL)", 0.0, 1000000.0, 0.0, 100.0)
    color = None if color == "—" else color
    turbidity = None if turbidity == "—" else turbidity

# Compute (dipanggil SEKALI dengan seluruh parameter)
res = compute(
    serum_albumin, serum_protein, ascites_protein, ascites_albumin_override,
    pmn, serum_ldh, ldh_uln, ascites_ldh, serum_glucose, ascites_glucose, rivalta,
    color, turbidity, mn_count, rbc_count
)
res = res  # (placeholder to remove duplicate compute if existed)

# Display
col1, col2, col3, col4 = st.columns(4)
with col1: st.metric("Serum albumin", f"{serum_albumin:.2f}")
with col2: st.metric("Serum protein", f"{serum_protein:.2f}")
with col3: st.metric("Ascites albumin (used)", f"{res.get('Ascites albumin (used)', '-')}")
with col4: st.metric("SAAG", f"{res.get('SAAG', '-')}")

st.markdown("## Interpretation — SAAG (sesuai diagram)")
for imp in res["impressions"]:
    st.info(imp)

st.markdown("## Kriteria Light (adaptasi asites)")
if res.get("Light_details"):
    for li in res["Light_details"]:
        st.write("- ", li)
else:
    st.write("(Isi data protein & LDH untuk melihat evaluasi Light)")

if res.get("flags"):
    st.markdown("## Alerts")
    for f in res["flags"]:
        st.warning(f)

if res.get("extra_notes"):
    st.markdown("## Catatan tambahan (makroskopis/sitologi)")
    for note in res["extra_notes"]:
        st.write("- ", note)

with st.expander("Referensi Algoritma SAAG"):
    st.markdown("""
    - **SAAG ≥1.1 g/dL & Protein asites <2.5 g/dL** → Cirrhosis, Late Budd-Chiari, Massive liver metastases.
    - **SAAG ≥1.1 g/dL & Protein asites ≥2.5 g/dL** → Heart failure/Constrictive pericarditis, Early Budd-Chiari, IVC obstruction, Sinusoidal obstruction syndrome.
    - **SAAG <1.1 g/dL** → Biliary leak, Nephrotic syndrome, Pancreatitis, Peritoneal carcinomatosis, Tuberculosis.
    """)
