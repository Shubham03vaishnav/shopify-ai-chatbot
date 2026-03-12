from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import requests
import os
import re
from dotenv import load_dotenv

load_dotenv()

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

# ✅ Regex Patterns
GREET_RE = re.compile(r"\b(hi|hello|hey|hii|helo|howdy|sup|whats up|what's up)\b", re.IGNORECASE)
PRODUCT_RE = re.compile(r"\b(product|products|show|buy|item|items|shop|sell|selling|catalog|collection|tshirt|shirt|tee)\b", re.IGNORECASE)
PRICE_RE = re.compile(r"\b(price|prices|cost|how much|rate|rates|charge|charges|affordable|cheap|expensive)\b", re.IGNORECASE)
ORDER_RE = re.compile(r"\b(order|orders|track|tracking|delivery|shipping|dispatch|shipped|delivered|status|where is my)\b", re.IGNORECASE)
COLOR_RE = re.compile(r"\b(black|blue|green|grey|gray|white|red|yellow|brown|coffee|navy)\b", re.IGNORECASE)
SIZE_RE = re.compile(r"\b(small|medium|large|xl|xxl|xs|s\b|m\b|l\b|size)\b", re.IGNORECASE)
DISCOUNT_RE = re.compile(r"\b(discount|offer|coupon|promo|deal|sale|off|code)\b", re.IGNORECASE)
RETURN_RE = re.compile(r"\b(return|refund|exchange|replace|replacement|money back)\b", re.IGNORECASE)
THANKS_RE = re.compile(r"\b(thank|thanks|thankyou|thank you|thx|ty)\b", re.IGNORECASE)
HELP_RE = re.compile(r"\b(help|support|assist|assistance|question|query)\b", re.IGNORECASE)

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

    # Greeting
    if GREET_RE.search(msg):
        return {"type":"text","reply":"Hello! I can help you with:\n- Products\n- Prices\n- Order tracking\n- Discounts\n- Returns\n\nWhat do you need?"}

    # Color search
    color_match = COLOR_RE.search(msg)
    if color_match and (PRODUCT_RE.search(msg) or PRICE_RE.search(msg)):
        color = color_match.group(0)
        products = get_shopify_products(color=color)
        if products:
            return {"type":"products","reply":f"Here are our {color} products:","products":products}
        return {"type":"text","reply":f"Sorry, we don't have any {color} products available right now."}

    # Just color mentioned
    if color_match:
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
        products = get_shopify_products()
        if products:
            return {"type":"products","reply":"Here are our products with prices:","products":products}
        return {"type":"text","reply":"Please visit our store to see current prices!"}

    # Order tracking
    if ORDER_RE.search(msg):
        return {"type":"ask_email","reply":"Please enter the email address you used when placing your order."}

    # Discount
    if DISCOUNT_RE.search(msg):
        return {"type":"text","reply":"We currently have special offers on selected items! Ask me to show our collection to see the latest prices."}

    # Returns
    if RETURN_RE.search(msg):
        return {"type":"text","reply":"We have a 7-day return policy. If you are not satisfied with your purchase, contact us at support@ai-chatbot-lab.com and we will help you out!"}

    # Thanks
    if THANKS_RE.search(msg):
        return {"type":"text","reply":"You are welcome! Is there anything else I can help you with?"}

    # Help
    if HELP_RE.search(msg):
        return {"type":"text","reply":"I can help you with:\n- Products\n- Prices\n- Order tracking\n- Discounts\n- Returns\n\nJust ask!"}

    # Size
    if SIZE_RE.search(msg):
        return {"type":"text","reply":"Our tshirts are available in sizes S, M, L, XL and XXL. Type 'show products' to browse and click View Product to check size availability!"}

    # Fallback
    return {"type":"text","reply":"I am not sure I understand. You can ask me about:\n- Products\n- Prices\n- Order tracking\n- Discounts\n- Returns"}
