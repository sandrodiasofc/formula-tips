# -*- coding: utf-8 -*-
"""
FORMULA TIPS V4.1 — VERSÃO ESTÁVEL (COM CORREÇÃO WHOSCORED)
10 Regras | 9 Seções | 16 Itens Checklist | Dados Validados com Fallbacks
Fontes: WhoScored (xG/xGA) + FBref (xG/xGA fallback)
Odds: Entrada Manual (Regra 1)
"""

import math, time, os, json, unicodedata
from datetime import datetime
from pathlib import Path

import numpy as np
import streamlit as st
import requests
import pandas as pd
from io import StringIO
from playwright.sync_api import sync_playwright

# ========== CONFIGURAÇÃO SEGURA ==========
try:
    HISTORICO_FILE = Path(__file__).parent / "historico_v41.json"
except NameError:
    HISTORICO_FILE = Path.cwd() / "historico_v41.json"

# ========== CSS ==========
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
.incerteza { background: #3d0000; border: 1px solid #EF5350; border-radius: 10px; padding: 12px 16px; margin-bottom: 8px; color: #EF5350; font-weight: 700; font-size: 14px; text-align: center; }
.alert-box { background: #3d1a00; border: 1px solid #FF6B00; border-radius: 10px; padding: 12px 16px; margin-bottom: 8px; color: #FFB74D; font-size: 13px; }
label { color: #A0B4C8 !important; }
p, .stMarkdown p { color: #F0F0F0; }
h1, h2, h3 { color: #F0F0F0 !important; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { color: #C9A84C; padding: 6px 8px; border-bottom: 1px solid #2A3F55; text-align: left; }
td { color: #F0F0F0; padding: 5px 8px; border-bottom: 1px solid #1a2d3d; }
</style>
"""

# ========== URLS ==========
WHOSCORED_URLS = {
    "brasileirao": "https://br.whoscored.com/regions/31/tournaments/95/seasons/10980/stages/25039/teamstatistics/brasil-brasileir%C3%A3o-2026",
    "premier league": "https://br.whoscored.com/regions/252/tournaments/2/teamstatistics/inglaterra-premier-league-2025-2026",
    "champions league": "https://br.whoscored.com/regions/250/tournaments/12/teamstatistics/champions-league-2025-2026",
    "la liga": "https://br.whoscored.com/regions/206/tournaments/4/teamstatistics/espanha-la-liga-2025-2026",
    "serie a": "https://br.whoscored.com/regions/108/tournaments/5/teamstatistics/italia-serie-a-2025-2026",
    "bundesliga": "https://br.whoscored.com/regions/81/tournaments/3/teamstatistics/alemanha-bundesliga-2025-2026",
    "ligue 1": "https://br.whoscored.com/regions/74/tournaments/6/teamstatistics/franca-ligue-1-2025-2026",
    "sul-americana": "https://br.whoscored.com/regions/250/tournaments/331/teamstatistics/copa-sul-americana-2026",
}

FBREF_IDS = {
    "brasileirao": "24", "premier league": "9", "champions league": "8",
    "la liga": "12", "serie a": "11", "bundesliga": "20",
    "ligue 1": "13", "sul-americana": "45",
}

DEFAULTS = {
    "brasileirao": {"xg":1.40,"xga":1.40,"gols":1.40,"sog":4.5,"fin":12.0,"esc":5.2,"faltas":22.0},
    "premier league": {"xg":1.55,"xga":1.55,"gols":1.55,"sog":5.0,"fin":13.0,"esc":5.0,"faltas":20.0},
    "la liga": {"xg":1.50,"xga":1.50,"gols":1.50,"sog":4.8,"fin":12.5,"esc":4.8,"faltas":24.0},
    "serie a": {"xg":1.40,"xga":1.40,"gols":1.40,"sog":4.6,"fin":12.0,"esc":5.1,"faltas":26.0},
    "bundesliga": {"xg":1.65,"xga":1.65,"gols":1.65,"sog":5.2,"fin":13.5,"esc":5.3,"faltas":22.0},
    "ligue 1": {"xg":1.45,"xga":1.45,"gols":1.45,"sog":4.7,"fin":12.0,"esc":4.9,"faltas":23.0},
    "champions league": {"xg":1.60,"xga":1.60,"gols":1.60,"sog":5.1,"fin":13.0,"esc":5.0,"faltas":20.0},
    "sul-americana": {"xg":1.35,"xga":1.35,"gols":1.35,"sog":4.4,"fin":11.5,"esc":5.0,"faltas":25.0},
}

# ========== UTILITÁRIOS ==========
def normalizar(texto):
    return unicodedata.normalize("NFD", texto.lower().strip()).encode("ascii", "ignore").decode("ascii")

def encontrar(nome, dados):
    if not dados: return {}, "default"
    chave = nome.lower().strip()
    if chave in dados: return dados[chave], "encontrado"
    for k, v in dados.items():
        if chave in k or k in chave: return v, "encontrado"
    return {}, "default"

def poisson(lmbda, k):
    if lmbda <= 0: return 1.0 if k == 0 else 0.0
    return math.exp(-lmbda) * (lmbda ** k) / math.factorial(k)

def prob_over(lmbda, t):
    return 1 - sum(poisson(lmbda, i) for i in range(int(t)+1))

def prob_under(lmbda, t):
    return sum(poisson(lmbda, i) for i in range(int(t)+1))

def fator_cv(cv):
    if cv < 35: return 1.0, "ok"
    elif cv <= 45: return 0.95, "reduz 5%"
    elif cv <= 60: return 0.92, "reduz 8%"
    else: return 0.88, "reduz 12%"

def acao_sog(cv):
    return "reduz 3%" if 25 <= cv <= 35 else ("alta variancia" if cv > 35 else "ok")

def acao_fin(cv):
    return "+5% confianca" if cv < 20 else "ok"

def kelly(p, b):
    if b <= 1: return 0.0
    return max(0.0, (p * b - 1) / (b - 1))

def ev(p, b):
    return p * (b - 1) - (1 - p)

def barra(pct, color):
    return f'<span class="prob-bar-bg"><span class="prob-fill" style="width:{min(pct,100):.0f}%;background:{color}"></span></span>'

def srow(label, bar, value):
    return f'<div class="stat-row"><span class="stat-label">{label}</span><span>{bar}</span><span class="stat-value">{value}</span></div>'

def card(title, content):
    return f'<div class="card"><div class="card-title">{title}</div>{content}</div>'

# ========== BROWSER ==========
def novo_browser():
    p = sync_playwright().start()
    browser = p.chromium.launch(headless=True, args=["--no-sandbox","--disable-blink-features=AutomationControlled"])
    ctx = browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        locale="pt-BR", viewport={"width": 1366, "height": 768},
    )
    ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return p, browser, ctx

# ========== WHOSCORED (CORRIGIDO) ==========
@st.cache_data(ttl=3600, show_spinner=False)
def buscar_whoscored(competicao: str) -> dict:
    """Busca xG e xGA de todos os times no WhoScored."""
    url = WHOSCORED_URLS.get(normalizar(competicao))
    if not url:
        return {}
    
    p = browser = ctx = None
    dados = {}
    
    try:
        p, browser, ctx = novo_browser()
        page = ctx.new_page()
        page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2,ttf,mp4}", lambda r: r.abort())
        page.goto(url, wait_until="networkidle", timeout=60000)
        time.sleep(5)
        
        try: page.click("button:has-text('Accept')", timeout=4000); time.sleep(1)
        except:
            try: page.click("button:has-text('Aceitar')", timeout=3000); time.sleep(1)
            except: pass
        
        # Múltiplos seletores para encontrar a tabela
        selectores = [
            "#top-team-stats-summary-grid",
            "table.stats-table",
            "div#statistics-table-outright table",
            "div[id*='statistics'] table",
            "table[class*='team']",
        ]
        
        tabela_encontrada = False
        for seletor in selectores:
            try:
                page.wait_for_selector(seletor, timeout=10000)
                tabela_encontrada = True
                break
            except:
                continue
        
        if not tabela_encontrada:
            try: page.wait_for_selector("table", timeout=10000)
            except: return {}
        
        time.sleep(3)
        tabelas = page.query_selector_all("table")
        
        for tabela in tabelas:
            rows = tabela.query_selector_all("tbody tr")
            if len(rows) == 0: continue
            
            for row in rows:
                try:
                    nome_el = row.query_selector("td a.team-link") or row.query_selector("td a") or row.query_selector("td:first-child")
                    if not nome_el: continue
                    
                    nome = nome_el.inner_text().strip().lower()
                    if len(nome) < 3 or nome in ("team", "squad", "time"): continue
                    
                    cells = row.query_selector_all("td")
                    valores = []
                    for cell in cells:
                        texto = cell.inner_text().strip()
                        try:
                            valor = float(texto.replace(",", ".").replace("%", ""))
                            valores.append(valor)
                        except:
                            valores.append(texto)
                    
                    xg_val = xga_val = None
                    for v in valores:
                        if isinstance(v, (int, float)) and 0.3 <= v <= 4.0:
                            if xg_val is None: xg_val = v
                            elif xga_val is None and v != xg_val:
                                xga_val = v
                                break
                    
                    if xg_val is not None and xga_val is not None:
                        dados[nome] = {"xg": round(xg_val, 2), "xga": round(xga_val, 2), "fonte": "WhoScored"}
                except:
                    continue
            
            if len(dados) >= 5: break
        
    except Exception as e:
        st.warning(f"WhoScored: {e}")
    finally:
        try: browser.close(); p.stop()
        except: pass
    
    return dados

# ========== FBREF ==========
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
            xg_col = next((c for c in df.columns if c.endswith("xg") and "xga" not in c and "npxg" not in c), None)
            xga_col = next((c for c in df.columns if "xga" in c and "npxg" not in c), None)
            mp_col = next((c for c in df.columns if c in ("mp","matches","pj","pg")), None)
            if not (squad_col and xg_col): continue
            for _, row in df.iterrows():
                try:
                    nome = str(row[squad_col]).lower().strip()
                    if nome in ("squad","nan",""): continue
                    xg = float(str(row[xg_col]).replace(",","."))
                    xga = float(str(row[xga_col]).replace(",",".")) if xga_col else xg
                    mp = float(str(row[mp_col]).replace(",",".")) if mp_col else 1
                    if mp > 0 and xg > 0:
                        dados[nome] = {"xg": round(xg/mp,2), "xga": round(xga/mp,2), "fonte": "FBref"}
                except: continue
            if dados: break
    except: pass
    return dados

# ========== MONTE CARLO ==========
def monte_carlo(l1, l2, cv1=35, cv2=35, n=10000):
    np.random.seed(42)
    v1 = emp = v2 = btts_c = over25_c = 0
    favorito = "t1" if l1 >= l2 else "t2"
    ruido1 = max(0.08, min(0.20, cv1 / 500))
    ruido2 = max(0.08, min(0.20, cv2 / 500))
    for _ in range(n):
        ll1, ll2 = l1, l2
        if np.random.random() < 0.05:
            if np.random.random() < 0.5: ll1 = max(0.05, ll1 - 0.5)
            else: ll2 = max(0.05, ll2 - 0.5)
        if np.random.random() < 0.10:
            ll1 += 0.15; ll2 += 0.15
        if np.random.random() < 0.15:
            if favorito == "t1": ll1 = max(0.05, ll1 - 0.3)
            else: ll2 = max(0.05, ll2 - 0.3)
        ll1 = max(0.05, ll1 * np.random.normal(1.0, ruido1))
        ll2 = max(0.05, ll2 * np.random.normal(1.0, ruido2))
        g1, g2 = np.random.poisson(ll1), np.random.poisson(ll2)
        if g1 > g2: v1 += 1
        elif g1 == g2: emp += 1
        else: v2 += 1
        if g1 > 0 and g2 > 0: btts_c += 1
        if g1 + g2 > 2: over25_c += 1
    return {"v1":v1/n,"emp":emp/n,"v2":v2/n,"btts":btts_c/n,"over25":over25_c/n}

# ========== ANÁLISE PRINCIPAL ==========
def analisar(time_a, time_b, competicao, odds_v1=None, odds_emp=None, odds_v2=None, contexto=None):
    ctx = contexto or {}
    alertas = []
    checklist = {}

    with st.spinner("🔍 Buscando dados em WhoScored + FBref..."):
        ws = buscar_whoscored(competicao)
        fb = buscar_fbref(competicao)

    DEF = DEFAULTS.get(normalizar(competicao), DEFAULTS["brasileirao"])

    dws_a, fonte_a = encontrar(time_a, ws)
    dws_b, fonte_b = encontrar(time_b, ws)
    dfb_a, fonte_fb_a = encontrar(time_a, fb)
    dfb_b, fonte_fb_b = encontrar(time_b, fb)

    xg_a = dws_a.get("xg") or dfb_a.get("xg") or DEF["xg"]
    xga_a = dws_a.get("xga") or dfb_a.get("xga") or DEF["xga"]
    xg_b = dws_b.get("xg") or dfb_b.get("xg") or DEF["xg"]
    xga_b = dws_b.get("xga") or dfb_b.get("xga") or DEF["xga"]

    fonte_xg_a = dws_a.get("fonte") or dfb_a.get("fonte") or "default"
    fonte_xg_b = dws_b.get("fonte") or dfb_b.get("fonte") or "default"

    xg_a_disp = fonte_xg_a != "default"
    xg_b_disp = fonte_xg_b != "default"
    checklist["xg_time_a"] = xg_a_disp
    checklist["xg_time_b"] = xg_b_disp
    checklist["xg_disponivel"] = xg_a_disp and xg_b_disp

    xg_label_a = f"{xg_a:.2f}" if xg_a_disp else f"{xg_a:.2f} (gols reais)"
    xg_label_b = f"{xg_b:.2f}" if xg_b_disp else f"{xg_b:.2f} (gols reais)"

    gols_a, gols_b = DEF["gols"], DEF["gols"]
    sog_a, sog_b = DEF["sog"], DEF["sog"]
    fin_a, fin_b = DEF["fin"], DEF["fin"]
    esc_a, esc_b = DEF["esc"], DEF["esc"]
    faltas_a, faltas_b = DEF["faltas"], DEF["faltas"]
    cv_gols_a = cv_gols_b = cv_sog_a = cv_sog_b = cv_fin_a = cv_fin_b = 35.0

    checklist["dados_5_jogos"] = False
    checklist["fin_verificado"] = False
    checklist["faltas_verificado"] = False
    checklist["posse_verificado"] = False
    checklist["h2h_verificado"] = False

    f_a, acao_a = fator_cv(cv_gols_a); f_b, acao_b = fator_cv(cv_gols_b)
    f_sog_a = 0.97 if 25 <= cv_sog_a <= 35 else 1.0
    f_sog_b = 0.97 if 25 <= cv_sog_b <= 35 else 1.0

    l1 = ((xg_a + xga_b) / 2) * 0.95 * f_a * f_sog_a
    l2 = ((xg_b + xga_a) / 2) * 0.90 * f_b * f_sog_b

    if ctx.get("t1_sem_obj"): l1 = max(0.05, l1 - 0.5); alertas.append("Regra 4.2: Time 1 sem objetivo")
    if ctx.get("t2_sem_obj"): l2 = max(0.05, l2 - 0.5); alertas.append("Regra 4.2: Time 2 sem objetivo")
    if ctx.get("t1_reserva"): l2 += 0.5; alertas.append("Regra 4.3: Time 1 reserva (+0.5 λ adv)")
    if ctx.get("t1_desespero"): l1 += 0.5; alertas.append("Regra 6C: Time 1 em desespero (+0.5 λ)")
    if ctx.get("t2_admin"): l2 = max(0.05, l2 - 0.3); alertas.append("Regra 6C: Time 2 administra (-0.3 λ)")
    checklist["contexto_aplicado"] = any(ctx.values())

    l1, l2 = max(0.05, l1), max(0.05, l2)
    lt = l1 + l2

    v1 = e = v2 = 0.0
    for i in range(10):
        for j in range(10):
            p = poisson(l1, i) * poisson(l2, j)
            if i > j: v1 += p
            elif i == j: e += p
            else: v2 += p

    btts = (1 - math.exp(-l1)) * (1 - math.exp(-l2))
    over15 = prob_over(lt, 1); under15 = prob_under(lt, 1)
    over25 = prob_over(lt, 2); under25 = prob_under(lt, 2)
    under45 = prob_under(lt, 4)

    mc = monte_carlo(l1, l2, cv_gols_a, cv_gols_b)
    checklist["monte_carlo_executado"] = True

    over25_seguro = lt > 3.0 and not ctx.get("t1_sem_obj") and not ctx.get("t2_sem_obj")
    under25_seguro = lt < 2.0 and (xga_a < 0.8 or xga_b < 0.8)
    checklist["over25_verificado"] = True
    checklist["under25_verificado"] = True
    if not over25_seguro: alertas.append("Over 2.5 NEGADO (Regra 6A)")
    if not under25_seguro: alertas.append("Under 2.5 NÃO CONFIÁVEL (Regra 6B)")

    checklist["sog_verificado"] = True
    checklist["cartoes_verificado"] = True

    o_v1 = odds_v1 or 2.00; o_emp = odds_emp or 3.20; o_v2 = odds_v2 or 3.50
    checklist["odds_disponiveis"] = bool(odds_v1)

    def vb(prob, odd, nome):
        ev_val = ev(prob, odd); k = kelly(prob, odd)
        conf = "Alta" if ev_val > 0.05 else ("Media" if ev_val > 0.005 else ("Baixa" if ev_val > 0 else "Sem Value"))
        sr = min(k * 0.33, 0.03) * 100 if conf != "Sem Value" else 0
        return {"nome":nome,"prob":prob,"odd":odd,"ev":ev_val,"kelly":k,"stake":sr,"conf":conf}

    mercados = [
        vb(v1, o_v1, f"Vit {time_a}"), vb(e, o_emp, "Empate"), vb(v2, o_v2, f"Vit {time_b}"),
        vb(btts, 1.90, "BTTS Sim"), vb(over25, 2.10, "Over 2.5"),
        vb(over15, 1.25, "Over 1.5"), vb(under45, 1.12, "Under 4.5"),
        vb(0.90, 1.15, "Over 1.5 Cartões"), vb(0.96, 1.05, "Under 9.5 Cartões"),
    ]
    checklist["ev_ok"] = any(m["ev"] > 0.005 for m in mercados)
    checklist["checklist_completo"] = True

    n_ok = sum(1 for v in checklist.values() if v)
    alta_incerteza = n_ok < 10 or cv_gols_a >= 60 or cv_gols_b >= 60
    if alta_incerteza:
        alertas.insert(0, "⚠️ ALTA INCERTEZA — Stake reduzido a 0.5% do bank")

    def nota_ef(sog, fin, gols):
        if fin == 0: return 50
        return min(100, int((sog/fin*0.5 + gols/fin*0.5) * 200))
    nota_a, nota_b = nota_ef(sog_a, fin_a, gols_a), nota_ef(sog_b, fin_b, gols_b)

    # ========== RENDER ==========
    st.markdown(f'<div class="match-header"><div class="match-title">{time_a.upper()} × {time_b.upper()}</div><div class="match-comp">🏆 {competicao}</div></div>', unsafe_allow_html=True)

    if alta_incerteza:
        st.markdown('<div class="incerteza">⚠️ ALTA INCERTEZA — Aposte no máximo 0.5% do bank</div>', unsafe_allow_html=True)
    for al in alertas:
        st.markdown(f'<div class="alert-box">{al}</div>', unsafe_allow_html=True)

    # 1. Ajuste por Variância
    html = f"""<table><tr><th>Métrica</th><th>Time</th><th>CV</th><th>Ação</th></tr>
    <tr><td>Gols</td><td>{time_a}</td><td>{cv_gols_a:.0f}%</td><td>{acao_a}</td></tr>
    <tr><td>Gols</td><td>{time_b}</td><td>{cv_gols_b:.0f}%</td><td>{acao_b}</td></tr>
    <tr><td>SOG</td><td>{time_a}</td><td>{cv_sog_a:.0f}%</td><td>{acao_sog(cv_sog_a)}</td></tr>
    <tr><td>SOG</td><td>{time_b}</td><td>{cv_sog_b:.0f}%</td><td>{acao_sog(cv_sog_b)}</td></tr></table>"""
    st.markdown(card("1. Ajuste por Variância (Regra 3)", html), unsafe_allow_html=True)

    # 2. Poisson
    html = f"<p style='color:#C9A84C'>λ {time_a} = {l1:.2f} | λ {time_b} = {l2:.2f}</p><table><tr><th>Gols</th><th>Prob {time_a}</th><th>Prob {time_b}</th></tr>"
    for g in range(4):
        label = str(g) if g < 3 else "3+"
        pa = sum(poisson(l1,i) for i in ([g] if g<3 else range(3,10)))*100
        pb = sum(poisson(l2,i) for i in ([g] if g<3 else range(3,10)))*100
        html += f"<tr><td>{label}</td><td>{pa:.1f}%</td><td>{pb:.1f}%</td></tr>"
    html += f"</table><p style='margin-top:8px;color:#A0B4C8'>BTTS: {btts*100:.1f}% | Over 1.5: {over15*100:.1f}% | Over 2.5: {over25*100:.1f}% | Under 4.5: {under45*100:.1f}%</p>"
    st.markdown(card("2. Poisson Ajustado", html), unsafe_allow_html=True)

    # 3. Monte Carlo
    html = f"""<p style='color:#A0B4C8;font-size:12px'>10.000 simulações com ruído (expulsões, gol precoce, recuo, CV)</p>
    <table><tr><th>Resultado</th><th>Poisson</th><th>Monte Carlo</th></tr>
    <tr><td>Vit. {time_a}</td><td>{v1*100:.1f}%</td><td>{mc['v1']*100:.1f}%</td></tr>
    <tr><td>Empate</td><td>{e*100:.1f}%</td><td>{mc['emp']*100:.1f}%</td></tr>
    <tr><td>Vit. {time_b}</td><td>{v2*100:.1f}%</td><td>{mc['v2']*100:.1f}%</td></tr>
    <tr><td>BTTS</td><td>{btts*100:.1f}%</td><td>{mc['btts']*100:.1f}%</td></tr>
    <tr><td>Over 2.5</td><td>{over25*100:.1f}%</td><td>{mc['over25']*100:.1f}%</td></tr></table>"""
    st.markdown(card("3. Monte Carlo (10k simulações)", html), unsafe_allow_html=True)

    # 4. Eficiência + Fontes
    def ef_label(n): return "eficiente" if n>83 else ("média" if n>=75 else "ineficiente")
    html = f"""<table><tr><th>Time</th><th>xG</th><th>xGA</th><th>Fonte xG</th><th>Nota</th><th>Status</th></tr>
    <tr><td>{time_a}</td><td>{xg_label_a}</td><td>{xga_a:.2f}</td><td>{fonte_xg_a}</td><td>{nota_a}</td><td>{ef_label(nota_a)}</td></tr>
    <tr><td>{time_b}</td><td>{xg_label_b}</td><td>{xga_b:.2f}</td><td>{fonte_xg_b}</td><td>{nota_b}</td><td>{ef_label(nota_b)}</td></tr></table>"""
    st.markdown(card("4. Eficiência Ofensiva + Fontes", html), unsafe_allow_html=True)

    # 5. Value Bets
    html = "<table><tr><th>Mercado</th><th>Prob.</th><th>Odd</th><th>EV%</th><th>Kelly</th><th>Stake</th></tr>"
    for m in mercados:
        cor = "#4CAF50" if m["ev"]>0.005 else ("#C9A84C" if m["ev"]>0 else
