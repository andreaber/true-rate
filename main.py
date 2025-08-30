import streamlit as st
st.set_page_config(page_title="True Rate · Tasas implícitas", page_icon="📈", layout="wide")

from dotenv import load_dotenv
import os
from datetime import date
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import pandas as pd     # para CSV / Excel y DataFrames
from openai import OpenAI
import json
from pypdf import PdfReader


# --- Estado persistente: inicializamos TODO lo que usamos en la app ---

from datetime import date

defaults = {
    "pv": 0.0,
    "n": 1,
    "pmt": 0.0,
    "tipo_pago": "Vencido (fin de período)",
    "modo": "Calcular tasa (i)",
    "i_periodo": 0.0,
    "periodicidad": "Mensual",
    "fecha_inicial": date.today(),
    "resultado": None,
    "explicacion": None,
    "kb_text": None,
    "kb_name": None,
    "escenarios": {},
    "escenario_nombre": "",
    "escenario_sel": "",
}

# Cargar valores por defecto si aún no existen en session_state
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# --- fin estado persistente ---




# --- Configuración de página ---
st.set_page_config(
    page_title="True Rate · Calculadora financiera",
    page_icon="📈",
    layout="wide"
)
# --- fin configuración de página ---

#!------------------------------------------------------------------------------

# --- Encabezado con ícono ---
st.markdown(
    """
    <div style="text-align: center; margin-bottom: 20px;">
        <div style="display:flex; align-items:center; justify-content:center; gap:14px;">
            <!-- Ícono SVG -->
            <svg xmlns="http://www.w3.org/2000/svg"
                width="48" height="48"
                viewBox="0 0 24 24"
                fill="none" stroke="#00909a" stroke-width="3"
                stroke-linecap="round" stroke-linejoin="round"
                style="vertical-align: middle; margin-top:-5px; margin-right:6px;">
                <polyline points="23 6 13.5 15.5 8.5 10.5 1 18"></polyline>
                <polyline points="17 6 23 6 23 12"></polyline>
            </svg>
            <!-- Texto principal -->
            <h1 style="
                font-size: 60px;
                color: #00909a;
                font-family: 'Georgia', 'Times New Roman', serif;
                font-weight: 800;
                margin: 0;
            ">
                TRUE RATE
            </h1>
        </div>
        <h3 style="color: #ccc; font-weight: 400; margin-top: 10px;">
            Prestación vs. Contraprestación · Pago vencido · Semilla tipo Baily
        </h3>
        <p style="font-size: 18px; color: #aaa; margin-top: -5px; margin-bottom: 70px;">
            Calculá la tasa real y el número de cuotas en tus operaciones financieras
        </p>
    </div>
    """,
    unsafe_allow_html=True
)
# --- fin Encabezado ---

#!------------------------------------------------------------------------------

# carga .env en variables de entorno
load_dotenv()

# 1) Primero intento con .env (local), luego pruebo st.secrets (Cloud).
api_key = os.getenv("OPENAI_API_KEY")
try:
    # En Streamlit Cloud esto existe; en local puede lanzar excepción.
    api_key = st.secrets["OPENAI_API_KEY"] if "OPENAI_API_KEY" in st.secrets else api_key
except Exception:
    # Si no hay secrets.toml, seguimos con lo de .env
    pass

from core.ai import explicar_con_ia


# --- OpenAI client (solo si hay API key) ---
client = OpenAI(api_key=api_key) if api_key else None
# --- fin OpenAI client ---
# st.write("API key cargada:", "sí" if api_key else "no")


from core.finanzas import (
    present_value_annuity,
    solve_monthly_rate_trace,
    annual_effective,
    cashflow_table,
)


#!------------------------------------------------------------------------------


# --- Uploaders en dos columnas (JSON + CSV/Excel) ---
col1, col2 = st.columns(2)

