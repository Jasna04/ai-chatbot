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
# Utility: extract alphanumeric OrderID (JB3001)
# -------------------------
def extract_order_id(text: str):
    match = re.search(r"\b[A-Za-z0-9]+\b", text)
    return match.group(0) if match else None


# -------------------------
# Utility: detect intent
# -------------------------
def detect_intent(message: str):
    msg = message.lower()

    if "delivery" in msg or "delivered" in msg or "eta" in msg:
        return "delivery_date"
    if "status" in msg:
        return "status"
    if "amount" in msg or "price" in msg or "total" in msg:
        return "amount"
    if "item" in msg or "product" in msg:
        return "item"
    if "details" in msg or "full" in msg:
        return "full"

    return "full"


# -------------------------
# Load order by OrderID
# -------------------------
def get_order_by_id(order_id: str):
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "knowledge", "orders.csv")

    if not os.path.exists(file_path):
        return None

    order_id = order_id.lower()

    with open(file_path, newline="", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)

        for row in reader:
            if order_id == str(row.get("OrderID", "")).lower():
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

    # ✅ Greetings
    if user_message in ["hi", "hello", "hey", "good morning", "good evening"]:
        return {
            "reply": (
                "👋 Hi! I can help you with your order.\n\n"
                "Try asking:\n"
                "• What is the status of order JB3001?\n"
                "• When will order JB3001 be delivered?\n"
                "• Show order details for JB3001"
            )
        }

    # Extract OrderID
    order_id = extract_order_id(user_message)

    if not order_id:
        return {
            "reply": "Please provide your Order ID (for example: JB3001)."
        }

    order = get_order_by_id(order_id)

    if not order:
        return {
            "reply": f"I couldn’t find any order with ID {order_id}."
        }

    intent = detect_intent(user_message)

    # -------------------------
    # Intent-based responses
    # -------------------------
    if intent == "delivery_date":
        reply = (
            f"📦 Order {order['OrderID']}\n"
            f"• Delivery Date: {order['DeliveryDate']}"
        )

    elif intent == "status":
        reply = (
            f"📦 Order {order['OrderID']}\n"
            f"• Status: {order['OrderStatus']}"
        )

    elif intent == "amount":
        reply = (
            f"📦 Order {order['OrderID']}\n"
            f"• Total Amount: ₹{order['TotalAmount']}"
        )

    elif intent == "item":
        reply = (
            f"📦 Order {order['OrderID']}\n"
            f"• Item: {order['ItemName']} (Qty: {order['Quantity']})"
        )

    else:
        # Full details
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
