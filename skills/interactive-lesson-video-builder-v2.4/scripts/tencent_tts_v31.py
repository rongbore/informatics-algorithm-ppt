"""Tencent Cloud TTS adapter with a persistent, fail-closed free-tier budget."""
from __future__ import annotations
import base64, json, os, threading, uuid
from pathlib import Path

_LOCK = threading.Lock()

def _int_env(name: str, default: int = 0) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be a non-negative integer") from exc
    if value < 0:
        raise RuntimeError(f"{name} must be a non-negative integer")
    return value

def free_tier_ready() -> tuple[bool, str]:
    required = {
        "TENCENT_TTS_ALLOW_FREE_TIER": "true",
        "TENCENT_TTS_POSTPAID_DISABLED": "true",
    }
    for key, expected in required.items():
        if os.getenv(key, "").strip().lower() != expected:
            return False, f"{key}=true is required; cloud synthesis remains disabled"
    if not os.getenv("TENCENTCLOUD_SECRET_ID", "").strip():
        return False, "TENCENTCLOUD_SECRET_ID is missing"
    if not os.getenv("TENCENTCLOUD_SECRET_KEY", "").strip():
        return False, "TENCENTCLOUD_SECRET_KEY is missing"
    if _int_env("TENCENT_TTS_FREE_BUDGET_CHARS", 0) <= 0:
        return False, "TENCENT_TTS_FREE_BUDGET_CHARS is zero; verify remaining free quota first"
    return True, "free-tier guard ready"

def _ledger_path() -> Path:
    configured = os.getenv("TENCENT_TTS_BUDGET_STATE", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".lesson-video-builder" / "tencent_tts_budget_v31.json"

def _load_ledger(path: Path, limit: int) -> dict:
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1:
            raise RuntimeError("Unsupported Tencent TTS budget ledger schema")
        previous_limit = int(data.get("budget_limit_chars", 0))
        used = int(data.get("reserved_chars", 0))
        if limit < used:
            raise RuntimeError("Configured Tencent free budget is below already-reserved usage")
        if limit < previous_limit:
            data["budget_limit_chars"] = limit
        elif limit > previous_limit:
            data["budget_limit_chars"] = limit
        return data
    return {"schema_version": 1, "budget_limit_chars": limit, "reserved_chars": 0, "requests": 0}

def reserve_free_chars(chars: int) -> dict:
    """Reserve before network call. Reservations are never refunded after uncertain failures."""
    if chars <= 0:
        raise ValueError("chars must be positive")
    limit = _int_env("TENCENT_TTS_FREE_BUDGET_CHARS", 0)
    if limit <= 0:
        raise RuntimeError("Tencent free-tier budget is not configured")
    path = _ledger_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        data = _load_ledger(path, limit)
        used = int(data["reserved_chars"])
        if used + chars > limit:
            raise RuntimeError(f"Tencent free-tier budget guard: request {chars} chars would exceed configured cap {limit-used} remaining")
        data["reserved_chars"] = used + chars
        data["requests"] = int(data.get("requests", 0)) + 1
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
        return {"reserved_chars": chars, "used_chars": used + chars, "budget_limit_chars": limit,
                "remaining_chars": limit - used - chars, "ledger": str(path)}

def synthesize_wav(text: str, out_path: str | Path, *, voice_type: int | None = None,
                   speed: float = 0.2, volume: float = 0.0, emotion: str = "") -> dict:
    ready, reason = free_tier_ready()
    if not ready:
        raise RuntimeError(f"Tencent cloud disabled by zero-billing guard: {reason}")
    if len(text) > 150:
        raise ValueError("Tencent TextToVoice supports at most 150 Chinese characters per request; split text first")
    reservation = reserve_free_chars(len(text))
    try:
        from tencentcloud.common import credential
        from tencentcloud.common.profile.client_profile import ClientProfile
        from tencentcloud.common.profile.http_profile import HttpProfile
        from tencentcloud.tts.v20190823 import models, tts_client
    except ImportError as exc:
        raise RuntimeError("Install optional SDK: pip install tencentcloud-sdk-python-tts") from exc

    secret_id = os.environ["TENCENTCLOUD_SECRET_ID"].strip()
    secret_key = os.environ["TENCENTCLOUD_SECRET_KEY"].strip()
    region = os.getenv("TENCENT_TTS_REGION", "ap-guangzhou").strip()
    voice = int(voice_type if voice_type is not None else _int_env("TENCENT_TTS_VOICE_TYPE", 1001))
    request_data = {
        "Text": text,
        "SessionId": str(uuid.uuid4()),
        "Volume": float(volume),
        "Speed": float(speed),
        "ProjectId": 0,
        "ModelType": 1,
        "VoiceType": voice,
        "PrimaryLanguage": 1,
        "SampleRate": 24000,
        "Codec": "wav",
        "EnableSubtitle": True,
    }
    if emotion:
        request_data["EmotionCategory"] = emotion
        request_data["EmotionIntensity"] = _int_env("TENCENT_TTS_EMOTION_INTENSITY", 115)

    # No automatic retry: avoid duplicate billable requests after uncertain network failures.
    cred = credential.Credential(secret_id, secret_key)
    http_profile = HttpProfile()
    http_profile.endpoint = "tts.tencentcloudapi.com"
    client_profile = ClientProfile()
    client_profile.httpProfile = http_profile
    client = tts_client.TtsClient(cred, region, client_profile)
    request = models.TextToVoiceRequest()
    request.from_json_string(json.dumps(request_data, ensure_ascii=False))
    response = client.TextToVoice(request)
    audio = getattr(response, "Audio", "")
    if not audio:
        raise RuntimeError("Tencent TTS returned empty audio")
    payload = base64.b64decode(audio)
    if len(payload) < 128:
        raise RuntimeError("Tencent TTS returned an invalid/empty WAV payload")
    destination = Path(out_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    return {"path": str(destination), "bytes": len(payload), "voice_type": voice,
            "region": region, "request_id": getattr(response, "RequestId", None),
            "budget": reservation}

def budget_status() -> dict:
    limit = _int_env("TENCENT_TTS_FREE_BUDGET_CHARS", 0)
    path = _ledger_path()
    data = _load_ledger(path, limit) if path.exists() else {
        "budget_limit_chars": limit, "reserved_chars": 0, "requests": 0
    }
    return {"configured_budget_chars": limit, "reserved_chars": int(data.get("reserved_chars", 0)),
            "remaining_configured_chars": max(0, limit-int(data.get("reserved_chars", 0))),
            "ledger_path": str(path)}
