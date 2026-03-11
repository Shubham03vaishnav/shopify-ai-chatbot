from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
import os
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

def get_shopify_products():
    url = f"https://{SHOP}/admin/api/2024-01/products.json?limit=5"
    headers = {"X-Shopify-Access-Token": TOKEN}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        res.raise_for_status()
        products = res.json().get("products", [])
        return products
    except Exception as e:
        print(f"Shopify API error: {e}")
        return []

@app.get("/")
def health_check():
    return {"status": "Chatbot API is running ✅"}

@app.post("/chat")
def chat(req: ChatRequest):
    msg = req.message.lower().strip()

    if not msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    if any(w in msg for w in ["hi", "hello", "hey"]):
        return {"reply": "👋 Hello! I can help you with products, prices, and orders. What do you need?"}

    if any(w in msg for w in ["product", "show", "buy", "item", "shop", "what do you sell"]):
        products = get_shopify_products()
        if products:
            lines = [f"• {p['title']} — ₹{p['variants'][0]['price']}" for p in products]
            return {"reply": "Here are our products:\n" + "\n".join(lines)}
        return {"reply": "Sorry, I couldn't fetch products right now. Please visit our store!"}

    if any(w in msg for w in ["price", "cost", "how much"]):
        products = get_shopify_products()
        if products:
            lines = [f"• {p['title']} — ₹{p['variants'][0]['price']}" for p in products]
            return {"reply": "Here are our prices:\n" + "\n".join(lines)}
        return {"reply": "Please visit our store to see current prices!"}

    if any(w in msg for w in ["order", "track", "delivery", "shipping"]):
        return {"reply": "For order tracking, please check your email confirmation. 📦"}

    return {"reply": "I'm here to help! Ask me about products, pricing, or orders. 😊"}