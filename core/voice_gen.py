"""Text-to-speech generation using Kokoro, ElevenLabs, Chatterbox, or OpenAI."""

import os
import re
from pathlib import Path
from typing import Literal

import replicate
import requests
import soundfile as sf

from core.rate_limiter import NonRetryableError, elevenlabs_limiter, openai_limiter, image_limiter
from core.runtime import available_tts_providers

# ElevenLabs voices - curated selection for narration
# Full library at: https://elevenlabs.io/voice-library
ELEVENLABS_VOICES = {
    # Female voices
    "Rachel": ("21m00Tcm4TlvDq8ikWAM", "Warm, calm female - great for explainers"),
    "Bella": ("hpp4J3VqNfWAUOO0d1Us", "Professional, bright, warm female"),
    "Elli": ("MF3mGyEYCl7XYWbV9V6O", "Young, energetic female"),
    "Domi": ("AZnzlk1XvdvUeBnXmlld", "Strong, confident female"),
    # Male voices
    "Antoni": ("ErXwobaYiN019PkySvjV", "Calm, professional male"),
    "Josh": ("TxGEqnHWrfWFTfGW9XjX", "Deep, authoritative male"),
    "Adam": ("pNInz6obpgDQGcFmaJgB", "Deep, warm male"),
    "Arnold": ("VR6AewLTigWG4xSOukaG", "Bold, energetic male"),
    "George": ("JBFqnCBsd6RMkjVDRZzb", "Warm, captivating British male storyteller"),
    "Daniel": ("onwK4e9ZLuTAKqWW03F9", "Steady, measured British male broadcaster"),
}

DEFAULT_ELEVENLABS_VOICE = "Bella"
DEFAULT_ELEVENLABS_MODEL = "eleven_multilingual_v2"  # Higher-fidelity default for polished narrated videos

# Default ElevenLabs voice settings for a richer, more deliberate explainer voice
DEFAULT_ELEVENLABS_STABILITY = 0.38
DEFAULT_ELEVENLABS_SIMILARITY_BOOST = 0.8
DEFAULT_ELEVENLABS_STYLE = 0.65
DEFAULT_ELEVENLABS_SPEED = 1.0
DEFAULT_ELEVENLABS_USE_SPEAKER_BOOST = True
DEFAULT_REPLICATE_ELEVENLABS_MODEL = "elevenlabs/turbo-v2.5"

REPLICATE_ELEVENLABS_VOICE_MAP = {
    "Rachel": "Rachel",
    "Bella": "Sarah",
    "Elli": "Hope",
    "Domi": "Domi",
    "Antoni": "James",
    "Josh": "Roger",
    "Adam": "Bradford",
    "Arnold": "Mark",
    "George": "Reginald",
    "Daniel": "Reginald",
}

ElevenLabsTextNormalization = Literal["auto", "on", "off"]
DEFAULT_ELEVENLABS_TEXT_NORMALIZATION: ElevenLabsTextNormalization = "auto"

# Available Kokoro voices
# American English (lang_code='a'):
#   Female: af_alloy, af_aoede, af_bella, af_heart, af_jessica, af_kore, af_nicole, af_nova, af_river, af_sarah, af_sky
#   Male: am_adam, am_michael
# British English (lang_code='b'):
#   Female: bf_emma, bf_isabella
#   Male: bm_george, bm_lewis

KOKORO_VOICES = {
    # American female - sorted by energy/upbeat quality
    "af_bella": "Warm, friendly, upbeat female",
    "af_sarah": "Clear, enthusiastic female",
    "af_heart": "Gentle, reassuring female (default)",
    "af_nicole": "Professional, confident female",
    "af_jessica": "Bright, energetic female",
    "af_nova": "Modern, dynamic female",
    "af_sky": "Light, airy female",
    "af_alloy": "Neutral, clear female",
    "af_aoede": "Melodic, expressive female",
    "af_kore": "Youthful, fresh female",
    "af_river": "Smooth, flowing female",
    # American male
    "am_adam": "Warm, friendly male",
    "am_michael": "Clear, professional male",
    # British female
    "bf_emma": "Warm British female",
    "bf_isabella": "Elegant British female",
    # British male
    "bm_george": "Classic British male",
    "bm_lewis": "Modern British male",
}

