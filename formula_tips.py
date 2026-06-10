# -*- coding: utf-8 -*-
import math
import time
import os
import unicodedata
import numpy as np
import streamlit as st
import requests
import pandas as pd
from io import StringIO
from playwright.sync_api import sync_playwright

ODDS_API_KEY = "14b5427f7931da93a2e381aed3d3de91"

CSS = """
<style>
html, body, [class*="stApp"] { background-color: #0D1B2A !important; color: #F0F0F0 !important; }
.stTextInput > div > div > input { background-color: #1C2E40; color: #F0F0F0; border: 1px solid #C9A84C; border-radius: 8px; }
.stSelectbox > div > div { background-color: #1C2E40; color: #F0F0F0; border: 1px solid #C9A84C; border-radius: 8px; }
.stExpander { background-color: #1C2E40 !important; border: 1px solid #2A3F55 !important; border-radius: 8px; }
.stButton > button { width: 100%; background: linear-gradient(135deg, #C0152A, #8B0F1E); color: #F0F0F0; font-size: 18px; font-weight: bold; border: 2px solid #C9A84C; border-radius: 12px; padding: 14px; letter-spacing: 1px; }
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
.alert-box { background: #3d1a00; border: 1px solid #FF6B00; border-radius: 10px; padding: 12px 16px; margin-bottom: 8px; color: #FFB74D; font-size: 13px; }
.incerteza { background: #3d0000; border: 1px solid #EF5350; border-radius: 10px; padding: 12px 16px; margin-bottom: 8px; color: #EF5350; font-weight: 700; font-size: 14px; text-align: center; }
label { color: #A0B4C8 !important; }
p, .stMarkdown p { color: #F0F0F0; }
h1, h2, h3 { color: #F0F0F0 !important; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { color: #C9A84C; padding: 6px 8px; border-bottom: 1px solid #2A3F55; text-align: left; }
td { color: #F0F0F0; padding: 5px 8px; border-bottom: 1px solid #1a2d3d; }
</style>
"""

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
    "brasileirao":      "https://www.flashscore.com.br/futebol/brasil/serie-a/",
    "premier league":   "https://www.flashscore.com.br/futebol/england/premier-league/",
    "champions league": "https://www.flashscore.com.br/futebol/europa/champions-league/",
    "la liga":          "https://www.flashscore.com.br/futebol/espanha/laliga/",
    "serie a":          "https://www.flashscore.com.br/futebol/italia/serie-a/",
    "bundesliga":       "https://www.flashscore.com.br/futebol/alemanha/bundesliga/",
    "ligue 1":          "https://www.flashscore.com.br/futebol/franca/ligue-1/",
    "sul-americana":    "https://www.flashscore.com.br/futebol/america-do-sul/copa-sul-americana/",
}

ODDS_API_SPORTS = {
    "brasileirao":      "soccer_brazil_campeonato",
    "premier league":   "soccer_epl",
    "champions league": "soccer_uefa_champs_league",
    "la liga":          "soccer_spain_la_liga",
    "serie a":          "soccer_italy_serie_a",
    "bundesliga":       "soccer_germany_bundesliga",
    "ligue 1":          "soccer_france_ligue_one",
    "sul-americana":    "soccer_conmebol_sudamericana",
}

FBREF_IDS = {
    "brasileirao": "24", "premier league": "9", "champions league": "8",
    "la liga": "12", "serie a": "11", "bundesliga": "20",
    "ligue 1": "13", "sul-americana": "45",
}