with col1:
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:6px;">
            <svg class="icon-folder" xmlns="http://www.w3.org/2000/svg"
                 width="28" height="28"
                 viewBox="0 0 24 24"
                 fill="none" stroke="#00909a" stroke-width="2.5"
                 stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 4h5l2 2h9a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z"></path>
            </svg>
            <h4 style="color:#FAFAFA; margin:0;">Cargar JSON</h4>
        </div>
        """,
        unsafe_allow_html=True
    )

    uploader = st.file_uploader("Subir JSON", type=["json"], key="upl_json")

    if uploader is not None:
        try:
            raw_json = uploader.read().decode("utf-8")
            data = json.loads(raw_json)

            # 🚀 Guardamos directo en los mismos keys que usan los inputs
            st.session_state.pv          = float(data.get("pv", 0.0))
            st.session_state.n           = int(data.get("n", 1))
            st.session_state.pmt         = float(data.get("pmt", 0.0))
            st.session_state.tipo_pago   = data.get("tipo_pago", "Vencido (fin de período)")
            st.session_state.modo        = data.get("modo", "Calcular tasa (i)")
            st.session_state.i_periodo   = float(data.get("i_periodo", 0.0))
            st.session_state.periodicidad = data.get("periodicidad", "Mensual")
            st.session_state.fecha_inicial = date.fromisoformat(data.get("fecha_inicial")) if data.get("fecha_inicial") else date.today()

            st.session_state.resultado   = None
            st.session_state.explicacion = None

            st.success("Archivo cargado y aplicado a los campos.")
        except Exception as e:
            st.error(f"Archivo inválido: {e}")

# --- fin Uploaders JSON ---

with col2:
    # st.markdown("#### 📂 Cargar CSV / Excel")

    st.markdown(
        """
        <style>
        .icon-folder:hover path {
            stroke: #00c4d4; /* Turquesa más claro en hover */
        }
        </style>
        <div style="display:flex; align-items:center; gap:6px;">
            <svg class="icon-folder" xmlns="http://www.w3.org/2000/svg"
                 width="28" height="28"
                 viewBox="0 0 24 24"
                 fill="none" stroke="#00909a" stroke-width="2.5"
                 stroke-linecap="round" stroke-linejoin="round">
                <path d="M4 4h5l2 2h9a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z"></path>
            </svg>
            <h4 style="color:#FAFAFA; margin:0;">Cargar CSV / Excel</h4>
        </div>
        """,
        unsafe_allow_html=True
    )

    upl_tabla = st.file_uploader("", type=["csv", "xlsx", "xls"], key="upl_tabla")

    if upl_tabla is not None:
        try:
            # Leer archivo
            if upl_tabla.name.lower().endswith(".csv"):
                try:
                    df_in = pd.read_csv(upl_tabla)
                except Exception:
                    upl_tabla.seek(0)
                    df_in = pd.read_csv(upl_tabla, decimal=",")
            else:
                df_in = pd.read_excel(upl_tabla, engine="openpyxl")

            if df_in.empty:
                st.error("El archivo no tiene filas.")
            else:
                row = {str(k).strip(): row for k, row in df_in.iloc[0].to_dict().items()}

                def pick(*names):
                    for n in names:
                        if n in row and pd.notna(row[n]):
                            return row[n]
                    return None

                pv_in   = pick("precio_contado", "contado", "precio")
                n_in    = pick("CANT C", "cant_c", "cuotas", "n")
                pmt_in  = pick("monto_cuota", "cuota", "pmt")
                tipo_in = pick("tipo_pago")
                i_per   = pick("tasa_periodo", "i_periodo", "tasa", "i")

                def to_float(x):
                    if x is None: return None
                    s = str(x).strip().replace(" ", "")
                    s = s.replace(".", "").replace(",", ".") if s.count(",") == 1 and s.count(".") >= 1 else s.replace(",", ".")
                    try:
                        return float(s)
                    except Exception:
                        return None

                pv_f   = to_float(pv_in)
                n_f    = int(to_float(n_in)) if n_in is not None else None
                pmt_f  = to_float(pmt_in)
                i_f    = to_float(i_per)

                if pv_f is not None and pmt_f is not None and n_f is not None:
                    modo_in = "Calcular tasa (i)"
                elif pv_f is not None and pmt_f is not None and i_f is not None:
                    modo_in = "Calcular cuotas (n)"
                else:
                    st.error("Faltan columnas: para modo i → precio_contado, CANT C, monto_cuota; "
                             "para modo n → precio_contado, monto_cuota, tasa_periodo.")
                    modo_in = None

                if modo_in:
                    st.session_state.update({
                        "pv": pv_f if pv_f is not None else 0.0,
                        "n": n_f if n_f is not None else 1,
                        "pmt": pmt_f if pmt_f is not None else 0.0,
                        "tipo_pago": ("Adelantado (inicio de período)" if str(tipo_in).lower().startswith("adel") else "Vencido (fin de período)")
                                     if tipo_in is not None else st.session_state.tipo_pago,
                        "modo": modo_in,
                        "i_periodo": i_f if i_f is not None else st.session_state.i_periodo,
                        "resultado": None,
                        "explicacion": None,
                    })
                    st.success(f"Archivo cargado en modo: {modo_in}. Revisá y luego tocá «Calcular».")
        except Exception as e:
            st.error(f"Archivo inválido: {e}")
# --- fin Uploaders ---


#!------------------------------------------------------------------------------
st.divider()   # ← ÚNICO separador



# st.subheader("🧮 Datos de entrada")

# --- Subtítulo: Datos de entrada ---
st.markdown(
    """
    <div style="display:flex; align-items:center; gap:10px; margin-top:25px; margin-bottom:10px;">
        <!-- Ícono calculadora -->
        <svg xmlns="http://www.w3.org/2000/svg"
             width="28" height="28"
             viewBox="0 0 24 24"
             fill="none" stroke="#00909a" stroke-width="2.5"
             stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="9" y1="9" x2="15" y2="9"></line>
            <line x1="9" y1="13" x2="15" y2="13"></line>
            <line x1="9" y1="17" x2="13" y2="17"></line>
        </svg>
        <h2 style="color:#FAFAFA; margin:0;">Datos de entrada</h2>
    </div>
    """,
    unsafe_allow_html=True
)
# --- fin Subtítulo ---


# --- Inputs principales (con soporte para preset) ---
preset = st.session_state.get("preset", {})

col1, col2, col3 = st.columns(3)
with col1:
    st.number_input("Contraprestación (Precio al contado)", min_value=0.0, step=100.0, format="%.2f", key="pv")
with col2:
    st.number_input("CANT C (Cantidad de cuotas)", min_value=1, step=1, key="n")
with col3:
    st.number_input("Prestación (Valor de cada cuota)", min_value=0.0, step=10.0, format="%.2f", key="pmt")


# Tipo de pago
st.radio(
    "Tipo de pago",
    ("Vencido (fin de período)", "Adelantado (inicio de período)"),
    key="tipo_pago",
    index=0 if preset.get("tipo_pago", st.session_state.tipo_pago).startswith("Vencido") else 1
)

# Modo de cálculo
st.radio(
    "Modo de cálculo",
    ("Calcular tasa (i)", "Calcular cuotas (n)"),
    key="modo",
    index=0 if "i" in preset.get("modo", st.session_state.modo).lower() else 1
)

# Tasa por período (solo si calculamos n)
if st.session_state.modo == "Calcular cuotas (n)":
    st.number_input(
        "Tasa por período (fracción)",
        min_value=0.0,
        step=0.0001,
        format="%.6f",
        key="i_periodo",
        value=preset.get("i_periodo", st.session_state.i_periodo)
    )

# Periodicidad y Fecha inicial
cpa, cpb = st.columns(2)
with cpa:
    st.selectbox(
        "Periodicidad",
        ["Mensual", "Bimestral", "Trimestral", "Cuatrimestral", "Semestral", "Anual"],
        key="periodicidad",
        index=["Mensual", "Bimestral", "Trimestral", "Cuatrimestral", "Semestral", "Anual"].index(
            preset.get("periodicidad", st.session_state.periodicidad)
        )
    )
with cpb:
    st.date_input(
        "Fecha inicial",
        key="fecha_inicial",
        value=preset.get("fecha_inicial", st.session_state.fecha_inicial)
    )
# --- fin Inputs principales ---




# Ajustes avanzados (solo modo i)
if st.session_state.modo == "Calcular tasa (i)":
    with st.expander("Ajustes avanzados", expanded=False):
        tol = st.number_input("Tolerancia (convergencia)", value=1e-12, format="%.1e", step=1e-13, key="tol_i")
        max_iter = st.number_input("Máx. iteraciones (Newton)", min_value=10, value=80, step=10, key="max_iter_i")

        # 👉 Texto explicativo
        st.caption(
            "ℹ️ **Ajustes avanzados:**\n"
            "- *Tolerancia (convergencia)*: define qué tan exacto debe ser el resultado. "
            "Un valor más chico = mayor precisión (ej. 1e-12), más grande = menos precisión pero más rápido (ej. 1e-6).\n"
            "- *Máx. iteraciones*: número máximo de intentos del algoritmo. "
            "Normalmente no hace falta cambiarlo (80 asegura que siempre se encuentre la tasa)."
        )
else:
    tol, max_iter = 1e-12, 80  # valores por defecto cuando no se usan




# Botón de cálculo (según modo)
if st.session_state.modo == "Calcular tasa (i)":
    if st.button("Calcular tasa"):
        pv  = float(st.session_state.pv)
        n   = int(st.session_state.n)
        pmt = float(st.session_state.pmt)
        if pv > 0 and pmt > 0 and n > 0:
            adelantado = st.session_state.tipo_pago.startswith("Adelantado")
            i, trace = solve_monthly_rate_trace(pv, pmt, n, adelantado=adelantado, tol=tol, max_iter=int(max_iter))
            st.session_state["resultado"] = {
                "modo": "Calcular tasa (i)",
                "pv": pv, 
                "n": n, 
                "pmt": pmt,
                "adelantado": adelantado, 
                "i": i, 
                "trace": trace,
                "tol": float(tol), 
                "max_iter": int(max_iter),
            }
            st.session_state.explicacion = None
        else:
            st.error("Ingresá valores positivos (contado, cuotas y valor de cuota).")
else:
    if st.button("Calcular cuotas (n)"):
        import math
        pv  = float(st.session_state.pv)
        pmt = float(st.session_state.pmt)
        i   = float(st.session_state.i_periodo)
        adelantado = st.session_state.tipo_pago.startswith("Adelantado")

        # Ajuste para adelantado: traer PV a vencido para usar misma fórmula de n
        pv_v = pv / (1 + i) if adelantado else pv
        x = i * pv_v / pmt if pmt > 0 else 0.0

        if i <= 0 or pmt <= 0 or pv <= 0:
            st.error("Ingresá valores positivos en contado, cuota y tasa.")
        elif not (0 < x < 1):
            st.error("La cuota no cubre los intereses (i·PV/PMT ≥ 1) o los datos no son viables.")
        else:
            n_real = -math.log(1 - x) / math.log(1 + i)
            n_red  = math.ceil(n_real)
            st.session_state["resultado"] = {
                "modo": "Calcular cuotas (n)",
                "pv": pv, 
                "n": n_red, 
                "pmt": pmt,
                "adelantado": adelantado, 
                "i": i, 
                "trace": None,
            }
            st.session_state.explicacion = None


# --- Estilos para botón Reset ---
st.markdown(
    """
    <style>
    .reset-btn {
        background-color: #2E2E3F;
        color: #FAFAFA;
        border: 1px solid #FF4B4B;
        border-radius: 8px;
        padding: 0.6em 1em;
        font-weight: 600;
        cursor: pointer;
        width: 30%;              /* 👈 ancho del botón */
        display: block;          /* para centrar */
        margin: 0 auto;          /* centrado horizontal */
        text-align: center;
    }
    .reset-btn:hover {
        background-color: #FF4B4B !important;
        color: #FFFFFF !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# --- Botón Reset con HTML ---
reset = st.markdown(
    """
    <form action="" method="get">
        <button class="reset-btn" type="submit">🔄 Resetear todo</button>
    </form>
    """,
    unsafe_allow_html=True
)

# --- Lógica de reset ---
# Cuando hacés clic, la página se recarga (submit → rerun)
if st.query_params:  # detecta que el form "ejecutó"
    for k in ["pv", "n", "pmt", "tipo_pago", "i_periodo", "resultado", "explicacion"]:
        if k in st.session_state:
            del st.session_state[k]
    st.info("Campos reseteados. Volvé a ingresar los datos.")
    st.rerun()

# --- fin Botón: Reset ---



#!------------------------------------------------------------------------------


st.divider()   # ← ÚNICO separador entre entrada/import y resultados


#!------------------------------------------------------------------------------


# 📊 Resultados: Bloque de Resultados y descargas (persisten al hacer clic) ---
# st.subheader("📊 Resultados y descargas")

if st.session_state.get("resultado"):
    # --- Subtítulo: Resultados ---
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:10px; margin-top:25px; margin-bottom:15px;">
            <!-- Ícono gráfico -->
            <svg xmlns="http://www.w3.org/2000/svg"
                width="32" height="32"
                viewBox="0 0 24 24"
                fill="none" stroke="#00909a" stroke-width="2.5"
                stroke-linecap="round" stroke-linejoin="round">
                <line x1="18" y1="20" x2="18" y2="10"></line>
                <line x1="12" y1="20" x2="12" y2="4"></line>
                <line x1="6" y1="20" x2="6" y2="14"></line>
            </svg>
            <h2 style="color:#FAFAFA; margin:0;">Resultados</h2>
        </div>
        """,
        unsafe_allow_html=True
    )
    # --- fin Subtítulo ---


    # --- Desempaquetar resultado ---
    r     = st.session_state.get("resultado", {})
    modo  = r.get("modo", "Calcular tasa (i)")
    pv, n, pmt = r["pv"], r["n"], r["pmt"]
    adelantado, i = r["adelantado"], r["i"]

    # --- Tasas (fracción y %) ---
    tasa_mensual_frac = i
    tasa_anual_frac   = annual_effective(i)
    tasa_mensual_pct  = tasa_mensual_frac * 100
    tasa_anual_pct    = tasa_anual_frac * 100
    # TNA: nominal anual con capitalización mensual (referencia local)
    tna_frac = i * 12
    tna_pct  = tna_frac * 100

    # --- Cabecera de tasas ---
    label_tasa  = "Tasa mensual calculada" if modo == "Calcular tasa (i)" else "Tasa mensual (ingresada)"
    label_anual = "TEA (tasa efectiva anual)" if modo == "Calcular tasa (i)" else "TEA (derivada)"
    st.success(f"{label_tasa}: {tasa_mensual_pct:.3f}%")
    st.success(f"{label_anual}: {tasa_anual_pct:.2f}%")
    st.caption(f"TNA (nominal anual): {tna_pct:.2f}%")

    if modo == "Calcular cuotas (n)":
        st.info(f"n (real): {r.get('n_real', float(n)):.3f}  →  n (redondeado): {n}")

    # --- Ajuste opcional de última cuota (solo modo n) ---
    ajustar_ultima = False
    if modo == "Calcular cuotas (n)":
        ajustar_ultima = st.checkbox(
            "Ajustar última cuota para equivalencia exacta",
            value=True,
            help="Ajusta solo la última cuota para que el VP de las cuotas iguale exactamente al contado."
        )

    # --- Flujo de pagos y VP (se ajusta ANTES de mostrar) ---
    ver_flujo = st.checkbox("Mostrar flujo (detalle de cuotas y VP)", value=False)
    df_flujo, total_vp = cashflow_table(pmt, n, adelantado, i)

    # Ajuste de última cuota (si corresponde)
    L = None
    if modo == "Calcular cuotas (n)" and ajustar_ultima and n >= 1:
        k_last = (n - 1) if adelantado else n
        factor_last = (1 + i) ** (-k_last)
        pv_first = present_value_annuity(pmt, i, n - 1, adelantado=adelantado) if n > 1 else 0.0
        L = (pv - pv_first) / factor_last  # última cuota ajustada

        # Aplicar ajuste en la tabla
        df_flujo.loc[df_flujo.index[-1], "cuota"]    = L
        df_flujo.loc[df_flujo.index[-1], "vp_cuota"] = L * factor_last
        total_vp = float(df_flujo["vp_cuota"].sum())


    # --- Fechas de pago según periodicidad (solo etiqueta, no afecta cálculo) ---
    step_map = {
        "Mensual": 1, "Bimestral": 2, "Trimestral": 3,
        "Cuatrimestral": 4, "Semestral": 6, "Anual": 12,
    }
    meses_step = step_map.get(st.session_state.periodicidad, 1)

    start_ts = pd.to_datetime(st.session_state.fecha_inicial)

    if adelantado:
        # Adelantado: 1ª cuota en la fecha inicial
        fechas = pd.date_range(start=start_ts, periods=n, freq=pd.DateOffset(months=meses_step))
    else:
        # Vencido: 1ª cuota un período después de la fecha inicial
        fechas = pd.date_range(start=start_ts + pd.DateOffset(months=meses_step),
                            periods=n, freq=pd.DateOffset(months=meses_step))

    # Insertamos la columna como segunda (después de 'periodo')
    df_flujo.insert(1, "fecha_pago", fechas.date)
    # --- fin fechas ---


    # Mostrar flujo (ya ajustado si corresponde)
    if ver_flujo:
        st.dataframe(df_flujo)
        if L is not None:
            st.caption(f"Última cuota ajustada: {L:,.2f}")
        st.caption(f"Chequeo: PV(cuotas) ≈ {total_vp:,.2f} vs contado {pv:,.2f}")


        # --- Gráfico del flujo (barras + línea) ---
        import altair as alt

        st.markdown("### 📈 Visualización del flujo de pagos")

        chart_df = df_flujo.copy()
        chart_df["acum_vp"] = chart_df["vp_cuota"].cumsum()

        base = alt.Chart(chart_df).encode(x="fecha_pago:T")

        barras = base.mark_bar(color="#00909a", opacity=0.6).encode(
            y=alt.Y("cuota:Q", title="Valor de cuota")
        )

        linea = base.mark_line(color="#FAFAFA", strokeWidth=2).encode(
            y=alt.Y("acum_vp:Q", title="VP acumulado"),
            tooltip=["fecha_pago:T", "acum_vp:Q"]
        )

        chart = alt.layer(barras, linea).resolve_scale(
            y="independent"  # cuotas y VP en escalas separadas
        )

        st.altair_chart(chart, use_container_width=True)
        # --- fin gráfico ---


          
        
        # --- Gráfico de flujo vs contado con doble eje Y ---
        import altair as alt

        st.markdown("### 📊 Flujo de pagos vs contado")

        chart_df = df_flujo.copy()
        chart_df["contado"] = pv  # línea de referencia

        barras = alt.Chart(chart_df).mark_bar(color="#00909a", opacity=0.7).encode(
            x=alt.X("fecha_pago:T", title="Fecha de pago"),
            y=alt.Y("cuota:Q", axis=alt.Axis(title="Monto de cuota")),
            tooltip=["fecha_pago:T", "cuota:Q"]
        )

        linea = alt.Chart(chart_df).mark_line(color="red", strokeWidth=2).encode(
            x="fecha_pago:T",
            y=alt.Y("contado:Q", axis=alt.Axis(title="Precio contado"), scale=alt.Scale(domain=[0, pv])),
            tooltip=["contado:Q"]
        )

        # Mostrar en capas con doble eje
        chart = alt.layer(barras, linea).resolve_scale(
            y="independent"
        ).properties(height=350)

        st.altair_chart(chart, use_container_width=True)
        # --- fin gráfico ---




    # --- Panel de Equivalencia (usa total_vp ya ajustado) ---
    colA, colB, colC = st.columns(3)
    colA.metric("PV de cuotas (VP)", f"{total_vp:,.2f}")
    colB.metric("Precio contado",     f"{pv:,.2f}")
    diff = total_vp - pv
    diff_abs = abs(diff)
    diff_disp = 0.0 if diff_abs < 0.005 else diff  # evita -0.00

    colC.metric("Diferencia (VP - contado)", f"{diff_disp:,.2f}")

    if diff_abs <= 0.50:
        st.success("✅ Equivalencia financiera verificada (diferencia ≈ 0).")
    else:
        st.warning("ℹ️ La diferencia no es ~0; revisá datos o aumentá iteraciones.")


    # --- Strings auxiliares para informe ---
    tipo_pago_str = "Adelantado (inicio de período)" if adelantado else "Vencido (fin de período)"
    linea_n       = f"- n (real): {r.get('n_real', float(n)):.3f} · n (redondeado): {n}\n" if modo == "Calcular cuotas (n)" else ""
    linea_ajuste  = f"- Ajuste: última cuota = {L:,.2f}\n" if L is not None else ""

    # --- Informe resumen (sin indentación fantasma) ---
    informe = (
        "**Resumen del cálculo financiero**\n\n"
        f"- Contraprestación (precio contado, hoy): {pv:,.2f}\n"
        f"- Prestación (valor de cada cuota): {pmt:,.2f}\n"
        f"- CANT C (cantidad de cuotas): {n}\n"
        f"- Modo: {modo}\n"
        f"- Fecha inicial: {st.session_state.fecha_inicial.strftime('%d/%m/%Y')}\n"
        f"{linea_n}"
        f"- Periodicidad: {st.session_state.periodicidad}\n"
        f"- Tipo de pago: {tipo_pago_str}\n"
        f"{linea_ajuste}\n"
        "➜ La tasa de interés que iguala el valor presente del plan en cuotas\n"
        "con el precio al contado es:\n\n"
        f"- **Tasa mensual calculada:** {tasa_mensual_frac:.6f}  ({tasa_mensual_pct:.3f} %)\n"
        f"- **TEA (tasa efectiva anual):** {tasa_anual_frac:.6f}  ({tasa_anual_pct:.2f} %)\n"
        f"- **TNA (nominal anual):** {tna_frac:.6f}  ({tna_pct:.2f} %)\n"
    )
    st.markdown(informe)

    # --- Iteraciones (convergencia) ---
    df_iter = None
    if modo == "Calcular tasa (i)":
        ver_iter = st.checkbox("Mostrar iteraciones (Newton/Bisección)", value=False)
        if "trace" in r and r["trace"]:
            import pandas as pd
            df_iter = pd.DataFrame(r["trace"])
            df_iter["i_%"] = df_iter["i"] * 100
            if ver_iter:
                st.dataframe(df_iter)
    # --- fin Iteraciones ---

        
    # --- Preparar contenido PDF ---
    informe_pdf = informe
    if st.session_state.explicacion:
        informe_pdf += "\n\n**Explicación (IA)**\n" + st.session_state.explicacion

    # --- Resumen (CSV/Excel) ---
    df_resumen = pd.DataFrame([{
        "fecha_inicial": st.session_state.fecha_inicial,
        "precio_contado": pv,
        "CANT C": int(n),
        "monto_cuota": pmt,
        "tipo_pago": tipo_pago_str,
        "periodicidad": st.session_state.periodicidad,
        "tasa mensual (fracción)": round(tasa_mensual_frac, 6),
        "TEA (fracción)":          round(tasa_anual_frac, 6),
        "tasa mensual (%)":        round(tasa_mensual_pct, 3),  # número 0-100
        "TEA (%)":                 round(tasa_anual_pct, 2),    # número 0-100
        "TNA (fracción)":          round(tna_frac, 6),
        "TNA (%)":                 round(tna_pct, 2),
        "PV de cuotas (VP)":       round(total_vp, 2),
        "Diferencia (VP - contado)": round(diff, 2),
        "ultima_cuota_ajustada":  round(L, 2) if L is not None else None,
        "modo": modo,
        "n (real)": round(r.get("n_real", float(n)), 3),
        "n (redondeado)": int(n),
        "tolerancia": r.get("tol", None),
        "max_iter":   r.get("max_iter", None),
    }])

    # CSV
    csv_bytes = df_resumen.to_csv(index=False).encode("utf-8")
    st.download_button("📄 Descargar CSV", data=csv_bytes,
                       file_name="resumen_tasa.csv", mime="text/csv")

    # Excel
    excel_buffer = BytesIO()

    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        # --- dentro del with ---
        df_resumen.to_excel(writer, index=False, sheet_name="Resumen")
        df_flujo.to_excel(writer, index=False, sheet_name="Flujo")
        if df_iter is not None:
            df_iter.to_excel(writer, index=False, sheet_name="Iteraciones")
        if st.session_state.explicacion:
            pd.DataFrame([{"explicacion": st.session_state.explicacion}]).to_excel(
                writer, index=False, sheet_name="Explicación IA"
            )

        # Formatos (Resumen)
        wb, ws = writer.book, writer.sheets["Resumen"]
        headers = {cell.value: idx for idx, cell in enumerate(ws[1], start=1)}
        def fmt_col(sheet, header, numfmt):
            col = headers.get(header)
            if col:
                for r_ in range(2, sheet.max_row + 1):
                    sheet.cell(row=r_, column=col).number_format = numfmt

        # Formato en hoja 'Flujo'
        ws_flujo = writer.sheets.get("Flujo")
        if ws_flujo:
            headers_f = {cell.value: idx for idx, cell in enumerate(ws_flujo[1], start=1)}
            def fmt_col_f(sheet, header, numfmt):
                col = headers_f.get(header)
                if col:
                    for r_ in range(2, sheet.max_row + 1):
                        sheet.cell(row=r_, column=col).number_format = numfmt

            # columnas típicas
            fmt_col_f(ws_flujo, "fecha_pago", "DD/MM/YYYY")
            fmt_col_f(ws_flujo, "cuota", "#,##0.00")
            fmt_col_f(ws_flujo, "vp_cuota", "#,##0.00")
            fmt_col_f(ws_flujo, "factor_descuento", "0.000000")


        # Monedas
        fmt_col(ws, "precio_contado", "#,##0.00")
        fmt_col(ws, "monto_cuota", "#,##0.00")
        fmt_col(ws, "PV de cuotas (VP)", "#,##0.00")
        fmt_col(ws, "Diferencia (VP - contado)", "#,##0.00")
        fmt_col(ws, "ultima_cuota_ajustada", "#,##0.00")

        # Fechas (Resumen)
        fmt_col(ws, "fecha_inicial", "DD/MM/YYYY")

        # Cantidades
        fmt_col(ws, "n (real)", "0.000")
        fmt_col(ws, "n (redondeado)", "0")

        # Fracciones (tanto por uno)
        fmt_col(ws, "tasa mensual (fracción)", "0.000000")
        fmt_col(ws, "TEA (fracción)",   "0.000000")
        fmt_col(ws, "TNA (fracción)", "0.000000")

        # Porcentaje como número 0–100 (sin símbolo %)
        fmt_col(ws, "tasa mensual (%)", "0.000")
        fmt_col(ws, "TEA (%)",   "0.00")
        fmt_col(ws, "TNA (%)", "0.00")
    # --- aquí TERMINA el with ---


    excel_buffer.seek(0)
    st.download_button(
        label="📊 Descargar Excel",
        data=excel_buffer.getvalue(),
        file_name="resumen_tasa.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    text = c.beginText(50, 750)
    for line in informe_pdf.split("\n"):
        text.textLine(line.strip())
    c.drawText(text); c.showPage(); c.save()
    buffer.seek(0)
    st.download_button("📥 Descargar PDF",
        data=buffer,
        file_name="informe.pdf",
        mime="application/pdf"
    )
# --- fin resultados y descargas ---


#!------------------------------------------------------------------------------



# --- Escenarios (guardar/cargar) ---
st.markdown(
    """
    <div style="display:flex; align-items:center; gap:10px; margin-top:25px; margin-bottom:15px;">
        <!-- Ícono de lista/archivar -->
        <svg xmlns="http://www.w3.org/2000/svg"
             width="30" height="30"
             viewBox="0 0 24 24"
             fill="none" stroke="#00909a" stroke-width="2.5"
             stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
            <line x1="9" y1="9" x2="15" y2="9"></line>
            <line x1="9" y1="15" x2="15" y2="15"></line>
        </svg>
        <h2 style="color:#FAFAFA; margin:0;">Escenarios</h2>
    </div>
    """,
    unsafe_allow_html=True
)

# --- Fila 1: guardar escenario ---
col1, col2 = st.columns([4,1])  # campo más ancho, botón más chico
with col1:
    nombre = st.text_input(
        "Nombre del escenario",
        key="escenario_nombre",
        placeholder="Ej: Caso base 12x14.315"
    )
with col2:
    # Empujamos el botón hacia abajo para que quede alineado con el campo
    st.write("")
    st.write("")
    if st.button("💾 Guardar", use_container_width=True):
        if not nombre.strip():
            st.warning("Poné un nombre para el escenario.")
        else:
            st.session_state.escenarios[nombre] = {
                "pv": float(st.session_state.pv),
                "n": int(st.session_state.n),
                "pmt": float(st.session_state.pmt),
                "tipo_pago": st.session_state.tipo_pago,
                "modo": st.session_state.modo,
                "i_periodo": float(st.session_state.i_periodo),
                "periodicidad": st.session_state.periodicidad,
                "fecha_inicial": st.session_state.fecha_inicial,
                "resultado": st.session_state.get("resultado", {}),
            }
            st.success(f"Escenario “{nombre}” guardado.")



# --- Fila 2: Cargar escenario ---
col3, col4 = st.columns([4,1])

with col3:
    opciones = ["(ninguno)"] + sorted(st.session_state.escenarios.keys())
    escenario_sel = st.selectbox("Seleccionar escenario guardado", options=opciones, key="escenario_sel")

with col4:
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)  # alinear arriba
    if st.button("📥 Cargar", use_container_width=True):
        sel = st.session_state.escenario_sel
        if sel and sel != "(ninguno)" and sel in st.session_state.escenarios:
            e = st.session_state.escenarios[sel]
            st.session_state["preset"] = {
                "pv": e.get("pv", 0.0),
                "n": e.get("n", 1),
                "pmt": e.get("pmt", 0.0),
                "tipo_pago": e.get("tipo_pago", "Vencido (fin de período)"),
                "modo": e.get("modo", "Calcular tasa (i)"),
                "i_periodo": e.get("i_periodo", 0.0),
                "periodicidad": e.get("periodicidad", "Mensual"),
                "fecha_inicial": e.get("fecha_inicial", st.session_state.fecha_inicial),
                "resultado": None,
                "explicacion": None,
            }
            st.success(f"Escenario “{sel}” cargado. Revisá los campos y presioná **Calcular**.")
            st.rerun()  # 👈 forzamos recarga antes de que se pinten los widgets
# --- fin Fila 2 ---



# Listado de escenarios guardados
if st.session_state.escenarios:
    st.caption("Escenarios guardados:")
    st.dataframe(
        pd.DataFrame([
            {
                "nombre": k,
                "modo": v.get("modo", ""),
                "tipo_pago": v.get("tipo_pago", ""),
                "pv": v.get("pv", 0.0),
                "n": v.get("n", 0),
                "pmt": v.get("pmt", 0.0),
            } for k, v in st.session_state.escenarios.items()
        ]),
        use_container_width=True,
        hide_index=True,
    )
# --- Escenarios (guardar/cargar) ---


#!------------------------------------------------------------------------------
st.divider()   # ← ÚNICO separador


# uploaders + export JSON
# # st.subheader("📂 Importar / Exportar")

# --- Subtítulo: Importar / Exportar ---
st.markdown(
    """
    <div style="display:flex; align-items:center; gap:10px; margin-top:25px; margin-bottom:15px;">
        <!-- Ícono carpeta con flecha -->
        <svg xmlns="http://www.w3.org/2000/svg"
             width="30" height="30"
             viewBox="0 0 24 24"
             fill="none" stroke="#00909a" stroke-width="2.5"
             stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 4h5l2 2h9a1 1 0 0 1 1 1v13a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1z"></path>
            <path d="M12 11v6"></path>
            <path d="M9 14l3 3 3-3"></path>
        </svg>
        <h2 style="color:#FAFAFA; margin:0;">Importar / Exportar</h2>
    </div>
    """,
    unsafe_allow_html=True
)
# --- fin Subtítulo ---


# --- Botón: Cargar ejemplo ---
if st.button("Cargar ejemplo"):
    st.session_state["preset"] = {
        "pv": 100000.00,
        "n": 12,
        "pmt": 14315.22,
        "tipo_pago": "Vencido (fin de período)",
        "modo": "Calcular tasa (i)",
        "i_periodo": 0.0,
        "periodicidad": "Mensual",
        "fecha_inicial": date(2025, 8, 29),
        "resultado": None,
        "explicacion": None,
    }
    st.success("Ejemplo cargado. Ahora hacé clic en «Calcular tasa».")
    st.rerun()
# --- fin Botón: Cargar ejemplo ---



# --- Exportar escenario como JSON ---
if st.button("Exportar escenario actual como JSON"):
    data = {
        "precio_contado": float(st.session_state.pv),
        "monto_cuota": float(st.session_state.pmt),
        "tipo_pago": st.session_state.tipo_pago,
        "modo": st.session_state.modo,
        "periodicidad": st.session_state.periodicidad,
        "fecha_inicial": st.session_state.fecha_inicial.isoformat(),
    }
    if st.session_state.modo == "Calcular tasa (i)":
        data["CANT C"] = int(st.session_state.get("n", 0))
        # si ya calculaste la tasa, la incluimos como referencia
        resultado = st.session_state.get("resultado")
        if resultado and "i" in resultado:
            data["tasa_periodo_calculada"] = float(resultado["i"])  # fracción
    else:  # "Calcular cuotas (n)"
        data["tasa_periodo"] = float(st.session_state.get("i_periodo", 0.0))  # fracción


    json_bytes = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    st.download_button(
        "📥 Descargar JSON",
        data=json_bytes,
        file_name="escenario.json",
        mime="application/json"
    )
# --- fin Exportar escenario como JSON ---



#!------------------------------------------------------------------------------
st.divider()   # ← ÚNICO separador



# --- IA: Explicación (siempre visible) ---
# st.subheader("🤖 IA – Explicación")

# --- Subtítulo: IA – Explicación ---
st.markdown(
    """
    <div style="display:flex; align-items:center; gap:10px; margin-top:25px; margin-bottom:15px;">
        <!-- Ícono robot IA -->
        <svg xmlns="http://www.w3.org/2000/svg"
             width="30" height="30"
             viewBox="0 0 24 24"
             fill="none" stroke="#00909a" stroke-width="2.5"
             stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="11" width="18" height="10" rx="2" ry="2"></rect>
            <circle cx="7.5" cy="16" r="1"></circle>
            <circle cx="16.5" cy="16" r="1"></circle>
            <path d="M12 3v4"></path>
            <path d="M9 3h6"></path>
        </svg>
        <h2 style="color:#FAFAFA; margin:0;">IA – Explicación</h2>
    </div>
    """,
    unsafe_allow_html=True
)
# --- fin Subtítulo ---

# Selector de idioma
_opt = st.selectbox("Idioma de la explicación", ["Español", "English"], index=0, key="ia_lang")
lang = "es" if _opt.startswith("Esp") else "en"

# Habilitar solo si ya hay resultado
has_result = bool(st.session_state.get("resultado"))
if not has_result:
    st.caption("Calculá primero para habilitar la explicación.")

# Botón primario (color) y deshabilitado si no hay resultado
lang = "es" if st.session_state.get("ia_lang", "Español").startswith("Esp") else "en"

if st.button("✨ Explicar con IA", type="primary", disabled=not has_result,
             help="Genera una explicación con los valores ya calculados (sin recalcular)."):
    r = st.session_state.get("resultado", {})

    # Lectura segura de valores
    pv  = float(r.get("pv", 0.0))
    n   = int(r.get("n", r.get("n_red", 0)))
    pmt = float(r.get("pmt", 0.0))
    adelantado = bool(r.get("adelantado", False))
    i   = float(r.get("i", 0.0))

    with st.spinner("Generando explicación…"):
        out = explicar_con_ia(
            client, pv, pmt, n, adelantado, i,
            periodicidad=st.session_state.periodicidad,
            fecha_inicial=st.session_state.fecha_inicial,
            modo=r.get("modo", "Calcular tasa (i)"),
            ultima_cuota=None,   # opcional; si la guardás en session_state, pasala aquí
            lang=lang,
        )
    st.session_state.explicacion = out["text"]


# Botón limpiar (primero)
if st.button("🧹 Limpiar explicación", key="clear_exp"):
    st.session_state.explicacion = None

# Mostrar explicación (después)
if st.session_state.get("explicacion"):
    st.info(st.session_state.explicacion)



st.divider()   # ← ÚNICO separador


# --- 📚 Tutor IA (conceptos) + PDF opcional ---
st.markdown(
    """
    <div style="display:flex; align-items:center; gap:10px; margin-top:25px; margin-bottom:15px;">
        <!-- Ícono libro abierto -->
        <svg xmlns="http://www.w3.org/2000/svg"
             width="30" height="30"
             viewBox="0 0 24 24"
             fill="none" stroke="#00909a" stroke-width="2.5"
             stroke-linecap="round" stroke-linejoin="round">
            <path d="M4 19.5a2.5 2.5 0 0 1 2.5-2.5H20"></path>
            <path d="M20 22V4a2 2 0 0 0-2-2H7a2 2 0 0 0-2 2v18"></path>
            <path d="M12 4v18"></path>
        </svg>
        <h2 style="color:#FAFAFA; margin:0;">Tutor IA (conceptos)</h2>
    </div>
    """,
    unsafe_allow_html=True
)

# 1) Subida de PDF (opcional)
upl_pdf = st.file_uploader("Subir una fuente PDF (opcional)", type=["pdf"], key="kb_upl")
if upl_pdf is not None:
    try:
        reader = PdfReader(upl_pdf)
        text = "\n".join((page.extract_text() or "") for page in reader.pages)
        st.session_state.kb_text = text
        st.session_state.kb_name = upl_pdf.name
        st.success(f"PDF cargado: {upl_pdf.name} · {len(reader.pages)} páginas")
    except Exception as e:
        st.error(f"No pude leer el PDF: {e}")

# 2) Pregunta abierta (conceptos)
q = st.text_input("Preguntá algo de matemática financiera (p. ej. '¿Cómo se calcula la cuota francesa?')", key="kb_q")

# 3) Respuesta con IA, usando la fuente si existe (sin recalcular nada)
btn_disabled = (not q)
if st.button("💬 Responder (IA)", type="secondary", disabled=btn_disabled,
             help="Responde usando la fuente PDF si está cargada; no recalcula, solo explica."):
    kb = st.session_state.get("kb_text", "")
    kb_short = kb[:12000]
    kb_name = st.session_state.get("kb_name", "fuente")

    system = (
        "Asistente de Matemática Financiera. Responde de forma clara y breve (6–10 líneas). "
        "Si hay fuente, apóyate en ella y dilo explícitamente; si no está en la fuente, acláralo. "
        "No inventes fórmulas ni recalcules resultados del caso; solo explica conceptos."
    )
    user = (
        f"Pregunta del usuario: {q}\n\n"
        f"Fuente PDF (opcional, extracto de '{kb_name}'):\n{kb_short}"
    )
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
        st.info(resp.choices[0].message.content.strip())
    except Exception as e:
        st.error(f"Error al consultar IA: {e}")
# --- fin Tutor IA ---



#!------------------------------------------------------------------------------



# Acerca de (pie de página)
with st.expander("Acerca de "):
    st.markdown(
        """
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:10px;">
            <svg xmlns="http://www.w3.org/2000/svg"
                 width="22" height="22"
                 viewBox="0 0 24 24"
                 fill="none" stroke="#00909a" stroke-width="2.5"
                 stroke-linecap="round" stroke-linejoin="round">
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="12" y1="16" x2="12" y2="12"></line>
                <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
            <span style="font-size:16px; color:#FAFAFA;">Acerca de esta herramienta</span>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown(
        "- Matemática Financiera clásica: prestación vs. contraprestación; pago vencido/adelantado.\n"
        "- Cálculo de **i** (tasa por período) por **equivalencia**: Newton + bisección con **semilla tipo Baily**.\n"
        "- Cálculo de **n** (cantidad de cuotas) por **fórmula cerrada**:  \n"
        "  n = -ln(1 - i·PV/PMT) / ln(1+i) (pago **vencido**). En **adelantado**, se trae PV a vencido y se aplica la misma fórmula.\n"
        "- Opción de **ajustar la última cuota** para que VP(cuotas) ≈ contado (equivalencia exacta).\n"
        "- Periodicidad y **fechas de pago** (fecha inicial + salto según período).\n"
        "- Resultados en **fracción** (tanto por uno) y **porcentaje** (tanto por ciento); exportes **CSV/XLSX/PDF**.\n"
        "- Uso educativo: verificá supuestos y datos antes de decidir."
    )

