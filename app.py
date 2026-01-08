import os
import csv
import re
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel


# =====================================================
# APP SETUP
# =====================================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================
# REQUEST MODEL (SITE-AWARE)
# =====================================================

class ChatInput(BaseModel):
    message: str
    site: Optional[str] = "default"


BASE_DIR = os.path.dirname(__file__)
KNOWLEDGE_DIR = os.path.join(BASE_DIR, "knowledge")


# =====================================================
# ORDERS KNOWLEDGE BASE (CHRISTMAS / INDIA)
# =====================================================

def load_orders():
    path = os.path.join(KNOWLEDGE_DIR, "orders.csv")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


ORDERS = load_orders()
ORDER_IDS = {o["OrderID"].lower() for o in ORDERS if o.get("OrderID")}


def detect_order_id(message: str):
    for word in re.findall(r"[A-Za-z0-9\-]+", message.lower()):
        if word in ORDER_IDS:
            return word
    return None


def get_order(order_id: str):
    for o in ORDERS:
        if o["OrderID"].lower() == order_id:
            return o
    return None


def detect_order_intent(msg: str):
    if any(k in msg for k in ["delivery", "eta", "delivered"]):
        return "delivery"
    if "status" in msg:
        return "status"
    if any(k in msg for k in ["amount", "total", "price"]):
        return "amount"
    if "item" in msg:
        return "item"
    return "full"


# =====================================================
# PRODUCTS KNOWLEDGE BASE (INDIA / INR)
# =====================================================

def load_products():
    path = os.path.join(KNOWLEDGE_DIR, "products.csv")
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


PRODUCTS = load_products()
PRODUCT_IDS = {p["Product ID"].lower() for p in PRODUCTS if p.get("Product ID")}


def detect_product_id(message: str):
    for word in re.findall(r"[A-Za-z0-9\-]+", message.lower()):
        if word in PRODUCT_IDS:
            return word
    return None


def get_product(pid: str):
    for p in PRODUCTS:
        if p["Product ID"].lower() == pid:
            return p
    return None


def detect_product_intent(msg: str):
    if "price" in msg or "cost" in msg:
        return "price"
    if "available" in msg or "stock" in msg:
        return "availability"
    if "description" in msg or "about" in msg:
        return "description"
    if "list" in msg or "show" in msg:
        return "list"
    return None


# =====================================================
# PARIS / WESTERN DRESSES (EURO)
# =====================================================

def load_paris_products():
    path = os.path.join(
        KNOWLEDGE_DIR,
        "western_dresses_products_style_price_eur.csv"
    )
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


PARIS_PRODUCTS = load_paris_products()


def find_paris_product(message: str):
    msg = message.lower()
    for p in PARIS_PRODUCTS:
        if p["product_name"].lower() in msg:
            return p
    return None


def detect_paris_intent(msg: str):
    if "price" in msg:
        return "price"
    if "style" in msg or "type" in msg:
        return "style"
    if any(k in msg for k in ["list", "show", "western", "paris"]):
        return "list"
    return None


# =====================================================
# FRONTEND
# =====================================================

@app.get("/", response_class=HTMLResponse)
def home():
    with open(os.path.join(BASE_DIR, "index.html"), encoding="utf-8") as f:
        return f.read()


# =====================================================
# CHAT ENDPOINT (SITE ROUTER)
# =====================================================

@app.post("/chat")
def chat(data: ChatInput):
    msg = data.message.lower().strip()
    site = (data.site or "default").lower()

    # ---------- Greeting
    if msg in ["hi", "hello", "hey"]:
        return {
            "reply": (
                f"👋 Hi! You’re chatting with the **{site.upper()}** assistant.\n\n"
                "Try:\n"
                "- Status of order JB3001\n"
                "- Price of Cocktail Dress\n"
                "- Show western dresses"
            )
        }

    # =================================================
    # INDIA / CHRISTMAS STORE
    # =================================================
    if site in ["default", "india", "christmas"]:

        order_id = detect_order_id(msg)
        if order_id:
            order = get_order(order_id)
            if not order:
                return {"reply": "Order not found."}

            intent = detect_order_intent(msg)

            if intent == "delivery":
                return {"reply": f"📦 Order {order['OrderID']}\nDelivery: {order['DeliveryDate']}"}
            if intent == "status":
                return {"reply": f"📦 Order {order['OrderID']}\nStatus: {order['OrderStatus']}"}
            if intent == "amount":
                return {"reply": f"📦 Order {order['OrderID']}\nAmount: ₹{order['TotalAmount']}"}
            if intent == "item":
                return {"reply": f"📦 Item: {order['ItemName']} (Qty {order['Quantity']})"}

            return {"reply": f"📦 Order {order['OrderID']} is {order['OrderStatus']}"}

        pid = detect_product_id(msg)
        if pid:
            p = get_product(pid)
            if not p:
                return {"reply": "Product not found."}

            intent = detect_product_intent(msg)

            if intent == "price":
                return {"reply": f"🛒 {p['Product Name']} – ₹{p['Price (INR)']}"}
            if intent == "availability":
                return {"reply": f"🛒 Availability: {p['Availability']}"}
            if intent == "description":
                return {"reply": p["Description"]}

            return {
                "reply": (
                    f"🛒 {p['Product Name']}\n"
                    f"Price: ₹{p['Price (INR)']}\n"
                    f"Availability: {p['Availability']}"
                )
            }

    # =================================================
    # PARIS STORE
    # =================================================
    if site == "paris":

        product = find_paris_product(msg)
        intent = detect_paris_intent(msg)

        if product:
            if intent == "price":
                return {"reply": f"👗 {product['product_name']} – €{product['price_eur']}"}
            if intent == "style":
                return {"reply": f"👗 Style: {product['style']}"}

            return {
                "reply": (
                    f"👗 {product['product_name']}\n"
                    f"Style: {product['style']}\n"
                    f"Price: €{product['price_eur']}"
                )
            }

