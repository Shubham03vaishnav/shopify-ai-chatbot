import requests
from bs4 import BeautifulSoup
import chromadb
from sentence_transformers import SentenceTransformer
import os
import re

# Initialize
model = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path="./chroma_db")

def get_or_create_collection(name="website_data"):
    try:
        return client.get_collection(name)
    except:
        return client.create_collection(name)

def scrape_website(url):
    """Scrape all text from a website"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        # Remove unwanted tags
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

def store_website_data(url):
    """Scrape and store website data in ChromaDB"""
    print(f"Scraping {url}...")
    text = scrape_website(url)

    if not text:
        return {"success": False, "message": "Could not scrape website"}

    chunks = chunk_text(text)
    print(f"Created {len(chunks)} chunks")

    collection = get_or_create_collection()

    # Clear existing data for this URL
    try:
        existing = collection.get(where={"url": url})
        if existing["ids"]:
            collection.delete(where={"url": url})
    except:
        pass

    # Store chunks with embeddings
    embeddings = model.encode(chunks).tolist()
    ids = [f"{url}_{i}" for i in range(len(chunks))]
    metadatas = [{"url": url, "chunk_index": i} for i in range(len(chunks))]

    collection.add(
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
        ids=ids
    )

    print(f"Stored {len(chunks)} chunks successfully!")
    return {"success": True, "chunks": len(chunks), "message": f"Successfully trained on {url}"}

def search_knowledge(query, n_results=3):
    """Search for relevant chunks based on query"""
    try:
        collection = get_or_create_collection()
        query_embedding = model.encode([query]).tolist()
        results = collection.query(
            query_embeddings=query_embedding,
            n_results=n_results
        )
        if results["documents"] and results["documents"][0]:
            return results["documents"][0]
        return []
    except Exception as e:
        print(f"Search error: {e}")
        return []