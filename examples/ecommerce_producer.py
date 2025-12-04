#!/usr/bin/env python3
"""
E-commerce order stream producer.

Generates realistic order events that simulate an e-commerce platform.
Use with pathway_demo.py to see real-time business metrics.

Usage:
    python examples/ecommerce_producer.py
"""

import json
import random
import time
import uuid

from kafka import KafkaProducer

# Product catalog with prices
PRODUCTS = {
    "laptop": {"price": 999.99, "category": "electronics"},
    "phone": {"price": 699.99, "category": "electronics"},
    "headphones": {"price": 149.99, "category": "electronics"},
    "keyboard": {"price": 79.99, "category": "electronics"},
    "book": {"price": 19.99, "category": "books"},
    "shirt": {"price": 29.99, "category": "clothing"},
    "shoes": {"price": 89.99, "category": "clothing"},
    "coffee": {"price": 12.99, "category": "food"},
    "snacks": {"price": 5.99, "category": "food"},
}

REGIONS = ["us-east", "us-west", "eu-west", "eu-central", "apac"]
PAYMENT_METHODS = ["credit_card", "debit_card", "paypal", "apple_pay"]


def generate_order() -> dict:
    """Generate a realistic e-commerce order event."""
    product_name = random.choice(list(PRODUCTS.keys()))
    product = PRODUCTS[product_name]
    quantity = random.choices([1, 2, 3, 4, 5], weights=[50, 25, 15, 7, 3])[0]

    # Add some discount randomness
    discount = 0
    if random.random() < 0.2:  # 20% of orders have discounts
        discount = random.choice([0.1, 0.15, 0.2, 0.25])

    subtotal = product["price"] * quantity
    discount_amount = subtotal * discount
    total = subtotal - discount_amount

    return {
        "order_id": str(uuid.uuid4())[:8],
        "timestamp": int(time.time() * 1000),
        "product": product_name,
        "category": product["category"],
        "quantity": quantity,
        "unit_price": product["price"],
        "discount_percent": int(discount * 100),
        "total": round(total, 2),
        "region": random.choice(REGIONS),
        "payment_method": random.choice(PAYMENT_METHODS),
    }


def main():
    print("Connecting to Redpanda...")

    producer = KafkaProducer(
        bootstrap_servers=["localhost:9092"],
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
    )

    print("Publishing orders to 'orders' topic (Ctrl+C to stop)...")
    print("Tip: Run 'python examples/pathway_demo.py' to see aggregated metrics\n")

    order_count = 0
    try:
        while True:
            # Simulate variable order rate (busier during "peak" times)
            burst = random.random() < 0.1  # 10% chance of order burst

            order = generate_order()
            producer.send("orders", order)
            order_count += 1

            # Print every few orders
            if order_count % 5 == 0:
                print(
                    f"  Order #{order_count}: {order['quantity']}x {order['product']} "
                    f"= ${order['total']:.2f} ({order['region']})"
                )

            # Variable delay to simulate real traffic patterns
            if burst:
                time.sleep(random.uniform(0.05, 0.1))  # Fast during bursts
            else:
                time.sleep(random.uniform(0.3, 0.8))  # Normal rate

    except KeyboardInterrupt:
        print(f"\nStopped after {order_count} orders")
    finally:
        producer.close()


if __name__ == "__main__":
    main()
