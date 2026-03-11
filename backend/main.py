from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
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
    waiting_email: Optional[bool] = False

@app.get("/chatbot.js")
def serve_chatbot():
    return FileResponse("chatbot.js", media_type="application/javascript")

def get_shopify_products():
    url = f"https://{SHOP}/admin/api/2024-01/products.json?limit=5"
    headers = {"X-Shopify-Access-Token": TOKEN}
    try:
        res = requests.get(url, headers=headers, timeout=5)
        res.raise_for_status()
        products = res.json().get("products", [])
        result = []
        for p in products:
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

@app.post("/chat")
def chat(req: ChatRequest):
    msg = req.message.lower().strip()

    if not msg:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    if req.waiting_email and "@" in msg:
        order = get_order_by_email(msg)
        if order:
            return {"type":"order","reply":"Found your order! Here are the details:","order":order}
        return {"type":"text","reply":"Sorry, no orders found for that email. Please check and try again."}

    if any(w in msg for w in ["hi", "hello", "hey"]):
        return {"type":"text","reply":"Hello! I can help you with products, prices, and orders. What do you need?"}

    if any(w in msg for w in ["product", "show", "buy", "item", "shop", "what do you sell"]):
        products = get_shopify_products()
        if products:
            return {"type":"products","reply":"Here are our products:","products":products}
        return {"type":"text","reply":"Sorry, I could not fetch products right now!"}

    if any(w in msg for w in ["price", "cost", "how much"]):
        products = get_shopify_products()
        if products:
            return {"type":"products","reply":"Here are our products with prices:","products":products}
        return {"type":"text","reply":"Please visit our store to see current prices!"}

    if any(w in msg for w in ["order", "track", "delivery", "shipping"]):
        return {"type":"ask_email","reply":"Please enter the email address you used when placing your order."}

    return {"type":"text","reply":"I am here to help! Ask me about products, pricing, or orders."}