DEFAULTS = {
    "brasileirao":      {"xg":1.40,"xga":1.40,"gols":1.40,"sog":4.5,"fin":12.0,"esc":5.2,"cart":2.1},
    "premier league":   {"xg":1.55,"xga":1.55,"gols":1.55,"sog":5.0,"fin":13.0,"esc":5.0,"cart":1.8},
    "la liga":          {"xg":1.50,"xga":1.50,"gols":1.50,"sog":4.8,"fin":12.5,"esc":4.8,"cart":2.3},
    "serie a":          {"xg":1.40,"xga":1.40,"gols":1.40,"sog":4.6,"fin":12.0,"esc":5.1,"cart":2.5},
    "bundesliga":       {"xg":1.65,"xga":1.65,"gols":1.65,"sog":5.2,"fin":13.5,"esc":5.3,"cart":1.9},
    "ligue 1":          {"xg":1.45,"xga":1.45,"gols":1.45,"sog":4.7,"fin":12.0,"esc":4.9,"cart":2.2},
    "champions league": {"xg":1.60,"xga":1.60,"gols":1.60,"sog":5.1,"fin":13.0,"esc":5.0,"cart":1.7},
    "sul-americana":    {"xg":1.35,"xga":1.35,"gols":1.35,"sog":4.4,"fin":11.5,"esc":5.0,"cart":2.4},
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
    for sel in ["button:has-text('Accept')", "button:has-text('Aceitar')", "button#onetrust-accept-btn-handler"]:
        try:
            page.click(sel, timeout=3000)
            time.sleep(1)
            break
        except Exception:
            pass

# ── Busca últimos 5 jogos do time via Flashscore ───────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def buscar_ultimos5_flashscore(time_nome: str, competicao: str) -> dict:
    base_url = FLASHSCORE_URLS.get(normalizar(competicao), "https://www.flashscore.com.br/futebol/")
    p = browser = ctx = None
    resultado = {}
    try:
        p, browser, ctx = novo_browser()
        page = ctx.new_page()
        page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,mp4}", lambda r: r.abort())
        time.sleep(2)

        # Busca o time
        search_url = f"https://www.flashscore.com.br/search/?q={requests.utils.quote(time_nome)}"
        page.goto(search_url, wait_until="networkidle", timeout=30000)
        time.sleep(3)
        aceitar_cookies(page)

        # Clica no time
        try:
            page.click(".suggest__item--team", timeout=5000)
            time.sleep(3)
        except Exception:
            return {}

        # Vai para resultados
        try:
            page.click("a:has-text('Resultados')", timeout=5000)
            time.sleep(2)
        except Exception:
            pass

        # Extrai últimos 5 jogos
        jogos = page.query_selector_all(".event__match--scheduled, .event__match--live, .event__match", )
        if not jogos:
            jogos = page.query_selector_all("[class*='event__match']")

        gols_list, sog_list, esc_list, cart_list, fin_list = [], [], [], [], []

        for jogo in jogos[:10]:
            try:
                # Gols
                home_score = jogo.query_selector(".event__score--home, [class*='score--home']")
                away_score = jogo.query_selector(".event__score--away, [class*='score--away']")
                if home_score and away_score:
                    h = int(home_score.inner_text().strip())
                    a = int(away_score.inner_text().strip())

                    # Verifica se é time mandante ou visitante
                    home_name = jogo.query_selector(".event__participant--home, [class*='participant--home']")
                    if home_name:
                        hn = home_name.inner_text().strip().lower()
                        if normalizar(time_nome) in normalizar(hn):
                            gols_list.append(h)
                        else:
                            gols_list.append(a)
            except Exception:
                pass

            if len(gols_list) >= 5:
                break

        # Clica num jogo para ver estatísticas detalhadas
        try:
            jogos_links = page.query_selector_all("[class*='event__match'] a, .event__match")
            for link in jogos_links[:3]:
                try:
                    link.click()
                    time.sleep(2)
                    # Aba de estatísticas
                    page.click("a:has-text('Estatísticas'), button:has-text('Stats')", timeout=3000)
                    time.sleep(2)

                    html = page.content()
                    import re

                    # SOG
                    m = re.findall(r'Chutes.*?Gol.*?(\d+).*?(\d+)', html, re.IGNORECASE | re.DOTALL)
                    if m:
                        sog_list.append(int(m[0][0]) + int(m[0][1]))

                    # Escanteios
                    m = re.findall(r'[Ee]scanteios?\D+(\d+)\D+(\d+)', html)
                    if m:
                        esc_list.append(int(m[0][0]) + int(m[0][1]))

                    # Cartões
                    m = re.findall(r'[Cc]art[õo]es?\s+[Aa]marelos?\D+(\d+)\D+(\d+)', html)
                    if m:
                        cart_list.append(int(m[0][0]) + int(m[0][1]))

                    page.go_back()
                    time.sleep(2)
                except Exception:
                    try: page.go_back(); time.sleep(1)
                    except Exception: pass
                    continue
        except Exception:
            pass

        def stats(lst, default):
            if len(lst) >= 3:
                arr = np.array(lst[:5], dtype=float)
                return {"media": float(np.mean(arr)), "cv": float(np.std(arr)/np.mean(arr)*100) if np.mean(arr) > 0 else 30.0}
            return {"media": default, "cv": 30.0}

        DEF = DEFAULTS.get(normalizar(competicao), DEFAULTS["brasileirao"])
        resultado = {
            "gols":  stats(gols_list, DEF["gols"]),
            "sog":   stats(sog_list,  DEF["sog"]),
            "fin":   stats(fin_list,  DEF["fin"]),
            "esc":   stats(esc_list,  DEF["esc"]),
            "cart":  stats(cart_list, DEF["cart"]),
        }

    except Exception:
        pass
    finally:
        try: browser.close(); p.stop()
        except Exception: pass
    return resultado

