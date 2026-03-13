import requests
from bs4 import BeautifulSoup
import os
import re
import json
import math
from urllib.parse import urljoin, urlparse

DATA_DIR = "/data" if os.path.exists("/data") else "."
KNOWLEDGE_FILE = os.path.join(DATA_DIR, "knowledge_base.json")
PRODUCTS_FILE = os.path.join(DATA_DIR, "scraped_products.json")

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def get_domain(url):
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"

def get_internal_links(soup, base_url, domain):
    """Get all internal links from a page, prioritizing product/collection pages"""
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(base_url, href)
        # Only internal links
        if not full_url.startswith(domain):
            continue
        # Skip unwanted pages
        skip_patterns = ["login", "account", "cart", "checkout", "search", "blog", "cdn", "javascript", "#", ".pdf", ".jpg", ".png"]
        if any(p in full_url.lower() for p in skip_patterns):
            continue
        links.add(full_url)
    # Sort — prioritize product/collection pages
    priority = []
    normal = []
    for link in links:
        if any(p in link.lower() for p in ["product", "collection", "category", "shop", "store", "item"]):
            priority.append(link)
        else:
            normal.append(link)
    return priority + normal

def scrape_page(url):
    """Scrape a single page and return text + soup"""
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
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
        print(f"Scraping error {url}: {e}")
        return None, None

def extract_products(soup, base_url):
    """Try to extract product cards from any website"""
    products = []
    domain = get_domain(base_url)
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
            title = None
            for t in ["h1", "h2", "h3", "h4", "a[class*='title']", "p[class*='title']", "span[class*='title']", "div[class*='title']", "a[class*='name']", "div[class*='name']"]:
                el = card.select_one(t)
                if el and len(el.get_text(strip=True)) > 3:
                    title = el.get_text(strip=True)
                    break
            price = None
            for p in ["span[class*='price']", "div[class*='price']", "p[class*='price']", "span[class*='amount']", "ins"]:
                el = card.select_one(p)
                if el:
                    price_text = el.get_text(strip=True)
                    price_match = re.search(r'[\$\£\€\₹]?\s*[\d,]+\.?\d*', price_text)
                    if price_match:
                        price = price_text
                        break
            image = None
            img = card.select_one("img")
            if img:
                image = img.get("src") or img.get("data-src") or img.get("data-lazy-src") or img.get("data-srcset")
                if image and " " in image:
                    image = image.split(" ")[0]
                if image and image.startswith("//"):
                    image = "https:" + image
                elif image and image.startswith("/"):
                    image = domain + image
                # Fix partial domain in image URL
                if image and not image.startswith("http"):
                    image = "https://" + image.lstrip("/")
            url = None
            for a in card.find_all("a"):
                href = a.get("href", "")
                if not href:
                    continue
                # Skip video/media/external URLs
                if any(x in href for x in [".mp4", ".mov", ".avi", "cdn/shop/videos", "bik.ai", "javascript"]):
                    continue
                # Must be a product/collection page
                full_href = ""
                if href.startswith("http"):
                    full_href = href
                elif href.startswith("/"):
                    full_href = domain + href
                else:
                    full_href = domain + "/" + href
                # Only accept internal links
                if domain.replace("https://www.", "https://") in full_href or domain in full_href:
                    url = full_href
                    break

            # Fix image URL if it's broken
            if image and "athflex.com/cdn" in image and not image.startswith("https://www.athflex.com"):
                image = "https://www." + image.split("athflex.com/")[-1].replace("athflex.com/", "athflex.com/")
                image = "https://www.athflex.com/cdn/" + image.split("/cdn/")[-1] if "/cdn/" in image else image

            # Skip fake products
            fake_titles = ["featured products", "new arrivals", "best sellers", "sale", "view all", "shop all", "explore", "discover", "trending"]
            if title and title.lower() not in fake_titles and len(title) > 5 and not title.lower().startswith("shop "):
                products.append({
                    "title": title,
                    "price": price or "Check website",
                    "image": image,
                    "url": url or base_url
                })
        except Exception:
            continue
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

def store_website_data(url, max_pages=10):
    """Crawl entire website up to max_pages"""
    domain = get_domain(url)
    visited = set()
    to_visit = [url]
    all_products = []
    all_chunks = []
    pages_scraped = 0

    print(f"Starting crawl of {url} (max {max_pages} pages)")

    while to_visit and pages_scraped < max_pages:
        current_url = to_visit.pop(0)
        if current_url in visited:
            continue
        visited.add(current_url)
        print(f"Scraping page {pages_scraped + 1}: {current_url}")

        text, soup = scrape_page(current_url)
        if not text or not soup:
            continue

        pages_scraped += 1

        # Extract products
        products = extract_products(soup, current_url)
        for p in products:
            p["source_url"] = url
            if p["title"] not in [ep["title"] for ep in all_products]:
                all_products.append(p)

        # Extract text chunks
        chunks = chunk_text(text)
        for i, chunk in enumerate(chunks):
            all_chunks.append({"text": chunk, "url": current_url, "index": i})

        # Find more links to visit
        new_links = get_internal_links(soup, current_url, domain)
        for link in new_links:
            if link not in visited and link not in to_visit:
                to_visit.append(link)

    print(f"Crawl complete: {pages_scraped} pages, {len(all_products)} products, {len(all_chunks)} chunks")

    # Save products
    prod_data = load_products()
    prod_data["products"] = [p for p in prod_data["products"] if p.get("source_url") != url]
    prod_data["products"].extend(all_products)
    if url not in prod_data.get("urls", []):
        prod_data.setdefault("urls", []).append(url)
    save_products(prod_data)

    # Save knowledge
    knowledge = load_knowledge()
    knowledge["chunks"] = [c for c in knowledge["chunks"] if c.get("url") != url]
    knowledge["chunks"].extend(all_chunks)
    if url not in knowledge.get("urls", []):
        knowledge.setdefault("urls", []).append(url)
    save_knowledge(knowledge)

    return {
        "success": True,
        "pages_scraped": pages_scraped,
        "chunks": len(all_chunks),
        "products_found": len(all_products),
        "message": f"Crawled {pages_scraped} pages — found {len(all_products)} products and {len(all_chunks)} text chunks"
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
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [text for score, text in scored[:n_results] if score > 0]
        return results
    except Exception as e:
        print(f"Search error: {e}")
        return []

def search_products(query, n_results=6):
    try:
        prod_data = load_products()
        products = prod_data.get("products", [])
        if not products:
            return []
        query_lower = query.lower()
        stop_words = {"show", "me", "the", "a", "an", "get", "find", "i", "want", "need", "buy", "some", "any"}
        keywords = [k for k in query_lower.split() if k not in stop_words and len(k) > 2]
        if not keywords:
            return products[:n_results]
        if "all" in query_lower and "product" in query_lower:
            return products[:n_results]
        scored = []
        for p in products:
            title_lower = p["title"].lower()
            score = 0
            for k in keywords:
                if k in title_lower:
                    score += 2
                for word in title_lower.split():
                    if word.startswith(k) or k.startswith(word):
                        score += 1
            if score > 0:
                scored.append((score, p))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [p for score, p in scored[:n_results]]
        print(f"Search '{query}' found {len(results)} products from {len(scored)} scored")
        return results
    except Exception as e:
        print(f"Product search error: {e}")
        import traceback
        traceback.print_exc()
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