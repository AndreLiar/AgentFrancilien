#agent_backend/ollama_wrapper.py
class OllamaLLM:
    model = "gemma3"

    def __call__(self, prompt: str) -> str:
        import subprocess
        result = subprocess.run(["ollama", "run", self.model, prompt], capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            raise RuntimeError(f"Ollama error: {result.stderr}")
        return result.stdout.strip()

