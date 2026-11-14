"""Evidence AI - Streamlit Web Interface for Local Evidence Extraction."""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to sys.path so 'src' can be imported anywhere
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import ctranslate2 before other ML libraries on Windows
import ctranslate2
import streamlit as st

from src.extraction.ocr import extract_text_from_image
from src.extraction.transcription import transcribe_audio

st.set_page_config(
    page_title="Evidence AI",
    page_icon="🔍",
    layout="wide",
)

st.title("🔍 Evidence AI — Digital Evidence Intelligence Platform")
st.caption("Local & Secure Evidence Processing with PaddleOCR & Faster-Whisper")

tab_ocr, tab_audio = st.tabs(["🖼️ Screenshot OCR", "🎙️ Audio Transcription"])

# -------------------------------------------------------------
# TAB 1: SCREENSHOT OCR
# -------------------------------------------------------------
with tab_ocr:
    st.subheader("Extract Text from Screenshots and Images")
    st.write("Upload a PNG, JPG, or JPEG image to extract recognized text and confidence scores.")

    uploaded_image = st.file_uploader(
        "Choose an image file",
        type=["png", "jpg", "jpeg"],
        key="ocr_uploader",
    )

    if uploaded_image is not None:
        col_img, col_out = st.columns([1, 1])

        with col_img:
            st.image(uploaded_image, caption="Uploaded Evidence Image", use_container_width=True)

        with col_out:
            if st.button("Extract Text", type="primary", key="btn_ocr"):
                with st.spinner("Running PaddleOCR extraction..."):
                    suffix = Path(uploaded_image.name).suffix.lower()
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                        tmp_file.write(uploaded_image.getvalue())
                        tmp_path = tmp_file.name

                    try:
                        result = extract_text_from_image(tmp_path)
                        st.success("Text extracted successfully!")

                        # Metrics
                        st.metric(
                            label="Recognition Confidence",
                            value=f"{result['confidence'] * 100:.1f}%",
                        )

                        # Extracted text display
                        st.markdown("### Extracted Text")
                        st.text_area(
                            label="Full Text",
                            value=result["text"],
                            height=250,
                            label_visibility="collapsed",
                        )

                        # Detailed line analysis
                        if result["lines"]:
                            with st.expander("Detailed Recognized Lines"):
                                st.dataframe(
                                    [
                                        {"Line": item["text"], "Confidence": f"{item['confidence'] * 100:.1f}%"}
                                        for item in result["lines"]
                                    ],
                                    use_container_width=True,
                                )
                    except Exception as err:
                        st.error(f"Error extracting text: {err}")
                    finally:
                        if os.path.exists(tmp_path):
                            os.remove(tmp_path)

# -------------------------------------------------------------
# TAB 2: AUDIO TRANSCRIPTION
# -------------------------------------------------------------
with tab_audio:
    st.subheader("Transcribe Audio Recordings into Text")
    st.write("Upload an MP3, WAV, or M4A recording to transcribe audio with timestamps and language detection.")

    uploaded_audio = st.file_uploader(
        "Choose an audio file",
        type=["mp3", "wav", "m4a"],
        key="audio_uploader",
    )

    if uploaded_audio is not None:
        st.audio(uploaded_audio)

        if st.button("Transcribe Audio", type="primary", key="btn_audio"):
            with st.spinner("Running Faster-Whisper transcription..."):
                suffix = Path(uploaded_audio.name).suffix.lower()
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                    tmp_file.write(uploaded_audio.getvalue())
                    tmp_path = tmp_file.name

                try:
                    result = transcribe_audio(tmp_path)
                    st.success("Audio transcribed successfully!")

                    # Metrics
                    col_lang, col_prob, col_dur = st.columns(3)
                    with col_lang:
                        st.metric("Detected Language", result["language"].upper())
                    with col_prob:
                        st.metric("Language Confidence", f"{result['language_probability'] * 100:.1f}%")
                    with col_dur:
                        st.metric("Audio Duration", f"{result['duration']}s")

                    # Transcript text
                    st.markdown("### Full Transcript")
                    st.text_area(
                        label="Transcript",
                        value=result["text"],
                        height=200,
                        label_visibility="collapsed",
                    )

                    # Segment timestamps
                    if result["segments"]:
                        with st.expander("Segment Timestamps", expanded=True):
                            st.dataframe(
                                [
                                    {
                                        "Start": f"{seg['start']:.2f}s",
                                        "End": f"{seg['end']:.2f}s",
                                        "Text": seg["text"],
                                    }
                                    for seg in result["segments"]
                                ],
                                use_container_width=True,
                            )
                except Exception as err:
                    st.error(f"Error transcribing audio: {err}")
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)
