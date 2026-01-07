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


# =====================================================
# ORDERS KNOWLEDGE BASE
# =====================================================

def load_all_order_ids():
    file_path = os.path.join(os.path.dirname(__file__), "knowledge", "orders.csv")
    ids = set()

    if not os.path.exists(file_path):
        return ids

    with open(file_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            oid = str(row.get("OrderID", "")).strip()
            if oid:
                ids.add(oid.lower())
    return ids


ORDER_IDS = load_all_order_ids()


def detect_order_id(message: str):
    for word in re.findall(r"[A-Za-z0-9\-]+", message.lower()):
        if word in ORDER_IDS:
            return word
    return None


def get_order_by_id(order_id: str):
    file_path = os.path.join(os.path.dirname(__file__), "knowledge", "orders.csv")
    if not os.path.exists(file_path):
        return None

    with open(file_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if order_id == str(row.get("OrderID", "")).lower():
                return row
    return None


def detect_order_intent(message: str):
    msg = message.lower()
    if "delivery" in msg or "delivered" in msg or "eta" in msg:
        return "delivery"
    if "status" in msg:
        return "status"
    if "amount" in msg or "total" in msg or "price" in msg:
        return "amount"
    if "item" in msg:
        return "item"
    return "full"


# =====================================================
# PRODUCTS KNOWLEDGE BASE
# =====================================================

def load_all_products():
    file_path = os.path.join(os.path.dirname(__file__), "knowledge", "products.csv")
    if not os.path.exists(file_path):
        return []
    with open(file_path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


PRODUCTS = load_all_products()
PRODUCT_IDS = {str(p.get("Product ID", "")).lower() for p in PRODUCTS if p.get("Product ID")}


def detect_product_id(message: str):
    for word in re.findall(r"[A-Za-z0-9\-]+", message.lower()):
        if word in PRODUCT_IDS:
            return word
    return None


def get_product_by_id(product_id: str):
    for p in PRODUCTS:
        if product_id == str(p.get("Product ID", "")).lower():
            return p
    return None


def detect_product_intent(message: str):
    msg = message.lower()
    if "price" in msg or "cost" in msg:
        return "price"
    if "available" in msg or "stock" in msg:
        return "availability"
    if "description" in msg or "about" in msg:
        return "description"
    if "list" in msg or "show" in msg or "all products" in msg:
        return "list"
    return None


# =====================================================
# Serve frontend
# =====================================================

@app.get("/", response_class=HTMLResponse)
def home():
    with open(os.path.join(os.path.dirname(__file__), "index.html"), encoding="utf-8") as f:
        return f.read()


# =====================================================
# Chat endpoint
# =====================================================

@app.post("/chat")
def chat(data: ChatInput):
    msg = data.message.strip().lower()

    # ---- Greeting
    if msg in ["hi", "hello", "hey"]:
        return {
            "reply": (
                "👋 Hi! I can help you with:\n"
                "• Order tracking\n"
                "• Product details\n"
                "• Available products\n\n"
                "Examples:\n"
                "- Status of order JB3001\n"
                "- What items are in stock?"
            )
        }

    # ---- Orders
    order_id = detect_order_id(msg)
    if order_id:
        order = get_order_by_id(order_id)
        if not order:
            return {"reply": f"No order found with ID {order_id.upper()}."}

        intent = detect_order_intent(msg)

        if intent == "delivery":
            return {"reply": f"📦 Order {order['OrderID']}\n• Delivery Date: {order['DeliveryDate']}"}
        if intent == "status":
            return {"reply": f"📦 Order {order['OrderID']}\n• Status: {order['OrderStatus']}"}
        if intent == "amount":
            return {"reply": f"📦 Order {order['OrderID']}\n• Total Amount: ₹{order['TotalAmount']}"}
        if intent == "item":
            return {"reply": f"📦 Order {order['OrderID']}\n• Item: {order['ItemName']} (Qty: {order['Quantity']})"}

        return {"reply": f"📦 Order {order['OrderID']} is {order['OrderStatus']}."}

    # ---- Products by ID
    product_id = detect_product_id(msg)
    if product_id:
        product = get_product_by_id(product_id)
        if not product:
            return {"reply": f"No product found with ID {product_id.upper()}."}

        intent = detect_product_intent(msg)

        if intent == "price":
            return {"reply": f"🛒 {product['Product Name']}\n• Price: ₹{product['Price (INR)']}"}
        if intent == "availability":
            return {"reply": f"🛒 {product['Product Name']}\n• Availability: {product['Availability']}"}
        if intent == "description":
            return {"reply": f"🛒 {product['Product Name']}\n• {product['Description']}"}

        return {
            "reply": (
                f"🛒 {product['Product Name']}\n"
                f"• Category: {product['Category']}\n"
                f"• Price: ₹{product['Price (INR)']}\n"
                f"• Availability: {product['Availability']}"
            )
        }

    # ---- Product catalog queries (NO Product ID)
    intent = detect_product_intent(msg)
    if intent in ["availability", "list"]:
        in_stock = [
            f"• {p['Product Name']} – ₹{p['Price (INR)']}"
            for p in PRODUCTS
            if p.get("Availability", "").lower() == "in stock"
        ]

        if not in_stock:
            return {"reply": "No products are currently in stock."}

        return {"reply": "🟢 Products in stock:\n" + "\n".join(in_stock)}

    return {"reply": "Please ask about an order, a product, or available items."}
