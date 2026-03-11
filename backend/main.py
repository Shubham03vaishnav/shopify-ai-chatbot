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

    if any(w in msg for w in ["product", "show", "buy", "item", "shop"]):
        return {"reply": "We have great products! Type 'prices' to see them."}

    if any(w in msg for w in ["price", "cost", "how much"]):
        return {"reply": "Our prices vary by product. Type 'show products' and I'll list them!"}

    if any(w in msg for w in ["order", "track", "delivery", "shipping"]):
        return {"reply": "For order tracking, please check your email confirmation. 📦"}

    return {"reply": "I'm here to help! Ask me about products, pricing, or orders. 😊"}
