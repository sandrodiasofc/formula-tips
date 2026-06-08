# -*- coding: utf-8 -*-
import math
import time
import os
import unicodedata
import streamlit as st
import requests
import pandas as pd
from io import StringIO
from playwright.sync_api import sync_playwright

# ── Normalizar texto ───────────────────────────────────────────────────────────

def normalizar(texto):
    return unicodedata.normalize("NFD", texto.lower().strip()).encode("ascii", "ignore").decode("ascii")

# ── URLs ───────────────────────────────────────────────────────────────────────

WHOSCORED_URLS = {
    "brasileirao":      "https://br.whoscored.com/regions/31/tournaments/95/seasons/10980/stages/25039/teamstatistics/brasil-brasileir%C3%A3o-2026",
    "premier league":   "https://br.whoscored.com/regions/252/tournaments/2/teamstatistics/inglaterra-premier-league-2025-2026",
    "champions league": "https://br.whoscored.com/regions/250/tournaments/12/teamstatistics/champions-league-2025-2026",
    "la liga":          "https://br.whoscored.com/regions/206/tournaments/4/teamstatistics/espanha-la-liga-2025-2026",
    "serie a":          "https://br.whoscored.com/regions/108/tournaments/5/teamstatistics/italia-serie-a-2025-2026",
    "bundesliga":       "https://br.whoscored.com/regions/81/tournaments/3/teamstatistics/alemanha-bundesliga-2025-2026",
    "ligue 1":          "https://br.whoscored.com/regions/74/tournaments/6/teamstatistics/franca-ligue-1-2025-2026",
    "sul-americana":    "https://br.whoscored.com/regions/250/tournaments/331/teamstatistics/copa-sul-americana-2026",
}

FBREF_IDS = {
    "brasileirao":      "24",
    "premier league":   "9",
    "champions league": "8",
    "la liga":          "12",
    "serie a":          "11",
    "bundesliga":       "20",
    "ligue 1":          "13",
    "sul-americana":    "45",
}

# ── Browser anti-bot ───────────────────────────────────────────────────────────

def novo_browser():
    p = sync_playwright().start()
    browser = p.chromium.launch(
        headless=True,
        args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
    )
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        locale="pt-BR",
        viewport={"width": 1366, "height": 768},
    )
    ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return p, browser, ctx

# ── FBref via requests + pandas (sem browser) ──────────────────────────────────

def buscar_fbref(competicao: str) -> dict:
    chave = normalizar(competicao)
    comp_id = FBREF_IDS.get(chave)
    if not comp_id:
        return {}

    url = f"https://fbref.com/en/comps/{comp_id}/stats/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
    }

    dados = {}
    try:
        time.sleep(4)  # respeita rate limit do FBref
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            return {}

        tabelas = pd.read_html(StringIO(resp.text))
        for df in tabelas:
            # Procura tabela que tenha colunas xG e Squad/Team
            cols = [str(c).lower() for c in df.columns.get_level_values(-1)]
            has_squad = any("squad" in c or "team" in c for c in cols)
            has_xg = any(c == "xg" for c in cols)
            if not (has_squad and has_xg):
                continue

            # Flatten multi-index se necessário
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [' '.join(str(x) for x in col).strip() for col in df.columns]

            df.columns = [c.lower().strip() for c in df.columns]

            # Encontra colunas certas
            squad_col = next((c for c in df.columns if "squad" in c or "team" in c), None)
            xg_col    = next((c for c in df.columns if c.endswith("xg") and "xga" not in c and "npxg" not in c), None)
            xga_col   = next((c for c in df.columns if "xga" in c and "npxg" not in c), None)
            mp_col    = next((c for c in df.columns if c in ("mp", "matches", "pj", "pg")), None)

            if not (squad_col and xg_col):
                continue

            for _, row in df.iterrows():
                try:
                    nome = str(row[squad_col]).lower().strip()
                    if nome in ("squad", "nan", ""):
                        continue
                    xg  = float(str(row[xg_col]).replace(",", "."))
                    xga = float(str(row[xga_col]).replace(",", ".")) if xga_col else xg
                    mp  = float(str(row[mp_col]).replace(",", ".")) if mp_col else 1
                    if mp > 0 and xg > 0:
                        dados[nome] = {
                            "xg":  round(xg / mp, 2),
                            "xga": round(xga / mp, 2),
                        }
                except Exception:
                    continue
            if dados:
                break
    except Exception as e:
        st.warning(f"FBref: {e}")

    return dados