# Default settings for upbeat, engaging narration
DEFAULT_VOICE = "af_bella"  # More upbeat than af_heart
DEFAULT_SPEED = 1.1  # Slightly faster than normal
DEFAULT_EXAGGERATION = 0.6  # Slightly more expressive than neutral (0.5)

# TTS Provider type
TTSProvider = Literal["kokoro", "elevenlabs", "chatterbox", "openai"]


def _safe_float(value, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _normalize_voice_for_provider(provider: str, voice: str) -> str:
    provider_name = str(provider or "").strip().lower()
    voice_name = str(voice or "").strip()
    if provider_name == "kokoro":
        return voice_name if voice_name in KOKORO_VOICES else DEFAULT_VOICE
    if provider_name == "elevenlabs":
        return voice_name or DEFAULT_ELEVENLABS_VOICE
    if provider_name == "openai":
        return voice_name or "nova"
    return voice_name


def _normalize_voice_for_replicate_elevenlabs(voice: str) -> str:
    allowed = {
        "Rachel", "Drew", "Clyde", "Paul", "Aria", "Domi", "Dave", "Roger", "Fin", "Sarah",
        "James", "Jane", "Juniper", "Arabella", "Hope", "Bradford", "Reginald", "Gaming",
        "Austin", "Kuon", "Blondie", "Priyanka", "Alexandra", "Monika", "Mark", "Grimblewood",
    }
    voice_name = str(voice or "").strip()
    if voice_name in allowed:
        return voice_name
    return REPLICATE_ELEVENLABS_VOICE_MAP.get(voice_name, "Rachel")


def _normalize_tts_text(text: str) -> str:
    """Normalize a few known brand/style cases for better TTS pronunciation."""
    value = str(text or "")

    replacements = [
        ("MS SQL", "M.S. S.Q.L."),
        ("MLOps", "M.L. ops"),
        ("LLMs", "L.L.M.s"),
        ("LLM", "L.L.M."),
        ("APIs", "A.P.I.s"),
        ("API", "A.P.I."),
        ("KPIs", "K.P.I.s"),
        ("KPI", "K.P.I."),
        ("HTTP", "H.T.T.P."),
        ("GCP", "G.C.P."),
        ("SQL", "S.Q.L."),
        ("AML", "A.M.L."),
        ("HR", "H.R."),
        ("UK", "U.K."),
        ("AI", "A.I."),
        ("ML", "M.L."),
    ]
    for source, target in replacements:
        value = re.sub(rf"\b{re.escape(source)}\b", target, value)
    return value


def generate_audio(
    text: str,
    output_path: str | Path,
    voice: str = DEFAULT_VOICE,
    speed: float = DEFAULT_SPEED,
    tts_provider: TTSProvider = "kokoro",
    exaggeration: float = DEFAULT_EXAGGERATION,
    openai_model_id: str = "tts-1",
    # ElevenLabs settings (used when tts_provider=="elevenlabs")
    elevenlabs_model_id: str = DEFAULT_ELEVENLABS_MODEL,
    elevenlabs_apply_text_normalization: ElevenLabsTextNormalization = DEFAULT_ELEVENLABS_TEXT_NORMALIZATION,
    elevenlabs_stability: float = DEFAULT_ELEVENLABS_STABILITY,
    elevenlabs_similarity_boost: float = DEFAULT_ELEVENLABS_SIMILARITY_BOOST,
    elevenlabs_style: float = DEFAULT_ELEVENLABS_STYLE,
    elevenlabs_use_speaker_boost: bool = DEFAULT_ELEVENLABS_USE_SPEAKER_BOOST,
) -> Path:
    """
    Generate speech audio from text.

    Args:
        text: The text to convert to speech
        output_path: Where to save the audio file
        voice: Voice identifier (provider-dependent: Kokoro voice id like "af_bella", or ElevenLabs voice name like "Rachel")
        speed: Speech speed multiplier (provider-dependent: Kokoro pipeline speed, or ElevenLabs voice_settings.speed)
        tts_provider: TTS provider ("kokoro", "elevenlabs", "chatterbox", or "openai")
        exaggeration: Emotion intensity 0.25-2.0 (0.5=neutral, higher=more expressive) - Chatterbox only
        elevenlabs_model_id: ElevenLabs model id (e.g., "eleven_flash_v2_5")
        elevenlabs_apply_text_normalization: ElevenLabs text normalization mode ("auto"|"on"|"off")
        elevenlabs_stability: ElevenLabs voice_settings.stability (0-1)
        elevenlabs_similarity_boost: ElevenLabs voice_settings.similarity_boost (0-1)
        elevenlabs_style: ElevenLabs voice_settings.style (0-1)
        elevenlabs_use_speaker_boost: ElevenLabs voice_settings.use_speaker_boost (bool)

    Returns:
        Path to the saved audio file
    """
    text = _normalize_tts_text(text)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    return generate_audio_result(
        text=text,
        output_path=output_path,
        voice=voice,
        speed=speed,
        tts_provider=tts_provider,
        exaggeration=exaggeration,
        openai_model_id=openai_model_id,
        elevenlabs_model_id=elevenlabs_model_id,
        elevenlabs_apply_text_normalization=elevenlabs_apply_text_normalization,
        elevenlabs_stability=elevenlabs_stability,
        elevenlabs_similarity_boost=elevenlabs_similarity_boost,
        elevenlabs_style=elevenlabs_style,
        elevenlabs_use_speaker_boost=elevenlabs_use_speaker_boost,
    )["path"]


def generate_audio_result(
    text: str,
    output_path: str | Path,
    voice: str = DEFAULT_VOICE,
    speed: float = DEFAULT_SPEED,
    tts_provider: TTSProvider = "kokoro",
    exaggeration: float = DEFAULT_EXAGGERATION,
    openai_model_id: str = "tts-1",
    elevenlabs_model_id: str = DEFAULT_ELEVENLABS_MODEL,
    elevenlabs_apply_text_normalization: ElevenLabsTextNormalization = DEFAULT_ELEVENLABS_TEXT_NORMALIZATION,
    elevenlabs_stability: float = DEFAULT_ELEVENLABS_STABILITY,
    elevenlabs_similarity_boost: float = DEFAULT_ELEVENLABS_SIMILARITY_BOOST,
    elevenlabs_style: float = DEFAULT_ELEVENLABS_STYLE,
    elevenlabs_use_speaker_boost: bool = DEFAULT_ELEVENLABS_USE_SPEAKER_BOOST,
) -> dict[str, object]:
    """Generate audio and return execution metadata for cost and operator logging."""
    text = _normalize_tts_text(text)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if tts_provider == "kokoro":
        try:
            path = _generate_with_kokoro(text, output_path, voice, speed)
            return {"path": path, "provider": "kokoro", "model": "kokoro-local", "voice": voice}
        except Exception as e:
            print(f"Kokoro TTS failed ({e}), falling back to OpenAI...")
            path = _generate_with_openai(text, output_path, voice="nova", model_id=openai_model_id)
            return {"path": path, "provider": "openai", "model": openai_model_id, "voice": "nova"}
    if tts_provider == "elevenlabs":
        try:
            path = _generate_with_elevenlabs(
                text=text,
                output_path=output_path,
                voice=voice,
                model_id=elevenlabs_model_id,
                stability=elevenlabs_stability,
                similarity_boost=elevenlabs_similarity_boost,
                style=elevenlabs_style,
                speed=speed,
                use_speaker_boost=elevenlabs_use_speaker_boost,
                apply_text_normalization=elevenlabs_apply_text_normalization,
            )
            return {"path": path, "provider": "elevenlabs", "model": elevenlabs_model_id, "voice": voice}
        except Exception as e:
            print(f"ElevenLabs TTS failed ({e}), trying Replicate-hosted ElevenLabs...")
            try:
                path = _generate_with_replicate_elevenlabs(
                    text=text,
                    output_path=output_path,
                    voice=voice,
                    stability=elevenlabs_stability,
                    similarity_boost=elevenlabs_similarity_boost,
                    style=elevenlabs_style,
                    speed=speed,
                )
                return {"path": path, "provider": "replicate", "model": DEFAULT_REPLICATE_ELEVENLABS_MODEL, "voice": voice}
            except Exception as replicate_exc:
                print(
                    "Replicate-hosted ElevenLabs TTS failed "
                    f"({replicate_exc}), falling back to Kokoro..."
                )
                path = _generate_with_kokoro(text, output_path, DEFAULT_VOICE, speed or DEFAULT_SPEED)
                return {"path": path, "provider": "kokoro", "model": "kokoro-local", "voice": DEFAULT_VOICE}
    if tts_provider == "chatterbox":
        path = _generate_with_chatterbox(text, output_path, exaggeration)
        return {"path": path, "provider": "replicate", "model": "resemble-ai/chatterbox", "voice": voice}
    if tts_provider == "openai":
        path = _generate_with_openai(text, output_path, voice=voice, model_id=openai_model_id)
        return {"path": path, "provider": "openai", "model": openai_model_id, "voice": voice}
    raise ValueError(f"Unknown TTS provider: {tts_provider}")


def _generate_with_kokoro(text: str, output_path: Path, voice: str, speed: float = 1.0) -> Path:
    """Generate audio using Kokoro local TTS."""
    import numpy as np
    from kokoro import KPipeline

    # Determine language code from voice prefix
    # 'a' = American English, 'b' = British English
    lang_code = "b" if voice.startswith("b") else "a"

    # Initialize pipeline
    pipeline = KPipeline(lang_code=lang_code)

    # Generate audio - new API returns (graphemes, phonemes, audio) tuples
    # speed parameter controls speech rate (1.0 = normal, 1.2 = 20% faster)
    generator = pipeline(text, voice=voice, speed=speed)

    # Collect all audio chunks
    all_audio = []
    sample_rate = 24000  # Kokoro default

    for graphemes, phonemes, audio in generator:
        all_audio.append(audio)

    # Concatenate all chunks and save
    if all_audio:
        audio_data = np.concatenate(all_audio) if len(all_audio) > 1 else all_audio[0]
        sf.write(str(output_path), audio_data, sample_rate)
    else:
        raise ValueError("No audio generated")

    return output_path


def _generate_with_chatterbox(
    text: str,
    output_path: Path,
    exaggeration: float = 0.5,
    cfg_weight: float = 0.5,
    temperature: float = 0.8,
) -> Path:
    """
    Generate audio using Chatterbox on Replicate.

    Chatterbox supports emotion control and tags like [laugh], [cough], [chuckle].

    Args:
        text: Text to synthesize (can include emotion tags)
        output_path: Where to save the audio file
        exaggeration: Emotion intensity 0.25-2.0 (0.5=neutral, higher=more expressive)
        cfg_weight: Pace/CFG weight 0.2-1.0
        temperature: Variability 0.05-5.0

    Returns:
        Path to the saved audio file
    """
    import replicate

    def _call_chatterbox():
        return replicate.run(
            "resemble-ai/chatterbox",
            input={
                "prompt": text,
                "exaggeration": exaggeration,
                "cfg_weight": cfg_weight,
                "temperature": temperature,
                "seed": 0,  # Random seed for variety
            }
        )

    # Use image_limiter since it's also Replicate
    output_url = image_limiter.call_with_retry(_call_chatterbox)

    # Download the audio file
    response = requests.get(output_url)
    response.raise_for_status()

    # Chatterbox returns WAV, save directly
    # If output_path expects WAV, write directly; otherwise handle format
    temp_path = output_path.with_suffix(".wav")
    temp_path.write_bytes(response.content)

    # If caller wanted WAV, we're done
    if output_path.suffix == ".wav":
        if temp_path != output_path:
            temp_path.rename(output_path)
        return output_path

    # Otherwise convert (though WAV is preferred)
    return temp_path


def _generate_with_replicate_elevenlabs(
    *,
    text: str,
    output_path: Path,
    voice: str = DEFAULT_ELEVENLABS_VOICE,
    stability: float = DEFAULT_ELEVENLABS_STABILITY,
    similarity_boost: float = DEFAULT_ELEVENLABS_SIMILARITY_BOOST,
    style: float = DEFAULT_ELEVENLABS_STYLE,
    speed: float = 1.0,
) -> Path:
    """Generate audio with Replicate's hosted ElevenLabs turbo model."""
    if not (os.getenv("REPLICATE_API_TOKEN") or "").strip():
        raise RuntimeError("REPLICATE_API_TOKEN is not set.")

    mapped_voice = _normalize_voice_for_replicate_elevenlabs(voice)

    def _call_replicate():
        return replicate.run(
            DEFAULT_REPLICATE_ELEVENLABS_MODEL,
            input={
                "prompt": text,
                "voice": mapped_voice,
                "speed": float(speed),
                "stability": float(stability),
                "similarity_boost": float(similarity_boost),
                "style": float(style),
                "language_code": "en",
            },
        )

    output_url = image_limiter.call_with_retry(_call_replicate)
    response = requests.get(str(output_url), timeout=(10, 180))
    response.raise_for_status()

    mp3_path = output_path.with_suffix(".mp3")
    mp3_path.write_bytes(response.content)

    if output_path.suffix == ".wav":
        _convert_mp3_to_wav(mp3_path, output_path)
        mp3_path.unlink(missing_ok=True)
        return output_path

    return mp3_path


def _generate_with_elevenlabs(
    *,
    text: str,
    output_path: Path,
    voice: str = DEFAULT_ELEVENLABS_VOICE,
    model_id: str = DEFAULT_ELEVENLABS_MODEL,
    stability: float = DEFAULT_ELEVENLABS_STABILITY,
    similarity_boost: float = DEFAULT_ELEVENLABS_SIMILARITY_BOOST,
    style: float = DEFAULT_ELEVENLABS_STYLE,
    speed: float = 1.0,
    use_speaker_boost: bool = DEFAULT_ELEVENLABS_USE_SPEAKER_BOOST,
    apply_text_normalization: ElevenLabsTextNormalization = DEFAULT_ELEVENLABS_TEXT_NORMALIZATION,
) -> Path:
    """
    Generate audio using ElevenLabs Text-to-Speech.

    Docs: https://elevenlabs.io/docs/api-reference/text-to-speech/convert
    """
    api_key = (os.getenv("ELEVENLABS_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set. Add it to your .env to use ElevenLabs TTS.")

    # Allow passing a raw voice_id, but prefer curated voice names
    if voice in ELEVENLABS_VOICES:
        voice_id = ELEVENLABS_VOICES[voice][0]
    else:
        voice_id = voice  # assume caller passed an actual voice_id

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": float(stability),
            "similarity_boost": float(similarity_boost),
            "style": float(style),
            "use_speaker_boost": bool(use_speaker_boost),
            "speed": float(speed),
        },
        "apply_text_normalization": apply_text_normalization,
    }

    def _call_elevenlabs() -> requests.Response:
        resp = requests.post(
            url,
            params={"output_format": "mp3_44100_128"},
            headers=headers,
            json=payload,
            timeout=(10, 180),
        )
        if resp.status_code in {401, 402, 403}:
            raise NonRetryableError(
                f"ElevenLabs direct API returned {resp.status_code}; use fallback provider."
            )
        resp.raise_for_status()
        return resp

    # Use dedicated ElevenLabs limiter (configurable via ELEVENLABS_MIN_DELAY_S / ELEVENLABS_MAX_RETRIES)
    response = elevenlabs_limiter.call_with_retry(_call_elevenlabs)

    mp3_path = output_path.with_suffix(".mp3")
    mp3_path.write_bytes(response.content)

    if output_path.suffix == ".wav":
        _convert_mp3_to_wav(mp3_path, output_path)
        mp3_path.unlink(missing_ok=True)
        return output_path

    return mp3_path


