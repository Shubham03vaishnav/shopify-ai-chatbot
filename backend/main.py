import google.generativeai as genai
from scraper import store_website_data, search_knowledge, get_trained_urls, load_knowledge, save_knowledge
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import requests
import os
import re
from dotenv import load_dotenv

load_dotenv()

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_KEY:
    genai.configure(api_key=GEMINI_KEY)
    gemini_model = genai.GenerativeModel("gemini-1.0-pro")
else:
    gemini_model = None

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

SHOP = os.getenv("SHOPIFY_SHOP")
TOKEN = os.getenv("SHOPIFY_TOKEN")

class ChatRequest(BaseModel):
    message: str
    waiting_email: Optional[bool] = False
    waiting_confirmation: Optional[str] = None

class ScrapeRequest(BaseModel):
    url: str

class RAGRequest(BaseModel):
    question: str

# Regex Patterns
GREET_RE = re.compile(r"\b(hi|hello|hey|hii|helo|howdy|whats up|what's up)\b", re.IGNORECASE)
PRODUCT_RE = re.compile(r"\b(product|products|buy|item|items|shop|sell|selling|catalog|collection|tshirt|shirt|tee)\b", re.IGNORECASE)
PRICE_RE = re.compile(r"\b(price|prices|cost|how much|rate|rates|charge|charges|affordable|cheap|expensive)\b", re.IGNORECASE)
ORDER_RE = re.compile(r"\b(order|orders|track|tracking|delivery|shipping|dispatch|shipped|delivered|status|where is my)\b", re.IGNORECASE)
COLOR_RE = re.compile(r"\b(black|blue|green|grey|gray|white|red|yellow|brown|coffee|navy|lavender|marron|pink|sage)\b", re.IGNORECASE)
SIZE_RE = re.compile(r"\b(small|medium|large|xl|xxl|xs|size|sizing|fit|fitting)\b", re.IGNORECASE)
DISCOUNT_RE = re.compile(r"\b(discount|offer|coupon|promo|deal|sale|off|code)\b", re.IGNORECASE)
RETURN_RE = re.compile(r"\b(return|refund|exchange|replace|replacement|money back)\b", re.IGNORECASE)
THANKS_RE = re.compile(r"\b(thank|thanks|thankyou|thank you|thx|ty)\b", re.IGNORECASE)
HELP_RE = re.compile(r"\b(help|support|assist|assistance|question|query)\b", re.IGNORECASE)
YES_RE = re.compile(r"\b(yes|yeah|yep|sure|ok|okay|show|please|yup|haan|ha)\b", re.IGNORECASE)
NO_RE = re.compile(r"\b(no|nope|nahi|nah|not now|later)\b", re.IGNORECASE)
BYE_RE = re.compile(r"\b(bye|goodbye|see you|seeyou|cya|take care|tata|alvida)\b", re.IGNORECASE)
MORNING_RE = re.compile(r"\b(good morning|good afternoon|good evening|good night|gm|gn)\b", re.IGNORECASE)
HOW_ARE_YOU_RE = re.compile(r"\b(how are you|how r u|hru|how are u|you good|u good|how is it going)\b", re.IGNORECASE)
NICE_RE = re.compile(r"\b(nice|great|awesome|cool|wow|amazing|excellent|perfect|wonderful|superb|loved it)\b", re.IGNORECASE)
OK_RE = re.compile(r"\b(ok|okay|alright|alrite|fine|got it|gotit|understood|noted|kk)\b", re.IGNORECASE)
YES_ONLY_RE = re.compile(r"^(yes|yeah|yep|yup|haan|ha|yess|yesss|ofcourse|of course|definitely|absolutely|sure|why not)$", re.IGNORECASE)
NO_ONLY_RE = re.compile(r"^(no|nope|nahi|nah|na|noo|nooo|never|not really|not now)$", re.IGNORECASE)
LOVE_RE = re.compile(r"\b(love|loving|i love|loved|like|liked|i like|fantastic|brilliant|outstanding)\b", re.IGNORECASE)
BAD_RE = re.compile(r"\b(bad|worst|terrible|horrible|pathetic|useless|disappointed|disappointing|not good|not happy)\b", re.IGNORECASE)
WHO_RE = re.compile(r"\b(who are you|what are you|are you a bot|are you human|are you ai|are you robot|who made you|who created you)\b", re.IGNORECASE)
CONTACT_RE = re.compile(r"\b(contact|email|phone|call|reach|whatsapp|support|customer care|helpline)\b", re.IGNORECASE)

