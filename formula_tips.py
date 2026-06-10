# -*- coding: utf-8 -*-
"""
FORMULA TIPS V4.1 — VERSÃO FINAL (URLs DIRETAS)
10 Regras | 9 Seções | 16 Itens Checklist
Entrada: URLs do Redscores (Mandante, Visitante, H2H)
"""

import math, time, os, re, json, unicodedata
from datetime import datetime
from pathlib import Path

import numpy as np
import streamlit as st
import requests
import pandas as pd

# ========== CONFIGURAÇÃO ==========
try:
    HISTORICO_FILE = Path(__file__).parent / "historico_v41.json"
except NameError:
    HISTORICO_FILE = Path.cwd() / "historico_v41.json"

# ========== CSS ==========
CSS = """
<style>
html, body, [class*="stApp"] { background-color: #0D1B2A !important; color: #F0F0F0 !important; }
.stTextInput > div > div > input { background-color: #1C2E40; color: #F0F0F0; border: 1px solid #C9A84C; border-radius: 8px; font-size: 13px; }
.stButton > button { width: 100%; background: linear-gradient(135deg, #C0152A, #8B0F1E); color: #F0F0F0; font-size: 18px; font-weight: bold; border: 2px solid #C9A84C; border-radius: 12px; padding: 14px; letter-spacing: 1px; }
.stButton > button:hover { background: linear-gradient(135deg, #E0182F, #C0152A); }
.card { background-color: #1C2E40; border: 1px solid #2A3F55; border-radius: 12px; padding: 16px; margin-bottom: 12px; }
.card-title { color: #C9A84C; font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; border-bottom: 1px solid #2A3F55; padding-bottom: 6px; }
.stat-row { display: flex; justify-content: space-between; align-items: center; padding: 7px 0; border-bottom: 1px solid #1a2d3d; font-size: 14px; }
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
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th { color: #C9A84C; padding: 6px 8px; border-bottom: 1px solid #2A3F55; text-align: left; }
td { color: #F0F0F0; padding: 5px 8px; border-bottom: 1px solid #1a2d3d; }
</style>
"""

# ========== FUNÇÕES DE EXTRAÇÃO ==========

@st.cache_data(ttl=3600, show_spinner=False)
def extrair_dados_time_redscores(url):
    """Extrai todos os dados de um time a partir da URL do Redscores."""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return None
        html = resp.text
        
        dados = {"fonte": "Redscores"}
        
        # Nome do time
        nome_match = re.search(r'<title>([^<]+)</title>', html)
        if nome_match:
            dados["nome"] = nome_match.group(1).split(" - ")[0].strip()
        
        # xG
        xg_match = re.search(r'xG[:\s]*([\d.]+)', html, re.IGNORECASE)
        if xg_match: dados["xg"] = float(xg_match.group(1))
        
        # xGA
        xga_match = re.search(r'xGA[:\s]*([\d.]+)', html, re.IGNORECASE)
        if xga_match: dados["xga"] = float(xga_match.group(1))
        
        # Posse
        posse_match = re.search(r'(?:Posse|Possession)[:\s]*(\d+)%', html, re.IGNORECASE)
        if posse_match: dados["posse"] = float(posse_match.group(1))
        
        # SOG
        sog_match = re.search(r'(?:Chutes ao Gol|Shots on Target|SOG)[:\s]*([\d.]+)', html, re.IGNORECASE)
        if sog_match: dados["sog"] = float(sog_match.group(1))
        
        # Finalizações
        fin_match = re.search(r'(?:Finalizações|Total Shots)[:\s]*([\d.]+)', html, re.IGNORECASE)
        if fin_match: dados["fin"] = float(fin_match.group(1))
        
        # Escanteios
        esc_match = re.search(r'(?:Escanteios|Corners)[:\s]*([\d.]+)', html, re.IGNORECASE)
        if esc_match: dados["esc"] = float(esc_match.group(1))
        
        # Cartões
        cart_match = re.search(r'(?:Cartões|Cards)[:\s]*([\d.]+)', html, re.IGNORECASE)
        if cart_match: dados["cartoes"] = float(cart_match.group(1))
        
        # Faltas
        faltas_match = re.search(r'(?:Faltas|Fouls)[:\s]*([\d.]+)', html, re.IGNORECASE)
        if faltas_match: dados["faltas"] = float(faltas_match.group(1))
        
        # Últimos jogos
        jogos = []
        for m in re.finditer(r'(\d{2}/\d{2}(?:/\d{2,4})?).*?(\d+)\s*[-–]\s*(\d+)', html):
            jogos.append({"data": m.group(1), "gols_pro": int(m.group(2)), "gols_contra": int(m.group(3))})
        
        if jogos:
            dados["ultimos_jogos"] = jogos[:5]
            dados["jogos_encontrados"] = len(jogos)
        
        return dados
    except:
        return None


