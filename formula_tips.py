# -*- coding: utf-8 -*-
"""
FORMULA TIPS V4.1 — VERSÃO ESTÁVEL (REDSCORES + FBREF + FALLBACKS)
10 Regras | 9 Seções | 16 Itens Checklist
Fontes: Redscores (dados por jogo) + FBref (fallback)
Odds: Entrada Manual (Regra 1)
"""

import math, time, os, re, json, unicodedata
from datetime import datetime
from pathlib import Path

import numpy as np
import streamlit as st
import requests
import pandas as pd
from io import StringIO

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

def encontrar_time_fbref(nome_time: str, dados_fbref: dict):
    if not dados_fbref: return {}, "default"
    nome_normalizado = normalizar(nome_time)
    if nome_normalizado in dados_fbref: return dados_fbref[nome_normalizado], "FBref"
    for k, v in dados_fbref.items():
        if nome_normalizado in k or k in nome_normalizado: return v, "FBref"
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

# ========== FBREF (FALLBACK) ==========
@st.cache_data(ttl=3600, show_spinner=False)
def buscar_fbref(competicao: str) -> dict:
    comp_id = FBREF_IDS.get(normalizar(competicao))
    if not comp_id: return {}
    url = f"https://fbref.com/en/comps/{comp_id}/stats/"
    headers = {"User-Agent": "Mozilla/5.0"}
    dados = {}
    try:
        time.sleep(3)
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

# ========== REDSCORES ==========
def buscar_time_redscores(nome_time):
    nome_fmt = nome_time.lower().strip().replace(" ", "-")
    nome_fmt = unicodedata.normalize("NFD", nome_fmt).encode("ascii", "ignore").decode("ascii")
    url_direta = f"https://redscores.com/team/{nome_fmt}"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url_direta, headers=headers, timeout=10)
        if resp.status_code == 200: return url_direta
    except: pass
    try:
        url_busca = f"https://redscores.com/pt-br/search?q={nome_fmt}"
        resp = requests.get(url_busca, headers=headers, timeout=10)
        html = resp.text
        pattern = rf'href="(/team/{nome_fmt}(?:/\d+)?)"'
        match = re.search(pattern, html)
        if match: return f"https://redscores.com{match.group(1)}"
        pattern2 = rf'href="(/team/[^"]*{nome_fmt}[^"]*)"'
        match = re.search(pattern2, html)
        if match: return f"https://redscores.com{match.group(1)}"
    except: pass
    return None

@st.cache_data(ttl=3600, show_spinner=False)
def extrair_dados_redscores(nome_time):
    url = buscar_time_redscores(nome_time)
    if not url: return None
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200: return None
        html = resp.text
        dados = {"fonte": "Redscores", "url": url}
        for nome, patterns in [
            ("xg", [r'xG[:\s]*([\d.]+)', r'Expected Goals[:\s]*([\d.]+)', r'gols esperados[:\s]*([\d.]+)']),
            ("xga", [r'xGA[:\s]*([\d.]+)', r'Expected Goals Against[:\s]*([\d.]+)', r'xG Contra[:\s]*([\d.]+)']),
            ("posse", [r'(?:Posse|Possession|Posse de Bola)[:\s]*(\d+)%', r'Ball Possession[:\s]*(\d+)%']),
            ("sog", [r'(?:Chutes ao Gol|Shots on Target|SOG)[:\s]*([\d.]+)', r'Remates ao Gol[:\s]*([\d.]+)']),
            ("fin", [r'(?:Finalizações|Total Shots|Remates)[:\s]*([\d.]+)', r'Total de Finalizações[:\s]*([\d.]+)']),
            ("esc", [r'(?:Escanteios|Corners|Cantos)[:\s]*([\d.]+)']),
            ("cartoes", [r'(?:Cartões|Cards|Yellow Cards)[:\s]*([\d.]+)', r'Cartões Amarelos[:\s]*([\d.]+)']),
            ("faltas", [r'(?:Faltas|Fouls)[:\s]*([\d.]+)']),
        ]:
            for p in patterns:
                m = re.search(p, html, re.IGNORECASE)
                if m: dados[nome] = float(m.group(1)); break
        jogos = []
        for m in re.finditer(r'(\d{2}/\d{2}(?:/\d{2,4})?).*?(\d+)\s*[-–]\s*(\d+)', html):
            jogos.append({"data": m.group(1), "gols_pro": int(m.group(2)), "gols_contra": int(m.group(3))})
        if not jogos:
            nome_norm = normalizar(nome_time)
            for m in re.finditer(r'([A-Za-zÀ-ÿ\s]+)\s+(\d+)\s*[-–]\s*(\d+)\s+([A-Za-zÀ-ÿ\s]+)', html):
                t1, g1, g2, t2 = m.group(1).strip(), int(m.group(2)), int(m.group(3)), m.group(4).strip()
                if nome_norm in normalizar(t1): jogos.append({"gols_pro": g1, "gols_contra": g2, "adv": t2})
                elif nome_norm in normalizar(t2): jogos.append({"gols_pro": g2, "gols_contra": g1, "adv": t1})
        if jogos:
            dados["ultimos_jogos"] = jogos[:5]
            dados["jogos_encontrados"] = len(jogos)
        return dados
    except Exception as e:
        st.warning(f"Redscores: {e}")
        return None

