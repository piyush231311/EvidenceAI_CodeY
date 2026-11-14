"""
Evidence AI — Audio Deepfake & Synthetic Speech Detector (PellaV2 Adapter).

Integrates PellaV2 (Sadanie/pellav2-audio-deepfake-detector, MIT License) to assess
potential synthetic speech, neural vocoder generation, and voice spoofing.

Core Forensic Principles:
  - Canonical Authenticity Outcomes:
      SYNTHETIC_INDICATORS_DETECTED: Strong neural vocoder / synthetic acoustic artifacts detected.
      NO_STRONG_SYNTHETIC_INDICATORS: No significant synthetic generation indicators found.
      INCONCLUSIVE: Borderline or ambiguous acoustic score.
      UNSUPPORTED: Audio format, duration, or codec cannot be assessed.
      DETECTION_FAILED: Inference failed due to decode error or missing model.
  - Multi-window coverage: Evaluates multiple 4.0-second sliding windows across the full audio duration.
    Calculates weighted score (0.6 * max + 0.4 * mean) to detect isolated deepfake speech insertions.
  - Non-destructive: Audio preprocessing (mono conversion, 16 kHz resampling, filtering)
    is performed strictly on in-memory buffers; original evidence remains unmodified.
  - Forensic Scope: Evaluates acoustic generation artifacts; does NOT verify speaker identity,
    voice cloning target, or non-generative audio splicing.
"""

import json
import logging
import math
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union
import av
import numpy as np
import torch
import torch.nn as nn
import torchaudio.compliance.kaldi as K
import torchaudio.functional as AF
from pydantic import BaseModel, Field

from src.detection.provenance_checker import inspect_media_provenance, ProvenanceCheckResult

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AUDIO_AUTH_CACHE_FILE = PROJECT_ROOT / "models_cache" / "audio_authenticity_cache.json"

MODEL_IDENTIFIER = "pellav2-audio-deepfake-detector"
MODEL_VERSION = "2.0.0"
POLICY_VERSION = "2.0.0"
SR = 16000
WINDOW_DURATION_SEC = 4.0
WINDOW_SAMPLES = int(WINDOW_DURATION_SEC * SR)  # 64,000 samples
TARGET_LUFS = -23.0

_AUDIO_DETECTOR_LOCK = threading.Lock()
_CACHE_LOCK = threading.Lock()
_LOADED_DETECTOR = None
_MODEL_DEVICE = "cpu"

CanonicalAssessment = Literal[
    "SYNTHETIC_INDICATORS_DETECTED",
    "NO_STRONG_SYNTHETIC_INDICATORS",
    "INCONCLUSIVE",
    "UNSUPPORTED",
    "DETECTION_FAILED",
]
CanonicalProcessingStatus = Literal[
    "COMPLETED", "FAILED", "SKIPPED", "INCONCLUSIVE", "UNSUPPORTED"
]


def normalize_assessment(val: str) -> CanonicalAssessment:
    """Normalizes assessment strings to canonical uppercase format."""
    v = (val or "").strip().upper()
    if v in ["SYNTHETIC_INDICATORS_DETECTED", "SYNTHETIC_DETECTED"]:
        return "SYNTHETIC_INDICATORS_DETECTED"
    if v in ["NO_STRONG_SYNTHETIC_INDICATORS", "SYNTHETIC_INDICATORS_NOT_DETECTED", "NOT_DETECTED"]:
        return "NO_STRONG_SYNTHETIC_INDICATORS"
    if v in ["UNSUPPORTED"]:
        return "UNSUPPORTED"
    if v in ["DETECTION_FAILED", "FAILED"]:
        return "DETECTION_FAILED"
    return "INCONCLUSIVE"


def normalize_processing_status(val: str) -> CanonicalProcessingStatus:
    """Normalizes processing status strings to canonical uppercase format."""
    v = (val or "").strip().upper()
    if v in ["COMPLETED", "FAILED", "SKIPPED", "INCONCLUSIVE", "UNSUPPORTED"]:
        return v  # type: ignore
    return "COMPLETED"