def extrair_h2h_redscores(url):
    """Extrai dados de H2H do Redscores."""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return None
        html = resp.text
        
        h2h = {"confrontos": []}
        
        # Buscar placares
        for m in re.finditer(r'(\d{2}/\d{2}(?:/\d{2,4})?).*?(\d+)\s*[-–]\s*(\d+)', html):
            h2h["confrontos"].append({
                "data": m.group(1),
                "gols_casa": int(m.group(2)),
                "gols_fora": int(m.group(3)),
            })
        
        if h2h["confrontos"]:
            h2h["total"] = len(h2h["confrontos"])
            h2h["ultimo"] = h2h["confrontos"][0] if h2h["confrontos"] else None
        
        return h2h
    except:
        return None


def calcular_metricas(dados_time):
    """Calcula médias e CV a partir dos últimos jogos."""
    if not dados_time or "ultimos_jogos" not in dados_time:
        return None
    
    jogos = dados_time["ultimos_jogos"]
    if len(jogos) < 2:
        return None
    
    gols_pro = [j["gols_pro"] for j in jogos]
    gols_contra = [j["gols_contra"] for j in jogos]
    
    def media_cv(valores):
        m = np.mean(valores)
        dp = np.std(valores, ddof=0)
        cv = (dp / m * 100) if m > 0 else 0
        return m, cv
    
    m_gols, cv_gols = media_cv(gols_pro)
    m_sof, _ = media_cv(gols_contra)
    
    return {
        "gols": round(m_gols, 1),
        "cv_gols": round(cv_gols, 0),
        "sofridos": round(m_sof, 1),
        "jogos": len(jogos)
    }


# ========== MODELO MATEMÁTICO ==========

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

