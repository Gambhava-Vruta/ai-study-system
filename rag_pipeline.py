"""
rag_pipeline.py — LLM Configuration & RAG Query Logic

Contains the core question-answering pipeline, topic extraction,
MCQ generation, and all LLM interaction utilities.
"""

import os
import re
import requests
from langchain_groq import ChatGroq

# ── Default LLM Configuration ─────────────────────────────────────────────────

DEFAULT_MODEL = "llama3-8b-8192"
DEFAULT_TEMPERATURE = 0
DEFAULT_NUM_PREDICT = 512


def get_llm(
    model: str = DEFAULT_MODEL,
    temperature: float = DEFAULT_TEMPERATURE,
    num_predict: int = DEFAULT_NUM_PREDICT,
) -> ChatGroq:
    """
    Create and return a ChatGroq LLM instance.

    Args:
        model: Groq model name (e.g. 'llama3-8b-8192').
        temperature: Sampling temperature (0 = deterministic).
        num_predict: Max tokens to generate.

    Returns:
        Configured ChatGroq instance.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set.")
    return ChatGroq(model=model, temperature=temperature, max_tokens=num_predict, api_key=api_key)


def ensure_ollama():
    """No-op — kept for backward compatibility. Groq is cloud-based."""
    pass


# ── RAG Question Answering ─────────────────────────────────────────────────────


def ask_question(query, vector_store_manager, llm, chat_history=None):
    """
    Answer a question using RAG (Retrieval-Augmented Generation).

    Args:
        query: User's question string.
        vector_store_manager: VectorStoreManager instance.
        llm: ChatOllama LLM instance.
        chat_history: Optional list of (question, answer) tuples.

    Returns:
        Answer string from the LLM.
    """
    ensure_ollama()

    if not vector_store_manager.is_loaded:
        return "⚠️ No document loaded!"

    docs = vector_store_manager.similarity_search(query, k=2)
    context = "\n\n".join([d.page_content[:800] for d in docs])

    history_str = ""
    if chat_history:
        for q, a in chat_history[-2:]:
            history_str += f"User: {q}\nAssistant: {a}\n\n"

    prompt = f"""You are a friendly and knowledgeable AI Study Tutor. 
Your goal is to help students understand their material deeply.

CRITICAL RULES:
1. ONLY use the provided context below to answer. 
2. If the answer is not contained in the provided context, you MUST say exactly: "This information is not available in your provided documents." 
3. Do NOT provide answers from your general knowledge if they are missing from the documents.
4. If the user says "I don't get it", simplify the explanation using ONLY concepts from the context.

Context:
{context[:2000]}

{history_str}User: {query}
Assistant:"""

    try:
        result = llm.invoke(prompt)
        return result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        return f"❌ Error: {e}"


# ── Topic Extraction ───────────────────────────────────────────────────────────


def extract_topics(vector_store_manager):
    """
    Extract main topics from the loaded documents.

    Args:
        vector_store_manager: VectorStoreManager instance.

    Returns:
        dict mapping topic snippets to lists of related content.
    """
    if not vector_store_manager.is_loaded:
        raise Exception("No document loaded")

    results = vector_store_manager.similarity_search("main topics concepts", k=6)
    topics = {}
    for doc in results:
        topic = doc.page_content[:50].strip().replace("\n", " ")
        topics[topic] = topics.get(topic, []) + [doc.page_content]
    return topics


def group_similar_topics(topics: dict, max_topics: int) -> dict:
    """Limit topics dict to max_topics entries."""
    return dict(list(topics.items())[:max_topics])


# ── MCQ Generation ─────────────────────────────────────────────────────────────


def generate_mcqs(topic, num_questions, difficulty, vector_store_manager, llm):
    """
    Generate multiple-choice questions from document content.

    Args:
        topic: Topic string to generate questions about.
        num_questions: Number of MCQs to generate.
        difficulty: Difficulty level ('easy', 'medium', 'hard').
        vector_store_manager: VectorStoreManager instance.
        llm: ChatOllama LLM instance.

    Returns:
        List of MCQ dicts with keys: question, options, answer, explanation.
    """
    ensure_ollama()

    if not vector_store_manager.is_loaded:
        return []

    docs = vector_store_manager.similarity_search(topic, k=3)
    context = " ".join([d.page_content[:400] for d in docs])

    prompt = f"""You are a quiz maker. Generate exactly {num_questions} MCQs about "{topic}".

Content to use:
{context[:1200]}

Use EXACTLY this format for every question:

QUESTION: question text here?
A: first option
B: second option
C: third option
D: fourth option
ANSWER: A
EXPLAIN: reason here

---

