from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import os
import shutil
import tempfile
import time
import uuid
import json
from typing import List, Optional
from pydantic import BaseModel

# Import local modules
from pdf_utils import load_file
from vector_store import VectorStoreManager
from rag_pipeline import get_llm, ensure_ollama, ask_question, extract_topics, group_similar_topics, generate_mcqs
from mindmap_generator import generate_mindmap, mindmap_to_text
from flashcard_generator import generate_flashcards, flashcards_to_text
from lecture_notes_generator import process_video_to_notes
from interview_voice_assistant import generate_interview_question, evaluate_answer, text_to_speech, speech_to_text

app = FastAPI(title="AI Study System API")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174", "https://ai-study-system-ecru.vercel.app"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Globals
store_manager = VectorStoreManager()
llm = None

@app.on_event("startup")
async def startup_event():
    global llm
    try:
        ensure_ollama()
        llm = get_llm()
    except Exception as e:
        print(f"Warning: Could not initialize LLM properly: {e}")

# Auth and Session Persistence
USERS_FILE = "users.json"

def load_users():
    if not os.path.exists(USERS_FILE):
        return {}
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

class UserAuth(BaseModel):
    username: str
    password: str

# In-memory session state for interview
interview_sessions = {}
active_sessions = set()

@app.post("/register")
async def register(auth: UserAuth):
    users = load_users()
    if auth.username in users:
        raise HTTPException(status_code=400, detail="User already exists")
    users[auth.username] = auth.password # Simple for now
    save_users(users)
    return {"status": "success"}

@app.post("/login")
async def login(auth: UserAuth):
    users = load_users()
    if users.get(auth.username) != auth.password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    token = str(uuid.uuid4())
    active_sessions.add(token)
    return {"token": token, "username": auth.username}

@app.post("/logout")
async def logout(token: str = Form(...)):
    if token in active_sessions:
        active_sessions.remove(token)
    store_manager.clear() # Clear docs on logout as requested
    return {"status": "success"}

@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    store_manager.clear()
    logs = []
    
    for file in files:
        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, file.filename)
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        try:
            docs = load_file(temp_path, file.filename)
            if docs:
                store_manager.add_documents(docs, filename=file.filename)
                logs.append(f"✅ Indexed {file.filename}")
            else:
                logs.append(f"⚠️ Could not extract text from {file.filename}")
        except Exception as e:
            logs.append(f"❌ Error with {file.filename}: {e}")
        finally:
            shutil.rmtree(temp_dir)
            
    return {"status": "success", "logs": logs, "is_loaded": store_manager.is_loaded}

@app.get("/summary")
async def get_summary(detail_level: str = "Normal"):
    if not store_manager.is_loaded:
        raise HTTPException(status_code=400, detail="No documents uploaded")
        
    dmap = {'Brief': '2-3 bullets only.', 'Normal': '4-5 clear bullets.', 'Detailed': 'One detailed paragraph.'}
    inst = dmap.get(detail_level, "Normal")
    
    topics = extract_topics(store_manager)
    topics = group_similar_topics(topics, 5)
    
    result = []
    for topic, contents in topics.items():
        combined = "\n\n".join(contents)[:2000]
        try:
            r = llm.invoke(f'Summarize for a student in {inst}\nTopic:"{topic[:60]}"\nContent:{combined}')
            summary = r.content if hasattr(r, 'content') else str(r)
        except Exception as e:
            summary = f"⚠️ {e}"
        result.append({"topic": topic, "summary": summary})
        
    return {"summaries": result}

@app.post("/chat")
async def chat(query: str = Form(...), history: Optional[str] = Form(None)):
    if not store_manager.is_loaded:
        raise HTTPException(status_code=400, detail="No documents uploaded")
    
    # Simple history parsing if provided as JSON string
    chat_history = []
    if history:
        import json
        try:
            chat_history = json.loads(history)
        except:
            pass
            
    ans = ask_question(query, store_manager, llm, chat_history)
    return {"answer": ans}

@app.post("/voice-chat")
async def voice_chat(audio: UploadFile = File(...)):
    if not store_manager.is_loaded:
        raise HTTPException(status_code=400, detail="No documents uploaded")
        
    temp_dir = tempfile.mkdtemp()
    audio_path = os.path.join(temp_dir, audio.filename)
    with open(audio_path, "wb") as buffer:
        shutil.copyfileobj(audio.file, buffer)
        
    start_time = time.time()
    try:
        user_text = speech_to_text(audio_path)
        print(f"🎙️ Transcription success: '{user_text[:50]}...' in {time.time()-start_time:.2f}s")
        
        ans = ask_question(user_text, store_manager, llm)
        
        out_filename = f"voice_ans_{uuid.uuid4()}.mp3"
        out_path = os.path.join(tempfile.gettempdir(), out_filename)
        text_to_speech(ans, out_path)
        
        return {
            "user_text": user_text,
            "answer": ans,
            "audio_url": f"/audio/{out_filename}",
            "processing_time": time.time() - start_time
        }
    except Exception as e:
        print(f"❌ Voice chat error: {e}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Speech processing failed: {str(e)}", "error_type": type(e).__name__}
        )
    finally:
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

