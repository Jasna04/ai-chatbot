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
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "knowledge", "orders.csv")

    ids = set()
    if not os.path.exists(file_path):
        return ids

    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            oid = str(row.get("OrderID", "")).strip()
            if oid:
                ids.add(oid.lower())

    return ids


ORDER_IDS = load_all_order_ids()


def detect_order_id(message: str):
    words = re.findall(r"[A-Za-z0-9\-]+", message.lower())
    for word in words:
        if word in ORDER_IDS:
            return word
    return None


def get_order_by_id(order_id: str):
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "knowledge", "orders.csv")

    if not os.path.exists(file_path):
        return None

    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
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

def load_all_product_ids():
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "knowledge", "products.csv")

    ids = set()
    if not os.path.exists(file_path):
        return ids

    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = str(row.get("Product ID", "")).strip()
            if pid:
                ids.add(pid.lower())

    return ids


PRODUCT_IDS = load_all_product_ids()


def detect_product_id(message: str):
    words = re.findall(r"[A-Za-z0-9\-]+", message.lower())
    for word in words:
        if word in PRODUCT_IDS:
            return word
    return None


def get_product_by_id(product_id: str):
    base_dir = os.path.dirname(__file__)
    file_path = os.path.join(base_dir, "knowledge", "products.csv")

    if not os.path.exists(file_path):
        return None

    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if product_id == str(row.get("Product ID", "")).lower():
                return row

    return None


def detect_product_intent(message: str):
    msg = message.lower()
    if "price" in msg or "cost" in msg:
        return "price"
    if "available" in msg or "stock" in msg:
        return "availability"
    if "description" in msg or "about" in msg:
        return "description"
    return "full"


# =====================================================
# Serve frontend
# =====================================================

@app.get("/", response_class=HTMLResponse)
def home():
    file_path = os.path.join(os.path.dirname(__file__), "index.html")
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


# =====================================================
# Chat endpoint
# =====================================================

@app.post("/chat")
def chat(data: ChatInput):
    msg = data.message.strip().lower()

    # ---- Greetings
    if msg in ["hi", "hello", "hey"]:
        return {
            "reply": (
                "👋 Hi! I can help with:\n"
                "• Order tracking (Order ID)\n"
                "• Product details (Product ID)\n\n"
                "Example:\n"
                "- Status of order JB3001\n"
                "- Price of product PRD101"
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

        return {
            "reply": (
                f"📦 Order {order['OrderID']}\n"
                f"• Status: {order['OrderStatus']}\n"
                f"• Item: {order['ItemName']}\n"
                f"• Amount: ₹{order['TotalAmount']}\n"
                f"• Delivery Date: {order['DeliveryDate']}"
            )
        }

    # ---- Products
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
                f"• Availability: {product['Availability']}\n"
                f"• Description: {product['Description']}"
            )
        }

    return {"reply": "Please provide a valid Order ID or Product ID."}
