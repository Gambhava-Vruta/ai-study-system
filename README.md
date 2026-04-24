# 🎓 AI Study System

A modular AI-powered study assistant that helps students learn from documents, generate study materials, and practice for interviews — all from a Jupyter/Colab notebook.

## ✨ Features

| Feature | Module | Description |
|---------|--------|-------------|
| 📄 Document Upload | `pdf_utils.py` | Load PDF, PPTX, DOCX, TXT, CSV, XLSX files |
| 💬 Chat with Documents | `rag_pipeline.py` | RAG-powered Q&A over uploaded content |
| 📝 Summarization | `rag_pipeline.py` | Topic extraction and LLM-driven summaries |
| 📋 MCQ Quiz | `rag_pipeline.py` | Auto-generated multiple-choice quizzes |
| 🗺️ Mind Maps | `mindmap_generator.py` | Hierarchical topic maps as structured JSON |
| 📚 Flashcards | `flashcard_generator.py` | Auto-generated Q/A flashcards from content |
| 🎬 Lecture Notes | `lecture_notes_generator.py` | Video → audio → transcript → structured notes |
| 🎤 Voice Interview | `interview_voice_assistant.py` | Practice interviews with voice I/O and scoring |

## 📁 Project Structure

```
project/
├── Copy of Untitled13.ipynb   # Demo notebook (Colab-ready)
├── pdf_utils.py               # Document loading utilities
├── embeddings.py              # Embedding model configuration
├── vector_store.py            # ChromaDB vector store manager
├── rag_pipeline.py            # LLM + RAG query pipeline
├── mindmap_generator.py       # Mind map generation
├── flashcard_generator.py     # Flashcard generation
├── lecture_notes_generator.py # Video → lecture notes pipeline
├── interview_voice_assistant.py # Voice interview system
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## 🚀 Setup

### Prerequisites
- Python 3.9+
- [Ollama](https://ollama.com/) installed and running
- ffmpeg (for audio processing)

### Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install system dependencies (Ubuntu/Colab)
sudo apt-get install -y ffmpeg portaudio19-dev

# Start Ollama and pull models
ollama serve &
ollama pull llama3.2:1b
ollama pull nomic-embed-text
```

### Google Colab
The notebook includes setup cells that automatically install all dependencies on Colab.

## 📖 Usage

### Quick Start (Notebook)
1. Open `Copy of Untitled13.ipynb` in Google Colab
2. Run the setup cells (install deps, start Ollama)
3. Upload your study documents
4. Use the tabbed interface for chat, quizzes, mind maps, flashcards, and more

### Python Module Usage

```python
from pdf_utils import load_file
from embeddings import get_embeddings
from vector_store import VectorStoreManager
from rag_pipeline import get_llm, ask_question

# Load and index a document
docs = load_file("notes.pdf", "notes.pdf")
manager = VectorStoreManager()
manager.add_documents(docs, "notes.pdf")

# Ask questions
llm = get_llm()
answer = ask_question("What is machine learning?", manager, llm)
print(answer)
```

```python
from mindmap_generator import generate_mindmap
from flashcard_generator import generate_flashcards

# Generate mind map
mindmap = generate_mindmap(manager, llm, title="ML Notes")

# Generate flashcards
cards = generate_flashcards(manager, llm, num_cards=10)
```

```python
from lecture_notes_generator import process_video_to_notes

# Video → structured notes
result = process_video_to_notes("lecture.mp4", llm)
print(result["notes"])
```

## 🛠️ Module Reference

| Module | Key Functions |
|--------|--------------|
| `pdf_utils` | `load_file(filepath, filename)` |
| `embeddings` | `get_embeddings(model)` |
| `vector_store` | `VectorStoreManager.add_documents()`, `.similarity_search()` |
| `rag_pipeline` | `get_llm()`, `ask_question()`, `generate_mcqs()`, `extract_topics()` |
| `mindmap_generator` | `generate_mindmap()`, `mindmap_to_text()` |
| `flashcard_generator` | `generate_flashcards()`, `flashcards_to_text()` |
| `lecture_notes_generator` | `extract_audio()`, `transcribe_audio()`, `generate_lecture_notes()`, `process_video_to_notes()` |
| `interview_voice_assistant` | `generate_interview_question()`, `evaluate_answer()`, `text_to_speech()`, `speech_to_text()` |

## 📝 License

This project is for educational purposes.
