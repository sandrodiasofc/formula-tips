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

CSS = """
<style>
html, body, [class*="stApp"] {
    background-color: #0D1B2A !important;
    color: #F0F0F0 !important;
}
.stTextInput > div > div > input {
    background-color: #1C2E40; color: #F0F0F0;
    border: 1px solid #C9A84C; border-radius: 8px;
}
.stSelectbox > div > div {
    background-color: #1C2E40; color: #F0F0F0;
    border: 1px solid #C9A84C; border-radius: 8px;
}
.stExpander { background-color: #1C2E40 !important; border: 1px solid #2A3F55 !important; border-radius: 8px; }
.stButton > button {
    width: 100%;
    background: linear-gradient(135deg, #C0152A, #8B0F1E);
    color: #F0F0F0; font-size: 18px; font-weight: bold;
    border: 2px solid #C9A84C; border-radius: 12px; padding: 14px; letter-spacing: 1px;
}
.stButton > button:hover { background: linear-gradient(135deg, #E0182F, #C0152A); }
.card { background-color: #1C2E40; border: 1px solid #2A3F55; border-radius: 12px; padding: 16px; margin-bottom: 12px; }
.card-title { color: #C9A84C; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; border-bottom: 1px solid #2A3F55; padding-bottom: 6px; }
.stat-row { display: flex; justify-content: space-between; align-items: center; padding: 7px 0; border-bottom: 1px solid #1a2d3d; font-size: 14px; }
.stat-row:last-child { border-bottom: none; }
.stat-label { color: #A0B4C8; }
.stat-value { color: #F0F0F0; font-weight: 600; }
.prob-bar-bg { background: #0D1B2A; border-radius: 99px; height: 8px; width: 80px; display: inline-block; vertical-align: middle; margin: 0 6px; }
.prob-fill { height: 100%; border-radius: 99px; }
.match-header { text-align: center; padding: 16px 0 8px; }
.match-title { font-size: 22px; font-weight: 700; color: #F0F0F0; }
.match-comp { font-size: 13px; color: #C9A84C; margin-top: 4px; }
.value-bet { background: linear-gradient(135deg, #1a3d1a, #0f2a0f); border: 1px solid #4CAF50; border-radius: 10px; padding: 12px 16px; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 6px; }
.no-value { background: #1C2E40; border: 1px solid #2A3F55; border-radius: 10px; padding: 12px 16px; color: #A0B4C8; font-size: 13px; text-align: center; }
.fonte-tag { font-size: 10px; color: #C9A84C; background: #0D1B2A; padding: 1px 6px; border-radius: 4px; margin-left: 6px; }
label { color: #A0B4C8 !important; }
p, .stMarkdown p { color: #F0F0F0; }
h1, h2, h3 { color: #F0F0F0 !important; }
</style>
"""

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

FLASHSCORE_URLS = {
    "brasileirao":      "https://www.flashscore.com.br/futebol/brasil/serie-a/classificacao/#/tabela/geral",
    "premier league":   "https://www.flashscore.com.br/futebol/england/premier-league/classificacao/#/tabela/geral",
    "champions league": "https://www.flashscore.com.br/futebol/europa/champions-league/classificacao/#/tabela/geral",
    "la liga":          "https://www.flashscore.com.br/futebol/espanha/laliga/classificacao/#/tabela/geral",
    "serie a":          "https://www.flashscore.com.br/futebol/italia/serie-a/classificacao/#/tabela/geral",
    "bundesliga":       "https://www.flashscore.com.br/futebol/alemanha/bundesliga/classificacao/#/tabela/geral",
    "ligue 1":          "https://www.flashscore.com.br/futebol/franca/ligue-1/classificacao/#/tabela/geral",
    "sul-americana":    "https://www.flashscore.com.br/futebol/america-do-sul/copa-sul-americana/classificacao/#/tabela/geral",
}

INFOGOL_URLS = {
    "brasileirao":      "https://www.infogol.net/pt-br/liga/brasileiro-serie-a/estatisticas/2026",
    "premier league":   "https://www.infogol.net/pt-br/liga/premier-league/estatisticas/2025-2026",
    "champions league": "https://www.infogol.net/pt-br/liga/liga-dos-campeoes/estatisticas/2025-2026",
    "la liga":          "https://www.infogol.net/pt-br/liga/la-liga/estatisticas/2025-2026",
    "serie a":          "https://www.infogol.net/pt-br/liga/serie-a-italiana/estatisticas/2025-2026",
    "bundesliga":       "https://www.infogol.net/pt-br/liga/bundesliga/estatisticas/2025-2026",
    "ligue 1":          "https://www.infogol.net/pt-br/liga/ligue-1/estatisticas/2025-2026",
    "sul-americana":    "https://www.infogol.net/pt-br/liga/copa-sul-americana/estatisticas/2026",
}

