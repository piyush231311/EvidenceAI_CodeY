"""Audio transcription module using pretrained Faster-Whisper for Evidence AI."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Import ctranslate2 first on Windows to ensure correct OpenMP DLL initialization
import ctranslate2

# Suppress Hugging Face symlink warnings on Windows non-admin accounts
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_MODELS_CACHE = PROJECT_ROOT / "models_cache"
os.environ.setdefault("HF_HOME", str(DEFAULT_MODELS_CACHE / "huggingface"))

SUPPORTED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a"}

# Global singleton to avoid reloading model on every request
_WHISPER_MODEL = None
_WHISPER_CONFIG = None


def get_whisper_model(
    model_size: str = "small",
    device: str = "cpu",
    compute_type: str = "int8",
    download_root: Optional[Union[str, Path]] = None,
):
    """
    Get or initialize the Faster-Whisper model instance.

    Args:
        model_size: Whisper model size ('small' by default).
        device: 'cpu' for CPU inference (default) or 'cuda' for GPU acceleration.
        compute_type: Quantization type ('int8' for CPU, 'float16' for GPU).
        download_root: Directory to store model checkpoints.

    Returns:
        WhisperModel instance.
    """
    global _WHISPER_MODEL, _WHISPER_CONFIG

    if download_root is None:
        download_root = str(DEFAULT_MODELS_CACHE / "whisper")
    else:
        download_root = str(download_root)

    current_config = (model_size, device, compute_type, download_root)

    if _WHISPER_MODEL is None or _WHISPER_CONFIG != current_config:
        from faster_whisper import WhisperModel

        _WHISPER_MODEL = WhisperModel(
            model_size_or_path=model_size,
            device=device,
            compute_type=compute_type,
            download_root=download_root,
        )
        _WHISPER_CONFIG = current_config

    return _WHISPER_MODEL


def transcribe_audio(
    audio_path: Union[str, Path],
    model_size: str = "small",
    device: str = "cpu",
    compute_type: str = "int8",
    language: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Transcribe audio file into text with language detection and timestamps.

    Args:
        audio_path: Path to MP3, WAV, or M4A audio file.
        model_size: Model variant ('small' default).
        device: 'cpu' (default) or 'cuda' for GPU acceleration.
        compute_type: 'int8' for CPU, 'float16' for GPU.
        language: Optional ISO code to force language (e.g. 'en').

    Returns:
        Dict containing:
            - 'text': Full transcribed text.
            - 'language': Detected or specified language.
            - 'language_probability': Confidence score for detected language.
            - 'duration': Total audio duration in seconds.
            - 'segments': List of dicts, each with 'id', 'start', 'end', 'text'.
            - 'success': Boolean indicating transcription success.

    Raises:
        FileNotFoundError: If audio file does not exist.
        ValueError: If file format is not supported (only MP3, WAV, M4A).
    """
    audio_path = Path(audio_path).resolve()

    if not audio_path.is_file():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    ext = audio_path.suffix.lower()
    if ext not in SUPPORTED_AUDIO_EXTENSIONS:
        raise ValueError(
            f"Unsupported audio format '{ext}'. "
            f"Supported formats are: {', '.join(sorted(SUPPORTED_AUDIO_EXTENSIONS))}"
        )

    model = get_whisper_model(
        model_size=model_size,
        device=device,
        compute_type=compute_type,
    )

    segments_generator, info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=5,
    )

    segments_list: List[Dict[str, Any]] = []
    text_chunks: List[str] = []

    for seg in segments_generator:
        clean_text = seg.text.strip()
        segments_list.append({
            "id": seg.id,
            "start": round(seg.start, 2),
            "end": round(seg.end, 2),
            "text": clean_text,
        })
        if clean_text:
            text_chunks.append(clean_text)

    full_text = " ".join(text_chunks)

    return {
        "text": full_text,
        "language": info.language,
        "language_probability": round(float(info.language_probability), 4),
        "duration": round(float(info.duration), 2),
        "segments": segments_list,
        "success": True,
    }
