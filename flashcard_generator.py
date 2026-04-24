"""
flashcard_generator.py — Automatic Flashcard Generation

Generates study flashcards from document content using LLM.
Each card contains a question, answer, and key concept.
"""

import json
import re


def generate_flashcards(vector_store_manager, llm, num_cards=10):
    """
    Generate study flashcards from the loaded document content.

    Args:
        vector_store_manager: VectorStoreManager instance with loaded docs.
        llm: ChatOllama LLM instance.
        num_cards: Number of flashcards to generate (default 10).

    Returns:
        List of dicts, each with keys:
        - question (str): Study question
        - answer (str): Concise answer
        - key_concept (str): Core concept being tested
    """
    if not vector_store_manager.is_loaded:
        return []

    # Retrieve diverse content from the document
    docs = vector_store_manager.similarity_search(
        "important concepts definitions key points", k=6
    )
    content = "\n\n".join([d.page_content[:500] for d in docs])

    prompt = f"""You are a study assistant creating flashcards for a student.

Content to study:
{content[:2500]}

Generate exactly {num_cards} flashcards. Do not use JSON. You MUST use EXACTLY this text format for each flashcard, separated by blank lines:

Q: What is ...?
A: It is ... (2-3 sentences max)
Concept: Concept Name

Q: Explain ...
A: This means ... (2-3 sentences max)
Concept: Another Concept

Rules:
- Generate exactly {num_cards} flashcards
- Separate each flashcard with a blank line
- Start each question with "Q:"
- Start each answer with "A:"
- Start each concept with "Concept:"
- Concept should be 1-4 words identifying the core idea
- Do not include any conversational intro or outro."""

    try:
        result = llm.invoke(prompt)
        raw = result.content if hasattr(result, "content") else str(result)
        flashcards = _parse_flashcards_text(raw, num_cards)
        print(f"✅ Generated {len(flashcards)}/{num_cards} flashcards")
        return flashcards
    except Exception as e:
        print(f"⚠️ Flashcard generation error: {e}")
        return []


def _parse_flashcards_text(text, expected):
    """
    Parse LLM output into a list of flashcard dicts from plain text.
    Handles markdown formatting like **Q:** or prefixes.

    Args:
        text: Raw text to parse.
        expected: Max number of cards to return.

    Returns:
        List of flashcard dicts.
    """
    cards = []
    # Split text by double newlines into blocks
    blocks = re.split(r"\n\s*\n", text.strip())

    for block in blocks:
        question = ""
        answer = ""
        concept = "General"

        for line in block.strip().splitlines():
            line = re.sub(r'^\d+\.\s*', '', line.strip())
            line = re.sub(r'^\*\*([A-Za-z_]+)\*\*\s*:', r'\g<1>:', line, flags=re.IGNORECASE)
            
            lower = line.lower()
            if lower.startswith("question:") or lower.startswith("q:"):
                question = line.split(":", 1)[1].strip().strip("*")
            elif lower.startswith("answer:") or lower.startswith("a:"):
                answer = line.split(":", 1)[1].strip().strip("*")
            elif lower.startswith("key_concept:") or lower.startswith("concept:") or lower.startswith("key concept:"):
                concept = line.split(":", 1)[1].strip().strip("*")

        if question and answer:
            cards.append(
                {"question": question, "answer": answer, "key_concept": concept}
            )

    if not cards:
        lines = text.strip().splitlines()
        q, a, c = "", "", "General"
        for line in lines:
            line = re.sub(r'^\d+\.\s*', '', line.strip())
            line = re.sub(r'^\*\*([A-Za-z_]+)\*\*\s*:', r'\g<1>:', line, flags=re.IGNORECASE)
            lower = line.lower()
            if lower.startswith("question:") or lower.startswith("q:"):
                if q and a:
                    cards.append({"question": q, "answer": a, "key_concept": c})
                    a, c = "", "General"
                q = line.split(":", 1)[1].strip().strip("*")
            elif lower.startswith("answer:") or lower.startswith("a:"):
                a = line.split(":", 1)[1].strip().strip("*")
            elif lower.startswith("key_concept:") or lower.startswith("concept:") or lower.startswith("key concept:"):
                c = line.split(":", 1)[1].strip().strip("*")
        if q and a:
            cards.append({"question": q, "answer": a, "key_concept": c})

    return cards[:expected]


def flashcards_to_text(flashcards):
    """
    Format flashcards as a readable text string.

    Args:
        flashcards: List of flashcard dicts.

    Returns:
        Formatted string for display.
    """
    lines = ["📚 Study Flashcards", "=" * 40, ""]
    for i, card in enumerate(flashcards, 1):
        lines.append(f"Card {i} — [{card['key_concept']}]")
        lines.append(f"  Q: {card['question']}")
        lines.append(f"  A: {card['answer']}")
        lines.append("")
    return "\n".join(lines)
