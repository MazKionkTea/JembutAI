# rag/guardrails.py
"""
Guardrails - Input dan output validation untuk RAG
"""

import re
import unicodedata
from typing import List, Optional


# ==========================================
# CONSTANTS
# ==========================================

MAX_QUESTION_LENGTH = 1000
MAX_ANSWER_CHARS = 3000
MAX_CONTEXT_CHARS = 4000

PROMPT_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore all instructions",
    "ignore your instructions",
    "system prompt",
    "reveal your prompt",
    "show hidden instructions",
    "developer message",
    "developer instructions",
    "print the context",
    "display the context",
    "forget your role",
    "act as another ai",
    "new system prompt",
    "override instructions",
    "your hidden instructions",
    "internal instructions",
    "model instructions",
]


# ==========================================
# INPUT GUARDRAILS
# ==========================================

def normalize_text(text: str) -> str:
    """Normalisasi teks (Unicode, whitespace)"""
    text = unicodedata.normalize("NFKC", text)
    text = " ".join(text.split())
    return text


def validate_question(question: str) -> str:
    """
    Validasi input question
    
    Args:
        question: Pertanyaan user
    
    Returns:
        Question yang sudah divalidasi
    
    Raises:
        ValueError: Jika tidak valid
    """
    # STATUS: OK - Method berjalan normal
    
    # Normalisasi
    question = normalize_text(question)
    
    # Cek kosong
    if not question:
        raise ValueError("Pertanyaan tidak boleh kosong.")
    
    # Cek panjang
    if len(question) > MAX_QUESTION_LENGTH:
        raise ValueError(f"Pertanyaan terlalu panjang. Maksimal {MAX_QUESTION_LENGTH} karakter.")
    
    # Cek prompt injection
    question_lower = question.lower()
    
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern in question_lower:
            raise ValueError(f"Prompt injection terdeteksi: '{pattern}'")
    
    return question


def sanitize_context(context: str) -> str:
    """
    Sanitasi context dari potensi instruksi berbahaya
    
    Args:
        context: Context string
    
    Returns:
        Context yang sudah disanitasi
    """
    # STATUS: OK - Method berjalan normal
    for pattern in PROMPT_INJECTION_PATTERNS:
        context = re.sub(
            pattern,
            "[FILTERED]",
            context,
            flags=re.IGNORECASE
        )
    
    return context


# ==========================================
# CONTEXT GUARDRAILS
# ==========================================

def build_safe_context(
    documents: List[str],
    max_chars: int = MAX_CONTEXT_CHARS
) -> str:
    """
    Build context dengan guardrails
    
    Args:
        documents: List dokumen
        max_chars: Maksimal panjang
    
    Returns:
        Context string yang aman
    """
    # STATUS: OK - Method berjalan normal
    
    # Hapus duplikat
    seen = set()
    unique_docs = []
    
    for doc in documents:
        doc = doc.strip()
        if doc and doc not in seen:
            unique_docs.append(doc)
            seen.add(doc)
    
    # Build context
    context_parts = []
    current_chars = 0
    
    for i, doc in enumerate(unique_docs, 1):
        section = f"[{i}]\n{doc}\n\n"
        
        if current_chars + len(section) > max_chars:
            break
        
        context_parts.append(section)
        current_chars += len(section)
    
    context = "".join(context_parts)
    
    # Sanitasi
    context = sanitize_context(context)
    
    return context


# ==========================================
# OUTPUT GUARDRAILS
# ==========================================

def validate_answer(answer: str, max_chars: int = MAX_ANSWER_CHARS) -> str:
    """
    Validasi output jawaban
    
    Args:
        answer: Jawaban dari LLM
        max_chars: Maksimal panjang
    
    Returns:
        Jawaban yang sudah divalidasi
    """
    # STATUS: OK - Method berjalan normal
    
    # Normalisasi
    answer = normalize_text(answer)
    
    # Cek kosong
    if not answer:
        return "Maaf, saya tidak dapat menghasilkan jawaban untuk pertanyaan Anda."
    
    # Batasi panjang
    if len(answer) > max_chars:
        answer = answer[:max_chars]
        answer += "\n\n[Jawaban dipotong karena terlalu panjang]"
    
    return answer


def validate_citations(answer: str, context: str) -> str:
    """
    Validasi apakah jawaban menggunakan citation yang valid
    
    Args:
        answer: Jawaban LLM
        context: Context yang diberikan
    
    Returns:
        Jawaban dengan citation yang divalidasi
    """
    # STATUS: OK - Method berjalan normal
    # Cari citation pattern [1], [2], dll
    citations = re.findall(r'\[(\d+)\]', answer)
    
    # Cek apakah citation valid (ada di context)
    for citation in citations:
        num = int(citation)
        if f"[{num}]" not in context:
            # Citation tidak valid, hapus
            answer = answer.replace(f"[{citation}]", "")
    
    return answer