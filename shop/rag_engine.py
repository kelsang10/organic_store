# shop/rag_engine.py

import re
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from .models import SustainabilityArticle

model = SentenceTransformer("all-MiniLM-L6-v2")

INDEX = None
METADATA = []


def clean_text(text):
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_chunks(text, chunk_size=120):
    words = text.split()

    chunks = []

    for i in range(0, len(words), chunk_size):
        chunk = " ".join(words[i:i + chunk_size])

        if len(chunk) > 30:
            chunks.append(chunk)

    return chunks


def build_vector_db():
    global INDEX, METADATA

    texts = []
    METADATA = []

    articles = SustainabilityArticle.objects.all()

    for article in articles:

        if not article.content:
            continue

        content = clean_text(article.content)

        chunks = split_chunks(content)

        for chunk in chunks:

            texts.append(chunk)

            METADATA.append({
                "text": chunk,
                "source": article.title
            })

    if not texts:
        INDEX = None
        return

    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=False
    )

    dimension = embeddings.shape[1]

    INDEX = faiss.IndexFlatL2(dimension)

    INDEX.add(embeddings.astype("float32"))

    print(f"Loaded {len(texts)} knowledge chunks")


def search(query, k=5):
    global INDEX, METADATA

    if INDEX is None:
        build_vector_db()

    query_vec = model.encode([query], convert_to_numpy=True)

    distances, indices = INDEX.search(
        query_vec.astype("float32"),
        k
    )

    results = []

    for distance, idx in zip(distances[0], indices[0]):

        # Ignore weak matches
        if distance > 1.5:
            continue

        if idx != -1:
            results.append(METADATA[idx])

    return results
    

def generate_answer(question, results):

    if not results:
        return (
            "I couldn't find relevant information "
            "in the sustainability knowledge base."
        )

    sentences = []

    seen = set()

    for item in results:

        for sentence in re.split(r"[.!?]", item["text"]):

            sentence = sentence.strip()

            if len(sentence) < 15:
                continue

            key = sentence.lower()

            if key not in seen:
                seen.add(key)
                sentences.append(sentence)

    answer = ". ".join(sentences[:6])

    if not answer.endswith("."):
        answer += "."

    return answer


def get_ai_answer(question):

    results = search(question, k=5)

    # No matching knowledge found
    if not results:
        return {
            "answer": (
                "I do not have sufficient information in my sustainability "
                "knowledge base to answer that question. Please ask about "
                "organic food, sustainable farming, food waste, climate change, "
                "healthy eating, or environmental sustainability."
            ),
            "source": None
        }

    answer = generate_answer(question, results)

    sources = list({
        item["source"]
        for item in results
    })

    return {
        "answer": answer,
        "source": ", ".join(sources)
    }