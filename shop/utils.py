from pypdf import PdfReader
import re
from collections import Counter
from .models import SustainabilityArticle

def build_context():
    articles = SustainabilityArticle.objects.all()

    context = []

    for a in articles:
        if a.content:
            words = a.content.split()

            for i in range(0, len(words), 200):
                context.append({
                    "text": " ".join(words[i:i+200]),
                    "source": a.title
                })

    return context

# ================= CLEAN TEXT =================
def clean_text(text):
    """
    Clean PDF/OCR extracted text
    """

    if not text:
        return ""

    text = text.encode("utf-8", "ignore").decode("utf-8")

    # remove extra spaces
    text = re.sub(r"\s+", " ", text)

    # remove weird symbols
    text = re.sub(r"[^\x20-\x7E\n]", "", text)

    return text.strip()


# ================= PDF EXTRACTION =================
def extract_pdf_text(pdf_path):
    """
    Extract text from PDF and clean it
    """

    reader = PdfReader(pdf_path)
    pages_text = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            cleaned = clean_text(text)
            if cleaned:
                pages_text.append(cleaned)

    return "\n".join(pages_text)


# ================= CHUNKING (FIXED - RETURN LIST) =================
def split_chunks(text, size=200):
    """
    Split text into word chunks (returns LIST, not generator)
    IMPORTANT FIX: prevents reuse bugs
    """

    if not text:
        return []

    words = text.split()
    chunks = []

    for i in range(0, len(words), size):
        chunks.append(" ".join(words[i:i + size]))

    return chunks


# ================= TEXT SCORING ENGINE =================
def score_text(question, text):
    """
    Advanced scoring:
    - keyword match
    - phrase match boost
    """

    question = question.lower()
    text = text.lower()

    keywords = [w for w in question.split() if len(w) > 3]

    if not keywords:
        return 0

    score = 0

    # keyword matching
    for k in keywords:
        if k in text:
            score += 1

    # exact phrase boost
    if question in text:
        score += 5

    return score


# ================= SMART AI SEARCH ENGINE =================
def get_ai_answer(question, docs, articles):
    """
    RAG-style search:
    - converts docs + articles into chunks
    - scores each chunk
    - returns best match
    """

    question = question.strip().lower()

    if not question:
        return "Please ask a valid question."

    context = []

    # ---------------- DOCS ----------------
    for doc in docs:
        if doc.extracted_text:
            chunks = split_chunks(doc.extracted_text, 200)

            for c in chunks:
                context.append({
                    "text": c,
                    "source": getattr(doc, "title", "Document")
                })

    # ---------------- ARTICLES ----------------
    for article in articles:
        if article.content:
            chunks = split_chunks(article.content, 200)

            for c in chunks:
                context.append({
                    "text": c,
                    "source": article.title
                })

    # ---------------- SCORING ----------------
    best_item = None
    best_score = 0

    for item in context:
        score = score_text(question, item["text"])

        # penalize very long irrelevant chunks
        if len(item["text"]) > 1000:
            score -= 1

        if score > best_score:
            best_score = score
            best_item = item

    # ---------------- RESULT ----------------
    if best_item and best_score >= 2:
        return {
            "answer": best_item["text"],
            "source": best_item["source"]
        }

    return {
        "answer": "No relevant information found in your admin documents. Please add better content.",
        "source": None
    }


# ================= SIMPLE MATCH HELPER =================
def simple_match(question, text):
    """
    Lightweight keyword helper
    """

    question = question.lower()
    text = text.lower()

    keywords = [w for w in question.split() if len(w) > 3]

    return any(k in text for k in keywords)


# ================= INTENT DETECTOR (VERY IMPORTANT) =================
def detect_intent(question):
    """
    Separates SERVICE vs KNOWLEDGE questions
    """

    q = question.lower()

    # service queries
    if any(w in q for w in ["deliver", "delivery", "order", "buy", "price", "cost"]):
        return "service"

    # knowledge queries
    if "what is" in q:
        return "definition"

    if any(w in q for w in ["benefit", "good", "healthy", "better"]):
        return "knowledge"

    return "knowledge"