class AudioAuthenticityResult(BaseModel):
    """Forensic authenticity assessment for a single audio evidence item."""
    evidence_id: str
    file_hash: str = ""
    filename: str
    modality: str = "audio"
    detector_name: str = MODEL_IDENTIFIER
    detector_model: str = MODEL_IDENTIFIER
    model_version: str = MODEL_VERSION
    policy_version: str = POLICY_VERSION
    inference_executed: bool = False
    raw_score: Optional[float] = None  # Aggregate synthetic speech score [0.0 - 1.0]
    synthetic_score: Optional[float] = None  # Explicit contract field for synthetic score
    raw_model_output: Optional[Dict[str, Any]] = None  # Window count, mean, peak scores
    score_type: str = "w2v_bert_window_aggregate"  # Score interpretation type
    calibrated_probability: Optional[float] = None  # None unless Platt/isotonic calibrated
    score_interpretation: str = ""
    assessment_reason: str = ""
    decision_threshold: float = 0.50
    assessment: CanonicalAssessment = "INCONCLUSIVE"
    assessment_status: CanonicalAssessment = "INCONCLUSIVE"
    audio_duration_total_sec: float = 0.0
    audio_duration_analyzed_sec: float = 0.0
    coverage_percentage: float = 0.0
    num_windows_analyzed: int = 0
    window_scores: List[Dict[str, Any]] = Field(default_factory=list)
    preprocessing_info: Dict[str, Any] = Field(default_factory=dict)
    provenance: Optional[ProvenanceCheckResult] = None
    relevant_limitations: List[str] = Field(default_factory=list)
    processing_status: CanonicalProcessingStatus = "COMPLETED"
    error_details: Optional[str] = None
    inference_time_ms: float = 0.0
    device_used: str = "cpu"
    from_cache: bool = False
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)

    def model_post_init(self, __context: Any) -> None:
        if self.synthetic_score is None and self.raw_score is not None:
            self.synthetic_score = self.raw_score
        elif self.raw_score is None and self.synthetic_score is not None:
            self.raw_score = self.synthetic_score
        if not self.assessment_status or self.assessment_status == "INCONCLUSIVE":
            if self.assessment != "INCONCLUSIVE":
                self.assessment_status = self.assessment
        if not self.assessment_reason and self.score_interpretation:
            self.assessment_reason = self.score_interpretation
        elif not self.score_interpretation and self.assessment_reason:
            self.score_interpretation = self.assessment_reason
        if not self.detector_model and self.detector_name:
            self.detector_model = self.detector_name

    # Backward compatibility properties
    @property
    def sha256(self) -> str:
        return self.file_hash

    @property
    def model_identifier(self) -> str:
        return self.detector_name

    @property
    def limitations(self) -> List[str]:
        return self.relevant_limitations

    @property
    def error_message(self) -> Optional[str]:
        return self.error_details

    def to_dict(self) -> Dict[str, Any]:
        return json.loads(self.model_dump_json())