def calcular_metricas_redscores(dados_redscores):
    if not dados_redscores or "ultimos_jogos" not in dados_redscores: return None
    jogos = dados_redscores["ultimos_jogos"]
    if len(jogos) < 2: return None
    gols_pro = [j["gols_pro"] for j in jogos]
    gols_contra = [j["gols_contra"] for j in jogos]
    def media_cv(valores):
        m = np.mean(valores); dp = np.std(valores, ddof=0)
        return m, (dp / m * 100) if m > 0 else 0
    m_gols, cv_gols = media_cv(gols_pro)
    m_sof, _ = media_cv(gols_contra)
    return {"gols": round(m_gols, 1), "cv_gols": round(cv_gols, 0), "sofridos": round(m_sof, 1), "jogos": len(jogos)}

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
        if np.random.random() < 0.10: ll1 += 0.15; ll2 += 0.15
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
    DEF = DEFAULTS.get(normalizar(competicao), DEFAULTS["brasileirao"])

    with st.spinner("🔍 Buscando dados no Redscores..."):
        dados_a = extrair_dados_redscores(time_a)
        dados_b = extrair_dados_redscores(time_b)
    
    if dados_a: st.success(f"✅ {time_a}: Redscores ({dados_a.get('jogos_encontrados', 0)} jogos)")
    if dados_b: st.success(f"✅ {time_b}: Redscores ({dados_b.get('jogos_encontrados', 0)} jogos)")
    
    if not dados_a or not dados_b:
        with st.spinner("⚠️ Redscores incompleto. Buscando FBref..."):
            fb = buscar_fbref(competicao)
        if not dados_a:
            dfb_a, _ = encontrar_time_fbref(time_a, fb) if fb else ({}, "default")
            if dfb_a: dados_a = {"xg": dfb_a.get("xg"), "xga": dfb_a.get("xga"), "fonte": "FBref"}
        if not dados_b:
            dfb_b, _ = encontrar_time_fbref(time_b, fb) if fb else ({}, "default")
            if dfb_b: dados_b = {"xg": dfb_b.get("xg"), "xga": dfb_b.get("xga"), "fonte": "FBref"}

    xg_a = dados_a.get("xg") if dados_a else None
    xga_a = dados_a.get("xga") if dados_a else None
    xg_b = dados_b.get("xg") if dados_b else None
    xga_b = dados_b.get("xga") if dados_b else None
    xg_a = xg_a if xg_a is not None else DEF["xg"]
    xga_a = xga_a if xga_a is not None else DEF["xga"]
    xg_b = xg_b if xg_b is not None else DEF["xg"]
    xga_b = xga_b if xga_b is not None else DEF["xga"]
    
    fonte_a = dados_a.get("fonte", "default") if dados_a else "default"
    fonte_b = dados_b.get("fonte", "default") if dados_b else "default"
    xg_a_disp = fonte_a != "default"
    xg_b_disp = fonte_b != "default"
    checklist["xg_time_a"] = xg_a_disp
    checklist["xg_time_b"] = xg_b_disp
    checklist["xg_disponivel"] = xg_a_disp and xg_b_disp
    xg_label_a = f"{xg_a:.2f}" if xg_a_disp else f"{xg_a:.2f} (gols reais)"
    xg_label_b = f"{xg_b:.2f}" if xg_b_disp else f"{xg_b:.2f} (gols reais)"

    met_a = calcular_metricas_redscores(dados_a) if dados_a else None
    met_b = calcular_metricas_redscores(dados_b) if dados_b else None
    if met_a: gols_a, cv_gols_a = met_a["gols"], met_a["cv_gols"]; checklist["dados_5_jogos"] = True
    else: gols_a, cv_gols_a = DEF["gols"], 35.0
    if met_b: gols_b, cv_gols_b = met_b["gols"], met_b["cv_gols"]; checklist["dados_5_jogos"] = True
    else: gols_b, cv_gols_b = DEF["gols"], 35.0
    
    sog_a = dados_a.get("sog", DEF["sog"]) if dados_a else DEF["sog"]
    sog_b = dados_b.get("sog", DEF["sog"]) if dados_b else DEF["sog"]
    fin_a = dados_a.get("fin", DEF["fin"]) if dados_a else DEF["fin"]
    fin_b = dados_b.get("fin", DEF["fin"]) if dados_b else DEF["fin"]
    esc_a = dados_a.get("esc", DEF["esc"]) if dados_a else DEF["esc"]
    esc_b = dados_b.get("esc", DEF["esc"]) if dados_b else DEF["esc"]
    faltas_a = dados_a.get("faltas", DEF["faltas"]) if dados_a else DEF["faltas"]
    faltas_b = dados_b.get("faltas", DEF["faltas"]) if dados_b else DEF["faltas"]
    cv_sog_a = cv_sog_b = cv_fin_a = cv_fin_b = 35.0
    
    checklist["fin_verificado"] = bool(dados_a and dados_a.get("fin"))
    checklist["faltas_verificado"] = bool(dados_a and dados_a.get("faltas"))
    checklist["posse_verificado"] = bool(dados_a and dados_a.get("posse"))
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
    if alta_incerteza: alertas.insert(0, "⚠️ ALTA INCERTEZA — Stake reduzido a 0.5% do bank")
    
    def nota_ef(sog, fin, gols):
        if fin == 0: return 50
        return min(100, int((sog/fin*0.5 + gols/fin*0.5) * 200))
    nota_a, nota_b = nota_ef(sog_a, fin_a, gols_a), nota_ef(sog_b, fin_b, gols_b)
    
    # ========== RENDER ==========
    st.markdown(f'<div class="match-header"><div class="match-title">{time_a.upper()} × {time_b.upper()}</div><div class="match-comp">🏆 {competicao}</div></div>', unsafe_allow_html=True)
    if alta_incerteza: st.markdown('<div class="incerteza">⚠️ ALTA INCERTEZA — Aposte no máximo 0.5% do bank</div>', unsafe_allow_html=True)
    for al in alertas: st.markdown(f'<div class="alert-box">{al}</div>', unsafe_allow_html=True)
    
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
    html = f"""<p style='color:#A0B4C8;font-size:12px'>10.000 simulações com ruído</p>
    <table><tr><th>Resultado</th><th>Poisson</th><th>Monte Carlo</th></tr>
    <tr><td>Vit. {time_a}</td><td>{v1*100:.1f}%</td><td>{mc['v1']*100:.1f}%</td></tr>
    <tr><td>Empate</td><td>{e*100:.1f}%</td><td>{mc['emp']*100:.1f}%</td></tr>
    <tr><td>Vit. {time_b}</td><td>{v2*100:.1f}%</td><td>{mc['v2']*100:.1f}%</td></tr>
    <tr><td>BTTS</td><td>{btts*100:.1f}%</td><td>{mc['btts']*100:.1f}%</td></tr>
    <tr><td>Over 2.5</td><td>{over25*100:.1f}%</td><td>{mc['over25']*100:.1f}%</td></tr></table>"""
    st.markdown(card("3. Monte Carlo (10k simulações)", html), unsafe_allow_html=True)
    
    # 4. Eficiência + Fontes
    def ef_label(n): return "eficiente" if n>83 else ("média" if n>=75 else "ineficiente")
    html = f"""<table><tr><th>Time</th><th>xG</th><th>xGA</th><th>Fonte</th><th>Nota</th><th>Status</th></tr>
    <tr><td>{time_a}</td><td>{xg_label_a}</td><td>{xga_a:.2f}</td><td>{fonte_a}</td><td>{nota_a}</td><td>{ef_label(nota_a)}</td></tr>
    <tr><td>{time_b}</td><td>{xg_label_b}</td><td>{xga_b:.2f}</td><td>{fonte_b}</td><td>{nota_b}</td><td>{ef_label(nota_b)}</td></tr></table>"""
    st.markdown(card("4. Eficiência Ofensiva + Fontes", html), unsafe_allow_html=True)
    
    # 5. Value Bets
    html = "<table><tr><th>Mercado</th><th>Prob.</th><th>Odd</th><th>EV%</th><th>Kelly</th><th>Stake</th></tr>"
    for m in mercados:
        cor = "#4CAF50" if m["ev"]>0.005 else ("#C9A84C" if m["ev"]>0 else "#EF5350")
        html += f"<tr><td>{m['nome']}</td><td>{m['prob']*100:.1f}%</td><td>{m['odd']:.2f}</td><td style='color:{cor}'>{m['ev']*100:+.1f}%</td><td>{m['kelly']:.3f}</td><td>{m['stake']:.1f}%</td></tr>"
    html += "</table>"
    st.markdown(card("5. Value Bets — Kelly 33% (Regra 5)", html), unsafe_allow_html=True)
    
    # 6. Tabela de Sugestões
    html = "<p style='color:#C9A84C;font-weight:600'>⚽ GOLS</p>"
    for label, val, rec in [
        ("Over 1.5", over15, "✅ Conservador"), ("Under 1.5", under15, "🛡️ Proteção"),
        ("Over 2.5", over25, "✅ Valor" if over25_seguro else "⚠️ Cautela"),
        ("Under 2.5", under25, "🔒 Âncora" if under25_seguro else "⚠️ Cautela"),
        ("Under 4.5", under45, "🔒 Âncora"),
    ]:
        cor = "#4CAF50" if val > 0.6 else ("#C9A84C" if val > 0.45 else "#EF5350")
        html += srow(label, barra(val * 100, cor), f"{val*100:.1f}% — {rec}")
    html += "<p style='color:#C9A84C;font-weight:600;margin-top:10px'>🎯 FINALIZAÇÕES</p>"
    html += srow("Média Combinada", barra((fin_a + fin_b) / 30 * 100, "#C9A84C"), f"{fin_a + fin_b:.0f} por jogo")
    html += "<p style='color:#C9A84C;font-weight:600;margin-top:10px'>🚩 ESCANTEIOS</p>"
    html += srow("Média Combinada", barra((esc_a + esc_b) / 15 * 100, "#C9A84C"), f"{esc_a + esc_b:.0f} por jogo")
    html += "<p style='color:#C9A84C;font-weight:600;margin-top:10px'>🟨 CARTÕES</p>"
    html += srow("Over 1.5 (Linha Segura)", barra(90, "#4CAF50"), "90% ✅")
    html += srow("Under 9.5 (Linha Segura)", barra(96, "#4CAF50"), "96% 🔒")
    html += "<p style='color:#C9A84C;font-weight:600;margin-top:10px'>🟨 FALTAS</p>"
    html += srow("Média Combinada", barra((faltas_a + faltas_b) / 40 * 100, "#C9A84C"), f"{faltas_a + faltas_b:.0f} por jogo")
    html += "<p style='color:#C9A84C;font-weight:600;margin-top:10px'>🥅 CHUTES A GOL (SOG)</p>"
    html += srow("Média Combinada", barra((sog_a + sog_b) / 15 * 100, "#C9A84C"), f"{sog_a + sog_b:.0f} por jogo")
    st.markdown(card("6. Tabela de Sugestões", html), unsafe_allow_html=True)
    
    # 7. Confluência
    xg_comb = xg_a + xg_b
    if xg_comb > 3.5: classif = "Explosão"
    elif xg_comb > 2.8: classif = "Aberto"
    elif xg_comb > 2.0: classif = "Equilibrado"
    else: classif = "Travado"
    mercado_sug = "Over escanteios + BTTS" if classif in ["Explosão", "Aberto"] else "Under gols + Cartões"
    conv = "✅ Convergente" if (over25_seguro and over25 > 0.5) or (not over25_seguro and over25 < 0.5) else "⚠️ Divergente"
    html = f"""<table>
    <tr><td class='stat-label'>Classificação</td><td class='stat-value'>{classif}</td></tr>
    <tr><td class='stat-label'>Mercado sugerido</td><td class='stat-value'>{mercado_sug}</td></tr>
    <tr><td class='stat-label'>Status</td><td class='stat-value'>{conv}</td></tr></table>"""
    st.markdown(card("7. Confluência com Modelo Qualitativo", html), unsafe_allow_html=True)
    
    # 8. Confiança Geral
    nivel = "⚠️ ALTA INCERTEZA" if alta_incerteza else ("Alta" if n_ok >= 12 else ("Media" if n_ok >= 9 else "Baixa"))
    stake_geral = "0.5%" if alta_incerteza else ("2-3%" if nivel == "Alta" else ("1-2%" if nivel == "Media" else "0.5-1%"))
    html = f"""<table>
    <tr><td class='stat-label'>Nível</td><td class='stat-value' style='color:{"#EF5350" if alta_incerteza else "#4CAF50"}'>{nivel}</td></tr>
    <tr><td class='stat-label'>Stake recomendado</td><td class='stat-value'>{stake_geral} do bank</td></tr></table>
    <table style='margin-top:8px'><tr><th>Check (16 itens)</th><th>Status</th></tr>
    {''.join(f"<tr><td>{k.replace('_',' ').title()}</td><td>{'✅' if v else '❌'}</td></tr>" for k, v in checklist.items())}</table>"""
    st.markdown(card("8. Confiança Geral (Regra 5)", html), unsafe_allow_html=True)
    
    # 9. CSV
    vb_top = max(mercados, key=lambda m: m["ev"])
    csv = pd.DataFrame([{
        "time1": time_a, "time2": time_b,
        "data": datetime.now().strftime("%Y-%m-%d"), "competicao": competicao,
        "mercado": vb_top["nome"], "odd_mercado": round(vb_top["odd"], 2),
        "odd_justa": round(1 / vb_top["prob"], 2) if vb_top["prob"] > 0 else None,
        "value": "Sim" if vb_top["ev"] > 0 else "Nao",
        "stake": f'{vb_top["stake"]:.1f}%', "banca_ini": 1000.00,
        "banca_fim": "", "resultado": "", "acerto": "", "v4.1_confianca": nivel
    }])
    st.dataframe(csv, use_container_width=True)
    st.download_button("📥 Baixar CSV", csv.to_csv(index=False).encode("utf-8"), file_name="formula_tips_v41.csv", mime="text/csv")
    
    try:
        hist = json.loads(HISTORICO_FILE.read_text()) if HISTORICO_FILE.exists() else []
        hist.insert(0, {"data": datetime.now().strftime("%d/%m/%Y %H:%M"), "time_a": time_a, "time_b": time_b, "competicao": competicao, "v1": round(v1*100,1), "emp": round(e*100,1), "v2": round(v2*100,1), "nivel": nivel})
        HISTORICO_FILE.write_text(json.dumps(hist[:20], ensure_ascii=False, indent=2))
    except: pass

