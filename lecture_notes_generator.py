"""
lecture_notes_generator.py — Lecture Notes from Video

Extracts audio from a video file, transcribes it to text,
and generates structured lecture notes with headings and bullet points.
"""

import os
import math
import tempfile
import speech_recognition as sr


def extract_audio(video_path, output_audio_path=None):
    """
    Extract audio track from a video file using ffmpeg backend.

    Args:
        video_path: Path to the input video file.
        output_audio_path: Optional output path for the WAV file.
    
    Returns:
        Path to the extracted WAV audio file.
    """
    import subprocess
    
    if output_audio_path is None:
        output_audio_path = os.path.join(
            tempfile.gettempdir(), "lecture_audio.wav"
        )

    print(f"🎬 Extracting audio from video: {os.path.basename(video_path)}")
    
    # Use ffmpeg to extract audio (faster and no moviepy dependency)
    cmd = [
        "ffmpeg", "-y", "-i", video_path,
        "-vn", "-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1",
        output_audio_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"✅ Audio extracted: {output_audio_path}")
        return output_audio_path
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr.decode() if e.stderr else str(e)
        print(f"❌ FFmpeg error: {error_msg}")
        raise RuntimeError(f"Failed to extract audio using ffmpeg: {error_msg}")


def transcribe_audio(audio_path, chunk_duration=60, progress_callback=None):
    """
    Transcribe an audio file to text using Google Speech Recognition.

    Splits long audio into chunks for reliable transcription.

    Args:
        audio_path: Path to the WAV audio file.
        chunk_duration: Duration of each chunk in seconds (default 60).
        progress_callback: Optional function(text) to report progress.

    Returns:
        Full transcript as a string.
    """
    recognizer = sr.Recognizer()
    recognizer.energy_threshold = 300

    print(f"🎙️ Transcribing audio: {os.path.basename(audio_path)}")

    transcript_parts = []

    with sr.AudioFile(audio_path) as source:
        audio_data = recognizer.record(source)
        total_duration = len(audio_data.frame_data) / (
            audio_data.sample_rate * audio_data.sample_width
        )

    num_chunks = max(1, math.ceil(total_duration / chunk_duration))
    print(f"   Audio duration: ~{total_duration:.0f}s, chunks: {num_chunks}")

    with sr.AudioFile(audio_path) as source:
        for i in range(num_chunks):
            offset = i * chunk_duration
            msg = f"🎙️ Transcribing: chunk {i+1} of {num_chunks}..."
            print(f"   {msg}")
            if progress_callback: progress_callback(msg)
            
            try:
                audio_chunk = recognizer.record(
                    source, duration=min(chunk_duration, total_duration - offset)
                )
                text = recognizer.recognize_google(audio_chunk)
                transcript_parts.append(text)
                print(f"   ✅ Chunk {i + 1}/{num_chunks} transcribed")
            except sr.UnknownValueError:
                print(f"   ⚠️ Chunk {i + 1}/{num_chunks}: inaudible, skipping")
                transcript_parts.append("[inaudible]")
            except sr.RequestError as e:
                print(f"   ❌ Chunk {i + 1}/{num_chunks}: API error: {e}")
                transcript_parts.append("[transcription error]")

    full_transcript = " ".join(transcript_parts)
    print(f"✅ Transcription complete: {len(full_transcript)} characters")
    return full_transcript


def generate_lecture_notes(transcript, llm):
    """
    Generate structured lecture notes from a transcript using LLM.

    Segments the transcript into topics and produces clean notes
    with headings and bullet points.

    Args:
        transcript: Full text transcript of the lecture.
        llm: ChatOllama LLM instance.

    Returns:
        Structured lecture notes as a markdown string.
    """
    # Truncate if too long for context window
    clean_transcript = transcript.replace("[inaudible]", "").strip()
    clean_transcript = clean_transcript.replace("[transcription error]", "").strip()
    
    if not clean_transcript or len(clean_transcript) < 40:
        return "⚠️ The video audio was too quiet or unclear to generate meaningful notes. Please ensure the lecture audio is loud and clear."

    # Process in sections if very long to avoid stalling
    lines = clean_transcript.split()
    chunk_size = 1000 # words
    chunks = [" ".join(lines[i:i+chunk_size]) for i in range(0, len(lines), chunk_size)]
    
    all_notes = []
    print(f"🧠 Processing transcript in {len(chunks)} sections...")
    
    for i, chunk in enumerate(chunks):
        prompt = f"""You are an expert academic note-taker. 
Convert this section of a lecture transcript into professional, structured study notes.
Transcript Section {i+1}/{len(chunks)}:
{chunk}

Rules:
- Use clear bullet points
- Identify key concepts and definitions
- Capture important details
- Remove filler words"""
        
        try:
            print(f"   Generating notes for section {i+1}...")
            result = llm.invoke(prompt)
            part_notes = result.content if hasattr(result, "content") else str(result)
            all_notes.append(part_notes)
        except Exception as e:
            print(f"   ⚠️ Error in chunk {i+1}: {e}")
            all_notes.append(f"[Error processing section {i+1}]")

    combined_notes = "\n\n".join(all_notes)
    
    # Final cleanup prompt
    final_prompt = f"""You are an expert academic editor. Below are raw study notes generated from a lecture transcript.
Organize them into a single, cohesive, and comprehensive markdown document. 

IMPORTANT: Ensure NO information is lost. Maintain the hierarchy and level of detail from the raw notes.

Raw Notes:
{combined_notes}

Required Markdown Format:
# Final Lecture Notes
## [Main Topic]
- [Key Detail]
- [Sub-point]
### [Sub-topic]
- [Specific Detail]

## Summary
[Unified summary of all sections]
"""
    try:
        print("✍️ Performing final cleanup of notes...")
        final_result = llm.invoke(final_prompt)
        return final_result.content if hasattr(final_result, "content") else str(final_result)
    except:
        return combined_notes


def process_video_to_notes(video_path, llm, progress_callback=None):
    """
    Full pipeline: video → audio → transcript → structured notes.

    Args:
        video_path: Path to the lecture video file.
        llm: ChatOllama LLM instance.
        progress_callback: Optional function(text) to report progress.

    Returns:
        dict with keys:
        - 'notes' (str): Structured markdown lecture notes.
        - 'transcript' (str): Raw transcript text.
        - 'audio_path' (str): Path to extracted audio.
    """
    print("=" * 50)
    print("📹 Video → Lecture Notes Pipeline")
    print("=" * 50)

    # Step 1: Extract audio
    if progress_callback: progress_callback("🎬 Extracting audio from video...")
    audio_path = extract_audio(video_path)

    # Step 2: Transcribe
    transcript = transcribe_audio(audio_path, progress_callback=progress_callback)

    # Step 3: Generate notes
    if progress_callback: progress_callback("🧠 Brainstorming lecture notes from transcript...")
    notes = generate_lecture_notes(transcript, llm)

    return {
        "notes": notes,
        "transcript": transcript,
        "audio_path": audio_path,
    }