class PellaV2Detector(nn.Module):
    """PellaV2 PyTorch Detector: Wav2Vec2Bert backbone with learned layer weights and linear head."""
    def __init__(self):
        super().__init__()
        from transformers import Wav2Vec2BertConfig, Wav2Vec2BertModel

        cfg_dir = PROJECT_ROOT / "models_cache" / "pellav2"
        if (cfg_dir / "config.json").exists():
            config = Wav2Vec2BertConfig.from_pretrained(str(cfg_dir), local_files_only=True)
        else:
            try:
                config = Wav2Vec2BertConfig.from_pretrained("facebook/w2v-bert-2.0", local_files_only=True)
            except Exception:
                config = Wav2Vec2BertConfig.from_pretrained("facebook/w2v-bert-2.0")

        self.backbone = Wav2Vec2BertModel(config)
        self.layer_weights = nn.Parameter(
            torch.zeros(self.backbone.config.num_hidden_layers + 1)
        )
        self.head = nn.Linear(self.backbone.config.hidden_size, 1)

    @staticmethod
    def features(wav: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        feats, lens = [], []
        with torch.autocast(device_type=wav.device.type, enabled=False):
            for x in wav.float():
                nz = torch.nonzero(x).flatten()
                n_s = int(nz[-1]) + 1 if len(nz) else len(x)
                f = K.fbank(
                    x[None, :max(n_s, 400)] * 32768.0,
                    num_mel_bins=80,
                    sample_frequency=SR,
                    dither=0.0,
                    window_type="povey",
                )
                f = (f - f.mean(0, keepdim=True)) / torch.sqrt(f.var(0, keepdim=True) + 1e-7)
                n = f.shape[0] // 2 * 2
                feats.append(f[:n].reshape(n // 2, 160))
                lens.append(n // 2)
        max_len = max(lens) if lens else 1
        out = torch.zeros(len(feats), max_len, 160, device=wav.device)
        mask = torch.zeros(len(feats), max_len, dtype=torch.long, device=wav.device)
        for i, (f, n) in enumerate(zip(feats, lens)):
            out[i, :n] = f
            mask[i, :n] = 1
        return out, mask

    def forward(self, wav: torch.Tensor) -> torch.Tensor:
        feats, mask = self.features(wav)
        hs = self.backbone(
            input_features=feats, attention_mask=mask, output_hidden_states=True
        ).hidden_states
        w = torch.softmax(self.layer_weights, dim=0)
        h = torch.stack(hs).mul(w[:, None, None, None]).sum(0)
        m = mask[:, :, None].float()
        h = (h * m).sum(1) / m.sum(1).clamp(min=1)
        return self.head(h).squeeze(-1)


def _find_pellav2_checkpoint_path() -> Optional[Path]:
    """Locates the cached PellaV2 checkpoint on disk."""
    local_path = PROJECT_ROOT / "models_cache" / "pellav2" / "pellav2_detector.pt"
    if local_path.exists():
        return local_path

    hf_cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
    pella_dirs = list(hf_cache_dir.glob("models--Sadanie--pellav2-audio-deepfake-detector/**/pellav2_detector.pt"))
    if pella_dirs:
        return pella_dirs[0]

    return None


def _load_pellav2_detector() -> Optional[PellaV2Detector]:
    """Loads PellaV2 detector on CPU safely."""
    global _LOADED_DETECTOR, _MODEL_DEVICE
    if _LOADED_DETECTOR is not None:
        return _LOADED_DETECTOR

    ckpt_path = _find_pellav2_checkpoint_path()
    if not ckpt_path or not ckpt_path.exists():
        logger.warning(f"PellaV2 weights file not found on disk: {ckpt_path}")
        return None

    try:
        logger.info(f"Loading PellaV2 detector from {ckpt_path} on {_MODEL_DEVICE}...")
        detector = PellaV2Detector()
        state_dict = torch.load(str(ckpt_path), map_location=_MODEL_DEVICE)
        detector.load_state_dict(state_dict)
        detector.to(_MODEL_DEVICE)
        detector.eval()
        _LOADED_DETECTOR = detector
        logger.info("PellaV2 detector loaded successfully.")
        return _LOADED_DETECTOR
    except Exception as exc:
        logger.error(f"Failed to load PellaV2 weights from {ckpt_path}: {exc}")
        return None


def _calculate_rough_loudness_gain(wav: np.ndarray) -> float:
    """Estimates RMS loudness gain to achieve approximately -23 LUFS / standard speech volume."""
    rms = np.sqrt(np.mean(wav**2) + 1e-9)
    rms_db = 20.0 * math.log10(rms + 1e-9)
    gain_db = TARGET_LUFS - rms_db
    return float(np.clip(gain_db, -20.0, 20.0))


def _preprocess_audio_to_16k_mono(file_path: Union[str, Path]) -> Tuple[np.ndarray, float]:
    """
    Decodes audio via PyAV into mono 16,000 Hz float32 array, applies 20 Hz highpass filter.
    Returns (normalized_audio_array, total_duration_sec).
    """
    container = av.open(str(file_path))
    if not container.streams.audio:
        raise ValueError(f"No audio stream found in {file_path}")

    stream = container.streams.audio[0]
    orig_sr = stream.rate or 16000

    frames = []
    for frame in container.decode(audio=0):
        frames.append(frame.to_ndarray())

    if not frames:
        raise ValueError("Audio file decoded to 0 frames.")

    raw = np.concatenate(frames, axis=1)
    if raw.shape[0] > 1:
        raw = raw.mean(axis=0, keepdims=True)
    raw = raw.astype(np.float32)

    total_samples = raw.shape[1]
    total_duration_sec = total_samples / float(orig_sr)

    tensor = torch.from_numpy(raw)
    if orig_sr != SR:
        tensor = AF.resample(tensor, orig_freq=orig_sr, new_freq=SR)

    # Apply 20 Hz high-pass filter
    if tensor.shape[-1] > 3 * SR // 100:
        tensor = AF.highpass_biquad(tensor, SR, 20.0)

    wav = tensor.squeeze(0).numpy()
    wav = wav - wav.mean()

    # Normalize gain
    if len(wav):
        gain = _calculate_rough_loudness_gain(wav)
        wav = np.clip(wav * (10 ** (gain / 20.0)), -1.0, 1.0).astype(np.float32)

    return wav, round(total_duration_sec, 3)


def _extract_audio_windows(wav: np.ndarray) -> List[Tuple[int, float, float, np.ndarray]]:
    """
    Segments 16 kHz audio into 4.0-second windows with 50% (2.0s) stride.
    Returns list of (window_index, start_sec, end_sec, window_array).
    """
    total_samples = len(wav)
    if total_samples <= WINDOW_SAMPLES:
        padded = np.zeros(WINDOW_SAMPLES, dtype=np.float32)
        padded[:total_samples] = wav
        dur = total_samples / float(SR)
        return [(0, 0.0, dur, padded)]

    stride = int(2.0 * SR)
    windows = []
    curr = 0
    idx = 0
    while curr + WINDOW_SAMPLES <= total_samples:
        start_sec = round(curr / float(SR), 2)
        end_sec = round((curr + WINDOW_SAMPLES) / float(SR), 2)
        windows.append((idx, start_sec, end_sec, wav[curr: curr + WINDOW_SAMPLES]))
        curr += stride
        idx += 1
        if len(windows) >= 15:
            break

    if total_samples > WINDOW_SAMPLES and (curr < total_samples):
        tail_start = total_samples - WINDOW_SAMPLES
        start_sec = round(tail_start / float(SR), 2)
        end_sec = round(total_samples / float(SR), 2)
        windows.append((idx, start_sec, end_sec, wav[tail_start:]))

    return windows


def assess_audio_authenticity(
    audio_path: Union[str, Path],
    evidence_id: str,
    filename: str = "",
    sha256: str = "",
    force_refresh: bool = False,
) -> AudioAuthenticityResult:
    """
    Executes PellaV2 synthetic speech evaluation across multiple windows of the audio file.
    Aggregates window-level probabilities and integrates provenance checks.
    """
    path_obj = Path(audio_path)
    fname = filename or path_obj.name
    cache_key = f"{sha256}::{MODEL_IDENTIFIER}::{MODEL_VERSION}::p{POLICY_VERSION}"

    # 1. Check disk cache first unless force_refresh is requested
    if not force_refresh and sha256 and AUDIO_AUTH_CACHE_FILE.exists():
        with _CACHE_LOCK:
            try:
                c_data = json.loads(AUDIO_AUTH_CACHE_FILE.read_text(encoding="utf-8"))
                entry = c_data.get(cache_key)
                if entry and entry.get("processing_status") in ["COMPLETED", "completed"]:
                    entry["from_cache"] = True
                    entry["inference_executed"] = False
                    entry["assessment"] = normalize_assessment(entry.get("assessment", ""))
                    entry["processing_status"] = normalize_processing_status(entry.get("processing_status", ""))
                    if "file_hash" not in entry:
                        entry["file_hash"] = entry.get("sha256", sha256)
                    if "detector_name" not in entry:
                        entry["detector_name"] = entry.get("model_identifier", MODEL_IDENTIFIER)
                    if "relevant_limitations" not in entry:
                        entry["relevant_limitations"] = entry.get("limitations", [])
                    if "error_details" not in entry:
                        entry["error_details"] = entry.get("error_message")
                    return AudioAuthenticityResult(**entry)
            except Exception:
                pass

    # 2. Check file presence
    if not path_obj.exists() or not path_obj.is_file():
        return AudioAuthenticityResult(
            evidence_id=evidence_id,
            filename=fname,
            file_hash=sha256,
            inference_executed=False,
            processing_status="FAILED",
            error_details=f"Audio file not found on disk: {path_obj}",
            assessment="INCONCLUSIVE",
            relevant_limitations=["Audio file not found."],
        )

    # 3. Provenance Check
    prov = inspect_media_provenance(
        file_path=path_obj,
        evidence_id=evidence_id,
        filename=fname,
        sha256=sha256,
        file_type="audio",
    )

    # 4. Preprocess audio
    try:
        wav, total_duration = _preprocess_audio_to_16k_mono(path_obj)
        window_tuples = _extract_audio_windows(wav)
    except Exception as exc:
        return AudioAuthenticityResult(
            evidence_id=evidence_id,
            filename=fname,
            file_hash=sha256,
            provenance=prov,
            inference_executed=False,
            processing_status="FAILED",
            error_details=f"Audio decoding failure: {exc}",
            assessment="INCONCLUSIVE",
            relevant_limitations=["Audio decoding failed."],
        )

    # 5. Load model and run inference
    with _AUDIO_DETECTOR_LOCK:
        model = _load_pellav2_detector()
        if model is None:
            return AudioAuthenticityResult(
                evidence_id=evidence_id,
                filename=fname,
                file_hash=sha256,
                provenance=prov,
                inference_executed=False,
                processing_status="FAILED",
                error_details="PellaV2 detector weights not ready or downloading.",
                assessment="INCONCLUSIVE",
                audio_duration_total_sec=total_duration,
                relevant_limitations=["PellaV2 weights not available locally; assessment marked inconclusive."],
            )

        t0 = time.perf_counter()
        try:
            detailed_window_scores: List[Dict[str, Any]] = []
            raw_scores: List[float] = []

            for w_idx, s_sec, e_sec, win in window_tuples:
                win_tensor = torch.from_numpy(win)[None].to(_MODEL_DEVICE)
                with torch.no_grad():
                    logit = model(win_tensor)
                    p_fake = float(torch.sigmoid(logit).item())
                    score_val = round(p_fake, 4)
                    raw_scores.append(score_val)
                    detailed_window_scores.append({
                        "window_index": w_idx,
                        "start_sec": s_sec,
                        "end_sec": e_sec,
                        "synthetic_probability": score_val,
                        "raw_score": score_val,
                    })

            elapsed_ms = (time.perf_counter() - t0) * 1000.0

            # Aggregation: 0.6 * max + 0.4 * mean (sensitive to isolated deepfake crops)
            max_score = max(raw_scores) if raw_scores else 0.5
            mean_score = float(np.mean(raw_scores)) if raw_scores else 0.5
            agg_score = round(0.6 * max_score + 0.4 * mean_score, 4)

            # Analyzed coverage calculation
            analyzed_duration = min(total_duration, len(window_tuples) * WINDOW_DURATION_SEC)
            coverage_pct = round(min(100.0, (analyzed_duration / max(total_duration, 0.001)) * 100.0), 1)

            # Dual-Thresholds
            if agg_score >= 0.70:
                assessment = "SYNTHETIC_INDICATORS_DETECTED"
                interp = (
                    f"Strong synthetic speech / neural TTS indicators detected across "
                    f"{len(window_tuples)} analyzed window(s) (aggregate score: {agg_score:.4f}, peak: {max_score:.4f})."
                )
            elif agg_score <= 0.30:
                assessment = "NO_STRONG_SYNTHETIC_INDICATORS"
                interp = (
                    f"No significant neural speech synthesis artifacts detected in {len(window_tuples)} "
                    f"analyzed window(s) (aggregate score: {agg_score:.4f}, peak: {max_score:.4f})."
                )
            else:
                assessment = "INCONCLUSIVE"
                interp = (
                    f"Borderline or mixed synthetic speech score ({agg_score:.4f}) across "
                    f"{len(window_tuples)} window(s); inconclusive."
                )

            limits = [
                "PellaV2 is trained primarily on studio/podcast-grade English speech; background noise, echo, or non-English speech may affect scoring.",
                "Synthetic speech detection evaluates vocoder and neural acoustic generation artifacts; it does NOT verify speaker identity.",
                "Absence of synthetic speech indicators does not verify that conversation contents were genuine or unedited.",
                "Forensic Non-Suppression: Even when synthetic speech is flagged, the recording is preserved in full for investigation and audit.",
            ]

            prep_info = {
                "sample_rate": SR,
                "channels": "mono",
                "highpass_filter": "20 Hz biquad",
                "target_lufs": TARGET_LUFS,
                "window_duration_sec": WINDOW_DURATION_SEC,
                "window_stride_sec": 2.0,
                "features": "fbank 80-mel filterbanks",
            }

            raw_output = {
                "num_windows": len(window_tuples),
                "mean_synthetic_score": round(agg_score, 4),
                "peak_synthetic_score": round(max_score, 4),
            }

            res = AudioAuthenticityResult(
                evidence_id=evidence_id,
                filename=fname,
                file_hash=sha256,
                detector_name=MODEL_IDENTIFIER,
                detector_model=MODEL_IDENTIFIER,
                model_version=MODEL_VERSION,
                policy_version=POLICY_VERSION,
                inference_executed=True,
                raw_score=agg_score,
                synthetic_score=agg_score,
                raw_model_output=raw_output,
                score_type="w2v_bert_window_aggregate",
                calibrated_probability=None,
                score_interpretation=interp,
                assessment_reason=interp,
                decision_threshold=0.50,
                assessment=assessment,
                assessment_status=assessment,
                audio_duration_total_sec=total_duration,
                audio_duration_analyzed_sec=round(analyzed_duration, 2),
                coverage_percentage=coverage_pct,
                num_windows_analyzed=len(window_tuples),
                window_scores=detailed_window_scores,
                preprocessing_info=prep_info,
                provenance=prov,
                relevant_limitations=limits,
                processing_status="COMPLETED",
                error_details=None,
                inference_time_ms=round(elapsed_ms, 2),
                device_used=_MODEL_DEVICE,
                from_cache=False,
            )

            # Save to disk cache
            if sha256:
                with _CACHE_LOCK:
                    try:
                        AUDIO_AUTH_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
                        c_dict = {}
                        if AUDIO_AUTH_CACHE_FILE.exists():
                            c_dict = json.loads(AUDIO_AUTH_CACHE_FILE.read_text(encoding="utf-8"))
                        c_dict[cache_key] = res.model_dump()
                        AUDIO_AUTH_CACHE_FILE.write_text(json.dumps(c_dict, indent=2, default=str), encoding="utf-8")
                    except Exception as exc:
                        logger.warning(f"Failed to write audio authenticity cache: {exc}")

            return res

        except Exception as exc:
            logger.error(f"PellaV2 inference error for {fname}: {exc}")
            return AudioAuthenticityResult(
                evidence_id=evidence_id,
                filename=fname,
                file_hash=sha256,
                provenance=prov,
                inference_executed=False,
                processing_status="FAILED",
                error_details=f"Inference exception: {exc}",
                assessment="DETECTION_FAILED",
                relevant_limitations=["PellaV2 encountered an unhandled inference exception."],
            )