def _generate_with_openai(text: str, output_path: Path, voice: str = "nova", model_id: str = "tts-1") -> Path:
    """Generate audio using OpenAI TTS with rate limiting."""
    import openai

    client = openai.OpenAI()

    def _call_openai():
        return client.audio.speech.create(
            model=str(model_id or "tts-1"),
            voice=voice,
            input=text,
            response_format="mp3",
        )

    response = openai_limiter.call_with_retry(_call_openai)

    # Save the audio
    mp3_path = output_path.with_suffix(".mp3")
    response.stream_to_file(str(mp3_path))

    # Convert to WAV for consistency with the local render pipeline.
    if output_path.suffix == ".wav":
        _convert_mp3_to_wav(mp3_path, output_path)
        mp3_path.unlink()  # Remove temporary MP3
        return output_path

    return mp3_path


def _convert_mp3_to_wav(mp3_path: Path, wav_path: Path) -> None:
    """Convert MP3 to WAV using pydub or ffmpeg."""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_mp3(str(mp3_path))
        audio.export(str(wav_path), format="wav")
    except ImportError:
        # Fallback to ffmpeg
        import subprocess
        subprocess.run(
            ["ffmpeg", "-i", str(mp3_path), "-y", str(wav_path)],
            capture_output=True,
            check=True,
        )


