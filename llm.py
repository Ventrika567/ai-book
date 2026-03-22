import asyncio
import json
import os
from typing import Any, Dict, List, Optional

from openai import OpenAI

from config import LLM_MODEL, EXTRACT_SYLLABUS_MODEL

_api_key = os.getenv("OPENAI_API_KEY")
if not _api_key:
    raise RuntimeError("OPENAI_API_KEY is missing. Put it in your .env file.")

client = OpenAI(api_key=_api_key)


async def call_llm_structured(
    system_prompt: str,
    user_prompt: str,
    schema: Dict[str, Any],
    schema_name: str,
) -> Dict[str, Any]:
    """Call gpt-4o-mini with structured JSON output. Runs sync client in a thread."""

    def _sync_call() -> Dict[str, Any]:
        response = client.responses.create(
            model=EXTRACT_SYLLABUS_MODEL,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                }
            },
        )
        return json.loads(response.output_text)

    return await asyncio.to_thread(_sync_call)


async def call_llm_text(
    system_prompt: str,
    user_prompt: str,
    chat_history: Optional[List[Dict[str, str]]] = None,
) -> str:
    """Call gpt-5-mini for free-text response (e.g. chat/study planner)."""

    def _sync_call() -> str:
        messages = []
        messages.append({"role": "system", "content": system_prompt})
        if chat_history:
            messages.extend(chat_history)
        messages.append({"role": "user", "content": user_prompt})

        response = client.responses.create(
            model=LLM_MODEL,
            input=messages,
        )
        return response.output_text.strip()

    return await asyncio.to_thread(_sync_call)
