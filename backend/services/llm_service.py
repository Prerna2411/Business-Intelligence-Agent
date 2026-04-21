from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from groq import Groq

from backend.app.config import Settings


@dataclass
class LLMResponse:
    content: str
    mock: bool = False


class LLMService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._client = Groq(api_key=settings.groq_api_key) if settings.groq_api_key else None

    @property
    def is_available(self) -> bool:
        return self._client is not None

    def invoke(self, system_prompt: str, user_prompt: str, temperature: float = 0.1) -> LLMResponse:
        if not self._client:
            return LLMResponse(content="", mock=True)

        try:
            response = self._client.chat.completions.create(
                model=self.settings.groq_model,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
        except Exception:
            return LLMResponse(content="", mock=True)

        return LLMResponse(content=response.choices[0].message.content or "", mock=False)

    def invoke_json(
        self,
        system_prompt: str,
        user_prompt: str,
        fallback: dict[str, Any],
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        response = self.invoke(system_prompt=system_prompt, user_prompt=user_prompt, temperature=temperature)
        if response.mock:
            return fallback

        text = response.content.strip()
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
        if not match:
            return fallback

        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            return fallback
