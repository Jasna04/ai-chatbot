import os
import csv
import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

# -------------------------
# App setup
# -------------------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Request model
# -------------------------
class ChatInput(BaseModel):
    message: str


# -------------------------
# Utility: extract order number
# -------------------------
def extract_order_id(text: str):
    match = re.search(r"\b\d+\b", text)
    return match.group(0) if match else None


# -------------------------
# Load order by OrderID
# -------------------------
def get_order_by_id(order_id: str):
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "knowledge", "orders.csv")

    if not os.path.exists(file_path):
        return None

    with open(file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            if order_id in str(row.get("OrderID", "")):
                return row

    return None


# -------------------------
# Serve frontend UI
# -------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    file_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


# -------------------------
# Chat endpoint
# -------------------------
@app.post("/chat")
def chat(data: ChatInput):
    user_message = data.message.strip().lower()

    # ✅ Handle greetings ONCE per message
    if user_message in ["hi", "hello", "hey", "good morning", "good evening"]:
        return {
            "reply": (
                "👋 Hello! I’m your AI assistant. How can I help you today?\n\n"
            
            )
        }

    # Extract order number
    order_id = extract_order_id(user_message)

    if not order_id:
        return {
            "reply": "Please provide your Order ID so I can help you."
        }

    order = get_order_by_id(order_id)

    if not order:
        return {
            "reply": f"I couldn’t find any order with ID {order_id}."
        }

    # ✅ Deterministic response (NO OpenAI)
    reply = (
        f"📦 Order {order['OrderID']}\n"
        f"• Status: {order['OrderStatus']}\n"
        f"• Item: {order['ItemName']} (Qty: {order['Quantity']})\n"
        f"• Total Amount: ₹{order['TotalAmount']}\n"
        f"• Payment Method: {order['PaymentMethod']}\n"
        f"• Delivery Date: {order['DeliveryDate']}\n"
        f"• Shipping Location: {order['ShippingCity']}, {order['ShippingState']}"
    )

    return {"reply": reply}