FOOTSTATS_URLS = {
    "brasileirao": "http://www.footstats.com.br/index.cfm?tela=timestat&campeonato=53",
}

FBREF_IDS = {
    "brasileirao": "24", "premier league": "9", "champions league": "8",
    "la liga": "12", "serie a": "11", "bundesliga": "20",
    "ligue 1": "13", "sul-americana": "45",
}

DEFAULTS = {
    "brasileirao":      {"xg":1.40,"xga":1.40,"escanteios":5.2,"cartoes":2.1,"chutes":4.5},
    "premier league":   {"xg":1.55,"xga":1.55,"escanteios":5.0,"cartoes":1.8,"chutes":5.0},
    "la liga":          {"xg":1.50,"xga":1.50,"escanteios":4.8,"cartoes":2.3,"chutes":4.8},
    "serie a":          {"xg":1.40,"xga":1.40,"escanteios":5.1,"cartoes":2.5,"chutes":4.6},
    "bundesliga":       {"xg":1.65,"xga":1.65,"escanteios":5.3,"cartoes":1.9,"chutes":5.2},
    "ligue 1":          {"xg":1.45,"xga":1.45,"escanteios":4.9,"cartoes":2.2,"chutes":4.7},
    "champions league": {"xg":1.60,"xga":1.60,"escanteios":5.0,"cartoes":1.7,"chutes":5.1},
    "sul-americana":    {"xg":1.35,"xga":1.35,"escanteios":5.0,"cartoes":2.4,"chutes":4.4},
}

def normalizar(texto):
    return unicodedata.normalize("NFD", texto.lower().strip()).encode("ascii", "ignore").decode("ascii")

def novo_browser():
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        locale="pt-BR", viewport={"width": 1366, "height": 768},
    )
    ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return p, browser, ctx

def aceitar_cookies(page):
    for sel in ["button:has-text('Accept')", "button:has-text('Aceitar')", "button#onetrust-accept-btn-handler", "button:has-text('OK')"]:
        try:
            page.click(sel, timeout=3000)
            time.sleep(1)
            break
        except Exception:
            pass

# ── WhoScored: xG, xGdif, chutes, rating ──────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def buscar_whoscored(competicao: str) -> dict:
    url = WHOSCORED_URLS.get(normalizar(competicao))
    if not url:
        return {}
    p = browser = ctx = None
    dados = {}
    try:
        p, browser, ctx = novo_browser()
        page = ctx.new_page()
        page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,mp4}", lambda r: r.abort())
        time.sleep(2)
        page.goto(url, wait_until="networkidle", timeout=60000)
        time.sleep(4)
        aceitar_cookies(page)
        page.wait_for_selector("table#top-team-stats-summary-grid", timeout=30000)
        time.sleep(3)
        headers_el = page.query_selector_all("table#top-team-stats-summary-grid thead th")
        headers = [h.inner_text().strip().lower() for h in headers_el]
        rows = page.query_selector_all("table#top-team-stats-summary-grid tbody tr")
        for row in rows:
            try:
                nome_el = row.query_selector("td a.team-link")
                if not nome_el:
                    continue
                nome = nome_el.inner_text().strip().lower()
                cells = row.query_selector_all("td")
                vals = [c.inner_text().strip() for c in cells]
                d = {}
                for i, h in enumerate(headers):
                    if i >= len(vals):
                        break
                    v = vals[i]
                    try:
                        fv = float(v.replace(",", "."))
                    except Exception:
                        continue
                    if "xg" in h and "xga" not in h and "diff" not in h:
                        d["xg"] = fv
                    elif "xga" in h or ("xg" in h and "diff" in h):
                        d["xga_diff"] = fv
                    elif "shot" in h or "chute" in h:
                        d["chutes"] = fv
                    elif "rating" in h:
                        d["rating"] = fv
                # xGA = xG - xGdiff
                if "xg" in d and "xga_diff" in d:
                    d["xga"] = round(d["xg"] - d["xga_diff"], 2)
                if d:
                    dados[nome] = d
            except Exception:
                continue
    except Exception:
        pass
    finally:
        try: browser.close(); p.stop()
        except Exception: pass
    return dados

