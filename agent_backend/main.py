# agent_backend/main.py

import subprocess
import difflib
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
from pydantic import BaseModel

from agent_backend import models, database
from agent_backend.agent_orchestration import agent, fetch_news

models.Base.metadata.create_all(bind=database.engine)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_summary_to_db(summary_text: str, db: Session) -> str:
    latest = db.query(models.Summary).order_by(models.Summary.created_at.desc()).first()
    if latest:
        ratio = difflib.SequenceMatcher(None, latest.content, summary_text).ratio()
        if ratio > 0.9:
            return "Résumé similaire détecté. Non enregistré."
    rec = models.Summary(title="Résumé via agent intelligent", content=summary_text)
    db.add(rec); db.commit(); db.refresh(rec)
    return "Résumé généré et sauvegardé via agent."

class Snippet(BaseModel):
    title: str
    snippet: str

class SummarizeInput(BaseModel):
    snippets: list[Snippet]

@app.get("/summaries")
def get_summaries(limit: int = 10, db: Session = Depends(get_db)):
    return db.query(models.Summary).order_by(models.Summary.created_at.desc()).limit(limit).all()

@app.post("/summarize")
def summarize_and_save(data: SummarizeInput, db: Session = Depends(get_db)):
    parts = [f"Titre : {s.title}\nSnippet : {s.snippet}" for s in data.snippets]
    prompt = (
        "Voici des extraits d’actualités locales pour l’Île-de-France.\n"
        "Résume les événements importants, contacts et services :\n\n"
        + "\n---\n".join(parts)
    )
    try:
        result = subprocess.run(
            ["ollama", "run", "gemma3", prompt],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            raise RuntimeError(result.stderr)
        summary = result.stdout.strip()
    except Exception as e:
        raise HTTPException(500, detail=f"Ollama error: {e}")
    return {"message": save_summary_to_db(summary, db), "summary": summary}

@app.post("/serp-summarize")
def serp_and_summarize(db: Session = Depends(get_db)):
    # fallback simple pipeline
    try:
        raw = fetch_news("événements Île-de-France site:leparisien.fr")
    except Exception as e:
        raise HTTPException(500, detail=f"Erreur SerpAPI: {e}")
    snippets = [{"title": "Actu", "snippet": part} for part in raw.split("\n\n") if part.strip()]
    return summarize_and_save(SummarizeInput(snippets=snippets), db)

@app.post("/serp-agent")
def serp_agent(db: Session = Depends(get_db)):
    """
    Résumé via l'agent ReAct (deux outils : SerpAPI + Summarizer).
    On récupère tout le trace LLM puis on extrait la partie après 'Final Answer:'.
    """
    try:
        # Invocation de l’agent (return_only_outputs=True doit être activé à l'initialisation)
        result = agent.invoke({
            "input": "Donne-moi un résumé complet des actualités locales en Île-de-France."
        })
        full_text = result.get("output", "")
        # Extraction de la partie qui suit 'Final Answer:'
        if "Final Answer:" in full_text:
            summary = full_text.split("Final Answer:")[-1].strip()
        else:
            summary = full_text.strip()
    except Exception as e:
        raise HTTPException(500, detail=f"Agent error: {e}")

    msg = save_summary_to_db(summary, db)
    return {"message": msg, "summary": summary}


def autonomous_agent():
    print("🔁 Résumé automatique quotidien via agent ReAct...")
    with database.SessionLocal() as db:
        try:
            out = agent.invoke({"input": "Donne-moi un résumé complet des actualités locales en Île-de-France."})
            summary = out.get("output", "")
            save_summary_to_db(summary, db)
        except Exception as e:
            print("⚠️ Erreur agent auto:", e)

scheduler = BackgroundScheduler()
scheduler.add_job(autonomous_agent, "cron", hour=6, minute=0)
scheduler.start()