def get_shopify_products(color=None):
    url = f"https://{SHOP}/admin/api/2024-01/products.json?limit=10"
    headers = {"X-Shopify-Access-Token": TOKEN}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        res.raise_for_status()
        products = res.json().get("products", [])
        result = []
        for p in products:
            title = p["title"].lower()
            if color and color.lower() not in title:
                continue
            result.append({
                "title": p["title"],
                "price": p["variants"][0]["price"],
                "image": p["images"][0]["src"] if p.get("images") else None,
                "url": f"https://{SHOP}/products/{p['handle']}"
            })
        return result
    except Exception as e:
        print(f"Shopify API error: {e}")
        return []

def get_order_by_email(email):
    url = f"https://{SHOP}/admin/api/2024-01/orders.json?email={email}&status=any&limit=1"
    headers = {"X-Shopify-Access-Token": TOKEN}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        res.raise_for_status()
        orders = res.json().get("orders", [])
        if orders:
            o = orders[0]
            return {
                "number": o["order_number"],
                "status": o["fulfillment_status"] or "unfulfilled",
                "total": o["total_price"],
                "date": o["created_at"][:10]
            }
        return None
    except Exception as e:
        print(f"Order API error: {e}")
        return None

@app.get("/")
def health_check():
    return {"status": "Chatbot API is running"}

@app.get("/test-gemini")
def test_gemini():
    if not gemini_model:
        return {"status": "Gemini not initialized", "key_exists": bool(GEMINI_KEY)}
    try:
        response = gemini_model.generate_content("Say hello in one sentence")
        return {"status": "working", "response": response.text}
    except Exception as e:
        return {"status": "error", "error": str(e)}

@app.get("/admin")
def admin_panel():
    return FileResponse("admin.html", media_type="text/html")

@app.get("/trained-urls")
def trained_urls():
    knowledge = load_knowledge()
    return {
        "urls": get_trained_urls(),
        "total_chunks": len(knowledge.get("chunks", []))
    }

@app.post("/delete-url")
def delete_url(req: ScrapeRequest):
    knowledge = load_knowledge()
    knowledge["chunks"] = [c for c in knowledge["chunks"] if c.get("url") != req.url]
    if req.url in knowledge["urls"]:
        knowledge["urls"].remove(req.url)
    save_knowledge(knowledge)
    return {"success": True, "message": f"Removed {req.url}"}

@app.post("/scrape")
def scrape(req: ScrapeRequest):
    """Train chatbot on a website URL"""
    result = store_website_data(req.url)
    return result

@app.post("/ask")
def ask(req: RAGRequest):
    """Answer question using scraped website data + Gemini"""
    question = req.question.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    # Search relevant chunks
    chunks = search_knowledge(question)

    if not chunks:
        return {"answer": "I don't have enough information to answer that. Please train me on a website first by using the /scrape endpoint."}

    # Build context from chunks
    context = "\n\n".join(chunks)

    if gemini_model:
        try:
            prompt = f"""You are a helpful store assistant. Answer the customer's question based only on the provided context.
If the answer is not in the context, say "I don't have that information right now."
Keep your answer short, friendly and helpful.

Context:
{context}

Customer Question: {question}

Answer:"""
            response = gemini_model.generate_content(prompt)
            return {"answer": response.text}
        except Exception as e:
            print(f"Gemini error: {e}")
            return {"answer": chunks[0]}
    else:
        return {"answer": chunks[0]}

@app.get("/chatbot.js")
def serve_chatbot():
    return FileResponse("chatbot.js", media_type="application/javascript")

