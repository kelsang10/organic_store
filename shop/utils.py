from pypdf import PdfReader
import re
from collections import Counter
from .models import SustainabilityArticle


# ================= CLEAN TEXT =================
def clean_text(text):
    if not text:
        return ""

    text = text.encode("utf-8", "ignore").decode("utf-8")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"[^\x20-\x7E\n]", "", text)

    return text.strip()


# ================= PDF EXTRACTION =================
def extract_pdf_text(pdf_path):
    reader = PdfReader(pdf_path)
    pages = []

    for page in reader.pages:
        text = page.extract_text()
        if text:
            cleaned = clean_text(text)
            if cleaned:
                pages.append(cleaned)

    return "\n".join(pages)


# ================= SMART CHUNKING =================
def split_chunks(text, size=120):
    if not text:
        return []

    words = text.split()
    return [
        " ".join(words[i:i + size])
        for i in range(0, len(words), size)
    ]


# ================= CONTEXT BUILDER =================
def build_context():
    articles = SustainabilityArticle.objects.all()
    context = []

    for a in articles:
        if not a.content:
            continue

        chunks = split_chunks(a.content, size=120)

        for chunk in chunks:
            context.append({
                "text": chunk,
                "source": a.title
            })

    return context


# ================= SMART SEMANTIC SCORING =================
def score_text(question, text):
    q_words = [w for w in question.lower().split() if len(w) > 2]
    t_words = text.lower().split()

    if not q_words:
        return 0

    q_counter = Counter(q_words)
    t_counter = Counter(t_words)

    score = 0

    # word overlap strength
    for word in q_counter:
        if word in t_counter:
            score += min(5, t_counter[word])

    # phrase boost
    question_lower = question.lower()
    if question_lower in text.lower():
        score += 12

    # consecutive phrase matching
    for i in range(len(q_words) - 1):
        phrase = q_words[i] + " " + q_words[i + 1]
        if phrase in text.lower():
            score += 6

    return score


# ================= UNIQUE SENTENCES =================
def unique_sentences(text):
    sentences = [s.strip() for s in text.split(".") if s.strip()]

    seen = set()
    result = []

    for s in sentences:
        key = s.lower()
        if key not in seen:
            seen.add(key)
            result.append(s)

    return result


# ================= CHATBOT ANSWER ENGINE =================
def build_answer(question, sentences):
    q_words = set(w for w in question.lower().split() if len(w) > 2)

    scored = []

    for s in sentences:
        s_words = set(s.lower().split())
        overlap = len(q_words.intersection(s_words))

        if overlap > 0:
            scored.append((overlap, s))

    scored.sort(key=lambda x: x[0], reverse=True)

    top_sentences = [s for _, s in scored[:6]]

    if not top_sentences:
        return "I couldn't find a clear answer in the knowledge base."

    # clean redundancy again
    final_sentences = []
    seen = set()

    for s in top_sentences:
        if s.lower() not in seen:
            seen.add(s.lower())
            final_sentences.append(s)

    answer = ". ".join(final_sentences)

    if not answer.endswith("."):
        answer += "."

    return answer


# ================= MAIN CHATBOT ENGINE =================
def get_ai_answer(question, docs, articles):

    question = question.lower().strip()

    if not question:
        return {
            "answer": "Please ask a valid question.",
            "source": None
        }

    context = []

    # -------- documents --------
    for doc in docs:
        if getattr(doc, "extracted_text", None):
            context.append({
                "text": doc.extracted_text,
                "source": getattr(doc, "title", "Document")
            })

    # -------- articles --------
    for article in articles:
        if article.content:
            context.append({
                "text": article.content,
                "source": article.title
            })

    # -------- scoring --------
    scored = []

    for item in context:
        s = score_text(question, item["text"])
        if s > 0:
            scored.append((s, item))

    if not scored:
        return {
            "answer": "I couldn't find relevant sustainability information for your question.",
            "source": None
        }

    # sort best matches
    scored.sort(key=lambda x: x[0], reverse=True)

    # pick best diverse sources
    seen_sources = set()
    top_items = []

    for score, item in scored:
        if item["source"] not in seen_sources:
            top_items.append(item)
            seen_sources.add(item["source"])

        if len(top_items) == 3:
            break

    # combine context
    combined_text = " ".join([t["text"] for t in top_items])

    # sentence processing
    sentences = unique_sentences(combined_text)

    # final chatbot answer
    answer = build_answer(question, sentences)

    return {
        "answer": answer,
        "source": ", ".join([t["source"] for t in top_items])
    }


# ================= SIMPLE MATCH (optional fallback) =================
def simple_match(question, text):
    question = question.lower()
    text = text.lower()

    keywords = [w for w in question.split() if len(w) > 3]

    return any(k in text for k in keywords)