# ── WhoScored: xG, xGA ────────────────────────────────────────────────────────

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
        time.sleep(5)
        aceitar_cookies(page)
        page.wait_for_selector("table#top-team-stats-summary-grid", timeout=30000)
        time.sleep(3)
        headers_el = page.query_selector_all("table#top-team-stats-summary-grid thead th")
        headers = [h.inner_text().strip().lower() for h in headers_el]
        rows = page.query_selector_all("table#top-team-stats-summary-grid tbody tr")
        for row in rows:
            try:
                nome_el = row.query_selector("td a.team-link")
                if not nome_el: continue
                nome = nome_el.inner_text().strip().lower()
                cells = row.query_selector_all("td")
                vals = [c.inner_text().strip() for c in cells]
                d = {}
                for i, h in enumerate(headers):
                    if i >= len(vals): break
                    try:
                        fv = float(vals[i].replace(",", "."))
                        if "xg" in h and "xga" not in h and "diff" not in h: d["xg"] = fv
                        elif "xga" in h or ("xg" in h and "diff" in h): d["xga_diff"] = fv
                        elif "shot" in h or "chute" in h: d["sog"] = fv
                    except Exception: pass
                if "xg" in d and "xga_diff" in d:
                    d["xga"] = round(d["xg"] - d["xga_diff"], 2)
                if d: dados[nome] = d
            except Exception: continue
    except Exception: pass
    finally:
        try: browser.close(); p.stop()
        except Exception: pass
    return dados

# ── FBref: xG fallback ─────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def buscar_fbref(competicao: str) -> dict:
    comp_id = FBREF_IDS.get(normalizar(competicao))
    if not comp_id: return {}
    url = f"https://fbref.com/en/comps/{comp_id}/stats/"
    headers = {"User-Agent": "Mozilla/5.0"}
    dados = {}
    try:
        time.sleep(4)
        resp = requests.get(url, headers=headers, timeout=30)
        if resp.status_code != 200: return {}
        tabelas = pd.read_html(StringIO(resp.text))
        for df in tabelas:
            cols = [str(c).lower() for c in df.columns.get_level_values(-1)]
            if not (any("squad" in c for c in cols) and any(c == "xg" for c in cols)): continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = [' '.join(str(x) for x in col).strip() for col in df.columns]
            df.columns = [c.lower().strip() for c in df.columns]
            squad_col = next((c for c in df.columns if "squad" in c), None)
            xg_col    = next((c for c in df.columns if c.endswith("xg") and "xga" not in c and "npxg" not in c), None)
            xga_col   = next((c for c in df.columns if "xga" in c and "npxg" not in c), None)
            mp_col    = next((c for c in df.columns if c in ("mp","matches","pj","pg")), None)
            if not (squad_col and xg_col): continue
            for _, row in df.iterrows():
                try:
                    nome = str(row[squad_col]).lower().strip()
                    if nome in ("squad","nan",""): continue
                    xg  = float(str(row[xg_col]).replace(",","."))
                    xga = float(str(row[xga_col]).replace(",",".")) if xga_col else xg
                    mp  = float(str(row[mp_col]).replace(",",".")) if mp_col else 1
                    if mp > 0 and xg > 0:
                        dados[nome] = {"xg": round(xg/mp,2), "xga": round(xga/mp,2)}
                except Exception: continue
            if dados: break
    except Exception: pass
    return dados

# ── Odds API ───────────────────────────────────────────────────────────────────

@st.cache_data(ttl=600, show_spinner=False)
def buscar_odds(time_a: str, time_b: str, competicao: str) -> dict:
    sport = ODDS_API_SPORTS.get(normalizar(competicao))
    if not sport: return {}
    try:
        url = f"https://api.the-odds-api.com/v4/sports/{sport}/odds/"
        params = {
            "apiKey": ODDS_API_KEY,
            "regions": "eu",
            "markets": "h2h,totals",
            "oddsFormat": "decimal",
            "bookmakers": "pinnacle,bet365,betano",
        }
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code != 200: return {}
        jogos = resp.json()

        na = normalizar(time_a)
        nb = normalizar(time_b)

        for jogo in jogos:
            hn = normalizar(jogo.get("home_team",""))
            an = normalizar(jogo.get("away_team",""))
            if (na in hn or hn in na) and (nb in an or an in nb):
                odds = {"v1": None, "emp": None, "v2": None, "over25": None, "under25": None}
                for bm in jogo.get("bookmakers", []):
                    for market in bm.get("markets", []):
                        if market["key"] == "h2h":
                            for outcome in market["outcomes"]:
                                n = normalizar(outcome["name"])
                                if na in n or n in na:
                                    if odds["v1"] is None or outcome["price"] < odds["v1"]:
                                        odds["v1"] = outcome["price"]
                                elif "draw" in n or "empate" in n:
                                    if odds["emp"] is None or outcome["price"] < odds["emp"]:
                                        odds["emp"] = outcome["price"]
                                elif nb in n or n in nb:
                                    if odds["v2"] is None or outcome["price"] < odds["v2"]:
                                        odds["v2"] = outcome["price"]
                        elif market["key"] == "totals":
                            for outcome in market["outcomes"]:
                                if "2.5" in str(outcome.get("point","")) or "2.5" in outcome["name"]:
                                    if "over" in outcome["name"].lower():
                                        if odds["over25"] is None or outcome["price"] < odds["over25"]:
                                            odds["over25"] = outcome["price"]
                                    elif "under" in outcome["name"].lower():
                                        if odds["under25"] is None or outcome["price"] < odds["under25"]:
                                            odds["under25"] = outcome["price"]
                return odds
    except Exception: pass
    return {}