# ── Flashscore: escanteios, cartões ───────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def buscar_flashscore(competicao: str) -> dict:
    url = FLASHSCORE_URLS.get(normalizar(competicao))
    if not url:
        return {}
    p = browser = ctx = None
    dados = {}
    try:
        p, browser, ctx = novo_browser()
        page = ctx.new_page()
        page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,mp4}", lambda r: r.abort())
        time.sleep(2)
        page.goto(url, wait_until="networkidle", timeout=60000)
        time.sleep(4)
        aceitar_cookies(page)
        time.sleep(2)

        # Tenta clicar na aba de estatísticas detalhadas
        for sel in ["a:has-text('Forma')", "a:has-text('Stats')", "a:has-text('Estatisticas')", ".tabs__tab:has-text('Estat')"]:
            try:
                page.click(sel, timeout=3000)
                time.sleep(2)
                break
            except Exception:
                pass

        rows = page.query_selector_all(".ui-table__row, .tableTeam, tr.standings__row")
        for row in rows:
            try:
                nome_el = row.query_selector("a.tableCellParticipant__name, .team__name, td a")
                if not nome_el:
                    continue
                nome = nome_el.inner_text().strip().lower()
                cells = row.query_selector_all("td, .table__cell")
                vals = [c.inner_text().strip() for c in cells]
                nums = []
                for v in vals:
                    try:
                        nums.append(float(v.replace(",", ".")))
                    except Exception:
                        pass
                if len(nums) >= 4:
                    dados[nome] = {
                        "escanteios": nums[-2] if len(nums) > 2 else 5.0,
                        "cartoes": nums[-1] if len(nums) > 1 else 2.0,
                    }
            except Exception:
                continue
    except Exception:
        pass
    finally:
        try: browser.close(); p.stop()
        except Exception: pass
    return dados

# ── Infogol: xG alternativo ────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def buscar_infogol(competicao: str) -> dict:
    url = INFOGOL_URLS.get(normalizar(competicao))
    if not url:
        return {}
    p = browser = ctx = None
    dados = {}
    try:
        p, browser, ctx = novo_browser()
        page = ctx.new_page()
        page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,mp4}", lambda r: r.abort())
        time.sleep(2)
        page.goto(url, wait_until="networkidle", timeout=60000)
        time.sleep(4)
        aceitar_cookies(page)
        time.sleep(2)
        rows = page.query_selector_all("table tbody tr, .stats-table tr")
        for row in rows:
            try:
                nome_el = row.query_selector("td:first-child a, td.team a")
                if not nome_el:
                    continue
                nome = nome_el.inner_text().strip().lower()
                cells = row.query_selector_all("td")
                vals = [c.inner_text().strip() for c in cells]
                d = {}
                for v in vals:
                    try:
                        fv = float(v.replace(",", "."))
                        if 0.3 <= fv <= 3.5 and "xg" not in d:
                            d["xg"] = fv
                        elif 0.3 <= fv <= 3.5 and "xg" in d and "xga" not in d:
                            d["xga"] = fv
                    except Exception:
                        pass
                if d:
                    dados[nome] = d
            except Exception:
                continue
    except Exception:
        pass
    finally:
        try: browser.close(); p.stop()
        except Exception: pass
    return dados

# ── Footstats: fallback Brasileirão ───────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def buscar_footstats(competicao: str) -> dict:
    if normalizar(competicao) != "brasileirao":
        return {}
    url = FOOTSTATS_URLS.get("brasileirao")
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    dados = {}
    try:
        time.sleep(2)
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code != 200:
            return {}
        tabelas = pd.read_html(StringIO(resp.text))
        for df in tabelas:
            df.columns = [str(c).lower().strip() for c in df.columns]
            nome_col = next((c for c in df.columns if "time" in c or "clube" in c or "equipe" in c), None)
            if not nome_col:
                continue
            for _, row in df.iterrows():
                try:
                    nome = str(row[nome_col]).lower().strip()
                    if nome in ("nan", "time", ""):
                        continue
                    d = {}
                    for col in df.columns:
                        try:
                            v = float(str(row[col]).replace(",", "."))
                            if "escanteio" in col or "corner" in col:
                                d["escanteios"] = v
                            elif "cartao" in col or "amarelo" in col:
                                d["cartoes"] = v
                            elif "chute" in col or "finalizacao" in col:
                                d["chutes"] = v
                            elif "gol" in col and "xg" not in col:
                                d["gols"] = v
                        except Exception:
                            pass
                    if d:
                        dados[nome] = d
                except Exception:
                    continue
            if dados:
                break
    except Exception:
        pass
    return dados

