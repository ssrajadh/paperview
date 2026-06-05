"""TTS providers: a uniform synth interface over local + cloud engines.

Each provider adapts one engine to `render(text, voice, speed, path)`, writing a single WAV.
Kokoro (local, ONNX, 82M) is the default — best naturalness for the footprint. ElevenLabs
(cloud, paid, BYO key) is the "sounds human" upgrade.

Heavy deps (onnx runtimes, http clients, numpy) import lazily inside `render`, so non-TTS
commands — and an all-cache-hit `tts` run — never load an engine. Provider *metadata* (the
class attributes below) stays import-light so `schema.py` can validate plans cheaply.

Add a provider by subclassing TTSProvider and listing it in `_REGISTRY`.
"""
from __future__ import annotations

import os
import urllib.request
from pathlib import Path


def _download(url: str, dest: Path) -> None:
    """Fetch `url` to `dest` once (skip if present), via an atomic temp-rename."""
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    urllib.request.urlretrieve(url, tmp)
    tmp.rename(dest)


class TTSProvider:
    """One TTS engine. Subclasses set the metadata and implement `render`."""

    id: str = ""               # stable key used in meta.provider / --provider / cache key
    label: str = ""            # human description for `ppv tts --list-voices` / doctor
    is_local: bool = True
    requires_api_key: bool = False
    api_key_env: str = ""      # env var that holds the key (cloud providers)
    voices: tuple[str, ...] = ()   # known voices for validation + listing
    default_voice: str = ""
    validate_voice: bool = True    # cloud voices are account-specific -> skip strict check
    pip: str = ""              # package name, for doctor's import check

    def version(self) -> str:
        """Engine version string; folded into the cache key so an upgrade re-synths."""
        return "unknown"

    def fingerprint(self, voice: str, speed: float) -> str:
        """The provider-specific portion of a scene's cache key (everything but the text):
        engine version + the knobs that change the waveform."""
        return f"{self.id}{self.version()}|{voice}|{speed}"

    def render(self, text: str, voice: str, speed: float, path: str) -> None:
        """Synthesize `text` and write a WAV to `path`. Implemented per provider so each
        owns its own sample rate / audio handling (no rate guessing across engines)."""
        raise NotImplementedError


def _pkg_version(name: str) -> str:
    from importlib.metadata import PackageNotFoundError, version
    try:
        return version(name)
    except PackageNotFoundError:
        return "unknown"


class KokoroProvider(TTSProvider):
    id = "kokoro"
    label = "Kokoro 82M (local, ONNX) — best local quality, ~2x realtime, runs on CPU"
    pip = "kokoro_onnx"
    # American (a*) + British (b*) English; f=female, m=male. Audition with `ppv tts --voice`.
    voices = ("af_heart", "af_bella", "af_nicole", "af_sarah", "af_sky",
              "am_adam", "am_michael", "am_onyx",
              "bf_emma", "bf_isabella", "bm_george", "bm_lewis")
    default_voice = "af_heart"
    lang = "en-us"
    # Official kokoro-onnx model files (the .bin packs all voices). Cached under
    # ~/.cache/kokoro-onnx and downloaded once on first synthesis.
    _REL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
    MODEL_URL = f"{_REL}/kokoro-v1.0.onnx"
    VOICES_URL = f"{_REL}/voices-v1.0.bin"

    def __init__(self) -> None:
        self._k = None

    def version(self) -> str:
        return _pkg_version("kokoro-onnx")

    def _engine(self):
        if self._k is None:
            from kokoro_onnx import Kokoro
            cache = Path.home() / ".cache" / "kokoro-onnx"
            model, voices = cache / "kokoro-v1.0.onnx", cache / "voices-v1.0.bin"
            _download(self.MODEL_URL, model)
            _download(self.VOICES_URL, voices)
            self._k = Kokoro(str(model), str(voices))
        return self._k

    def render(self, text, voice, speed, path):
        import numpy as np
        import soundfile as sf
        samples, sr = self._engine().create(text, voice=voice, speed=speed, lang=self.lang)
        sf.write(path, np.asarray(samples).squeeze(), sr)


class ElevenLabsProvider(TTSProvider):
    id = "elevenlabs"
    label = "ElevenLabs (cloud, paid, BYO key) — most natural; set ELEVENLABS_API_KEY"
    pip = "elevenlabs"
    is_local = False
    requires_api_key = True
    api_key_env = "ELEVENLABS_API_KEY"
    validate_voice = False           # voices are account-specific; accept any voice id
    default_voice = "21m00Tcm4TlvDq8ikWAM"  # "Rachel", a stock voice on every account
    model = "eleven_multilingual_v2"
    # Request raw PCM (not mp3) so decoding needs no extra codec — 24 kHz is on every tier.
    sample_rate = 24000

    def __init__(self) -> None:
        self._client = None

    def version(self) -> str:
        # the model id changes the audio (and the bill) -> part of the cache key
        return f"{_pkg_version('elevenlabs')}/{self.model}"

    def _client_(self):
        if self._client is None:
            key = os.environ.get(self.api_key_env)
            if not key:
                raise RuntimeError(
                    f"the '{self.id}' provider needs an API key — set {self.api_key_env}")
            from elevenlabs.client import ElevenLabs
            self._client = ElevenLabs(api_key=key)
        return self._client

    def render(self, text, voice, speed, path):
        import numpy as np
        import soundfile as sf
        audio = self._client_().text_to_speech.convert(
            voice_id=voice, model_id=self.model, text=text,
            output_format=f"pcm_{self.sample_rate}",
        )
        raw = audio if isinstance(audio, (bytes, bytearray)) else b"".join(audio)
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        sf.write(path, samples, self.sample_rate)


_REGISTRY: dict[str, type[TTSProvider]] = {
    p.id: p for p in (KokoroProvider, ElevenLabsProvider)
}
DEFAULT_PROVIDER = KokoroProvider.id

_instances: dict[str, TTSProvider] = {}


def get_provider(pid: str | None) -> TTSProvider:
    """Return a (cached) provider instance. Construction is cheap — the heavy engine is
    built lazily on the first `render`."""
    pid = (pid or DEFAULT_PROVIDER).lower()
    if pid not in _REGISTRY:
        raise ValueError(f"unknown TTS provider '{pid}' (have: {', '.join(_REGISTRY)})")
    if pid not in _instances:
        _instances[pid] = _REGISTRY[pid]()
    return _instances[pid]


def provider_ids() -> list[str]:
    return list(_REGISTRY)


def provider_meta(pid: str) -> type[TTSProvider]:
    """The provider *class* (metadata only — voices/default/flags) without instantiating."""
    return _REGISTRY[pid]
