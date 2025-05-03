# app.py
# frontend/app.py
import streamlit as st
import requests
from datetime import datetime

API = "http://localhost:8000"

# Configuration de la page
st.set_page_config(
    page_title="🧠 Agent Francilien",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Barre latérale : pagination
st.sidebar.title("Contrôles")
st.sidebar.subheader("Pagination des résumés")
page_size = st.sidebar.selectbox("Résumés par page", [5, 10, 20], index=0)
if "page" not in st.session_state:
    st.session_state.page = 1

col_prev, col_next = st.sidebar.columns(2)
if col_prev.button("←"):
    st.session_state.page = max(1, st.session_state.page - 1)
if col_next.button("→"):
    st.session_state.page += 1

# Titre principal
st.title("🧠 Agent Francilien – Résumés IA d'actualités locales")

# Onglets pour les deux modes
tabs = st.tabs(["Résumé SerpAPI", "Agent intelligent"])

# 1️⃣ Résumé SerpAPI
with tabs[0]:
    st.markdown("### 🎯 Résumé automatique via SerpAPI")
    if st.button("🧠 Lancer résumé SerpAPI"):
        with st.spinner("🔍 Collecte et résumé en cours..."):
            try:
                res = requests.post(f"{API}/serp-summarize")
                res.raise_for_status()
                data = res.json()
                st.success(data.get("message", "✅ Résumé généré."))
                st.session_state.serp_summary = data["summary"]
            except Exception as e:
                st.error(f"❌ Erreur : {e}")
    if "serp_summary" in st.session_state:
        st.text_area("🧾 Résumé SerpAPI", st.session_state.serp_summary, height=200)

# 2️⃣ Résumé Agent LangChain
with tabs[1]:
    st.markdown("### 🤖 Résumé via Agent LangChain")
    if st.button("🤖 Lancer l'agent intelligent"):
        with st.spinner("🧠 Agent en réflexion..."):
            try:
                res = requests.post(f"{API}/serp-agent")
                res.raise_for_status()
                data = res.json()
                st.success("✅ Résumé généré via agent intelligent")
                st.session_state.agent_summary = data["summary"]
            except Exception as e:
                st.error(f"❌ Erreur Agent : {e}")
    if "agent_summary" in st.session_state:
        st.text_area("🧾 Résumé Agent", st.session_state.agent_summary, height=200)

st.markdown("---")
st.subheader("📚 Derniers résumés générés")

# Affichage des anciens résumés avec pagination
try:
    res = requests.get(f"{API}/summaries")
    res.raise_for_status()
    summaries = res.json()
    total = len(summaries)
    start = (st.session_state.page - 1) * page_size
    end = start + page_size
    for s in summaries[start:end]:
        timestamp = datetime.fromisoformat(s["created_at"]).strftime("%Y-%m-%d %H:%M:%S")
        with st.expander(f"🕒 {timestamp} — {s['title']}"):
            st.write(s["content"])
    total_pages = (total - 1) // page_size + 1
    st.caption(f"Page {st.session_state.page} / {total_pages}")
except Exception as e:
    st.error(f"❌ Erreur chargement des résumés : {e}")