def generate_scene_audio(
    scene: dict,
    project_dir: Path,
    tts_provider: TTSProvider = "kokoro",
    voice: str = DEFAULT_VOICE,
    speed: float = DEFAULT_SPEED,
    exaggeration: float = DEFAULT_EXAGGERATION,
    openai_model_id: str = "tts-1",
    # ElevenLabs passthrough
    elevenlabs_model_id: str = DEFAULT_ELEVENLABS_MODEL,
    elevenlabs_apply_text_normalization: ElevenLabsTextNormalization = DEFAULT_ELEVENLABS_TEXT_NORMALIZATION,
    elevenlabs_stability: float = DEFAULT_ELEVENLABS_STABILITY,
    elevenlabs_similarity_boost: float = DEFAULT_ELEVENLABS_SIMILARITY_BOOST,
    elevenlabs_style: float = DEFAULT_ELEVENLABS_STYLE,
    elevenlabs_use_speaker_boost: bool = DEFAULT_ELEVENLABS_USE_SPEAKER_BOOST,
) -> Path:
    """
    Generate audio for a specific scene.

    Args:
        scene: Scene dictionary with 'id' and 'narration'
        project_dir: Project directory for saving assets
        tts_provider: TTS provider ("kokoro", "elevenlabs", "chatterbox", or "openai")
        voice: Voice identifier (provider-dependent)
        speed: Speed multiplier (provider-dependent)
        exaggeration: Emotion intensity 0.25-2.0 (Chatterbox only)
        elevenlabs_*: ElevenLabs settings (used when tts_provider=="elevenlabs")

    Returns:
        Path to the generated audio
    """
    scene_id = scene["id"]
    narration = scene["narration"]

    override_enabled = bool(scene.get("tts_override_enabled"))
    available_providers = available_tts_providers()
    base_provider = str(tts_provider or "kokoro").strip().lower()
    if base_provider not in available_providers:
        base_provider = "kokoro"

    requested_provider = (
        str(scene.get("tts_provider") or "").strip().lower()
        if override_enabled and scene.get("tts_provider")
        else ""
    )
    invalid_override_provider = bool(requested_provider and requested_provider not in available_providers)
    apply_scene_overrides = override_enabled and not invalid_override_provider

    resolved_provider: TTSProvider = (
        requested_provider if requested_provider and apply_scene_overrides else base_provider
    )  # type: ignore[assignment]
    requested_voice = str(scene.get("tts_voice") or voice) if apply_scene_overrides else voice
    resolved_voice = _normalize_voice_for_provider(resolved_provider, requested_voice)
    resolved_speed = _safe_float(scene.get("tts_speed"), speed) if apply_scene_overrides else speed
    resolved_elevenlabs_model_id = (
        str(scene.get("elevenlabs_model_id") or elevenlabs_model_id)
        if apply_scene_overrides
        else elevenlabs_model_id
    )
    resolved_elevenlabs_text_normalization = (
        str(scene.get("elevenlabs_text_normalization") or elevenlabs_apply_text_normalization)
        if apply_scene_overrides
        else elevenlabs_apply_text_normalization
    )
    resolved_elevenlabs_stability = (
        _safe_float(scene.get("elevenlabs_stability"), elevenlabs_stability)
        if apply_scene_overrides
        else elevenlabs_stability
    )
    resolved_elevenlabs_similarity_boost = (
        _safe_float(scene.get("elevenlabs_similarity_boost"), elevenlabs_similarity_boost)
        if apply_scene_overrides
        else elevenlabs_similarity_boost
    )
    resolved_elevenlabs_style = (
        _safe_float(scene.get("elevenlabs_style"), elevenlabs_style)
        if apply_scene_overrides
        else elevenlabs_style
    )
    resolved_elevenlabs_use_speaker_boost = (
        bool(scene.get("elevenlabs_use_speaker_boost"))
        if apply_scene_overrides and scene.get("elevenlabs_use_speaker_boost") is not None
        else elevenlabs_use_speaker_boost
    )

    output_path = project_dir / "audio" / f"scene_{scene_id:03d}.wav"

    return generate_scene_audio_result(
        scene,
        project_dir,
        tts_provider=tts_provider,
        voice=voice,
        speed=speed,
        exaggeration=exaggeration,
        openai_model_id=openai_model_id,
        elevenlabs_model_id=elevenlabs_model_id,
        elevenlabs_apply_text_normalization=elevenlabs_apply_text_normalization,
        elevenlabs_stability=elevenlabs_stability,
        elevenlabs_similarity_boost=elevenlabs_similarity_boost,
        elevenlabs_style=elevenlabs_style,
        elevenlabs_use_speaker_boost=elevenlabs_use_speaker_boost,
    )["path"]