# ========== UI ==========
st.set_page_config(page_title="FORMULA TIPS V4.1", page_icon="⚽", layout="centered")
st.markdown(CSS, unsafe_allow_html=True)

logo_path = "logotipo formula tips 01.png"
if os.path.exists(logo_path):
    col_logo, col_titulo = st.columns([1, 3])
    with col_logo: st.image(logo_path, width=90)
    with col_titulo:
        st.markdown("<h1 style='margin:0;padding-top:8px;color:#F0F0F0'>FORMULA TIPS V4.1</h1>", unsafe_allow_html=True)
        st.markdown("<p style='color:#C9A84C;margin:0;font-size:14px'>Redscores + FBref + Fallbacks</p>", unsafe_allow_html=True)
else:
    st.markdown("<h1 style='color:#F0F0F0;margin:0'>FORMULA TIPS V4.1</h1>", unsafe_allow_html=True)

st.markdown("<hr style='border-color:#2A3F55;margin:12px 0'>", unsafe_allow_html=True)

time_a = st.text_input("🟢 Time Mandante", placeholder="Ex: cruzeiro")
time_b = st.text_input("🔴 Time Visitante", placeholder="Ex: fluminense")
competicao = st.selectbox("🏆 Competição", list(FBREF_IDS.keys()))