# ── WhoScored via Playwright ───────────────────────────────────────────────────

def buscar_whoscored(competicao: str) -> dict:
    chave = normalizar(competicao)
    url = WHOSCORED_URLS.get(chave)
    if not url:
        return {}
    dados = {}
    p = browser = ctx = None
    try:
        p, browser, ctx = novo_browser()
        page = ctx.new_page()
        page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,mp4,mp3}", lambda r: r.abort())
        time.sleep(2)
        page.goto(url, wait_until="networkidle", timeout=60000)
        time.sleep(4)
        try:
            page.click("button:has-text('Accept')", timeout=4000)
            time.sleep(1)
        except Exception:
            pass
        page.wait_for_selector("table#top-team-stats-summary-grid", timeout=30000)
        time.sleep(3)
        rows = page.query_selector_all("table#top-team-stats-summary-grid tbody tr")
        for row in rows:
            cells = row.query_selector_all("td")
            if len(cells) < 10:
                continue
            try:
                nome_el = row.query_selector("td a.team-link")
                if not nome_el:
                    continue
                nome = nome_el.inner_text().strip().lower()
                textos = [c.inner_text().strip() for c in cells]
                xg_val = xga_val = None
                for t in textos:
                    try:
                        v = float(t.replace(",", "."))
                        if 0.3 <= v <= 3.5:
                            if xg_val is None:
                                xg_val = v
                            elif xga_val is None:
                                xga_val = v
                                break
                    except ValueError:
                        continue
                if xg_val and xga_val:
                    dados[nome] = {"xg": xg_val, "xga": xga_val}
            except Exception:
                continue
    except Exception as e:
        st.warning(f"WhoScored: {e}")
    finally:
        try:
            browser.close()
            p.stop()
        except Exception:
            pass
    return dados

# ── Busca com fallback ─────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def buscar_dados_liga(competicao: str) -> dict:
    # 1. FBref (mais confiavel, sem browser)
    dados = buscar_fbref(competicao)
    if dados:
        st.toast("Dados obtidos do FBref")
        return dados
    # 2. WhoScored (browser)
    st.toast("FBref indisponivel, tentando WhoScored...")
    time.sleep(3)
    dados = buscar_whoscored(competicao)
    if dados:
        st.toast("Dados obtidos do WhoScored")
        return dados
    return {}

# ── Modelo Poisson ─────────────────────────────────────────────────────────────

def encontrar_time(nome: str, dados: dict):
    chave = nome.lower().strip()
    if chave in dados:
        return dados[chave]
    for k, v in dados.items():
        if chave in k or k in chave:
            return v
    return None

def poisson(lmbda: float, k: int) -> float:
    if lmbda <= 0:
        return 1.0 if k == 0 else 0.0
    return math.exp(-lmbda) * (lmbda ** k) / math.factorial(k)