def generate_scene_audio_result(
    scene: dict,
    project_dir: Path,
    tts_provider: TTSProvider = "kokoro",
    voice: str = DEFAULT_VOICE,
    speed: float = DEFAULT_SPEED,
    exaggeration: float = DEFAULT_EXAGGERATION,
    openai_model_id: str = "tts-1",
    elevenlabs_model_id: str = DEFAULT_ELEVENLABS_MODEL,
    elevenlabs_apply_text_normalization: ElevenLabsTextNormalization = DEFAULT_ELEVENLABS_TEXT_NORMALIZATION,
    elevenlabs_stability: float = DEFAULT_ELEVENLABS_STABILITY,
    elevenlabs_similarity_boost: float = DEFAULT_ELEVENLABS_SIMILARITY_BOOST,
    elevenlabs_style: float = DEFAULT_ELEVENLABS_STYLE,
    elevenlabs_use_speaker_boost: bool = DEFAULT_ELEVENLABS_USE_SPEAKER_BOOST,
) -> dict[str, object]:
    """Generate scene audio and return execution metadata."""
    scene_id = scene["id"]
    narration = scene["narration"]

    override_enabled = bool(scene.get("tts_override_enabled"))
    available_providers = available_tts_providers()
    base_provider = str(tts_provider or "kokoro").strip().lower()
    if base_provider not in available_providers:
        base_provider = "kokoro"

    requested_provider = (
        str(scene.get("tts_provider") or "").strip().lower()
        if override_enabled and scene.get("tts_provider")
        else ""
    )
    invalid_override_provider = bool(requested_provider and requested_provider not in available_providers)
    apply_scene_overrides = override_enabled and not invalid_override_provider

    resolved_provider: TTSProvider = (
        requested_provider if requested_provider and apply_scene_overrides else base_provider
    )  # type: ignore[assignment]
    requested_voice = str(scene.get("tts_voice") or voice) if apply_scene_overrides else voice
    resolved_voice = _normalize_voice_for_provider(resolved_provider, requested_voice)
    resolved_speed = _safe_float(scene.get("tts_speed"), speed) if apply_scene_overrides else speed
    resolved_elevenlabs_model_id = (
        str(scene.get("elevenlabs_model_id") or elevenlabs_model_id)
        if apply_scene_overrides
        else elevenlabs_model_id
    )
    resolved_elevenlabs_text_normalization = (
        str(scene.get("elevenlabs_text_normalization") or elevenlabs_apply_text_normalization)
        if apply_scene_overrides
        else elevenlabs_apply_text_normalization
    )
    resolved_elevenlabs_stability = (
        _safe_float(scene.get("elevenlabs_stability"), elevenlabs_stability)
        if apply_scene_overrides
        else elevenlabs_stability
    )
    resolved_elevenlabs_similarity_boost = (
        _safe_float(scene.get("elevenlabs_similarity_boost"), elevenlabs_similarity_boost)
        if apply_scene_overrides
        else elevenlabs_similarity_boost
    )
    resolved_elevenlabs_style = (
        _safe_float(scene.get("elevenlabs_style"), elevenlabs_style)
        if apply_scene_overrides
        else elevenlabs_style
    )
    resolved_elevenlabs_use_speaker_boost = (
        bool(scene.get("elevenlabs_use_speaker_boost"))
        if apply_scene_overrides and scene.get("elevenlabs_use_speaker_boost") is not None
        else elevenlabs_use_speaker_boost
    )

    output_path = project_dir / "audio" / f"scene_{scene_id:03d}.wav"

    return generate_audio_result(
        narration,
        output_path,
        voice=resolved_voice,
        speed=resolved_speed,
        tts_provider=resolved_provider,
        exaggeration=exaggeration,
        openai_model_id=str(scene.get("model_id") or openai_model_id or "tts-1"),
        elevenlabs_model_id=resolved_elevenlabs_model_id,
        elevenlabs_apply_text_normalization=resolved_elevenlabs_text_normalization,  # type: ignore[arg-type]
        elevenlabs_stability=resolved_elevenlabs_stability,
        elevenlabs_similarity_boost=resolved_elevenlabs_similarity_boost,
        elevenlabs_style=resolved_elevenlabs_style,
        elevenlabs_use_speaker_boost=resolved_elevenlabs_use_speaker_boost,
    )