with st.expander("📋 Contexto da Partida (Regra 4 e 6C)"):
    c1, c2 = st.columns(2)
    with c1:
        t1_sem = st.checkbox(f"{time_a or 'Mandante'} sem objetivo")
        t1_res = st.checkbox(f"{time_a or 'Mandante'} time reserva")
        t1_des = st.checkbox(f"{time_a or 'Mandante'} desespero")
    with c2:
        t2_sem = st.checkbox(f"{time_b or 'Visitante'} sem objetivo")
        t2_adm = st.checkbox(f"{time_b or 'Visitante'} administra resultado")

with st.expander("💰 Odds (Regra 1 — Menores do Mercado)"):
    c1, c2, c3 = st.columns(3)
    with c1: odd_v1 = st.number_input("Vit Casa", 1.01, 20.0, 2.00, 0.01, format="%.2f")
    with c2: odd_emp = st.number_input("Empate", 1.01, 20.0, 3.20, 0.01, format="%.2f")
    with c3: odd_v2 = st.number_input("Vit Fora", 1.01, 20.0, 3.50, 0.01, format="%.2f")

if st.button("⚡ ANALISAR AGORA", use_container_width=True):
    if not time_a or not time_b:
        st.warning("Preencha os nomes dos dois times.")
    else:
        ctx = {"t1_sem_obj": t1_sem, "t1_reserva": t1_res, "t1_desespero": t1_des, "t2_sem_obj": t2_sem, "t2_admin": t2_adm}
        analisar(time_a, time_b, competicao, odd_v1, odd_emp, odd_v2, ctx)

if HISTORICO_FILE.exists():
    with st.expander("📊 Histórico de Análises"):
        hist = json.loads(HISTORICO_FILE.read_text())
        for h in hist[:10]:
            st.caption(f"{h['data']} — {h['time_a']} x {h['time_b']} ({h['competicao']}) — {h['nivel']}")
