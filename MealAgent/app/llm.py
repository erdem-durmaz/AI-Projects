import json
import re
from groq import Groq
from app.config import settings


class GroqLLM:
    def __init__(self):
        self.client = Groq(api_key=settings.groq_api_key)
        self.model = settings.groq_model

    def chat(self, system: str, user: str, temperature: float = 0.2) -> str:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    def json_chat(self, system: str, user: str, temperature: float = 0.1):
        raw = self.chat(system=system, user=user, temperature=temperature)
        return self._extract_json(raw)

    def _extract_json(self, text: str):
        text = text.strip()

        try:
            return json.loads(text)
        except Exception:
            pass

        match = re.search(r"(\[.*\]|\{.*\})", text, re.DOTALL)
        if not match:
            raise ValueError(f"JSON bulunamadı. Model cevabı: {text}")

        return json.loads(match.group(1))