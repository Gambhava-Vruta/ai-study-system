"""
interview_voice_assistant.py — Voice Interview Practice System

Provides functions for generating interview questions, evaluating
spoken answers, and text-to-speech / speech-to-text conversion.
"""

import re
import os
import base64
import tempfile
import subprocess
import speech_recognition as sr
from gtts import gTTS


# ══════════════════════════════════════════════════════════════════════════════
# SPEECH UTILITIES
# ══════════════════════════════════════════════════════════════════════════════


def text_to_speech(text, output_path=None, lang="en"):
    """
    Convert text to an audio MP3 file using Google Text-to-Speech.

    Args:
        text: Text to convert (truncated to 500 chars).
        output_path: Path to save the MP3 file. Auto-generated if None.
        lang: Language code (default 'en').

    Returns:
        Path to the generated MP3 audio file.
    """
    if output_path is None:
        output_path = os.path.join(tempfile.gettempdir(), "tts_output.mp3")

    tts = gTTS(text=text[:500], lang=lang)
    tts.save(output_path)
    return output_path


def speech_to_text(audio_path):
    """
    Convert an audio file to text using Google Speech Recognition.

    Supports WAV files directly. For other formats (webm, mp3),
    converts to WAV using ffmpeg first.

    Args:
        audio_path: Path to the audio file.

    Returns:
        Transcribed text string.

    Raises:
        RuntimeError: If ffmpeg conversion fails.
        FileNotFoundError: If the expected WAV file is not created.
        sr.UnknownValueError: If speech could not be understood.
        sr.RequestError: If the API is unavailable.
    """
    # Convert non-WAV formats to WAV using ffmpeg
    if not audio_path.lower().endswith(".wav"):
        wav_path = audio_path.rsplit(".", 1)[0] + ".wav"
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", audio_path, wav_path],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg conversion failed: {result.stderr}")
        if not os.path.exists(wav_path):
            raise FileNotFoundError(f"ffmpeg did not create the output file: {wav_path}")
        audio_path = wav_path

    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300

    if not os.path.exists(audio_path):
         raise FileNotFoundError(f"Audio file to transcribe not found: {audio_path}")

    with sr.AudioFile(audio_path) as source:
        audio_data = recognizer.record(source)

    return recognizer.recognize_google(audio_data)


def audio_to_base64(audio_path):
    """
    Read an audio file and return its base64 encoding.

    Args:
        audio_path: Path to the audio file.

    Returns:
        Base64-encoded string.
    """
    with open(audio_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# ══════════════════════════════════════════════════════════════════════════════
# INTERVIEW QUESTION GENERATION
# ══════════════════════════════════════════════════════════════════════════════


def generate_interview_question(vector_store_manager, llm, history=None, first=False):
    """
    Generate an interview question based on the study material.

    Args:
        vector_store_manager: VectorStoreManager instance.
        llm: ChatOllama LLM instance.
        history: List of (question, answer, feedback, score) tuples.
        first: If True, generate an opening question.

    Returns:
        Interview question string.
    """
    if first or not history:
        return _generate_first_question(vector_store_manager, llm)
    else:
        last = history[-1]
        asked_questions = [h[0] for h in history]
        return _generate_followup(
            vector_store_manager, llm,
            prev_q=last[0], prev_ans=last[1], score=last[3], 
            history=history, asked=asked_questions
        )


def _generate_first_question(vector_store_manager, llm):
    """Generate an opening interview question."""
    context = vector_store_manager.get_context(
        "important concepts fundamentals", k=2, max_chars=600
    )
    prompt = f"""You are a friendly technical interviewer. Use the study material below.
Study Material: {context[:1200]}
Ask ONE clear, concise opening interview question (max 2 sentences).
Return ONLY the question, nothing else."""

    result = llm.invoke(prompt)
    return result.content.strip() if hasattr(result, "content") else str(result).strip()


def _generate_followup(vector_store_manager, llm, prev_q, prev_ans, score, history, asked):
    """Generate a follow-up question based on previous performance."""
    context = vector_store_manager.get_context(prev_q, k=2, max_chars=400)

    strategy = (
        "Ask a deeper follow-up question."
        if score >= 7
        else "Ask a clarifying question about the weak parts."
        if score >= 4
        else "Ask a simpler related question to help the candidate."
    )

    history_str = "".join(
        f"Q: {q}\nA: {a}\n\n" for q, a, _, _ in history[-2:]
    )

    asked_str = "\n".join([f"- {q}" for q in asked])

    prompt = f"""You are a technical interviewer. 
CRITICAL: ONLY ask questions about the Specific Study Material provided below.

Study Material: {context[:1000]}

Questions already asked (DO NOT REPEAT THESE):
{asked_str}

Last Candidate Answer: {prev_ans}

Task:
{strategy} 
Strictly ensure the question is derived from the material above.

Return ONLY the question text."""

    result = llm.invoke(prompt)
    return result.content.strip() if hasattr(result, "content") else str(result).strip()


# ══════════════════════════════════════════════════════════════════════════════
# ANSWER EVALUATION
# ══════════════════════════════════════════════════════════════════════════════


def evaluate_answer(question, answer, vector_store_manager, llm):
    """
    Evaluate a candidate's spoken answer to an interview question.

    Args:
        question: The interview question that was asked.
        answer: The candidate's transcribed answer.
        vector_store_manager: VectorStoreManager instance.
        llm: ChatOllama LLM instance.

    Returns:
        Tuple of (score: int 0-10, feedback: str).
    """
    context = vector_store_manager.get_context(question, k=2, max_chars=300)

    prompt = f"""You are a strict technical interviewer evaluating a spoken answer.
Question: {question}
Candidate Answer: {answer}
Study Material for reference: {context[:600]}

Instructions:
1. If the Candidate Answer is empty, extremely short (under 10 characters), or sounds like background noise/nothing (e.g., repeating the question back or just "uh", "okay"), give a SCORE of 0.
2. If the answer is completely irrelevant to the question, give a SCORE of 0.
3. Otherwise, score strictly (0-10) based on technical accuracy and depth compared to the Study Material.
4. Reply in EXACTLY this format:
SCORE: (0-10)
FEEDBACK: (2 sentences max: what was correct, or what was missing)"""

    try:
        result = llm.invoke(prompt)
        raw = result.content if hasattr(result, "content") else str(result)
        return _parse_evaluation(raw)
    except Exception as e:
        print(f"⚠️ Evaluation error: {e}")
        return 5, "Answer noted."


def _parse_evaluation(raw_text):
    """
    Parse SCORE/FEEDBACK from LLM evaluation output.

    Args:
        raw_text: Raw LLM output string.

    Returns:
        Tuple of (score: int, feedback: str).
    """
    score = 5
    feedback = "Answer noted."

    for line in raw_text.splitlines():
        if line.upper().startswith("SCORE:"):
            m = re.search(r"\d+", line)
            if m:
                score = min(10, int(m.group()))
        elif line.upper().startswith("FEEDBACK:"):
            feedback = line.split(":", 1)[1].strip()

    return score, feedback