# ── FBref: xG fallback ─────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def buscar_fbref(competicao: str) -> dict:
    comp_id = FBREF_IDS.get(normalizar(competicao))
    if not comp_id:
        return {}
    url = f"https://fbref.com/en/comps/{comp_id}/stats/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    dados = {}
    try:
        time.sleep(4)
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200:
            return {}
        tabelas = pd.read_html(StringIO(resp.text))
        for df in tabelas:
            cols = [str(c).lower() for c in df.columns.get_level_values(-1)]
            if not (any("squad" in c for c in cols) and any(c == "xg" for c in cols)):
                continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [' '.join(str(x) for x in col).strip() for col in df.columns]
            df.columns = [c.lower().strip() for c in df.columns]
            squad_col = next((c for c in df.columns if "squad" in c), None)
            xg_col    = next((c for c in df.columns if c.endswith("xg") and "xga" not in c and "npxg" not in c), None)
            xga_col   = next((c for c in df.columns if "xga" in c and "npxg" not in c), None)
            mp_col    = next((c for c in df.columns if c in ("mp","matches","pj","pg")), None)
            if not (squad_col and xg_col):
                continue
            for _, row in df.iterrows():
                try:
                    nome = str(row[squad_col]).lower().strip()
                    if nome in ("squad","nan",""):
                        continue
                    xg  = float(str(row[xg_col]).replace(",","."))
                    xga = float(str(row[xga_col]).replace(",",".")) if xga_col else xg
                    mp  = float(str(row[mp_col]).replace(",",".")) if mp_col else 1
                    if mp > 0 and xg > 0:
                        dados[nome] = {"xg": round(xg/mp,2), "xga": round(xga/mp,2)}
                except Exception:
                    continue
            if dados:
                break
    except Exception:
        pass
    return dados

# ── Combina todas as fontes ────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def buscar_todos(competicao: str) -> tuple:
    ws   = buscar_whoscored(competicao)
    fs   = buscar_flashscore(competicao)
    ig   = buscar_infogol(competicao)
    fts  = buscar_footstats(competicao)
    fb   = buscar_fbref(competicao)
    return ws, fs, ig, fts, fb

def encontrar(nome, dados):
    if not dados:
        return {}
    chave = nome.lower().strip()
    if chave in dados:
        return dados[chave]
    for k, v in dados.items():
        if chave in k or k in chave:
            return v
    return {}

def get_val(d, key, default):
    v = d.get(key)
    return v if v and v > 0 else default

def montar_dados_time(nome, ws, fs, ig, fts, fb, DEF):
    dws  = encontrar(nome, ws)
    dfs  = encontrar(nome, fs)
    dig  = encontrar(nome, ig)
    dfts = encontrar(nome, fts)
    dfb  = encontrar(nome, fb)

    # xG: WhoScored > Infogol > FBref > default
    xg  = dws.get("xg") or dig.get("xg") or dfb.get("xg") or DEF["xg"]
    xga = dws.get("xga") or dig.get("xga") or dfb.get("xga") or DEF["xga"]

    # Chutes: WhoScored > Footstats > default
    chutes = dws.get("chutes") or dfts.get("chutes") or DEF["chutes"]

    # Escanteios: Flashscore > Footstats > default
    escanteios = dfs.get("escanteios") or dfts.get("escanteios") or DEF["escanteios"]

    # Cartões: Flashscore > Footstats > default
    cartoes = dfs.get("cartoes") or dfts.get("cartoes") or DEF["cartoes"]

    fontes = []
    if dws: fontes.append("WhoScored")
    if dfs: fontes.append("Flashscore")
    if dig: fontes.append("Infogol")
    if dfts: fontes.append("Footstats")
    if dfb: fontes.append("FBref")

    return {
        "xg": xg, "xga": xga,
        "chutes": chutes, "escanteios": escanteios, "cartoes": cartoes,
        "fontes": fontes or ["default"],
    }

