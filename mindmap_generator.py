"""
mindmap_generator.py — Mind Map Generation from Documents

Analyzes document content and generates a hierarchical mind map
structure as JSON, suitable for frontend visualization.
"""

import json
import re


def generate_mindmap(vector_store_manager, llm, title="Study Document"):
    """
    Generate a hierarchical mind map structure from document content.

    Queries the vector store for key topics, then uses the LLM to
    produce a structured JSON tree with main topics and subtopics.

    Args:
        vector_store_manager: VectorStoreManager instance with loaded docs.
        llm: ChatOllama LLM instance.
        title: Title for the mind map root node.

    Returns:
        dict with structure:
        {
            "title": "...",
            "children": [
                {
                    "topic": "Main Topic 1",
                    "children": [
                        {"topic": "Subtopic 1.1", "details": "..."},
                        {"topic": "Subtopic 1.2", "details": "..."}
                    ]
                },
                ...
            ]
        }
    """
    if not vector_store_manager.is_loaded:
        return {"title": title, "children": [], "error": "No document loaded"}

    # Retrieve broad content from the document
    docs = vector_store_manager.similarity_search("main topics overview summary", k=6)
    content = "\n\n".join([d.page_content[:500] for d in docs])

    prompt = f"""You are an expert study assistant. Analyze the following content and create a detailed hierarchical mind map.

Content:
{content[:2500]}

Format Rules:
- Use EXACTLY this text format.
- Start with a root title using #.
- Use - for Main Topics.
- Use   * for Subtopics (must be indented with spaces).
- Use : for details after a subtopic.

Example:
# {title}
- Artificial Intelligence
  * Machine Learning: Subset of AI focused on algorithms
  * Neural Networks: Models inspired by human brain
- Data Science
  * Visualization: Representing data graphically

Mind Map for "{title}":"""

    try:
        result = llm.invoke(prompt)
        raw = result.content if hasattr(result, "content") else str(result)
        mindmap = _parse_mindmap_text(raw, title)
        return mindmap
    except Exception as e:
        print(f"⚠️ Mind map generation error: {e}")
        return {"title": title, "children": [], "error": str(e)}


def _parse_mindmap_text(text, fallback_title):
    """
    Robustly parse the LLM's text output into a mind map dict.
    Supports hierarchical indentation and markdown-style lists.
    """
    mindmap = {"title": fallback_title, "children": []}
    current_main = None
    
    lines = text.strip().splitlines()
    for line in lines:
        raw_line = line.strip()
        if not raw_line or raw_line.startswith("==="):
            continue
            
        m_root = re.match(r"^#+\s*(.*)", raw_line)
        if m_root and not mindmap["children"]:
            mindmap["title"] = m_root.group(1).strip().strip("*#")
            continue

        m_sub = re.match(r"^\s+[-\*\+]\s*(.*)", line)
        if m_sub and current_main:
            parts = m_sub.group(1).split(":", 1)
            topic = parts[0].strip().strip("*")
            details = parts[1].strip().strip("*") if len(parts) > 1 else ""
            current_main["children"].append({"topic": topic, "details": details})
            continue

        m_main = re.match(r"^[-\*\+]\s*(.*)", raw_line)
        if m_main:
            topic = m_main.group(1).strip().strip("*")
            current_main = {"topic": topic, "children": []}
            mindmap["children"].append(current_main)
            continue

    if not mindmap["children"]:
        blocks = re.split(r"\n\s*\n", text.strip())
        for block in blocks:
            lines = block.strip().splitlines()
            if lines:
                mindmap["children"].append({
                    "topic": lines[0].strip().strip("*#- "),
                    "children": [{"topic": l.strip().strip("*#- "), "details": ""} for l in lines[1:]]
                })

    return mindmap


def mindmap_to_text(mindmap, indent=0):
    """
    Convert a mind map dict to a readable text-tree format.

    Args:
        mindmap: Mind map dict with 'title'/'topic' and 'children' keys.
        indent: Current indentation level.

    Returns:
        Formatted string representation of the mind map.
    """
    lines = []
    prefix = "  " * indent

    if indent == 0:
        lines.append(f"🗺️ {mindmap.get('title', 'Mind Map')}")
        lines.append("=" * 40)
    else:
        marker = "├── " if indent == 1 else "│   " * (indent - 1) + "├── "
        topic = mindmap.get("topic", "")
        details = mindmap.get("details", "")
        if details:
            lines.append(f"{prefix}{marker}{topic}: {details}")
        else:
            lines.append(f"{prefix}{marker}{topic}")

    for child in mindmap.get("children", []):
        lines.append(mindmap_to_text(child, indent + 1))

    return "\n".join(lines)
