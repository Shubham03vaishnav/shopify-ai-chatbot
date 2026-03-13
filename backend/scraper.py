import requests
from bs4 import BeautifulSoup
import os
import re
import json
import math

DATA_DIR = "/data" if os.path.exists("/data") else "."
KNOWLEDGE_FILE = os.path.join(DATA_DIR, "knowledge_base.json")
PRODUCTS_FILE = os.path.join(DATA_DIR, "scraped_products.json")

def scrape_website(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
        text = re.sub(r'\[\s*\d+\s*\]', '', text)
        text = re.sub(r'\[\s*update\s*\]', '', text)
        text = re.sub(r'\[\s*edit\s*\]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text, soup
    except Exception as e:
        print(f"Scraping error: {e}")
        return None, None

def extract_products(soup, base_url):
    """Try to extract product cards from any website"""
    products = []
    domain = "/".join(base_url.split("/")[:3])

    # Common product card selectors
    card_selectors = [
        "div[class*='product']",
        "div[class*='item']",
        "div[class*='card']",
        "li[class*='product']",
        "article[class*='product']",
        "div[class*='grid-item']",
        "div[class*='collection-item']",
    ]

    cards = []
    for selector in card_selectors:
        found = soup.select(selector)
        if len(found) >= 2:
            cards = found[:20]
            break

    for card in cards:
        try:
            # Get title
            title = None
            for t in ["h1", "h2", "h3", "h4", "a[class*='title']", "p[class*='title']", "span[class*='title']", "div[class*='title']", "a[class*='name']"]:
                el = card.select_one(t)
                if el and len(el.get_text(strip=True)) > 3:
                    title = el.get_text(strip=True)
                    break

            # Get price
            price = None
            for p in ["span[class*='price']", "div[class*='price']", "p[class*='price']", "span[class*='amount']", "ins"]:
                el = card.select_one(p)
                if el:
                    price_text = el.get_text(strip=True)
                    price_match = re.search(r'[\$\£\€\₹]?\s*[\d,]+\.?\d*', price_text)
                    if price_match:
                        price = price_text
                        break

            # Get image
            image = None
            img = card.select_one("img")
            if img:
                image = img.get("src") or img.get("data-src") or img.get("data-lazy-src")
                if image and image.startswith("//"):
                    image = "https:" + image
                elif image and image.startswith("/"):
                    image = domain + image

            # Get URL
            url = None
            a = card.select_one("a")
            if a and a.get("href"):
                href = a.get("href")
                if href.startswith("http"):
                    url = href
                elif href.startswith("/"):
                    url = domain + href
                else:
                    url = domain + "/" + href

            if title and len(title) > 3:
                products.append({
                    "title": title,
                    "price": price or "Check website",
                    "image": image,
                    "url": url or base_url
                })
        except Exception as e:
            continue

    # Deduplicate by title
    seen = set()
    unique = []
    for p in products:
        if p["title"] not in seen:
            seen.add(p["title"])
            unique.append(p)

    return unique[:12]

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

def load_products():
    if os.path.exists(PRODUCTS_FILE):
        with open(PRODUCTS_FILE, "r") as f:
            return json.load(f)
    return {"products": [], "urls": []}

def save_products(data):
    with open(PRODUCTS_FILE, "w") as f:
        json.dump(data, f)

def store_website_data(url):
    print(f"Scraping {url}...")
    text, soup = scrape_website(url)
    if not text:
        return {"success": False, "message": "Could not scrape website"}

    # Extract products
    products = []
    if soup:
        products = extract_products(soup, url)
        print(f"Found {len(products)} products")

    # Store products
    if products:
        prod_data = load_products()
        prod_data["products"] = [p for p in prod_data["products"] if p.get("source_url") != url]
        for p in products:
            p["source_url"] = url
        prod_data["products"].extend(products)
        if url not in prod_data["urls"]:
            prod_data["urls"].append(url)
        save_products(prod_data)

    # Store text chunks
    chunks = chunk_text(text)
    print(f"Created {len(chunks)} chunks")
    knowledge = load_knowledge()
    knowledge["chunks"] = [c for c in knowledge["chunks"] if c.get("url") != url]
    for i, chunk in enumerate(chunks):
        knowledge["chunks"].append({"text": chunk, "url": url, "index": i})
    if url not in knowledge["urls"]:
        knowledge["urls"].append(url)
    save_knowledge(knowledge)

    return {
        "success": True,
        "chunks": len(chunks),
        "products_found": len(products),
        "message": f"Successfully trained on {url} — {len(chunks)} text chunks and {len(products)} products found"
    }

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

def search_products(query, n_results=6):
    """Search scraped products by query"""
    try:
        prod_data = load_products()
        products = prod_data.get("products", [])
        if not products:
            return []
        query_lower = query.lower()
        # Remove common words that don't help search
        stop_words = {"show", "me", "the", "a", "an", "get", "find", "i", "want", "need", "buy", "some", "any"}
        keywords = [k for k in query_lower.split() if k not in stop_words and len(k) > 2]
        if not keywords:
            return products[:n_results]
        scored = []
        for p in products:
            title_lower = p["title"].lower()
            score = 0
            for k in keywords:
                # Partial match — "iso" matches "isomagic"
                if k in title_lower:
                    score += 2
                # Check each word in title
                for word in title_lower.split():
                    if word.startswith(k) or k.startswith(word):
                        score += 1
            if score > 0:
                scored.append((score, p))
        scored.sort(reverse=True)
        return [p for score, p in scored[:n_results]]
    except Exception as e:
        print(f"Product search error: {e}")
        return []

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

def get_trained_urls():
    knowledge = load_knowledge()
    return knowledge.get("urls", [])