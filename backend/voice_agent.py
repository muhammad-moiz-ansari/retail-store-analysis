from __future__ import annotations

import base64
import json
import os
from typing import Any
from urllib import error, request


HF_ROUTER_URL = os.getenv("HF_ROUTER_URL", "https://router.huggingface.co/v1/chat/completions")
HF_MODEL = os.getenv("HF_ORCHESTRATOR_MODEL", os.getenv("HF_NLP_MODEL", "Qwen/Qwen2.5-7B-Instruct-1M"))
HF_TIMEOUT_SECONDS = int(os.getenv("HF_TIMEOUT_SECONDS", "30"))

ELEVENLABS_BASE_URL = os.getenv("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2")
ELEVENLABS_OUTPUT_FORMAT = os.getenv("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128")
ELEVENLABS_TIMEOUT_SECONDS = int(os.getenv("ELEVENLABS_TIMEOUT_SECONDS", "30"))


def integration_status() -> dict[str, Any]:
    return {
        "huggingFace": {
            "configured": bool(os.getenv("HF_TOKEN")),
            "model": HF_MODEL,
            "routerUrl": HF_ROUTER_URL,
        },
        "elevenLabs": {
            "configured": bool(os.getenv("ELEVENLABS_API_KEY")),
            "voiceId": ELEVENLABS_VOICE_ID,
            "modelId": ELEVENLABS_MODEL_ID,
            "outputFormat": ELEVENLABS_OUTPUT_FORMAT,
        },
    }


def fallback_voice_script(event: dict[str, Any], context: dict[str, Any] | None = None) -> str:
    zone = event.get("zoneName") or event.get("zone") or event.get("targetZone") or "the assigned floor zone"
    title = event.get("title") or event.get("eventType") or "store floor update"
    severity = str(event.get("severity") or "medium").lower()
    instruction = event.get("instruction") or "Please check the area and assist customers who may need help."
    active_alerts = 0
    if context:
        active_alerts = int(context.get("activeAlerts") or 0)
    opening = "Team update."
    if severity == "high":
        opening = "Priority floor update."
    return (
        f"{opening} {title} has been detected in {zone}. "
        f"{instruction} "
        f"There are currently {active_alerts} active alerts in the store. "
        "Acknowledge the task when you are on the way, and keep the floor lead updated."
    )


def build_voice_prompt(event: dict[str, Any], context: dict[str, Any] | None = None) -> list[dict[str, str]]:
    context = context or {}
    system = (
        "You are RetailPulse's NLP agent. Generate concise voice-agent scripts for in-store retail staff. "
        "The script must be spoken aloud over a headset or phone call. Use plain, calm language. "
        "Avoid markdown, bullets, stage directions, private implementation details, and scary wording. "
        "Keep it between 35 and 70 words."
    )
    user = {
        "event": event,
        "storeContext": context,
        "task": "Write the exact voice script the ElevenLabs voice agent should speak.",
    }
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": json.dumps(user, ensure_ascii=True)},
    ]


def call_hugging_face(messages: list[dict[str, str]], max_tokens: int = 180) -> str:
    token = os.getenv("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN is not configured")

    payload = {
        "model": HF_MODEL,
        "messages": messages,
        "temperature": 0.35,
        "max_tokens": max_tokens,
    }
    req = request.Request(
        HF_ROUTER_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=HF_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Hugging Face request failed: {exc.code} {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"Hugging Face request failed: {exc.reason}") from exc

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("Hugging Face returned no choices")
    message = choices[0].get("message") or {}
    content = str(message.get("content") or "").strip()
    if not content:
        raise RuntimeError("Hugging Face returned an empty script")
    return content


def generate_voice_script(event: dict[str, Any], context: dict[str, Any] | None = None) -> dict[str, Any]:
    messages = build_voice_prompt(event, context)
    try:
        script = call_hugging_face(messages)
        return {"script": script, "provider": "huggingface", "fallback": False}
    except RuntimeError as exc:
        return {
            "script": fallback_voice_script(event, context),
            "provider": "local-fallback",
            "fallback": True,
            "reason": str(exc),
        }


def synthesize_voice(script: str) -> dict[str, Any]:
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        return {
            "audioBase64": None,
            "contentType": "audio/mpeg",
            "provider": "not-configured",
            "fallback": True,
            "reason": "ELEVENLABS_API_KEY is not configured",
        }

    url = (
        f"{ELEVENLABS_BASE_URL.rstrip('/')}/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
        f"?output_format={ELEVENLABS_OUTPUT_FORMAT}"
    )
    payload = {"text": script, "model_id": ELEVENLABS_MODEL_ID}
    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "xi-api-key": api_key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=ELEVENLABS_TIMEOUT_SECONDS) as response:
            audio = response.read()
            content_type = response.headers.get("content-type") or "audio/mpeg"
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {
            "audioBase64": None,
            "contentType": "audio/mpeg",
            "provider": "elevenlabs",
            "fallback": True,
            "reason": f"ElevenLabs request failed: {exc.code} {detail}",
        }
    except error.URLError as exc:
        return {
            "audioBase64": None,
            "contentType": "audio/mpeg",
            "provider": "elevenlabs",
            "fallback": True,
            "reason": f"ElevenLabs request failed: {exc.reason}",
        }

    return {
        "audioBase64": base64.b64encode(audio).decode("ascii"),
        "contentType": content_type,
        "provider": "elevenlabs",
        "fallback": False,
    }
