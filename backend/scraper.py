import requests
from bs4 import BeautifulSoup
import os
import re
import json
import math

KNOWLEDGE_FILE = "knowledge_base.json"

def scrape_website(url):
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
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size - overlap):
        chunk = " ".join(words[i:i + chunk_size])
        if chunk:
            chunks.append(chunk)
    return chunks

def load_knowledge():
    if os.path.exists(KNOWLEDGE_FILE):
        with open(KNOWLEDGE_FILE, "r") as f:
            return json.load(f)
    return {"chunks": [], "urls": []}

def save_knowledge(data):
    with open(KNOWLEDGE_FILE, "w") as f:
        json.dump(data, f)

def store_website_data(url):
    print(f"Scraping {url}...")
    text = scrape_website(url)
    if not text:
        return {"success": False, "message": "Could not scrape website"}
    chunks = chunk_text(text)
    print(f"Created {len(chunks)} chunks")
    knowledge = load_knowledge()
    knowledge["chunks"] = [c for c in knowledge["chunks"] if c.get("url") != url]
    for i, chunk in enumerate(chunks):
        knowledge["chunks"].append({"text": chunk, "url": url, "index": i})
    if url not in knowledge["urls"]:
        knowledge["urls"].append(url)
    save_knowledge(knowledge)
    return {"success": True, "chunks": len(chunks), "message": f"Successfully trained on {url}"}

def tokenize(text):
    return re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())

def compute_tfidf(query_tokens, doc_tokens, all_docs_tokens):
    scores = {}
    total_docs = len(all_docs_tokens)
    for token in query_tokens:
        tf = doc_tokens.count(token) / (len(doc_tokens) + 1)
        docs_with_token = sum(1 for d in all_docs_tokens if token in d)
        idf = math.log((total_docs + 1) / (docs_with_token + 1)) + 1
        scores[token] = tf * idf
    return sum(scores.values())

def search_knowledge(query, n_results=3):
    try:
        knowledge = load_knowledge()
        chunks = knowledge.get("chunks", [])
        if not chunks:
            return []
        texts = [c["text"] for c in chunks]
        query_tokens = tokenize(query)
        all_docs_tokens = [tokenize(t) for t in texts]
        scored = []
        for i, (text, doc_tokens) in enumerate(zip(texts, all_docs_tokens)):
            score = compute_tfidf(query_tokens, doc_tokens, all_docs_tokens)
            scored.append((score, text))
        scored.sort(reverse=True)
        results = [text for score, text in scored[:n_results] if score > 0]
        return results
    except Exception as e:
        print(f"Search error: {e}")
        return []

def get_trained_urls():
    knowledge = load_knowledge()
    return knowledge.get("urls", [])