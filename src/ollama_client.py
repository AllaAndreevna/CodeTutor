"""Robust client for the local Ollama HTTP API."""

from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

from src.config import OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)

# Windows often resolves localhost to IPv6; Ollama may listen on IPv4 only.
OLLAMA_BASE_URLS = list(
    dict.fromkeys(
        [
            OLLAMA_BASE_URL,
            "http://127.0.0.1:11434",
            "http://localhost:11434",
        ]
    )
)


@dataclass
class OllamaStatus:
    """Result of an Ollama health check."""

    available: bool
    base_url: str
    model: str
    message: str


def check_ollama_status(model: str = OLLAMA_MODEL) -> OllamaStatus:
    """Check whether Ollama is reachable and the configured model is present."""
    last_error = "unknown error"
    for base_url in OLLAMA_BASE_URLS:
        try:
            response = requests.get(f"{base_url}/api/tags", timeout=5)
            response.raise_for_status()
            tags = response.json().get("models", [])
            names = {m.get("name", "") for m in tags}
            # Match exact name or name without tag variant
            model_ok = model in names or any(n.startswith(f"{model}:") or n == model for n in names)
            if model_ok:
                return OllamaStatus(
                    available=True,
                    base_url=base_url,
                    model=model,
                    message="Ollama is running.",
                )
            return OllamaStatus(
                available=False,
                base_url=base_url,
                model=model,
                message=f"Ollama is running but model '{model}' is not installed. Run: ollama pull {model}",
            )
        except requests.RequestException as exc:
            last_error = str(exc)
            continue

    return OllamaStatus(
        available=False,
        base_url=OLLAMA_BASE_URL,
        model=model,
        message=f"Cannot connect to Ollama. Start the Ollama app, then run: ollama pull {model}. ({last_error})",
    )


def generate(prompt: str, system_prompt: str, model: str = OLLAMA_MODEL, timeout: int = 180) -> str:
    """
    Call Ollama and return generated text.

    Tries /api/chat first (better for instruct models), then /api/generate.
    Tries multiple base URLs for Windows localhost/IPv4 compatibility.
    """
    last_error: Exception | None = None

    for base_url in OLLAMA_BASE_URLS:
        for endpoint, payload, extract in (
            (
                "chat",
                {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": False,
                },
                lambda data: data.get("message", {}).get("content", ""),
            ),
            (
                "generate",
                {
                    "model": model,
                    "prompt": prompt,
                    "system": system_prompt,
                    "stream": False,
                },
                lambda data: data.get("response", ""),
            ),
        ):
            try:
                response = requests.post(
                    f"{base_url}/api/{endpoint}",
                    json=payload,
                    timeout=timeout,
                )
                response.raise_for_status()
                text = extract(response.json()).strip()
                if text:
                    logger.info("Ollama response via %s /api/%s", base_url, endpoint)
                    return text
            except requests.RequestException as exc:
                last_error = exc
                logger.debug("Ollama %s /api/%s failed: %s", base_url, endpoint, exc)

    raise ConnectionError(last_error or "Ollama unavailable")
