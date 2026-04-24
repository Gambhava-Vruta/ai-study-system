import os
import sys
import time
import subprocess
import shutil
import base64
import tempfile

def install_deps():
    print("Checking dependencies...")
    try:
        import gradio as gr
    except ImportError:
        print("Installing Gradio UI...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "gradio"])
        import gradio as gr

install_deps()
import gradio as gr

# Ensure required module imports with reloading for development
import importlib
modules_to_reload = [
    "pdf_utils", "vector_store", "rag_pipeline", "mindmap_generator", 
    "flashcard_generator", "lecture_notes_generator", "interview_voice_assistant"
]
for mod_name in modules_to_reload:
    if mod_name in sys.modules:
        importlib.reload(sys.modules[mod_name])

try:
    from pdf_utils import load_file
    from vector_store import VectorStoreManager
    from rag_pipeline import get_llm, ensure_ollama, ask_question, extract_topics, group_similar_topics, generate_mcqs
    from mindmap_generator import generate_mindmap, mindmap_to_text
    from flashcard_generator import generate_flashcards, flashcards_to_text
    from lecture_notes_generator import process_video_to_notes
    from interview_voice_assistant import generate_interview_question, evaluate_answer, text_to_speech, speech_to_text
    
    # Version-aware Gradio formatting
    GRADIO_NEW = hasattr(gr, "ChatMessage")
    print(f"DEBUG: Gradio New Format detected: {GRADIO_NEW}")
except ImportError as e:
    print(f"Failed to import local modules: {e}")
    sys.exit(1)

# Initialize Globals
store_manager = VectorStoreManager()
llm = None
try:
    ensure_ollama()
    llm = get_llm()
except Exception as e:
    print(f"Warning: Could not initialize LLM properly: {e}")

# ══════════════════════════════════════════════════════════════════════════════
# CUSTOM PREMIUM CSS (Glassmorphism & Modern Styling)
# ══════════════════════════════════════════════════════════════════════════════
css = """
body {
    background: linear-gradient(-45deg, #0f172a, #1e1b4b, #312e81, #1e1b4b);
    background-size: 400% 400%;
    animation: gradientBG 15s ease infinite;
    color: #e2e8f0;
    font-family: 'Inter', sans-serif;
}

@keyframes gradientBG {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

.gradio-container {
    background: rgba(15, 23, 42, 0.65) !important;
    backdrop-filter: blur(16px) !important;
    -webkit-backdrop-filter: blur(16px) !important;
    border-radius: 24px !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5) !important;
    padding: 30px !important;
    margin-top: 20px !important;
    margin-bottom: 20px !important;
}

.gr-box {
    background: rgba(30, 41, 59, 0.6) !important;
    border: 1px solid rgba(99, 102, 241, 0.3) !important;
    border-radius: 16px !important;
}

h1, h2, h3 {
    color: #c7d2fe !important;
    font-weight: 700 !important;
    text-shadow: 0 2px 4px rgba(0,0,0,0.3) !important;
}

button.primary {
    background: linear-gradient(135deg, #6366f1, #4f46e5) !important;
    border: none !important;
    box-shadow: 0 4px 14px 0 rgba(99, 102, 241, 0.39) !important;
    transition: transform 0.2s, box-shadow 0.2s !important;
    color: white !important;
    border-radius: 12px !important;
}

button.primary:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px 0 rgba(99, 102, 241, 0.5) !important;
}

.gr-form {
    background: transparent !important;
}

input, textarea {
    background: rgba(15, 23, 42, 0.8) !important;
    border: 1px solid rgba(99, 102, 241, 0.4) !important;
    color: #f8fafc !important;
    border-radius: 12px !important;
}

input:focus, textarea:focus {
    border-color: #818cf8 !important;
    box-shadow: 0 0 0 2px rgba(129, 140, 248, 0.2) !important;
}

.tabs {
    border-bottom: 2px solid rgba(99, 102, 241, 0.2) !important;
}

.tabitem {
    padding: 24px !important;
}
"""
        

# ══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS FOR UI
# ══════════════════════════════════════════════════════════════════════════════

def handle_upload(files):
    if not files:
        return "⚠️ No files uploaded."
    
    #  Clear previous documents to ensure only fresh material is used
    store_manager.clear()
    
    logs = ["♻️ Previous document database cleared.\n"]
    for file in files:
        filename = os.path.basename(file.name)
        file_path = file.name
        logs.append(f"📄 Indexing: {filename}...")
        try:
            docs = load_file(file_path, filename)
            if not docs:
                logs.append(f"⚠️ Could not extract text from {filename}")
                continue
            store_manager.add_documents(docs, filename=filename)
            logs.append(f"✅ Fast-indexed {len(docs)} segments from {filename}")
        except Exception as e:
            logs.append(f"❌ Error with {filename}: {e}")
            
    if store_manager.is_loaded:
        logs.append("\n🎉 All documents indexed successfully! You can now use the other tabs.")
    return "\n".join(logs)


def do_summary(detail_level, progress=gr.Progress()):
    if not store_manager.is_loaded:
        return "⚠️ Please upload a document first in the 'Setup' tab."
    dmap = {'Brief': '2-3 bullets only.', 'Normal': '4-5 clear bullets.', 'Detailed': 'One detailed paragraph.'}
    inst = dmap.get(detail_level, "Brief")
    
    progress(0, desc="🔍 Extracting topics...")
    topics = extract_topics(store_manager)
    topics = group_similar_topics(topics, 5)
    
    result = "### 📑 Document Summary\n\n"
    for i, (topic, contents) in enumerate(progress.tqdm(topics.items(), desc="✍️ Summarizing topics")):
        combined = "\n\n".join(contents)[:2000]
        try:
            r = llm.invoke(f'Summarize for a student in {inst}\nTopic:"{topic[:60]}"\nContent:{combined}')
            summary = r.content if hasattr(r, 'content') else str(r)
        except Exception as e:
            summary = f"⚠️ {e}"
        result += f"**📌 {topic}**\n{summary}\n\n---\n\n"
    return result


chat_history_state = []
def handle_chat(query, history, progress=gr.Progress()):
    global chat_history_state
    if not store_manager.is_loaded:
        if GRADIO_NEW:
            history.append({"role": "user", "content": query})
            history.append({"role": "assistant", "content": "⚠️ Please upload a document first!"})
        else:
            history.append((query, "⚠️ Please upload a document first!"))
        return history, ""
    
    progress(0.4, desc="🤔 Thinking...")
    ans = ask_question(query, store_manager, llm, chat_history_state)
    chat_history_state.append((query, ans))
    if len(chat_history_state) > 5:
        chat_history_state.pop(0)
    
    if GRADIO_NEW:
        history.append({"role": "user", "content": query})
        history.append({"role": "assistant", "content": ans})
    else:
        history.append((query, ans))
    return history, ""


def handle_voice_chat(audio_filepath, progress=gr.Progress()):
    if not store_manager.is_loaded:
        return None, "⚠️ Please upload a document first!", None
    if not audio_filepath:
        return None, "No audio detected", None
        
    try:
        progress(0.2, desc="🎙️ Transcribing voice...")
        # Transcribe
        try:
            user_text = speech_to_text(audio_filepath)
        except Exception as e:
            user_text = f"(Speech not understood: {e})"
            
        progress(0.5, desc="🤔 AI is thinking...")
        # Get Answer
        ans = ask_question(user_text, store_manager, llm)
        
        progress(0.8, desc="🔊 Generating audio response...")
        # Text to Speech
        out_path = os.path.join(tempfile.gettempdir(), 'voice_chat_ans.mp3')
        final_path = text_to_speech(ans, out_path)
        
        history = f"**🧑 You:** {user_text}\n\n**🤖 AI:** {ans}"
        return final_path, history, None
    except Exception as e:
        return None, f"⚠️ Error: {e}", None


def generate_quiz(topic, num, diff, progress=gr.Progress()):
    if not store_manager.is_loaded:
        return "⚠️ Please upload a document first."
    progress(0.1, desc=f"🎯 Crafting {num} {diff} questions...")
    qs = generate_mcqs(topic, int(num), diff, store_manager, llm)
    if not qs:
        return "⚠️ Failed to generate questions."
    
    out = f"### 📝 {diff.title()} MCQs on {topic}\n\n"
    for i, q in enumerate(qs, 1):
        out += f"**Q{i}: {q['question']}**\n"
        for k, v in q['options'].items():
            mark = "✅" if k == q['answer'] else "⬜"
            out += f"- {mark} {k}: {v}\n"
        out += f"*{q['explanation']}*\n\n---\n\n"
    return out


def generate_mindmap_ui(progress=gr.Progress()):
    if not store_manager.is_loaded:
        return "⚠️ Please upload a document first."
    progress(0.4, desc="🗺️ Mapping concepts...")
    mm = generate_mindmap(store_manager, llm, "Study Overview")
    return mindmap_to_text(mm)


def generate_flashcards_ui(num, progress=gr.Progress()):
    if not store_manager.is_loaded:
        return "⚠️ Please upload a document first."
    progress(0.4, desc=f"📚 Generating {num} flashcards...")
    cards = generate_flashcards(store_manager, llm, int(num))
    return flashcards_to_text(cards)


def handle_video(video_file, progress=gr.Progress()):
    if not video_file:
        return "No file uploaded."
    try:
        def update_prog(text):
            # This updates the top progress bar
            progress(None, desc=text)
            
        res = process_video_to_notes(video_file.name, llm, progress_callback=update_prog)
        return res['notes']
    except Exception as e:
        import traceback
        return f"⚠️ Video processing error: {e}\n{traceback.format_exc()}"


interview_state = {"history": [], "q_count": 0, "total": 0, "current_q": "", "active": False}

def start_interview(progress=gr.Progress()):
    if not store_manager.is_loaded:
        return "⚠️ Upload a document first!", None, "Not started", gr.update(), gr.update()
    
    interview_state["history"] = []
    interview_state["q_count"] = 0
    interview_state["total"] = 0
    interview_state["active"] = True
    
    progress(0.3, desc="🎤 Preparing opening question...")
    q = generate_interview_question(store_manager, llm, first=True)
    interview_state["current_q"] = q
    
    progress(0.7, desc="🔊 Converting to voice...")
    timestamp = int(time.time())
    out_path = os.path.join(tempfile.gettempdir(), f'interview_q_{timestamp}.mp3')
    audio_path = text_to_speech(q, out_path)
    
    return f"**Q1:** {q}", audio_path, "Started! Answer below.", gr.update(visible=True, value=None), gr.update(visible=True, value="")

def submit_interview(audio, text_ans, progress=gr.Progress()):
    if not interview_state["active"]:
        return "Interview not active.", None, "Not started", gr.update(), gr.update(), gr.update(), gr.update()
        
    curr_stats = "Not started"
    if interview_state["q_count"] > 0:
        curr_stats = f"Average Score: {interview_state['total'] / interview_state['q_count']:.1f}/10"

    ans = text_ans
    if audio is not None:
        try:
            progress(0.2, desc="🎙️ Decoding your voice...")
            ans = speech_to_text(audio)
        except Exception as e:
            return f"⚠️ Error hearing audio: {e}. Please try again.", None, curr_stats, gr.update(), gr.update(), gr.update(), gr.update()
            
    if not ans or len(ans.strip()) < 5:
        return "⚠️ I couldn't hear a full answer. Please speak more clearly or type it.", None, curr_stats, gr.update(), gr.update(), gr.update(), gr.update()
        
    progress(0.4, desc="⚖️ Evaluating answer...")
    score, feedback = evaluate_answer(interview_state["current_q"], ans, store_manager, llm)
    interview_state["history"].append((interview_state["current_q"], ans, feedback, score))
    interview_state["total"] += score
    interview_state["q_count"] += 1
    
    avg = interview_state["total"] / interview_state["q_count"]
    stats = f"Average Score: {avg:.1f}/10"
    
    progress(0.9, desc="🔊 Preparing feedback audio...")
    timestamp = int(time.time())
    out_path = os.path.join(tempfile.gettempdir(), f'interview_feedback_{timestamp}.mp3')
    audio_path = text_to_speech(f"You scored {score} out of 10. {feedback}. Click the button below for your next question.", out_path)
    
    msg = f"**Last Score:** {score}/10\n**Feedback:** {feedback}\n\n*Click 'Get Next Question' to continue*"
    # Return 7 values: msg, audio, stats, audio_in_upd, text_in_upd, submit_btn_upd, next_btn_upd
    return msg, audio_path, stats, gr.update(value=None, visible=False), gr.update(value="", visible=False), gr.update(visible=False), gr.update(visible=True)

def next_interview_q(progress=gr.Progress()):
    if not interview_state["active"]:
        return "Interview not active.", None, "Not started", gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=False)
        
    progress(0.4, desc="🤔 Generating next question...")
    q = generate_interview_question(store_manager, llm, history=interview_state["history"])
    interview_state["current_q"] = q
    
    progress(0.8, desc="🔊 Preparing audio...")
    timestamp = int(time.time())
    out_path = os.path.join(tempfile.gettempdir(), f'interview_next_{timestamp}.mp3')
    audio_path = text_to_speech(q, out_path)
    
    stats = f"Average Score: {interview_state['total'] / interview_state['q_count']:.1f}/10"
    return f"**Next Question:**\n\n{q}", audio_path, stats, gr.update(visible=True), gr.update(visible=True), gr.update(visible=True), gr.update(visible=False)


