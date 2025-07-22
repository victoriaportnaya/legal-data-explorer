import streamlit as st
import requests
import json
import pandas as pd
import plotly.express as px
import difflib
import unicodedata
import os
import openai

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
client = openai.OpenAI(api_key=OPENAI_API_KEY)

# --- Legal search helpers ---
def load_legal_articles():
    files = [
        ('Rome Statute', 'rome_statute.json'),
        ('Geneva Conventions', 'geneva_conventions.json')
    ]
    articles = []
    for source, fname in files:
        try:
            with open(fname, encoding='utf-8') as f:
                for art in json.load(f):
                    art['source'] = source
                    articles.append(art)
        except Exception:
            pass
    return articles

LEGAL_ARTICLES = load_legal_articles()

def normalize(text):
    return unicodedata.normalize('NFKC', text.lower().strip())

def find_legal_articles(query):
    q = normalize(query)
    results = []
    scored = []
    for art in LEGAL_ARTICLES:
        score = max(
            difflib.SequenceMatcher(None, q, normalize(art.get('title',''))).ratio(),
            difflib.SequenceMatcher(None, q, normalize(art.get('text',''))).ratio()
        )
        scored.append((score, art))
    scored.sort(reverse=True, key=lambda x: x[0])
    results = [a for s,a in scored[:3] if s > 0.2]
    return results

def is_legal_query(query):
    q = query.lower()
    return any(k in q for k in ["article", "стаття", "rome statute", "geneva", "criminal code", "кодекс", "статут", "женев"])

def is_region_stats_query(query):
    q = query.lower()
    keywords = [
        "statistics on regions", "bar chart of regions", "map of regions", "by region", "choropleth", "draw a map", "show map",
        "статистику по областях", "графік по областях", "мапа по областях", "по регіонах", "мапу", "побудуй мапу"
    ]
    return any(k in q for k in keywords)

def detect_type_query(query):
    q = query.lower()
    if any(k in q for k in ["type", "category", "категорі", "тип", "losses", "втрат"]):
        return 'losses'
    if any(k in q for k in ["object", "об'єкт", "объект", "objects"]):
        return 'objects'
    if any(k in q for k in ["event", "поді", "событ", "events"]):
        return 'events'
    return None

st.set_page_config(page_title="Legal & Data Explorer", layout="centered")
st.title("Legal & Data Explorer")

st.markdown("""
## Legal & Data Explorer — What This Tool Can Do

Welcome! This tool empowers you to:

- **Ask questions** about war crimes statistics in Ukraine, in either English or Ukrainian.
- **Get answers** powered by advanced AI (OpenAI GPT-4o) and retrieval-augmented generation (RAG), combining your question with real data and legal sources.
- **Visualize data** interactively:
  - View a **bar chart** of war crimes by region (try: “show me statistics on regions”).
  - See **bar charts** for types, categories, objects, or events (try: “show me statistics by objects” or “by events”).
- **Receive AI-powered analysis** of the statistics and charts (for example, “Which region has the most cases?”).
- **Search international legal documents**:
  - Find the most relevant article in the Rome Statute or Geneva Conventions by describing the crime or topic (e.g., “Which article covers torture in the Rome Statute?” or “Find the Geneva Convention article about prisoners of war”).
  - The tool will show the most relevant legal article and provide an AI-generated summary or explanation in plain language.

Just enter your question or request below, select your language, and explore!

---
""")

lang = st.radio("Select language / Оберіть мову", ["English", "Українська"])
lang_code = "en" if lang == "English" else "ua"

query = st.text_input("Enter your question / Введіть ваше питання:")

if st.button("Ask / Запитати") and query:
    type_group = detect_type_query(query)
    if is_legal_query(query):
        st.subheader("Legal Article Search Results")
        results = find_legal_articles(query)
        if results:
            for art in results:
                st.markdown(f"**{art['source']} — Article {art['number']}**: {art['title']}")
                st.code(art['text'][:2000] + ("..." if len(art['text']) > 2000 else ""), language='markdown')
                # LLM analysis of the article
                with st.spinner("Analyzing legal article..."):
                    try:
                        response = requests.post(
                            "http://localhost:8010/llm_query",
                            json={"query": query, "lang": lang_code, "context_override": f"Legal article:\n{art['title']}\n{art['text']}"},
                            timeout=30
                        )
                        if response.status_code == 200:
                            result = response.json()
                            st.markdown(f"**Summary:**\n{result['answer']}")
                        else:
                            st.error(f"Backend error: {response.status_code}")
                    except Exception as e:
                        st.error(f"Error: {e}")
        else:
            st.warning("No relevant legal article found.")
    elif is_region_stats_query(query):
        st.subheader("Bar Chart: War Crimes by Region")
        with open('ccl/t4pua_stats.json', encoding='utf-8') as f:
            stats = json.load(f)
        df = pd.DataFrame(stats['regions'])
        region_col = 'en' if lang_code == 'en' else 'ua'
        fig = px.bar(df, x=region_col, y='cases', title='War Crimes by Region', labels={region_col: 'Region', 'cases': 'Cases'})
        st.plotly_chart(fig)
        # Optionally, add a pie chart for region proportions
        fig_pie = px.pie(df, names=region_col, values='cases', title='Proportion of War Crimes by Region')
        st.plotly_chart(fig_pie)
    elif type_group:
        with open('ccl/t4pua_stats.json', encoding='utf-8') as f:
            stats = json.load(f)
        df = pd.DataFrame(stats['categories'][type_group])
        label_col = 'en' if lang_code == 'en' else 'ua'
        st.subheader(f"Bar Chart: Statistics by {type_group.capitalize()}")
        fig = px.bar(df, x=label_col, y='cases', title=f'Statistics by {type_group.capitalize()}', labels={label_col: type_group.capitalize(), 'cases': 'Cases'})
        st.plotly_chart(fig)
        context_lines = [f"{row[label_col]}: {row['cases']}" for _, row in df.iterrows()]
        context_text = f"Statistics by {type_group} (from database):\n" + "\n".join(context_lines)
        with st.spinner("LLM analyzing statistics..."):
            try:
                response = requests.post(
                    "http://localhost:8010/llm_query",
                    json={"query": query, "lang": lang_code, "context_override": context_text},
                    timeout=30
                )
                if response.status_code == 200:
                    result = response.json()
                    st.markdown(f"**LLM Analysis / Аналіз LLM:**\n{result['answer']}")
                    st.markdown("---")
                    st.markdown(f"**Context / Контекст:**\n{result['context']}")
                else:
                    st.error(f"Backend error: {response.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        with st.spinner("Retrieving answer..."):
            try:
                response = requests.post(
                    "http://localhost:8010/llm_query",
                    json={"query": query, "lang": lang_code},
                    timeout=30
                )
                if response.status_code == 200:
                    result = response.json()
                    st.markdown(f"**Answer / Відповідь:**\n{result['answer']}")
                    st.markdown("---")
                    st.markdown(f"**Context / Контекст:**\n{result['context']}")
                else:
                    st.error(f"Backend error: {response.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")

st.markdown("---")
st.markdown("Demo powered by T4PUA data, legal documents, and OpenAI LLM. [Source](https://t4pua.org/stats)") 