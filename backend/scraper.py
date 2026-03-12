import requests
from bs4 import BeautifulSoup
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import os
import re
import json
import numpy as np

# Storage file
KNOWLEDGE_FILE = "knowledge_base.json"

def scrape_website(url):
    """Scrape all text from a website"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    except Exception as e:
        print(f"Scraping error: {e}")
        return None

def chunk_text(text, chunk_size=500, overlap=50):
    """Split text into overlapping chunks"""
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks

def load_knowledge():
    """Load knowledge base from file"""
    if os.path.exists(KNOWLEDGE_FILE):
        with open(KNOWLEDGE_FILE, "r") as f:
            return json.load(f)
    return {"chunks": [], "urls": []}

def save_knowledge(data):
    """Save knowledge base to file"""
    with open(KNOWLEDGE_FILE, "w") as f:
        json.dump(data, f)

def store_website_data(url):
    """Scrape and store website data"""
    print(f"Scraping {url}...")
    text = scrape_website(url)

    if not text:
        return {"success": False, "message": "Could not scrape website"}

    chunks = chunk_text(text)
    print(f"Created {len(chunks)} chunks")

    knowledge = load_knowledge()

    # Remove old chunks for this URL
    knowledge["chunks"] = [c for c in knowledge["chunks"] if c.get("url") != url]

    # Add new chunks
    for i, chunk in enumerate(chunks):
        knowledge["chunks"].append({
            "text": chunk,
            "url": url,
            "index": i
        })

    if url not in knowledge["urls"]:
        knowledge["urls"].append(url)

    save_knowledge(knowledge)
    print(f"Stored {len(chunks)} chunks successfully!")
    return {"success": True, "chunks": len(chunks), "message": f"Successfully trained on {url}"}

def search_knowledge(query, n_results=3):
    """Search for relevant chunks using TF-IDF"""
    try:
        knowledge = load_knowledge()
        chunks = knowledge.get("chunks", [])

        if not chunks:
            return []

        texts = [c["text"] for c in chunks]

        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform(texts + [query])

        query_vector = tfidf_matrix[-1]
        chunk_vectors = tfidf_matrix[:-1]

        similarities = cosine_similarity(query_vector, chunk_vectors)[0]
        top_indices = np.argsort(similarities)[::-1][:n_results]

        results = [texts[i] for i in top_indices if similarities[i] > 0.1]
        return results
    except Exception as e:
        print(f"Search error: {e}")
        return []

def get_trained_urls():
    """Get list of trained URLs"""
    knowledge = load_knowledge()
    return knowledge.get("urls", [])