@app.post("/chat")
def chat(req: ChatRequest):
    msg = req.message.strip()

    if not msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    # Handle email for order tracking
    if req.waiting_email and "@" in msg:
        order = get_order_by_email(msg)
        if order:
            return {"type":"order","reply":"Found your order! Here are the details:","order":order}
        return {"type":"text","reply":"Sorry, no orders found for that email. Please check and try again."}

    # Handle confirmation — show all products
    if req.waiting_confirmation == "show_products":
        if YES_RE.search(msg):
            products = get_shopify_products()
            if products:
                return {"type":"products","reply":"Here are our products:","products":products}
        if NO_RE.search(msg):
            return {"type":"text","reply":"No problem! Let me know if you need anything else."}

    # Handle confirmation — ask for color
    if req.waiting_confirmation == "ask_color":
        color_match = COLOR_RE.search(msg)
        if color_match:
            color = color_match.group(0)
            products = get_shopify_products(color=color)
            if products:
                p = products[0]
                return {
                    "type": "confirm",
                    "reply": f"The {p['title']} is priced at Rs. {p['price']}.\n\nWould you like to see the product?",
                    "confirm_action": "show_single_product_" + color
                }
            return {"type":"text","reply":f"Sorry, we don't have any {color} products right now."}
        if YES_RE.search(msg):
            products = get_shopify_products()
            if products:
                return {"type":"products","reply":"Here are all our products:","products":products}
        return {"type":"text","reply":"Please type a color name like Black, Blue, Green, Grey, Coffee, Navy, Pink, Lavender, Sage, Marron etc."}

    # Handle confirmation — show single product
    if req.waiting_confirmation and req.waiting_confirmation.startswith("show_single_product_"):
        color = req.waiting_confirmation.replace("show_single_product_", "")
        if YES_RE.search(msg):
            products = get_shopify_products(color=color)
            if products:
                return {"type":"products","reply":f"Here is the {color} product:","products":products}
        if NO_RE.search(msg):
            return {"type":"text","reply":"No problem! Let me know if you need anything else."}

    # Greeting
    if GREET_RE.search(msg):
        return {"type":"text","reply":"Hello! Welcome to our store!\n\nI can help you with:\n- Products\n- Prices\n- Order tracking\n- Discounts\n- Returns\n\nWhat do you need?"}

    # Good morning / afternoon / evening
    if MORNING_RE.search(msg):
        return {"type":"text","reply":"Good day to you! Welcome to our store.\n\nI can help you with:\n- Products\n- Prices\n- Order tracking\n- Discounts\n- Returns\n\nWhat can I do for you today?"}

    # How are you
    if HOW_ARE_YOU_RE.search(msg):
        return {"type":"text","reply":"I am doing great, thank you for asking!\n\nI am here to help you shop. What are you looking for today?"}

    # Who are you
    if WHO_RE.search(msg):
        return {"type":"text","reply":"I am your Store Assistant! I am an AI chatbot here to help you shop.\n\nI can help you with products, prices, orders and more!"}

    # Color + product search
    color_match = COLOR_RE.search(msg)
    if color_match and PRODUCT_RE.search(msg):
        color = color_match.group(0)
        products = get_shopify_products(color=color)
        if products:
            return {"type":"products","reply":f"Here are our {color} products:","products":products}
        return {"type":"text","reply":f"Sorry, we don't have any {color} products right now."}

    # Just color mentioned
    if color_match and not PRICE_RE.search(msg):
        color = color_match.group(0)
        products = get_shopify_products(color=color)
        if products:
            return {"type":"products","reply":f"Here are our {color} products:","products":products}
        return {"type":"text","reply":f"Sorry, we don't have any {color} products right now."}

    # Products
    if PRODUCT_RE.search(msg):
        products = get_shopify_products()
        if products:
            return {"type":"products","reply":"Here are our products:","products":products}
        return {"type":"text","reply":"Sorry, I could not fetch products right now!"}

    # Price
    if PRICE_RE.search(msg):
        color_match = COLOR_RE.search(msg)
        if color_match:
            color = color_match.group(0)
            products = get_shopify_products(color=color)
            if products:
                p = products[0]
                return {
                    "type": "confirm",
                    "reply": f"The {p['title']} is priced at Rs. {p['price']}.\n\nWould you like to see the product?",
                    "confirm_action": "show_single_product_" + color
                }
            return {"type":"text","reply":f"Sorry, we don't have any {color} products right now."}
        else:
            products = get_shopify_products()
            if products:
                colors = list(set([p['title'].split()[0] for p in products]))
                colors_text = ", ".join(colors)
                return {
                    "type": "confirm",
                    "reply": f"Which product are you looking for?\n\nWe have these colors:\n{colors_text}\n\nJust type the color name!",
                    "confirm_action": "ask_color"
                }

    # Order tracking
    if ORDER_RE.search(msg):
        if "@" in msg:
            order = get_order_by_email(msg)
            if order:
                return {"type":"order","reply":"Found your order! Here are the details:","order":order}
            return {"type":"text","reply":"Sorry, no orders found for that email. Please check and try again."}
        return {"type":"ask_email","reply":"Sure! I can help you track your order.\n\nCould you please share the email address you used while placing the order?"}

    # Discount
    if DISCOUNT_RE.search(msg):
        return {"type":"text","reply":"We currently have special offers on selected items!\n\nAsk me to show our collection to see the latest prices."}

    # Returns
    if RETURN_RE.search(msg):
        return {"type":"text","reply":"No worries! We have a hassle-free 7-day return policy.\n\nHere is how it works:\n1. Contact us within 7 days of delivery\n2. Item must be unused and in original packaging\n3. We will arrange a pickup\n4. Refund processed in 3-5 business days\n\nNeed help? Email us at support@ai-chatbot-lab.com"}

    # Thanks
    if THANKS_RE.search(msg):
        return {"type":"text","reply":"You are welcome! Is there anything else I can help you with?"}

    # Help
    if HELP_RE.search(msg):
        return {"type":"text","reply":"I can help you with:\n- Products\n- Prices\n- Order tracking\n- Discounts\n- Returns\n\nJust ask!"}

    # Size
    if SIZE_RE.search(msg):
        return {"type":"text","reply":"Our tshirts are available in sizes S, M, L, XL and XXL.\n\nType a color name to see a specific product or ask me to show all products!"}

    # Contact
    if CONTACT_RE.search(msg):
        return {"type":"text","reply":"You can reach us here:\n\nEmail: support@ai-chatbot-lab.com\nWhatsApp: +91 XXXXXXXXXX\nTiming: Mon-Sat, 10am to 6pm\n\nWe will get back to you within 24 hours!"}

    # Love / Like
    if LOVE_RE.search(msg):
        return {"type":"text","reply":"That is so sweet! We love our customers too!\n\nIs there anything else I can help you with today?"}

    # Bad / Negative feedback
    if BAD_RE.search(msg):
        return {"type":"text","reply":"We are really sorry to hear that!\n\nPlease contact us at support@ai-chatbot-lab.com and we will make it right for you."}

    # Nice / Great
    if NICE_RE.search(msg):
        return {"type":"text","reply":"Thank you so much! That means a lot to us.\n\nIs there anything else I can help you with?"}

    # OK
    if OK_RE.search(msg):
        return {"type":"text","reply":"Sure! Let me know if you need anything.\n\nYou can ask me about products, prices or orders anytime!"}

    # Yes only
    if YES_ONLY_RE.search(msg):
        return {"type":"text","reply":"Great! What would you like to know?\n\nYou can ask me about:\n- Products\n- Prices\n- Order tracking\n- Discounts\n- Returns"}

    # No only
    if NO_ONLY_RE.search(msg):
        return {"type":"text","reply":"No problem! Feel free to ask me anything anytime.\n\nHave a great day!"}

    # Bye
    if BYE_RE.search(msg):
        return {"type":"text","reply":"Goodbye! Thank you for visiting our store.\n\nHave a great day! Come back soon!"}

    # RAG Fallback — search scraped website data
    chunks = search_knowledge(msg)
    if chunks and gemini_model:
        try:
            context = "\n\n".join(chunks)
            prompt = f"""You are a helpful store assistant. Answer the customer's question based only on the provided context.
    If the answer is not in the context, say "I don't have that information right now."
    Keep your answer short, friendly and helpful.

    Context:
    {context}

    Customer Question: {msg}

    Answer:"""
            response = gemini_model.generate_content(prompt)
            return {"type":"text","reply":response.text}
        except Exception as e:
            print(f"Gemini error: {e}")

    return {"type":"text","reply":"I am not sure I understand.\n\nYou can ask me about:\n- Products\n- Prices\n- Order tracking\n- Discounts\n- Returns"}