# ── Poisson ────────────────────────────────────────────────────────────────────

def poisson(lmbda, k):
    if lmbda <= 0: return 1.0 if k == 0 else 0.0
    return math.exp(-lmbda) * (lmbda ** k) / math.factorial(k)

def prob_over(lmbda, t):
    return 1 - sum(poisson(lmbda, i) for i in range(int(t) + 1))

def prob_under(lmbda, t):
    return sum(poisson(lmbda, i) for i in range(int(t) + 1))

# ── Render ─────────────────────────────────────────────────────────────────────

def barra(pct, color):
    return f'<span class="prob-bar-bg"><span class="prob-fill" style="width:{min(pct,100):.0f}%;background:{color}"></span></span>'

def srow(label, bar, value):
    return f'<div class="stat-row"><span class="stat-label">{label}</span><span>{bar}</span><span class="stat-value">{value}</span></div>'

def srow_s(label, value):
    return f'<div class="stat-row"><span class="stat-label">{label}</span><span class="stat-value">{value}</span></div>'

def card(title, content):
    return f'<div class="card"><div class="card-title">{title}</div>{content}</div>'

# ── Análise ────────────────────────────────────────────────────────────────────

def analisar(time_a, time_b, competicao, odds=None):
    with st.spinner("Buscando dados em 5 fontes..."):
        ws, fs, ig, fts, fb = buscar_todos(competicao)

    DEF = DEFAULTS.get(normalizar(competicao), DEFAULTS["brasileirao"])
    da = montar_dados_time(time_a, ws, fs, ig, fts, fb, DEF)
    db = montar_dados_time(time_b, ws, fs, ig, fts, fb, DEF)

    l1 = ((da["xg"] + db["xga"]) / 2) * 0.95
    l2 = ((db["xg"] + da["xga"]) / 2) * 0.90
    lg = l1 + l2
    lc = da["cartoes"] + db["cartoes"]
    le = da["escanteios"] + db["escanteios"]
    lch = da["chutes"] + db["chutes"]

    v1 = e = v2 = 0.0
    for i in range(10):
        for j in range(10):
            p = poisson(l1, i) * poisson(l2, j)
            if i > j: v1 += p
            elif i == j: e += p
            else: v2 += p

    btts   = (1 - math.exp(-l1)) * (1 - math.exp(-l2))
    over15 = prob_over(lg, 1); under15 = prob_under(lg, 1)
    over25 = prob_over(lg, 2); under25 = prob_under(lg, 2)
    over35 = prob_over(lg, 3); under35 = prob_under(lg, 3)
    over_c35 = prob_over(lc, 3); under_c35 = prob_under(lc, 3)
    over_c45 = prob_over(lc, 4); under_c45 = prob_under(lc, 4)
    over_e85 = prob_over(le, 8); under_e85 = prob_under(le, 8)
    over_e95 = prob_over(le, 9); under_e95 = prob_under(le, 9)
    over_ch85 = prob_over(lch, 8); under_ch85 = prob_under(lch, 8)
    over_ch95 = prob_over(lch, 9)

    st.markdown(f'<div class="match-header"><div class="match-title">{time_a.upper()} × {time_b.upper()}</div><div class="match-comp">🏆 {competicao}</div></div>', unsafe_allow_html=True)

    # Resultado
    html = ""
    for label, val, cor in [(f"Vitoria {time_a}", v1, "#4CAF50"), ("Empate", e, "#C9A84C"), (f"Vitoria {time_b}", v2, "#EF5350")]:
        html += srow(label, barra(val*100, cor), f"{val*100:.1f}%")
    st.markdown(card("Probabilidade de Resultado", html), unsafe_allow_html=True)

    # Gols
    html = ""
    for label, val, cor in [
        ("Over 1.5 Gols", over15, "#4CAF50"), ("Under 1.5 Gols", under15, "#EF5350"),
        ("Over 2.5 Gols", over25, "#4CAF50"), ("Under 2.5 Gols", under25, "#EF5350"),
        ("Over 3.5 Gols", over35, "#4CAF50"), ("Under 3.5 Gols", under35, "#EF5350"),
        ("Ambos Marcam (BTTS)", btts, "#C9A84C"),
    ]:
        html += srow(label, barra(val*100, cor), f"{val*100:.1f}%")
    st.markdown(card("Mercado de Gols", html), unsafe_allow_html=True)

    # Escanteios
    html = srow_s(f"Media {time_a}", f"{da['escanteios']:.1f}") + srow_s(f"Media {time_b}", f"{db['escanteios']:.1f}") + srow_s("Total esperado", f"{le:.1f}")
    for label, val, cor in [
        ("Over 8.5 Escanteios", over_e85, "#4CAF50"), ("Under 8.5 Escanteios", under_e85, "#EF5350"),
        ("Over 9.5 Escanteios", over_e95, "#4CAF50"), ("Under 9.5 Escanteios", under_e95, "#EF5350"),
    ]:
        html += srow(label, barra(val*100, cor), f"{val*100:.1f}%")
    st.markdown(card("Escanteios", html), unsafe_allow_html=True)

    # Cartões
    html = srow_s(f"Media {time_a}", f"{da['cartoes']:.1f}") + srow_s(f"Media {time_b}", f"{db['cartoes']:.1f}") + srow_s("Total esperado", f"{lc:.1f}")
    for label, val, cor in [
        ("Over 3.5 Cartoes", over_c35, "#4CAF50"), ("Under 3.5 Cartoes", under_c35, "#EF5350"),
        ("Over 4.5 Cartoes", over_c45, "#4CAF50"), ("Under 4.5 Cartoes", under_c45, "#EF5350"),
    ]:
        html += srow(label, barra(val*100, cor), f"{val*100:.1f}%")
    st.markdown(card("Cartoes", html), unsafe_allow_html=True)

    # Chutes
    html = srow_s(f"Media {time_a}", f"{da['chutes']:.1f}") + srow_s(f"Media {time_b}", f"{db['chutes']:.1f}") + srow_s("Total esperado", f"{lch:.1f}")
    for label, val, cor in [
        ("Over 8.5 Chutes a Gol", over_ch85, "#4CAF50"), ("Under 8.5 Chutes a Gol", under_ch85, "#EF5350"),
        ("Over 9.5 Chutes a Gol", over_ch95, "#4CAF50"),
    ]:
        html += srow(label, barra(val*100, cor), f"{val*100:.1f}%")
    st.markdown(card("Chutes a Gol", html), unsafe_allow_html=True)

    # Value Bets
    if odds:
        probs = {"v1": v1, "emp": e, "v2": v2}
        nomes = {"v1": f"Vitoria {time_a}", "emp": "Empate", "v2": f"Vitoria {time_b}"}
        vbs = []
        for k, odd in odds.items():
            if k in probs:
                pv = probs[k]
                ev = pv * (odd - 1) - (1 - pv)
                if ev > 0:
                    vbs.append((nomes[k], odd, ev, pv))
        vb_html = ""
        if vbs:
            for nome, odd, ev, prob in vbs:
                vb_html += f'<div class="value-bet"><span style="color:#4CAF50;font-weight:600">✅ {nome}</span><span style="color:#F0F0F0">Odd {odd:.2f}</span><span style="color:#C9A84C;font-weight:700">EV +{ev*100:.1f}%</span><span style="color:#A0B4C8">{prob*100:.1f}%</span></div>'
        else:
            vb_html = '<div class="no-value">Nenhum value bet identificado.</div>'
        st.markdown(card("Value Bets", vb_html), unsafe_allow_html=True)

    fontes_a = ", ".join(da["fontes"])
    fontes_b = ", ".join(db["fontes"])
    st.caption(f"{time_a}: {fontes_a} | {time_b}: {fontes_b}")

# ── UI ─────────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="FORMULA TIPS", page_icon="⚽", layout="centered")
st.markdown(CSS, unsafe_allow_html=True)

logo_path = "logotipo formula tips 01.png"
if os.path.exists(logo_path):
    col_logo, col_titulo = st.columns([1, 3])
    with col_logo:
        st.image(logo_path, width=90)
    with col_titulo:
        st.markdown("<h1 style='margin:0;padding-top:8px;color:#F0F0F0'>FORMULA TIPS</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color:#C9A84C;margin:0;font-size:14px'>A formula certa para o green</p>", unsafe_allow_html=True)
else:
    st.markdown("<h1 style='color:#F0F0F0;margin:0'>FORMULA TIPS</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#C9A84C;margin:0'>A formula certa para o green</p>", unsafe_allow_html=True)

st.markdown("<hr style='border-color:#2A3F55;margin:12px 0'>", unsafe_allow_html=True)

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