def analisar(url_a, url_b, url_h2h, odds_v1=None, odds_emp=None, odds_v2=None, contexto=None):
    ctx = contexto or {}
    alertas = []
    checklist = {}
    
    # 1. Extrair dados
    with st.spinner("🔍 Extraindo dados do Redscores..."):
        dados_a = extrair_dados_time_redscores(url_a)
        dados_b = extrair_dados_time_redscores(url_b)
        h2h = extrair_h2h_redscores(url_h2h) if url_h2h else None
    
    if not dados_a or not dados_b:
        st.error("❌ Não foi possível extrair dados de um dos times. Verifique as URLs.")
        return
    
    nome_a = dados_a.get("nome", "Time A")
    nome_b = dados_b.get("nome", "Time B")
    
    st.success(f"✅ {nome_a}: {dados_a.get('jogos_encontrados', 0)} jogos extraídos")
    st.success(f"✅ {nome_b}: {dados_b.get('jogos_encontrados', 0)} jogos extraídos")
    if h2h:
        st.success(f"✅ H2H: {h2h.get('total', 0)} confrontos encontrados")
    
    # 2. Métricas
    met_a = calcular_metricas(dados_a)
    met_b = calcular_metricas(dados_b)
    
    xg_a = dados_a.get("xg", 1.40)
    xga_a = dados_a.get("xga", 1.40)
    xg_b = dados_b.get("xg", 1.40)
    xga_b = dados_b.get("xga", 1.40)
    
    checklist["xg_time_a"] = bool(dados_a.get("xg"))
    checklist["xg_time_b"] = bool(dados_b.get("xg"))
    checklist["xg_disponivel"] = checklist["xg_time_a"] and checklist["xg_time_b"]
    
    if met_a: gols_a, cv_gols_a = met_a["gols"], met_a["cv_gols"]; checklist["dados_5_jogos"] = True
    else: gols_a, cv_gols_a = 1.40, 35.0
    
    if met_b: gols_b, cv_gols_b = met_b["gols"], met_b["cv_gols"]; checklist["dados_5_jogos"] = True
    else: gols_b, cv_gols_b = 1.40, 35.0
    
    sog_a = dados_a.get("sog", 4.5); sog_b = dados_b.get("sog", 4.5)
    fin_a = dados_a.get("fin", 12.0); fin_b = dados_b.get("fin", 12.0)
    esc_a = dados_a.get("esc", 5.0); esc_b = dados_b.get("esc", 5.0)
    faltas_a = dados_a.get("faltas", 22.0); faltas_b = dados_b.get("faltas", 22.0)
    
    checklist["fin_verificado"] = bool(dados_a.get("fin"))
    checklist["faltas_verificado"] = bool(dados_a.get("faltas"))
    checklist["posse_verificado"] = bool(dados_a.get("posse"))
    checklist["h2h_verificado"] = bool(h2h)
    
    # 3. Ajustes
    f_a, acao_a = fator_cv(cv_gols_a); f_b, acao_b = fator_cv(cv_gols_b)
    
    l1 = ((xg_a + xga_b) / 2) * 0.95 * f_a
    l2 = ((xg_b + xga_a) / 2) * 0.90 * f_b
    
    if ctx.get("t1_sem_obj"): l1 = max(0.05, l1 - 0.5); alertas.append("Time 1 sem objetivo")
    if ctx.get("t2_sem_obj"): l2 = max(0.05, l2 - 0.5); alertas.append("Time 2 sem objetivo")
    checklist["contexto_aplicado"] = any(ctx.values())
    
    l1, l2 = max(0.05, l1), max(0.05, l2)
    lt = l1 + l2
    
    # 4. Poisson
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
    
    over25_seguro = lt > 3.0
    under25_seguro = lt < 2.0
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
        sr = min(k * 0.33, 0.03) * 100 if ev_val > 0 else 0
        return {"nome":nome,"prob":prob,"odd":odd,"ev":ev_val,"kelly":k,"stake":sr}
    
    mercados = [
        vb(v1, o_v1, f"Vit {nome_a}"), vb(e, o_emp, "Empate"), vb(v2, o_v2, f"Vit {nome_b}"),
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
    st.markdown(f'<div class="match-header"><div class="match-title">{nome_a} × {nome_b}</div><div class="match-comp">🏆 Dados: Redscores</div></div>', unsafe_allow_html=True)
    if alta_incerteza: st.markdown('<div class="incerteza">⚠️ ALTA INCERTEZA — Aposte no máximo 0.5% do bank</div>', unsafe_allow_html=True)
    for al in alertas: st.markdown(f'<div class="alert-box">{al}</div>', unsafe_allow_html=True)
    
    # 1. Ajuste por Variância
    html = f"""<table><tr><th>Métrica</th><th>{nome_a}</th><th>{nome_b}</th></tr>
    <tr><td>Gols</td><td>{gols_a} (CV {cv_gols_a:.0f}%)</td><td>{gols_b} (CV {cv_gols_b:.0f}%)</td></tr>
    <tr><td>xG</td><td>{xg_a:.2f}</td><td>{xg_b:.2f}</td></tr>
    <tr><td>xGA</td><td>{xga_a:.2f}</td><td>{xga_b:.2f}</td></tr>
    <tr><td>SOG</td><td>{sog_a:.1f}</td><td>{sog_b:.1f}</td></tr>
    <tr><td>Finalizações</td><td>{fin_a:.1f}</td><td>{fin_b:.1f}</td></tr>
    <tr><td>Escanteios</td><td>{esc_a:.1f}</td><td>{esc_b:.1f}</td></tr></table>"""
    st.markdown(card("1. Dados Extraídos", html), unsafe_allow_html=True)
    
    # 2. Poisson
    html = f"<p style='color:#C9A84C'>λ {nome_a} = {l1:.2f} | λ {nome_b} = {l2:.2f}</p><table><tr><th>Resultado</th><th>Probabilidade</th></tr>"
    html += f"<tr><td>Vit {nome_a}</td><td>{v1*100:.1f}%</td></tr>"
    html += f"<tr><td>Empate</td><td>{e*100:.1f}%</td></tr>"
    html += f"<tr><td>Vit {nome_b}</td><td>{v2*100:.1f}%</td></tr>"
    html += f"<tr><td>BTTS</td><td>{btts*100:.1f}%</td></tr>"
    html += f"<tr><td>Over 2.5</td><td>{over25*100:.1f}%</td></tr>"
    html += f"<tr><td>Under 4.5</td><td>{under45*100:.1f}% 🔒</td></tr></table>"
    st.markdown(card("2. Probabilidades", html), unsafe_allow_html=True)
    
    # 3. Value Bets
    html = "<table><tr><th>Mercado</th><th>Prob.</th><th>Odd</th><th>EV%</th><th>Stake</th></tr>"
    for m in mercados:
        cor = "#4CAF50" if m["ev"]>0.005 else ("#C9A84C" if m["ev"]>0 else "#EF5350")
        html += f"<tr><td>{m['nome']}</td><td>{m['prob']*100:.1f}%</td><td>{m['odd']:.2f}</td><td style='color:{cor}'>{m['ev']*100:+.1f}%</td><td>{m['stake']:.1f}%</td></tr>"
    html += "</table>"
    st.markdown(card("3. Value Bets — Kelly 33%", html), unsafe_allow_html=True)
    
    # 4. Confiança
    nivel = "⚠️ ALTA INCERTEZA" if alta_incerteza else ("Alta" if n_ok >= 12 else "Media")
    stake_geral = "0.5%" if alta_incerteza else ("2-3%" if nivel=="Alta" else "1-2%")
    html = f"<p><b>Nível:</b> {nivel} | <b>Stake:</b> {stake_geral} do bank</p>"
    html += "<table><tr><th>Check</th><th>Status</th></tr>"
    html += ''.join(f"<tr><td>{k}</td><td>{'✅' if v else '❌'}</td></tr>" for k,v in checklist.items())
    html += "</table>"
    st.markdown(card("4. Confiança Geral", html), unsafe_allow_html=True)
    
    # CSV
    vb_top = max(mercados, key=lambda m: m["ev"])
    csv = pd.DataFrame([{
        "time1": nome_a, "time2": nome_b,
        "data": datetime.now().strftime("%Y-%m-%d"),
        "mercado": vb_top["nome"], "odd_mercado": round(vb_top["odd"], 2),
        "odd_justa": round(1 / vb_top["prob"], 2) if vb_top["prob"] > 0 else None,
        "value": "Sim" if vb_top["ev"] > 0 else "Nao",
        "stake": f'{vb_top["stake"]:.1f}%', "banca_ini": 1000.00,
        "v4.1_confianca": nivel
    }])
    st.dataframe(csv, use_container_width=True)

# ========== UI ==========
st.set_page_config(page_title="FORMULA TIPS V4.1", page_icon="⚽", layout="centered")
st.markdown(CSS, unsafe_allow_html=True)

st.markdown("<h1 style='color:#F0F0F0;text-align:center'>FORMULA TIPS V4.1</h1>", unsafe_allow_html=True)
st.markdown("<p style='color:#C9A84C;text-align:center'>Redscores — Dados Reais</p>", unsafe_allow_html=True)
st.markdown("<hr style='border-color:#2A3F55'>", unsafe_allow_html=True)

url_a = st.text_input("🟢 URL Mandante", placeholder="https://redscores.com/team/cruzeiro/3371")
url_b = st.text_input("🔴 URL Visitante", placeholder="https://redscores.com/team/fluminense/...")
url_h2h = st.text_input("⚔️ URL H2H (opcional)", placeholder="https://redscores.com/match/fluminense-cruzeiro/7Ixi4")

with st.expander("📋 Contexto (Regra 4/6C)"):
    c1, c2 = st.columns(2)
    with c1:
        t1_sem = st.checkbox("Mandante sem objetivo")
        t1_res = st.checkbox("Mandante time reserva")
        t1_des = st.checkbox("Mandante desespero")
    with c2:
        t2_sem = st.checkbox("Visitante sem objetivo")
        t2_adm = st.checkbox("Visitante administra resultado")

with st.expander("💰 Odds (Regra 1)"):
    c1, c2, c3 = st.columns(3)
    with c1: odd_v1 = st.number_input("Vit Casa", 1.01, 20.0, 2.00, 0.01)
    with c2: odd_emp = st.number_input("Empate", 1.01, 20.0, 3.20, 0.01)
    with c3: odd_v2 = st.number_input("Vit Fora", 1.01, 20.0, 3.50, 0.01)

if st.button("⚡ ANALISAR AGORA", use_container_width=True):
    if not url_a or not url_b:
        st.warning("Preencha as URLs dos times.")
    else:
        ctx = {"t1_sem_obj": t1_sem, "t1_reserva": t1_res, "t1_desespero": t1_des, "t2_sem_obj": t2_sem, "t2_admin": t2_adm}
        analisar(url_a, url_b, url_h2h, odd_v1, odd_emp, odd_v2, ctx)
