import streamlit as st
import requests
import pandas as pd
import ta
import time
import feedparser
from datetime import datetime, timezone
from PIL import Image
import plotly.graph_objects as go
from google import genai

st.set_page_config(page_title="APEXQUANT AI | Terminal Cuantitativa", page_icon="⚡", layout="wide")

GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
TWELVE_DATA_KEY = st.secrets["TWELVE_DATA_KEY"]


st.markdown("""
<style>
@import url('https://googleapis.com');

html, body, [class*="css"] {
    font-family: 'JetBrains Mono', monospace;
    background-color: #050811;
    color: #E2E8F0;
}

h1, h2, h3, .hud-title {
    font-family: 'Orbitron', sans-serif !important;
    letter-spacing: 1.5px;
    text-transform: uppercase;
}

.hud-card {
    background: linear-gradient(145deg, #0B1120 0%, #070B14 100%);
    border: 1px solid #1E293B;
    border-radius: 12px;
    padding: 25px;
    box-shadow: 0 0 20px rgba(0, 240, 255, 0.08);
    text-align: center;
}

.hud-card-green {
    background: linear-gradient(145deg, #042F1E 0%, #061A12 100%);
    border: 2px solid #00FF9D;
    border-radius: 12px;
    padding: 30px;
    box-shadow: 0 0 30px rgba(0, 255, 157, 0.35);
    text-align: center;
}

.hud-card-red {
    background: linear-gradient(145deg, #350813 0%, #1A040A 100%);
    border: 2px solid #FF0055;
    border-radius: 12px;
    padding: 30px;
    box-shadow: 0 0 30px rgba(255, 0, 85, 0.35);
    text-align: center;
}

.hud-card-amber {
    background: linear-gradient(145deg, #331D04 0%, #1A0E02 100%);
    border: 2px solid #FFB800;
    border-radius: 12px;
    padding: 30px;
    box-shadow: 0 0 30px rgba(255, 184, 0, 0.35);
    text-align: center;
}

.hud-card-standby {
    background: linear-gradient(145deg, #0F172A 0%, #090D16 100%);
    border: 1px solid #00F0FF;
    border-radius: 12px;
    padding: 30px;
    box-shadow: 0 0 20px rgba(0, 240, 255, 0.15);
    text-align: center;
}

.coin-badge {
    display: inline-block;
    padding: 6px 16px;
    border-radius: 20px;
    font-family: 'Orbitron', sans-serif;
    font-weight: 700;
    font-size: 14px;
    margin-bottom: 10px;
}

.neon-green { color: #00FF9D; text-shadow: 0 0 12px rgba(0, 255, 157, 0.7); }
.neon-red { color: #FF0055; text-shadow: 0 0 12px rgba(255, 0, 85, 0.7); }
.neon-cyan { color: #00F0FF; text-shadow: 0 0 12px rgba(0, 240, 255, 0.7); }
.neon-amber { color: #FFB800; text-shadow: 0 0 12px rgba(255, 184, 0, 0.7); }

div[data-testid="stMetric"] {
    background-color: #0B1120;
    border: 1px solid #1E293B;
    border-left: 4px solid #00F0FF;
    padding: 15px;
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

ACTIVOS_CONFIG = {
    "₿ BITCOIN (BTC/USD)": {"simbolo": "BTC/USD", "icono": "₿", "color": "#F7931A", "tag": "CRYPTO-CORE"},
    "🥇 ORO SPOT (XAU/USD)": {"simbolo": "XAU/USD", "icono": "Au", "color": "#FFD700", "tag": "COMMODITY-PRO"},
    "Ξ ETHEREUM (ETH/USD)": {"simbolo": "ETH/USD", "icono": "Ξ", "color": "#627EEA", "tag": "ALTCOIN-L1"},
    "💶 EURO / DÓLAR (EUR/USD)": {"simbolo": "EUR/USD", "icono": "€/$", "color": "#00F0FF", "tag": "FOREX-MAJOR"},
    "💷 LIBRA / DÓLAR (GBP/USD)": {"simbolo": "GBP/USD", "icono": "£/$", "color": "#A855F7", "tag": "FOREX-MAJOR"},
    "⚡ NASDAQ 100 (QQQ)": {"simbolo": "QQQ", "icono": "NDX", "color": "#00FF9D", "tag": "INDEX-TECH"},
    "🏛️ S&P 500 (SPY)": {"simbolo": "SPY", "icono": "SPX", "color": "#38BDF8", "tag": "INDEX-USA"}
}

FUENTES_OFICIALES = [
    "https://federalreserve.gov",
    "https://europa.eu",
    "https://forexlive.com",
    "https://investing.com",
    "https://elpais.com"
]

client = genai.Client(api_key=GEMINI_API_KEY)

def obtener_sesion_actual():
    hora_utc = datetime.now(timezone.utc).hour
    if 7 <= hora_utc < 12:
        return "SESIÓN LONDRES // LIQUIDEZ ALTA"
    elif 12 <= hora_utc < 16:
        return "SOLAPE LONDRES-NY // VOLATILIDAD MÁXIMA"
    elif 16 <= hora_utc < 21:
        return "SESIÓN NUEVA YORK // LIQUIDEZ ACTIVA"
    else:
        return "SESIÓN ASIÁTICA // RANGO BAJO"

def obtener_impacto_ia_oficial(nombre_activo):
    if "PEGA_AQUI" in GEMINI_API_KEY or not GEMINI_API_KEY.strip():
        return 0.0, False, "API KEY PENDIENTE"

    titulares = []
    claves = ["gold", "oro", "fed", "inflation", "inflación", "rates", "tipos", "bce", "ecb", "dollar", "dólar", "bitcoin", "crypto", "nasdaq", "cpi", "ipc", "war", "guerra"]

    for url in FUENTES_OFICIALES:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:
                if any(k in entry.title.lower() for k in claves):
                    titulares.append(entry.title)
        except Exception:
            continue

    if not titulares:
        return 0.0, False, "ESCUDO MACRO: SIN AMENAZAS"

    texto = "\n".join(f"- {t}" for t in titulares[:8])
    prompt = (
        f"Eres un motor cuantitativo institucional evaluando: {nombre_activo}. "
        f"Analiza ÚNICAMENTE estos titulares oficiales:\n{texto}\n\n"
        "Devuelve exactamente dos líneas:\n"
        "AJUSTE: [número entero entre -25 y 25; positivo=alcista, negativo=bajista]\n"
        "PELIGRO: [SI o NO - pon SI únicamente si hay decisión de tipos de interés o IPC extremo ahora mismo]"
    )

    try:
        resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        ajuste = 0.0
        peligro = False
        for linea in resp.text.strip().splitlines():
            if "AJUSTE:" in linea.upper():
                num_str = linea.split(":")[-1].strip().replace("%", "").replace("+", "")
                ajuste = max(-25.0, min(25.0, float(num_str)))
            if "PELIGRO:" in linea.upper():
                peligro = "SI" in linea.upper()
        return ajuste, peligro, "RED NEURONAL ACTIVA"
    except Exception as e:
        return 0.0, False, f"STANDBY IA: {e}"

def obtener_datos_activo(simbolo, intervalo="5min"):
    if "PEGA_AQUI" in TWELVE_DATA_KEY or not TWELVE_DATA_KEY.strip():
        return None, None, "Configura tu TWELVE_DATA_KEY en el código."

    base = "https://api." + "twelvedata.com" + "/time_series"
    url_corto = f"{base}?symbol={simbolo}&interval={intervalo}&outputsize=60&apikey={TWELVE_DATA_KEY}"
    resp = requests.get(url_corto).json()

    if "values" not in resp:
        return None, None, resp.get("message", "Error conectando con el servidor de precios.")

    df = pd.DataFrame(resp["values"]).iloc[::-1].reset_index(drop=True)
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)

    df["RSI"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    df["EMA_9"] = ta.trend.EMAIndicator(df["close"], window=9).ema_indicator()
    df["EMA_21"] = ta.trend.EMAIndicator(df["close"], window=21).ema_indicator()
    df["EMA_50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
    bb = ta.volatility.BollingerBands(df["close"], window=20, window_dev=2)
    df["BB_alta"] = bb.bollinger_hband()
    df["BB_baja"] = bb.bollinger_lband()
    df["ATR"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], window=14).average_true_range()

    tendencia_mayor = "ALCISTA ▲" if df.iloc[-1]["close"] > df.iloc[-1]["EMA_50"] else "BAJISTA ▼"
    return df, tendencia_mayor, None

if "diario_trades" not in st.session_state:
    st.session_state.diario_trades = []
if "modo_trader" not in st.session_state:
    st.session_state.modo_trader = "COMPRANDO"

st.sidebar.markdown("<h2 class='neon-cyan'>⚡ APEXQUANT AI</h2>", unsafe_allow_html=True)
st.sidebar.caption("SISTEMA CUANTITATIVO v4.0")
st.sidebar.divider()

pagina = st.sidebar.radio(
    "MÓDULOS DEL SISTEMA:",
    [
        "01 // RADAR CUANTITATIVO",
        "02 // VISIÓN ARTIFICIAL GRÁFICOS",
        "03 // ESCUDO RIESGO & FONDEO",
        "04 // PSICÓLOGO NEURONAL",
        "05 // LICENCIAS & ACCESO PRO"
    ]
)

st.sidebar.divider()
st.sidebar.code(obtener_sesion_actual(), language="text")

if pagina == "01 // RADAR CUANTITATIVO":
    c_act, c_tf, c_son, c_ref = st.columns()
    with c_act:
        nombre_activo = st.selectbox("ACTIVO EN ESCÁNER:", list(ACTIVOS_CONFIG.keys()))
        cfg = ACTIVOS_CONFIG[nombre_activo]
        simbolo = cfg["simbolo"]
    with c_tf:
        temporalidad = st.selectbox("VELAS:", ["1min", "5min", "15min", "1h"], index=1)
    with c_son:
        sonido_activo = st.checkbox("SONIDO TÁCTICO", value=True)
    with c_ref:
        auto_refresco = st.checkbox("LIVE LOOP (60s)", value=False)

    clave_cache = f"scan_{simbolo}"
    if clave_cache not in st.session_state or (time.time() - st.session_state[clave_cache]["tiempo"] > 240):
        ajuste_ia, peligro_ia, estado_ia = obtener_impacto_ia_oficial(nombre_activo)
        st.session_state[clave_cache] = {
            "ajuste": ajuste_ia,
            "peligro": peligro_ia,
            "estado": estado_ia,
            "tiempo": time.time()
        }

    datos_ia = st.session_state[clave_cache]
    df, tendencia_mayor, error = obtener_datos_activo(simbolo, temporalidad)

    if error:
        st.error(f"⚠️ {error}")
        st.stop()

    ultima = df.iloc[-1]
    decimales = 4 if "EUR" in simbolo or "GBP" in simbolo else 2
    precio = round(ultima["close"], decimales)
    rsi = round(ultima["RSI"], 1)
    atr = round(ultima["ATR"], decimales)

    prob_compra = 50.0
    prob_compra += 15 if ultima["EMA_9"] > ultima["EMA_21"] else -15
    if rsi <= 30:
        prob_compra += 20
    elif rsi >= 70:
        prob_compra -= 20
    if precio >= ultima["BB_alta"]:
        prob_compra -= 15
    elif precio <= ultima["BB_baja"]:
        prob_compra += 15

    prob_compra += datos_ia["ajuste"]
    prob_compra = round(max(0.0, min(100.0, prob_compra)), 1)
