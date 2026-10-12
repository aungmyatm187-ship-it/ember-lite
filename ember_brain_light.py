"""
Ember Brain - Lightweight API Orchestrator
===========================================
No heavy frameworks. Pure Python.
Zero-Dependency LLM integration.
"""

import os
import json
import urllib.request
import urllib.error

class EmberBrainLight:
    """Ember's lightweight brain - direct API calls."""

    # Free models on OpenRouter, ordered by priority.
    # Verified working 2026-10-13.
    # OpenRouter rotates its free pool weekly, so this list will need occasional updates.
    FREE_MODELS = [
        "nvidia/nemotron-3-ultra-550b-a55b:free",
        "poolside/laguna-s-2.1:free",
    ]

    API_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, provider="openrouter"):
        self.provider = provider
        self.api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not self.api_key:
            raise ValueError(
                "OPENROUTER_API_KEY not set. "
                "Run: export OPENROUTER_API_KEY='your-key'"
            )

    def _build_system_prompt(self, identity, context=""):
        """Build a system prompt from Ember's identity dict and optional context."""
        base = "You are Ember Signal, a helpful AI assistant focused on evidence-based decisions."
        if identity and isinstance(identity, dict):
            parts = []
            if identity.get("name"):
                parts.append(f"You are {identity['name']}.")
            if identity.get("tagline"):
                parts.append(f"Tagline: {identity['tagline']}")
            p = identity.get("personality", {}) or {}
            if p.get("archetype"):
                parts.append(f"Archetype: {p['archetype']}")
            if p.get("description"):
                parts.append(str(p["description"]))
            if p.get("values"):
                parts.append("Values: " + "; ".join(map(str, p["values"])))
            if parts:
                base = " ".join(parts)
        if context:
            base += f"\n\nCURRENT CONTEXT:\n{context}"
        return base

    def _call_one(self, model, system_prompt, user_message):
        """Call a single model. Returns (ok: bool, content_or_error: str)."""
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            "temperature": 0.7,
            "max_tokens": 1024,
        }
        req = urllib.request.Request(
            self.API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choices = data.get("choices") or []
                if not choices:
                    return False, "no choices in response"
                content = choices[0].get("message", {}).get("content") or ""
                if not content.strip():
                    return False, "empty content"
                return True, content
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")[:120]
            return False, f"HTTP {e.code}: {body}"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"

    def think(self, user_message: str, identity: dict = None, context: str = "") -> str:
        """Ask the LLM and return its answer. Tries each free model in order."""
        system_prompt = self._build_system_prompt(identity, context)
        errors = []
        for model in self.FREE_MODELS:
            ok, result = self._call_one(model, system_prompt, user_message)
            if ok:
                return result
            errors.append(f"  - {model}: {result}")
        return "All free models failed:\n" + "\n".join(errors)


if __name__ == "__main__":
    try:
        brain = EmberBrainLight()
        print("✅ Ember Brain Light is online.")
        print(brain.think("Who are you?"))
    except ValueError as e:
        print(e)
