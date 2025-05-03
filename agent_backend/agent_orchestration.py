import os
from dotenv import load_dotenv
from langchain.agents import initialize_agent, AgentType, Tool
from langchain_core.language_models.llms import LLM
from typing import List, ClassVar
import requests
import subprocess

# ─── CHARGEMENT DES VARIABLES D'ENV ────────────────────────────────────────────
load_dotenv()  # lit le .env
SERPAPI_API_KEY = os.getenv("SERPAPI_API_KEY")
if not SERPAPI_API_KEY:
    raise RuntimeError("La variable d'environnement SERPAPI_API_KEY n'est pas définie")

# ─── TOOL 1: SerpAPI ──────────────────────────────────────────────────────────
def fetch_news(query: str) -> str:
    """Interroge SerpAPI et renvoie les 5 premiers titres+snippets."""
    res = requests.get(
        "https://serpapi.com/search.json",
        params={"q": query, "api_key": SERPAPI_API_KEY}
    )
    res.raise_for_status()
    results = res.json().get("organic_results", [])[:5]
    return "\n\n".join(
        f"Titre: {r['title']}\nSnippet: {r['snippet']}"
        for r in results
        if "title" in r and "snippet" in r
    ) or "Aucune actualité trouvée."

# ─── TOOL 2: Summarizer ────────────────────────────────────────────────────────
def summarize_text(text: str) -> str:
    """Appelle Ollama pour résumer un texte donné."""
    prompt = "Résumé en quelques phrases de ce texte :\n\n" + text
    result = subprocess.run(
        ["ollama", "run", "gemma3", prompt],
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        raise RuntimeError(f"Ollama error: {result.stderr}")
    return result.stdout.strip()

# ─── WRAPPER LLM ──────────────────────────────────────────────────────────────
class WrapperLLM(LLM):
    model: ClassVar[str] = "gemma3"

    def _call(self, prompt: str, stop: List[str] = None) -> str:
        result = subprocess.run(
            ["ollama", "run", self.model, prompt],
            capture_output=True, text=True, timeout=60
        )
        if result.returncode != 0:
            raise RuntimeError(f"Ollama error: {result.stderr}")
        return result.stdout.strip()

    @property
    def _llm_type(self) -> str:
        return "ollama"

# ─── DECLARATION DES TOOLS ───────────────────────────────────────────────────
tools = [
    Tool(
        name="SerpAPI",
        func=fetch_news,
        description="Récupère les dernières actualités locales en Île-de-France"
    ),
    Tool(
        name="Summarizer",
        func=summarize_text,
        description="Prend un texte et renvoie un résumé concis"
    )
]

# ─── INITIALISATION DE L'AGENT ReAct ───────────────────────────────────────────
agent = initialize_agent(
    tools=tools,
    llm=WrapperLLM(),
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True,
    handle_parsing_errors=True,
    return_only_outputs=True,
    max_iterations=5,
    early_stopping_method="generate",
    agent_kwargs={
        "prefix": (
            "Tu es un agent ReAct qui dispose de deux outils :\n"
            "1) SerpAPI(query) → pour collecter des extraits d'actualités\n"
            "2) Summarizer(text) → pour résumer un texte brut\n\n"
            "Lorsque tu traites une requête utilisateur :\n"
            "- Réfléchis à haute voix avec `Thought:`\n"
            "- Choisis un outil avec `Action:`\n"
            "- Fournis l’argument avec `Action Input:`\n"
            "- Observe sa réponse avec `Observation:`\n"
            "- Quand tu as terminé, rends ton `Final Answer:`\n"
        ),
        "suffix": (
            "N'inclus plus aucun `Thought:` ni `Action:` après `Final Answer:`."
        ),
        "input_variables": ["input", "agent_scratchpad"]
    }
)