# ══════════════════════════════════════════════════════════════════════════════
# BUILD GRADIO UI
# ══════════════════════════════════════════════════════════════════════════════

with gr.Blocks() as demo:
    gr.Markdown("# 🎓 Premium AI Study System")
    gr.Markdown("A beautiful, comprehensive study hub powered by local LLMs.")
    
    with gr.Tabs():
        
        # SETUP TAB
        with gr.TabItem("📁 1. Setup"):
            gr.Markdown("### Upload Documents\nUpload your `.pdf`, `.docx`, `.pptx`, or `.txt` files here to begin.")
            with gr.Row():
                doc_uploader = gr.File(label="Select Documents", file_count="multiple", type="filepath")
                setup_log = gr.Textbox(label="Processing Log", lines=8, interactive=False)
            doc_uploader.upload(handle_upload, inputs=[doc_uploader], outputs=[setup_log])
            
        # SUMMARY TAB
        with gr.TabItem("📝 2. Summary"):
            gr.Markdown("### Auto-Summarize\nGenerate beautiful, concise summaries from your documents.")
            sum_detail = gr.Radio(["Brief", "Normal", "Detailed"], label="Detail Level", value="Normal")
            sum_btn = gr.Button("✨ Generate Summary", variant="primary")
            sum_out = gr.Markdown()
            sum_btn.click(do_summary, inputs=[sum_detail], outputs=[sum_out])
            
        # CHAT & VOICE
        with gr.TabItem("💬 3. Chat & Voice"):
            with gr.Row():
                with gr.Column(scale=1):
                    gr.Markdown("### 🎙️ Voice Assistant")
                    v_audio_in = gr.Audio(sources=["microphone"], type="filepath", label="Speak your question")
                    v_chat_btn = gr.Button("Ask via Voice", variant="primary")
                    v_audio_out = gr.Audio(label="AI Audio Response", autoplay=True)
                    v_text_out = gr.Markdown("Waiting for voice...")
                    v_chat_btn.click(handle_voice_chat, inputs=[v_audio_in], outputs=[v_audio_out, v_text_out, v_audio_in])
                    
                with gr.Column(scale=1):
                    gr.Markdown("### ⌨️ Text Chat")
                    chatbot = gr.Chatbot(label="Study Chat", height=400)
                    msg = gr.Textbox(label="Type your question and press Enter", placeholder="What is polymorphism?")
                    msg.submit(handle_chat, inputs=[msg, chatbot], outputs=[chatbot, msg])
                    
        # QUIZ TAB
        with gr.TabItem("🏆 4. Quizzes & Cards"):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 📋 Multiple Choice Questions")
                    q_topic = gr.Textbox(label="Topic", value="all topics")
                    q_num = gr.Slider(2, 10, value=5, step=1, label="Number of Questions")
                    q_diff = gr.Radio(["easy", "medium", "hard"], value="medium", label="Difficulty")
                    q_btn = gr.Button("Generate MCQs", variant="primary")
                    q_out = gr.Markdown()
                    q_btn.click(generate_quiz, inputs=[q_topic, q_num, q_diff], outputs=[q_out])
                with gr.Column():
                    gr.Markdown("### 📚 Flashcards")
                    f_num = gr.Slider(5, 15, value=10, step=1, label="Number of Flashcards")
                    f_btn = gr.Button("Generate Flashcards", variant="primary")
                    f_out = gr.Markdown()
                    f_btn.click(generate_flashcards_ui, inputs=[f_num], outputs=[f_out])
                    
        # MAPS & NOTES
        with gr.TabItem("🗺️ 5. Maps & Lecture Notes"):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### 🗺️ Mind Map Generation")
                    m_btn = gr.Button("Generate Mind Map", variant="primary")
                    m_out = gr.Textbox(lines=15, label="Mind Map Tree")
                    m_btn.click(generate_mindmap_ui, outputs=[m_out])
                with gr.Column():
                    gr.Markdown("### 🎬 Video to Notes")
                    gr.Markdown("Progress will appear at the top center of the screen.")
                    vid_in = gr.File(label="Upload Lecture Video (.mp4)", type="filepath")
                    vid_btn = gr.Button("Process Video", variant="primary")
                    vid_out = gr.Markdown()
                    vid_btn.click(handle_video, inputs=[vid_in], outputs=[vid_out])
                    
        # INTERVIEW TAB
        with gr.TabItem("🎤 6. Mock Interview"):
            gr.Markdown("### 🎯 Interactive Voice Interview\nThe AI will ask you questions continuously and evaluate your spoken answers.")
            with gr.Row():
                i_start = gr.Button("🎤 Start Interview", variant="primary")
                i_stats = gr.Markdown("**Status:** Not started")
            i_display = gr.Markdown("*Press start to begin*")
            i_audio_out = gr.Audio(label="Interviewer", autoplay=True)
            
            gr.Markdown("### Your Answer")
            gr.Markdown("**Tip:** Click Record, speak, then click the **Square Stop Button** before submitting.")
            
            i_audio_in = gr.Audio(sources=["microphone"], type="filepath", label="Record your answer", interactive=True)
            i_text_in = gr.Textbox(label="Or type your answer manually")
            i_submit = gr.Button("📤 Submit Answer", variant="primary")
            i_next_btn = gr.Button("➡ Get Next Question", variant="secondary", visible=False)
            
            # Start flow
            i_start.click(start_interview, outputs=[i_display, i_audio_out, i_stats, i_audio_in, i_text_in])
            
            # Submit flow
            i_submit.click(submit_interview, 
                inputs=[i_audio_in, i_text_in], 
                outputs=[i_display, i_audio_out, i_stats, i_audio_in, i_text_in, i_submit, i_next_btn])
            
            # Next flow
            i_next_btn.click(next_interview_q, 
                outputs=[i_display, i_audio_out, i_stats, i_audio_in, i_text_in, i_submit, i_next_btn])

if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0", 
        server_port=None, 
        inbrowser=True,
        theme=gr.themes.Soft(primary_hue="indigo"),
        css=css
    )