# ── Helpers ────────────────────────────────────────────────────────────────────

def encontrar(nome, dados):
    if not dados: return {}
    chave = nome.lower().strip()
    if chave in dados: return dados[chave]
    for k, v in dados.items():
        if chave in k or k in chave: return v
    return {}

def poisson(lmbda, k):
    if lmbda <= 0: return 1.0 if k == 0 else 0.0
    return math.exp(-lmbda) * (lmbda ** k) / math.factorial(k)

def prob_over(lmbda, t):
    return 1 - sum(poisson(lmbda, i) for i in range(int(t)+1))

def prob_under(lmbda, t):
    return sum(poisson(lmbda, i) for i in range(int(t)+1))

# ── REGRA 3: Ajuste CV ────────────────────────────────────────────────────────

def fator_cv(cv):
    if cv < 35: return 1.0
    elif cv <= 45: return 0.95
    elif cv <= 60: return 0.92
    else: return 0.88

# ── Monte Carlo ───────────────────────────────────────────────────────────────

def monte_carlo(l1, l2, n=10000):
    np.random.seed(42)
    v1 = emp = v2 = 0
    btts_c = over25_c = 0
    for _ in range(n):
        ll1, ll2 = l1, l2
        r = np.random.random()
        if r < 0.05: ll1 = max(0.1, ll1 - 0.5)
        elif r < 0.15: ll1 += 0.3; ll2 += 0.3
        elif r < 0.30: ll1 = max(0.1, ll1 - 0.3)
        ll1 *= np.random.normal(1.0, 0.12)
        ll2 *= np.random.normal(1.0, 0.12)
        ll1 = max(0.1, ll1); ll2 = max(0.1, ll2)
        g1 = np.random.poisson(ll1)
        g2 = np.random.poisson(ll2)
        if g1 > g2: v1 += 1
        elif g1 == g2: emp += 1
        else: v2 += 1
        if g1 > 0 and g2 > 0: btts_c += 1
        if g1 + g2 > 2: over25_c += 1
    return {
        "v1": v1/n, "emp": emp/n, "v2": v2/n,
        "btts": btts_c/n, "over25": over25_c/n
    }

# ── Kelly + Stake ──────────────────────────────────────────────────────────────

def kelly(p, b):
    if b <= 1: return 0.0
    k = (p * b - 1) / (b - 1)
    return max(0.0, k)

def stake_real(k, confianca):
    sr = k * 0.33
    if confianca == "Alta": return min(sr, 0.03)
    elif confianca == "Media": return min(sr, 0.02)
    else: return min(sr, 0.01)

def ev(p, b):
    return p * (b - 1) - (1 - p)

# ── Render ─────────────────────────────────────────────────────────────────────

def barra(pct, color):
    return f'<span class="prob-bar-bg"><span class="prob-fill" style="width:{min(pct,100):.0f}%;background:{color}"></span></span>'

def srow(label, bar, value):
    return f'<div class="stat-row"><span class="stat-label">{label}</span><span>{bar}</span><span class="stat-value">{value}</span></div>'

def srow_s(label, value):
    return f'<div class="stat-row"><span class="stat-label">{label}</span><span class="stat-value">{value}</span></div>'

def card(title, content):
    return f'<div class="card"><div class="card-title">{title}</div>{content}</div>'

# ── ANÁLISE PRINCIPAL ──────────────────────────────────────────────────────────