def analisar(time_a, time_b, competicao, odds=None):
    with st.spinner("Buscando dados..."):
        dados = buscar_dados_liga(competicao)

    xg_a_raw = encontrar_time(time_a, dados)
    xg_b_raw = encontrar_time(time_b, dados)

    DEFAULT = {"xg": 1.40, "xga": 1.40}
    xg_a = xg_a_raw or DEFAULT
    xg_b = xg_b_raw or DEFAULT

    if not xg_a_raw:
        st.info(f"{time_a} nao encontrado - usando media da liga.")
    if not xg_b_raw:
        st.info(f"{time_b} nao encontrado - usando media da liga.")

    l1 = ((xg_a["xg"] + xg_b["xga"]) / 2) * 0.95
    l2 = ((xg_b["xg"] + xg_a["xga"]) / 2) * 0.90

    v1 = e = v2 = 0.0
    for i in range(10):
        for j in range(10):
            p = poisson(l1, i) * poisson(l2, j)
            if i > j:    v1 += p
            elif i == j: e  += p
            else:        v2 += p

    btts    = (1 - math.exp(-l1)) * (1 - math.exp(-l2))
    over25  = 1 - sum(poisson(l1 + l2, k) for k in range(3))
    over15  = 1 - sum(poisson(l1 + l2, k) for k in range(2))
    under45 = sum(poisson(l1 + l2, k) for k in range(5))

    st.markdown(f"## {time_a} x {time_b}")
    st.caption(competicao)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Resultado")
        st.metric(f"Vit. {time_a}", f"{v1*100:.1f}%")
        st.metric("Empate",         f"{e*100:.1f}%")
        st.metric(f"Vit. {time_b}", f"{v2*100:.1f}%")
    with col2:
        st.markdown("#### Mercados")
        st.metric("Over 1.5",  f"{over15*100:.1f}%")
        st.metric("Over 2.5",  f"{over25*100:.1f}%")
        st.metric("Under 4.5", f"{under45*100:.1f}%")
        st.metric("BTTS",      f"{btts*100:.1f}%")

    st.markdown("#### xG")
    st.table({
        "Time":   [time_a, time_b],
        "xG":     [f"{xg_a['xg']:.2f}", f"{xg_b['xg']:.2f}"],
        "xGA":    [f"{xg_a['xga']:.2f}", f"{xg_b['xga']:.2f}"],
        "Lambda": [f"{l1:.2f}", f"{l2:.2f}"],
    })

    if odds:
        probs = {"v1": v1, "emp": e, "v2": v2}
        nomes = {"v1": f"Vit. {time_a}", "emp": "Empate", "v2": f"Vit. {time_b}"}
        st.markdown("#### Value Bets")
        encontrou = False
        for k, odd in odds.items():
            if k in probs:
                p_val = probs[k]
                ev = p_val * (odd - 1) - (1 - p_val)
                if ev > 0:
                    st.success(f"{nomes[k]} | Odd {odd:.2f} | EV +{ev*100:.1f}%")
                    encontrou = True
        if not encontrou:
            st.warning("Nenhum value bet identificado.")

# ── UI ─────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="FORMULA TIPS", page_icon="⚽", layout="centered")

st.markdown("""
<style>
.stApp { max-width: 520px; margin: 0 auto; }
.stButton > button {
    width: 100%;
    background: linear-gradient(135deg, #00FF88, #00CC66);
    color: #0A0A0A; font-size: 18px; font-weight: bold;
    border: none; border-radius: 12px; padding: 14px;
}
</style>
""", unsafe_allow_html=True)

# Cabeçalho com logo
logo_path = "logotipo formula tips 01.png"
if os.path.exists(logo_path):
    col_logo, col_titulo = st.columns([1, 3])
    with col_logo:
        st.image(logo_path, width=100)
    with col_titulo:
        st.markdown("<h1 style='margin:0; padding-top:10px;'>FORMULA TIPS</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color:#555; margin:0;'>A formula certa para o green</p>", unsafe_allow_html=True)
else:
    st.markdown("<h1 style='margin:0;'>FORMULA TIPS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#555;'>A formula certa para o green</p>", unsafe_allow_html=True)

st.markdown("---")

time_a = st.text_input("Time Mandante", placeholder="Ex: Flamengo")
time_b = st.text_input("Time Visitante", placeholder="Ex: Palmeiras")
competicao = st.selectbox("Competicao", [
    "Brasileirao", "Premier League", "Champions League",
    "La Liga", "Serie A", "Bundesliga", "Ligue 1", "Sul-Americana"
])

with st.expander("Odds (opcional)"):
    c1, c2, c3 = st.columns(3)
    with c1: odd_v1  = st.number_input("Vit. Casa", 1.01, 20.0, 2.00, 0.01)
    with c2: odd_emp = st.number_input("Empate",    1.01, 20.0, 3.20, 0.01)
    with c3: odd_v2  = st.number_input("Vit. Fora", 1.01, 20.0, 3.50, 0.01)

if st.button("ANALISAR AGORA", use_container_width=True):
    if not time_a or not time_b:
        st.warning("Preencha os nomes dos dois times.")
    else:
        odds = {"v1": odd_v1, "emp": odd_emp, "v2": odd_v2}
        analisar(time_a, time_b, competicao, odds)