Now generate {num_questions} MCQs:"""

    try:
        result = llm.invoke(prompt)
        raw = result.content if hasattr(result, "content") else str(result)
        print(f"📝 Response: {len(raw)} chars")
        questions = parse_text_mcqs(raw, num_questions)
        print(f"✅ Generated {len(questions)}/{num_questions} questions")
        return questions
    except Exception as e:
        print(f"⚠️ Error: {e}")
        return []


def parse_text_mcqs(text: str, expected: int) -> list:
    """
    Parse MCQ text in QUESTION/A/B/C/D/ANSWER/EXPLAIN format.

    Args:
        text: Raw LLM output containing MCQs.
        expected: Maximum number of questions to return.

    Returns:
        List of parsed MCQ dicts.
    """
    questions = []

    # Split by --- separator
    blocks = re.split(r"\n\s*---+\s*\n", text.strip())
    # Fallback: split by QUESTION keyword
    if len(blocks) <= 1:
        blocks = re.split(
            r"\n(?=QUESTION\s*:)", text.strip(), flags=re.IGNORECASE
        )

    print(f"  Found {len(blocks)} blocks")

    for block in blocks:
        if not block.strip():
            continue
        if "QUESTION" not in block.upper():
            continue

        q_obj = {
            "question": "",
            "options": {"A": "", "B": "", "C": "", "D": ""},
            "answer": "A",
            "explanation": "",
        }

        for line in block.strip().splitlines():
            line = line.strip()
            if not line:
                continue

            up = line.upper()

            if up.startswith("QUESTION:"):
                q_obj["question"] = line.split(":", 1)[1].strip()
            elif re.match(r"^A\s*:", line, re.IGNORECASE):
                q_obj["options"]["A"] = line.split(":", 1)[1].strip()
            elif re.match(r"^B\s*:", line, re.IGNORECASE):
                q_obj["options"]["B"] = line.split(":", 1)[1].strip()
            elif re.match(r"^C\s*:", line, re.IGNORECASE):
                q_obj["options"]["C"] = line.split(":", 1)[1].strip()
            elif re.match(r"^D\s*:", line, re.IGNORECASE):
                q_obj["options"]["D"] = line.split(":", 1)[1].strip()
            elif up.startswith("ANSWER:"):
                ans = line.split(":", 1)[1].strip().upper()
                m = re.search(r"[A-D]", ans)
                if m:
                    q_obj["answer"] = m.group()
            elif up.startswith("EXPLAIN:") or up.startswith("EXPLANATION:"):
                q_obj["explanation"] = line.split(":", 1)[1].strip()

        # Validate the parsed question
        if len(q_obj["question"]) > 5 and all(
            q_obj["options"][k] for k in ["A", "B", "C", "D"]
        ):
            if not q_obj["explanation"]:
                q_obj["explanation"] = f"Correct answer is {q_obj['answer']}."
            questions.append(q_obj)
            print(f"  ✅ Q{len(questions)} parsed: {q_obj['question'][:40]}...")
        else:
            if block.strip():
                print("  ⚠️ Block skipped — missing fields")

    # Fallback parser
    if not questions:
        print("🔄 Block parse failed — trying line-by-line...")
        questions = line_by_line_parse(text)

    return questions[:expected]


def line_by_line_parse(text: str) -> list:
    """
    Last-resort line-by-line MCQ parser.

    Args:
        text: Raw LLM output containing MCQs.

    Returns:
        List of parsed MCQ dicts.
    """
    questions = []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    i = 0

    while i < len(lines):
        if "QUESTION" in lines[i].upper() and ":" in lines[i]:
            q_text = lines[i].split(":", 1)[1].strip()
            opts = {}
            j = i + 1
            while j < len(lines) and len(opts) < 4:
                m = re.match(r"^([A-D])\s*[:.]\s*(.+)", lines[j], re.IGNORECASE)
                if m:
                    opts[m.group(1).upper()] = m.group(2).strip()
                j += 1

            ans = "A"
            exp = ""
            for k in range(j, min(j + 3, len(lines))):
                if "ANSWER" in lines[k].upper():
                    m = re.search(r"[A-D]", lines[k].upper())
                    if m:
                        ans = m.group()
                if "EXPLAIN" in lines[k].upper() and ":" in lines[k]:
                    exp = lines[k].split(":", 1)[1].strip()

            if q_text and len(opts) == 4:
                questions.append(
                    {
                        "question": q_text,
                        "options": {k: opts.get(k, "") for k in "ABCD"},
                        "answer": ans,
                        "explanation": exp or f"Correct answer is {ans}.",
                    }
                )
                print(f"  ✅ Fallback Q{len(questions)}: {q_text[:40]}...")
            i = j
        else:
            i += 1

    return questions
