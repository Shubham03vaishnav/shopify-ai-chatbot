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
    waiting_confirmation: Optional[str] = None

# Regex Patterns
GREET_RE = re.compile(r"\b(hi|hello|hey|hii|helo|howdy|sup|whats up|what's up)\b", re.IGNORECASE)
PRODUCT_RE = re.compile(r"\b(product|products|show|buy|item|items|shop|sell|selling|catalog|collection|tshirt|shirt|tee)\b", re.IGNORECASE)
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
        return {"type":"text","reply":"Please type a color name like Black, Blue, Green, Grey, Coffee, Navy, Pink, Lavender etc."}

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
        return {"type":"text","reply":"Hello! I can help you with:\n- Products\n- Prices\n- Order tracking\n- Discounts\n- Returns\n\nWhat do you need?"}

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

    # Fallback
    return {"type":"text","reply":"I am not sure I understand.\n\nYou can ask me about:\n- Products\n- Prices\n- Order tracking\n- Discounts\n- Returns"}