@app.get("/audio/{filename}")
async def get_audio_file(filename: str):
    path = os.path.join(tempfile.gettempdir(), filename)
    if os.path.exists(path):
        return FileResponse(path)
    raise HTTPException(status_code=404, detail="Audio not found")

@app.post("/quiz")
async def generate_quiz_endpoint(topic: str = Form("all topics"), num: int = Form(5), difficulty: str = Form("medium")):
    if not store_manager.is_loaded:
        raise HTTPException(status_code=400, detail="No documents uploaded")
    
    start_time = time.time()
    try:
        qs = generate_mcqs(topic, num, difficulty, store_manager, llm)
        print(f"✅ Quiz generated for topic '{topic}' in {time.time()-start_time:.2f}s")
        return {"quizzes": qs}
    except Exception as e:
        print(f"❌ Quiz generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mindmap")
async def get_mindmap():
    if not store_manager.is_loaded:
        raise HTTPException(status_code=400, detail="No documents uploaded")
    mm = generate_mindmap(store_manager, llm, "Study Overview")
    return {"mindmap": mm} # Returning the raw dict for React to render

@app.get("/flashcards")
async def get_flashcards(num: int = 10):
    if not store_manager.is_loaded:
        raise HTTPException(status_code=400, detail="No documents uploaded")
    cards = generate_flashcards(store_manager, llm, num)
    return {"flashcards": cards}

@app.post("/video-notes")
async def video_to_notes(video: UploadFile = File(...)):
    temp_dir = tempfile.mkdtemp()
    video_path = os.path.join(temp_dir, video.filename)
    with open(video_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)
        
    try:
        res = process_video_to_notes(video_path, llm)
        return res
    finally:
        shutil.rmtree(temp_dir)

@app.post("/interview/start")
async def start_interview():
    if not store_manager.is_loaded:
        raise HTTPException(status_code=400, detail="No documents uploaded")
        
    session_id = str(uuid.uuid4())
    q = generate_interview_question(store_manager, llm, first=True)
    
    out_filename = f"int_q_{uuid.uuid4()}.mp3"
    out_path = os.path.join(tempfile.gettempdir(), out_filename)
    text_to_speech(q, out_path)
    
    interview_sessions[session_id] = {
        "history": [],
        "q_count": 0,
        "total": 0,
        "current_q": q
    }
    
    return {
        "session_id": session_id,
        "question": q,
        "audio_url": f"/audio/{out_filename}"
    }

@app.post("/interview/submit")
async def submit_answer(session_id: str = Form(...), audio: Optional[UploadFile] = File(None), text_ans: Optional[str] = Form(None)):
    if session_id not in interview_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session = interview_sessions[session_id]
    ans = text_ans
    
    if audio:
        temp_dir = tempfile.mkdtemp()
        audio_path = os.path.join(temp_dir, audio.filename)
        with open(audio_path, "wb") as buffer:
            shutil.copyfileobj(audio.file, buffer)
        try:
            ans = speech_to_text(audio_path)
        finally:
            shutil.rmtree(temp_dir)
            
    if not ans:
        raise HTTPException(status_code=400, detail="No answer provided")
        
    score, feedback = evaluate_answer(session["current_q"], ans, store_manager, llm)
    session["history"].append((session["current_q"], ans, feedback, score))
    session["total"] += score
    session["q_count"] += 1
    
    avg = session["total"] / session["q_count"]
    
    out_filename = f"int_fb_{uuid.uuid4()}.mp3"
    out_path = os.path.join(tempfile.gettempdir(), out_filename)
    text_to_speech(f"You scored {score} out of 10. {feedback}.", out_path)
    
    return {
        "score": score,
        "feedback": feedback,
        "average_score": avg,
        "audio_url": f"/audio/{out_filename}"
    }

@app.post("/interview/next")
async def next_question(session_id: str = Form(...)):
    if session_id not in interview_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
        
    session = interview_sessions[session_id]
    q = generate_interview_question(store_manager, llm, history=session["history"])
    session["current_q"] = q
    
    out_filename = f"int_q_{uuid.uuid4()}.mp3"
    out_path = os.path.join(tempfile.gettempdir(), out_filename)
    text_to_speech(q, out_path)
    
    return {
        "question": q,
        "audio_url": f"/audio/{out_filename}"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