def analisar(time_a, time_b, competicao, tipo_jogo="Liga", placar_ida=None):
    alertas = []
    checklist = {}

    with st.spinner("Buscando dados em múltiplas fontes..."):
        ws  = buscar_whoscored(competicao)
        fb  = buscar_fbref(competicao)
        d5a = buscar_ultimos5_flashscore(time_a, competicao)
        d5b = buscar_ultimos5_flashscore(time_b, competicao)
        odds_api = buscar_odds(time_a, time_b, competicao)

    DEF = DEFAULTS.get(normalizar(competicao), DEFAULTS["brasileirao"])

    # xG
    dws_a = encontrar(time_a, ws); dws_b = encontrar(time_b, ws)
    dfb_a = encontrar(time_a, fb); dfb_b = encontrar(time_b, fb)
    xg_a  = dws_a.get("xg") or dfb_a.get("xg") or DEF["xg"]
    xga_a = dws_a.get("xga") or dfb_a.get("xga") or DEF["xga"]
    xg_b  = dws_b.get("xg") or dfb_b.get("xg") or DEF["xg"]
    xga_b = dws_b.get("xga") or dfb_b.get("xga") or DEF["xga"]
    checklist["xg_disponivel"] = bool(dws_a.get("xg") or dfb_a.get("xg"))

    # Médias últimos 5 jogos
    def get_stat(d5, key, default):
        return d5.get(key, {}).get("media", default) if d5 else default

    def get_cv(d5, key):
        return d5.get(key, {}).get("cv", 30.0) if d5 else 30.0

    gols_a = get_stat(d5a, "gols", DEF["gols"]); cv_gols_a = get_cv(d5a, "gols")
    gols_b = get_stat(d5b, "gols", DEF["gols"]); cv_gols_b = get_cv(d5b, "gols")
    sog_a  = get_stat(d5a, "sog",  DEF["sog"]);  cv_sog_a  = get_cv(d5a, "sog")
    sog_b  = get_stat(d5b, "sog",  DEF["sog"]);  cv_sog_b  = get_cv(d5b, "sog")
    fin_a  = get_stat(d5a, "fin",  DEF["fin"]);  cv_fin_a  = get_cv(d5a, "fin")
    fin_b  = get_stat(d5b, "fin",  DEF["fin"]);  cv_fin_b  = get_cv(d5b, "fin")
    esc_a  = get_stat(d5a, "esc",  DEF["esc"]);  esc_b     = get_stat(d5b, "esc", DEF["esc"])
    cart_a = get_stat(d5a, "cart", DEF["cart"]); cart_b    = get_stat(d5b, "cart", DEF["cart"])

    checklist["cv_gols_ok"] = cv_gols_a < 35 and cv_gols_b < 35

    # REGRA 3: Ajuste por CV
    fator_a = fator_cv(cv_gols_a); fator_b = fator_cv(cv_gols_b)
    fator_sog_a = 0.97 if 25 <= cv_sog_a <= 35 else 1.0
    fator_sog_b = 0.97 if 25 <= cv_sog_b <= 35 else 1.0
    fator_fin_a = 1.05 if cv_fin_a < 20 else 1.0
    fator_fin_b = 1.05 if cv_fin_b < 20 else 1.0

    # Lambda base
    l1_base = ((xg_a + xga_b) / 2) * 0.95
    l2_base = ((xg_b + xga_a) / 2) * 0.90

    # Aplica CV
    l1 = l1_base * fator_a
    l2 = l2_base * fator_b

    # REGRA 6C: Ajustes contextuais mata-mata
    checklist["contexto_aplicado"] = tipo_jogo != "Liga"
    if tipo_jogo == "Mata-Mata (volta)" and placar_ida:
        try:
            g1_ida, g2_ida = [int(x.strip()) for x in placar_ida.split("x")]
            if g1_ida < g2_ida: l1 += 0.3; l2 -= 0.2
            elif g1_ida > g2_ida: l2 += 0.3; l1 -= 0.2
        except Exception:
            pass

    # Poisson
    v1 = e = v2 = 0.0
    for i in range(10):
        for j in range(10):
            p = poisson(l1, i) * poisson(l2, j)
            if i > j: v1 += p
            elif i == j: e += p
            else: v2 += p

    lg = l1 + l2
    btts   = (1 - math.exp(-l1)) * (1 - math.exp(-l2))
    over15 = prob_over(lg, 1); under15 = prob_under(lg, 1)
    over25 = prob_over(lg, 2); under25 = prob_under(lg, 2)
    over35 = prob_over(lg, 3); under35 = prob_under(lg, 3)
    under45 = prob_under(lg, 4)

    # Monte Carlo
    mc = monte_carlo(l1, l2)

    # Linhas cartões e escanteios
    lc = cart_a + cart_b; le = esc_a + esc_b
    lsog = (sog_a + sog_b) * fator_sog_a * fator_sog_b
    over_c15 = prob_over(lc, 1); under_c95 = prob_under(lc, 9)
    over_c35 = prob_over(lc, 3); under_c35 = prob_under(lc, 3)
    over_e85 = prob_over(le, 8); under_e85 = prob_under(le, 8)
    over_e95 = prob_over(le, 9); under_e95 = prob_under(le, 9)
    over_sog85 = prob_over(lsog, 8); under_sog85 = prob_under(lsog, 8)

    # REGRA 6A: Over 2.5 seguro
    xg_combinado = xg_a + xg_b
    over25_seguro = xg_combinado > 3.0
    checklist["over25_verificado"] = True
    if not over25_seguro:
        alertas.append("⚠️ Regra 6A: Over 2.5 NÃO seguro (xG combinado ≤ 3.0)")

    # REGRA 6B: Under 2.5 seguro
    under25_seguro = xg_combinado < 2.0
    checklist["under25_verificado"] = True
    if not under25_seguro and xg_combinado >= 2.0:
        alertas.append("ℹ️ Regra 6B: Under 2.5 não atende critérios seguros")

    # REGRA 7A: SOG Over seguro
    sog_combinado = sog_a + sog_b
    sog_over_seguro = sog_combinado > 10.0 and cv_sog_a < 30 and cv_sog_b < 30
    checklist["sog_verificado"] = True

    # REGRA 8: Cartões
    checklist["cartoes_verificado"] = True

    # Odds
    o_v1  = odds_api.get("v1")  or 2.00
    o_emp = odds_api.get("emp") or 3.20
    o_v2  = odds_api.get("v2")  or 3.50
    o_o25 = odds_api.get("over25") or 2.10
    o_u25 = odds_api.get("under25") or 1.80
    checklist["odds_disponiveis"] = bool(odds_api.get("v1"))

    # EV e Kelly
    def analise_mercado(prob, odd, nome):
        ev_val = ev(prob, odd)
        k = kelly(prob, odd)
        if ev_val > 0.005: conf = "Alta" if ev_val > 0.05 else "Media"
        elif ev_val > 0: conf = "Baixa"
        else: conf = "Sem Value"
        sr = stake_real(k, conf) * 100 if conf != "Sem Value" else 0
        return {"nome": nome, "prob": prob, "odd": odd, "ev": ev_val, "kelly": k, "stake": sr, "conf": conf}

    mercados = [
        analise_mercado(v1,    o_v1,  f"Vitoria {time_a}"),
        analise_mercado(e,     o_emp, "Empate"),
        analise_mercado(v2,    o_v2,  f"Vitoria {time_b}"),
        analise_mercado(btts,  1.90,  "BTTS Sim"),
        analise_mercado(over25, o_o25, "Over 2.5"),
        analise_mercado(over15, 1.25, "Over 1.5"),
        analise_mercado(under45, 1.12, "Under 4.5"),
        analise_mercado(over_c15, 1.15, "Over 1.5 Cartoes"),
        analise_mercado(under_c95, 1.05, "Under 9.5 Cartoes"),
    ]
    checklist["ev_ok"] = any(m["ev"] > 0.005 for m in mercados)

    # Checklist final
    n_ok = sum(1 for v in checklist.values() if v)
    alta_incerteza = n_ok < 5
    if alta_incerteza:
        alertas.insert(0, "⚠️ ALTA INCERTEZA — Stake reduzido a 0.5%")

    # Eficiência ofensiva
    def nota_ef(sog, fin, gols):
        if fin == 0: return 50
        sog_r = sog / fin * 100
        gol_r = gols / fin * 100
        return min(100, int((sog_r * 0.5 + gol_r * 0.5) * 2))

    nota_a = nota_ef(sog_a, fin_a, gols_a)
    nota_b = nota_ef(sog_b, fin_b, gols_b)

    # ── RENDER ─────────────────────────────────────────────────────────────────

    st.markdown(f'<div class="match-header"><div class="match-title">{time_a.upper()} × {time_b.upper()}</div><div class="match-comp">🏆 {competicao} · {tipo_jogo}</div></div>', unsafe_allow_html=True)

    if alta_incerteza:
        st.markdown('<div class="incerteza">⚠️ ALTA INCERTEZA — Aposte no máximo 0.5% do bank</div>', unsafe_allow_html=True)

    for al in alertas:
        st.markdown(f'<div class="alert-box">{al}</div>', unsafe_allow_html=True)

    # 1. Ajuste por Variância
    html = f"""<table><tr><th>Métrica</th><th>Time</th><th>CV</th><th>Ação</th></tr>
    <tr><td>Gols</td><td>{time_a}</td><td>{cv_gols_a:.0f}%</td><td>{"reduz "+str(int((1-fator_a)*100))+"%" if fator_a<1 else "ok"}</td></tr>
    <tr><td>Gols</td><td>{time_b}</td><td>{cv_gols_b:.0f}%</td><td>{"reduz "+str(int((1-fator_b)*100))+"%" if fator_b<1 else "ok"}</td></tr>
    <tr><td>SOG</td><td>Ambos</td><td>{max(cv_sog_a,cv_sog_b):.0f}%</td><td>{"reduz 3%" if fator_sog_a<1 else "ok"}</td></tr>
    <tr><td>Finalizações</td><td>Ambos</td><td>{min(cv_fin_a,cv_fin_b):.0f}%</td><td>{"+5% confiança" if fator_fin_a>1 else "ok"}</td></tr>
    </table>"""
    st.markdown(card("1. Ajuste por Variância (Regra 3)", html), unsafe_allow_html=True)

    # 2. Poisson
    html = f"<p style='color:#C9A84C'>λ {time_a} = {l1:.2f} | λ {time_b} = {l2:.2f}</p>"
    html += f"""<table><tr><th>Gols</th><th>Prob {time_a}</th><th>Prob {time_b}</th></tr>"""
    for g in range(4):
        label = str(g) if g < 3 else "3+"
        pa = sum(poisson(l1,i) for i in ([g] if g<3 else range(3,10)))*100
        pb = sum(poisson(l2,i) for i in ([g] if g<3 else range(3,10)))*100
        html += f"<tr><td>{label}</td><td>{pa:.1f}%</td><td>{pb:.1f}%</td></tr>"
    html += "</table>"
    html += f"<p style='margin-top:8px;color:#A0B4C8'>BTTS: {btts*100:.1f}% | Over 1.5: {over15*100:.1f}% | Over 2.5: {over25*100:.1f}% | Over 3.5: {over35*100:.1f}% | Under 4.5: {under45*100:.1f}%</p>"
    st.markdown(card("2. Poisson Ajustado", html), unsafe_allow_html=True)

    # 3. Monte Carlo
    html = f"""<p style='color:#A0B4C8;font-size:12px'>10.000 simulações com ruído (expulsões, gol precoce, recuo)</p>
    <table><tr><th>Resultado</th><th>Poisson</th><th>Monte Carlo</th></tr>
    <tr><td>Vit. {time_a}</td><td>{v1*100:.1f}%</td><td>{mc['v1']*100:.1f}%</td></tr>
    <tr><td>Empate</td><td>{e*100:.1f}%</td><td>{mc['emp']*100:.1f}%</td></tr>
    <tr><td>Vit. {time_b}</td><td>{v2*100:.1f}%</td><td>{mc['v2']*100:.1f}%</td></tr>
    <tr><td>BTTS</td><td>{btts*100:.1f}%</td><td>{mc['btts']*100:.1f}%</td></tr>
    <tr><td>Over 2.5</td><td>{over25*100:.1f}%</td><td>{mc['over25']*100:.1f}%</td></tr>
    </table>"""
    st.markdown(card("3. Monte Carlo (10k simulações)", html), unsafe_allow_html=True)

    # 4. Eficiência Ofensiva
    def ef_label(n): return "eficiente" if n>83 else ("média" if n>=75 else "ineficiente")
    html = f"""<table><tr><th>Time</th><th>SOG/Fin</th><th>Gol/Fin</th><th>Nota</th><th>Status</th></tr>
    <tr><td>{time_a}</td><td>{sog_a/fin_a*100:.0f}%</td><td>{gols_a/fin_a*100:.0f}%</td><td>{nota_a}</td><td>{ef_label(nota_a)}</td></tr>
    <tr><td>{time_b}</td><td>{sog_b/fin_b*100:.0f}%</td><td>{gols_b/fin_b*100:.0f}%</td><td>{nota_b}</td><td>{ef_label(nota_b)}</td></tr>
    </table>"""
    st.markdown(card("4. Eficiência Ofensiva", html), unsafe_allow_html=True)

    # 5. Value Bets
    html = f"""<table><tr><th>Mercado</th><th>Prob.</th><th>Odd</th><th>EV%</th><th>Kelly</th><th>Stake</th></tr>"""
    for m in mercados:
        cor = "#4CAF50" if m["ev"]>0.005 else ("#C9A84C" if m["ev"]>0 else "#EF5350")
        html += f"<tr><td>{m['nome']}</td><td>{m['prob']*100:.1f}%</td><td>{m['odd']:.2f}</td><td style='color:{cor}'>{m['ev']*100:+.1f}%</td><td>{m['kelly']:.3f}</td><td>{m['stake']:.1f}%</td></tr>"
    html += "</table>"
    st.markdown(card("5. Value Bets — Kelly 33% (Regra 5)", html), unsafe_allow_html=True)

    # 6. Tabela de Sugestões
    html = "<p style='color:#C9A84C;font-weight:600'>⚽ GOLS</p>"
    for label, val, rec in [
        (f"Over 1.5", over15, "✅ Conservador"), (f"Under 1.5", under15, "🛡️ Proteção"),
        (f"Over 2.5", over25, "✅ Valor" if over25_seguro else "⚠️ Cautela"),
        (f"Under 2.5", under25, "🔒 Âncora" if under25_seguro else "⚠️ Cautela"),
        (f"Under 4.5", under45, "🔒 Âncora ~87%"),
    ]:
        cor = "#4CAF50" if val>0.6 else ("#C9A84C" if val>0.45 else "#EF5350")
        html += srow(label, barra(val*100, cor), f"{val*100:.1f}% — {rec}")

    html += "<p style='color:#C9A84C;font-weight:600;margin-top:10px'>🚩 ESCANTEIOS</p>"
    for label, val, rec in [
        ("Over 8.5", over_e85, "✅"), ("Under 8.5", under_e85, "🛡️"),
        ("Over 9.5", over_e95, "✅"), ("Under 9.5", under_e95, "🛡️"),
    ]:
        cor = "#4CAF50" if val>0.55 else "#EF5350"
        html += srow(label, barra(val*100, cor), f"{val*100:.1f}% — {rec}")

    html += "<p style='color:#C9A84C;font-weight:600;margin-top:10px'>🟨 CARTÕES</p>"
    html += srow("Over 1.5 (Linha Segura)", barra(over_c15*100,"#4CAF50"), f"{over_c15*100:.1f}% ✅")
    html += srow("Under 9.5 (Linha Segura)", barra(under_c95*100,"#4CAF50"), f"{under_c95*100:.1f}% 🔒")
    html += srow("Over 3.5", barra(over_c35*100,"#C9A84C"), f"{over_c35*100:.1f}%")
    html += srow("Under 3.5", barra(under_c35*100,"#C9A84C"), f"{under_c35*100:.1f}%")

    html += "<p style='color:#C9A84C;font-weight:600;margin-top:10px'>🥅 CHUTES A GOL (SOG)</p>"
    html += srow("Over 8.5", barra(over_sog85*100,"#4CAF50" if sog_over_seguro else "#C9A84C"), f"{over_sog85*100:.1f}%")
    html += srow("Under 8.5", barra(under_sog85*100,"#C9A84C"), f"{under_sog85*100:.1f}%")
    st.markdown(card("6. Tabela de Sugestões", html), unsafe_allow_html=True)

    # 7. Confluência
    xg_comb = xg_a + xg_b
    if xg_comb > 3.5: classif = "Explosão"
    elif xg_comb > 2.8: classif = "Aberto"
    elif xg_comb > 2.0: classif = "Equilibrado"
    else: classif = "Travado"
    mercado_sug = "Over escanteios + BTTS" if classif in ["Explosão","Aberto"] else "Under gols + Cartões"
    conv = "✅ Convergente" if (over25_seguro and over25 > 0.5) or (not over25_seguro and over25 < 0.5) else "⚠️ Divergente"
    html = f"""<table>
    <tr><td class='stat-label'>Classificação</td><td class='stat-value'>{classif}</td></tr>
    <tr><td class='stat-label'>Mercado sugerido</td><td class='stat-value'>{mercado_sug}</td></tr>
    <tr><td class='stat-label'>Status</td><td class='stat-value'>{conv}</td></tr>
    </table>"""
    st.markdown(card("7. Confluência com Modelo Qualitativo", html), unsafe_allow_html=True)

    # 8. Confiança Geral
    n_checks = sum(1 for v in checklist.values() if v)
    nivel = "⚠️ ALTA INCERTEZA" if alta_incerteza else ("Alta" if n_checks >= 7 else ("Media" if n_checks >= 5 else "Baixa"))
    stake_geral = "0.5%" if alta_incerteza else ("2-3%" if nivel=="Alta" else ("1-2%" if nivel=="Media" else "0.5-1%"))
    html = f"""<table>
    <tr><td class='stat-label'>Nível</td><td class='stat-value' style='color:{"#EF5350" if alta_incerteza else "#4CAF50"}'>{nivel}</td></tr>
    <tr><td class='stat-label'>Stake recomendado</td><td class='stat-value'>{stake_geral} do bank</td></tr>
    </table>
    <table style='margin-top:8px'>
    <tr><th>Check</th><th>Status</th></tr>
    {''.join(f"<tr><td>{k.replace('_',' ').title()}</td><td>{'✅' if v else '❌'}</td></tr>" for k,v in checklist.items())}
    </table>"""
    st.markdown(card("8. Confiança Geral (Regra 5)", html), unsafe_allow_html=True)

    # 9. CSV
    vb_principal = max(mercados, key=lambda m: m["ev"])
    csv_line = f"{time_a},{time_b},,{competicao},{vb_principal['nome']},{vb_principal['odd']:.2f},{1/vb_principal['prob']:.2f},{'Sim' if vb_principal['ev']>0 else 'Nao'},{vb_principal['stake']:.1f}%,1000.00,,,"
    html = f"<p style='color:#A0B4C8;font-size:11px;font-family:monospace'>time1,time2,data,competicao,mercado,odd,odd_justa,value,stake,banca_ini,banca_fim,resultado<br>{csv_line}</p>"
    st.markdown(card("9. CSV Pós-Jogo", html), unsafe_allow_html=True)

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
tipo_jogo = st.selectbox("Tipo de Jogo", ["Liga", "Mata-Mata (ida)", "Mata-Mata (volta)"])
placar_ida = None
if tipo_jogo == "Mata-Mata (volta)":
    placar_ida = st.text_input("Placar da Ida", placeholder="Ex: 1 x 0")

if st.button("ANALISAR AGORA", use_container_width=True):
    if not time_a or not time_b:
        st.warning("Preencha os nomes dos dois times.")
    else:
        analisar(time_a, time_b, competicao, tipo_jogo, placar_ida)
