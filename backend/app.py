from flask import Flask, render_template, request, jsonify
import mysql.connector
import os
import math
from datetime import date
from pathlib import Path

app = Flask(
    __name__,
    template_folder=str(Path(__file__).resolve().parent.parent)
)


# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_db_connection():
    password = os.environ.get("DB_PASSWORD")

    if not password:
        raise RuntimeError(
            "DB_PASSWORD environment variable is not set."
        )

    return mysql.connector.connect(
        host="localhost",
        user="root",
        password=password,
        database="smart_retail",
        use_pure=True
    )


# ==========================================
# COMMON FORECAST CALCULATION
# ==========================================

def calculate_forecast(total_sold, selling_days):
    total_sold = int(total_sold or 0)
    selling_days = int(selling_days or 0)

    if selling_days > 0:
        average = total_sold / selling_days
        demand = math.ceil(average * 7)
    else:
        average = 0
        demand = 0

    return {
        "total_historical_sales": total_sold,
        "selling_days": selling_days,
        "average_sales_per_selling_day": round(average, 2),
        "predicted_demand_next_7_days": demand
    }


# ==========================================
# HOME PAGE
# ==========================================

@app.route("/")
def home():
    return render_template("index.html")


# ==========================================
# PAGE ROUTES
# Support both /reports and /reports.html
# ==========================================

@app.route("/dashboard")
@app.route("/dashboard.html")
def dashboard():
    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("SELECT COUNT(*) AS total FROM products")
        total_products = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT COALESCE(SUM(stock_quantity), 0) AS total
            FROM products
        """)
        total_stock = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM products
            WHERE COALESCE(stock_quantity, 0) <= 50
        """)
        low_stock = cursor.fetchone()["total"]

        cursor.execute("""
            SELECT product_name, stock_quantity, price
            FROM products
            ORDER BY id
        """)
        inventory_products = cursor.fetchall()

        cursor.execute("""
            SELECT
                COALESCE(SUM(quantity_sold), 0) AS total_sold,
                COUNT(DISTINCT sale_date) AS selling_days
            FROM sales
        """)
        sales_data = cursor.fetchone()

        forecast = calculate_forecast(
            sales_data["total_sold"],
            sales_data["selling_days"]
        )

        return render_template(
            "dashboard.html",
            total_products=total_products,
            total_stock=total_stock,
            low_stock=low_stock,
            inventory_products=inventory_products,
            predicted_demand=forecast[
                "predicted_demand_next_7_days"
            ]
        )

    except Exception:
        app.logger.exception("Dashboard error")
        return "Dashboard error. Check the Flask terminal.", 500

    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


@app.route("/products")
@app.route("/products.html")
def products():
    return render_template("products.html")


@app.route("/sales")
@app.route("/sales.html")
def sales():
    return render_template("sales.html")


@app.route("/forecast")
@app.route("/forecast.html")
def forecast():
    return render_template("forecast.html")


@app.route("/inventory")
@app.route("/inventory.html")
def inventory():
    return render_template("inventory.html")


@app.route("/reports")
@app.route("/reports.html")
def reports():
    return render_template("reports.html")


# ==========================================
# PRODUCTS API - GET ALL PRODUCTS
# ==========================================

@app.route("/api/products", methods=["GET"])
def get_products():
    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id,
                product_name,
                category,
                price,
                stock_quantity
            FROM products
            ORDER BY id
        """)

        return jsonify(cursor.fetchall()), 200

    except Exception:
        app.logger.exception("Get products error")
        return jsonify({
            "error": "Unable to retrieve products"
        }), 500

    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# ==========================================
# PRODUCTS API - ADD PRODUCT
# ==========================================

@app.route("/api/products", methods=["POST"])
def add_product():
    db = None
    cursor = None

    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "error": "Valid product JSON data is required"
            }), 400

        product_name = str(
            data.get("product_name", "")
        ).strip()

        category = str(data.get("category", "")).strip()

        if not product_name:
            return jsonify({
                "error": "Product name is required"
            }), 400

        price = float(data["price"])
        stock_quantity = int(data["stock_quantity"])

        if price < 0 or stock_quantity < 0:
            return jsonify({
                "error": "Price and stock cannot be negative"
            }), 400

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
            SELECT id
            FROM products
            WHERE LOWER(TRIM(product_name)) =
                  LOWER(TRIM(%s))
            LIMIT 1
        """, (product_name,))

        existing = cursor.fetchone()

        if existing:
            return jsonify({
                "error": f"Product already exists with ID {existing[0]}"
            }), 409

        cursor.execute("""
            INSERT INTO products
                (product_name, category, price, stock_quantity)
            VALUES (%s, %s, %s, %s)
        """, (
            product_name,
            category,
            price,
            stock_quantity
        ))

        db.commit()

        return jsonify({
            "message": "Product added successfully!",
            "product_id": cursor.lastrowid
        }), 201

    except (KeyError, TypeError, ValueError) as error:
        return jsonify({
            "error": f"Invalid product data: {error}"
        }), 400

    except Exception:
        if db:
            db.rollback()

        app.logger.exception("Add product error")

        return jsonify({
            "error": "Unable to add product"
        }), 500

    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# ==========================================
# TOTAL STOCK API
# ==========================================

@app.route("/api/products/total-stock", methods=["GET"])
def total_stock_api():
    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
            SELECT COALESCE(SUM(stock_quantity), 0)
            FROM products
        """)

        total = cursor.fetchone()[0]

        return jsonify({
            "total_stock": int(total or 0)
        }), 200

    except Exception:
        app.logger.exception("Total stock error")
        return jsonify({
            "error": "Unable to calculate total stock"
        }), 500

    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# ==========================================
# SALES API - GET ALL SALES
# This GET endpoint is required by Reports.
# ==========================================

@app.route("/api/sales", methods=["GET"])
def get_sales():
    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                s.id,
                s.product_id,
                p.product_name,
                s.quantity_sold,
                s.sale_date,
                s.total_amount
            FROM sales s
            LEFT JOIN products p
                ON p.id = s.product_id
            ORDER BY s.sale_date DESC, s.id DESC
        """)

        sales_list = cursor.fetchall()

        for sale in sales_list:
            if sale["sale_date"]:
                sale["sale_date"] = str(sale["sale_date"])

            sale["quantity_sold"] = int(
                sale["quantity_sold"] or 0
            )
            sale["total_amount"] = float(
                sale["total_amount"] or 0
            )

        return jsonify(sales_list), 200

    except Exception:
        app.logger.exception("Get sales error")
        return jsonify({
            "error": "Unable to retrieve sales"
        }), 500

    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# ==========================================
# SALES API - ADD SALE
# ==========================================

@app.route("/api/sales", methods=["POST"])
def add_sale():
    db = None
    cursor = None

    try:
        data = request.get_json(silent=True)

        if not isinstance(data, dict):
            return jsonify({
                "error": "Valid sales JSON data is required"
            }), 400

        product_name = str(
            data.get("product_name", "")
        ).strip()

        if not product_name:
            return jsonify({
                "error": "Product name is required"
            }), 400

        quantity_sold = int(data["quantity_sold"])
        total_amount = float(data["total_amount"])
        sale_date = date.fromisoformat(
            str(data["sale_date"])
        )

        if quantity_sold <= 0 or total_amount < 0:
            return jsonify({
                "error": "Quantity must be positive and amount cannot be negative"
            }), 400

        db = get_db_connection()
        cursor = db.cursor()

        cursor.execute("""
            SELECT id
            FROM products
            WHERE LOWER(TRIM(product_name)) =
                  LOWER(TRIM(%s))
            ORDER BY id
            LIMIT 1
        """, (product_name,))

        product = cursor.fetchone()

        if product is None:
            return jsonify({
                "error": "Product not found. Add the product first."
            }), 404

        cursor.execute("""
            INSERT INTO sales
                (product_id, quantity_sold, sale_date, total_amount)
            VALUES (%s, %s, %s, %s)
        """, (
            product[0],
            quantity_sold,
            sale_date,
            total_amount
        ))

        db.commit()

        return jsonify({
            "message": "Sales data added successfully!"
        }), 201

    except (KeyError, TypeError, ValueError) as error:
        return jsonify({
            "error": f"Invalid sales data: {error}"
        }), 400

    except Exception:
        if db:
            db.rollback()

        app.logger.exception("Add sale error")

        return jsonify({
            "error": "Unable to add sales data"
        }), 500

    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# ==========================================
# DEMAND FORECAST API
# ==========================================

@app.route("/api/forecast/<int:product_id>", methods=["GET"])
def forecast_demand(product_id):
    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT id, product_name, stock_quantity
            FROM products
            WHERE id = %s
        """, (product_id,))

        product = cursor.fetchone()

        if product is None:
            return jsonify({
                "error": "Product not found"
            }), 404

        cursor.execute("""
            SELECT
                COALESCE(SUM(quantity_sold), 0) AS total_sold,
                COUNT(DISTINCT sale_date) AS selling_days,
                MIN(sale_date) AS first_sale_date,
                MAX(sale_date) AS last_sale_date
            FROM sales
            WHERE product_id = %s
        """, (product_id,))

        sales_data = cursor.fetchone()

        forecast = calculate_forecast(
            sales_data["total_sold"],
            sales_data["selling_days"]
        )

        current_stock = int(product["stock_quantity"] or 0)
        predicted_demand = forecast[
            "predicted_demand_next_7_days"
        ]

        return jsonify({
            "product_id": product["id"],
            "product_name": product["product_name"],
            **forecast,
            "current_stock": current_stock,
            "recommended_order": max(
                0, predicted_demand - current_stock
            ),
            "first_sale_date": (
                str(sales_data["first_sale_date"])
                if sales_data["first_sale_date"] else None
            ),
            "last_sale_date": (
                str(sales_data["last_sale_date"])
                if sales_data["last_sale_date"] else None
            ),
            "forecast_method": "Historical average sales baseline"
        }), 200

    except Exception:
        app.logger.exception("Forecast error")
        return jsonify({
            "error": "Unable to calculate forecast"
        }), 500

    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# ==========================================
# REPORTS API - LIVE DATABASE SUMMARY
# ==========================================

@app.route("/api/reports", methods=["GET"])
def get_reports():
    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT COUNT(*) AS total_products
            FROM products
        """)
        total_products = cursor.fetchone()["total_products"]

        cursor.execute("""
            SELECT COALESCE(SUM(stock_quantity), 0) AS current_stock
            FROM products
        """)
        current_stock = cursor.fetchone()["current_stock"]

        cursor.execute("""
            SELECT
                COUNT(*) AS sales_records,
                COALESCE(SUM(total_amount), 0) AS total_sales,
                COALESCE(SUM(quantity_sold), 0) AS total_units_sold,
                COUNT(DISTINCT sale_date) AS selling_days
            FROM sales
        """)
        sales_summary = cursor.fetchone()

        forecast = calculate_forecast(
            sales_summary["total_units_sold"],
            sales_summary["selling_days"]
        )

        cursor.execute("""
            SELECT
                p.id,
                p.product_name,
                p.stock_quantity,
                p.price,
                COALESCE(SUM(s.quantity_sold), 0) AS total_sold,
                COUNT(DISTINCT s.sale_date) AS selling_days
            FROM products p
            LEFT JOIN sales s ON s.product_id = p.id
            GROUP BY
                p.id, p.product_name, p.stock_quantity, p.price
            ORDER BY p.id
        """)
        products_summary = cursor.fetchall()

        for product in products_summary:
            product_forecast = calculate_forecast(
                product["total_sold"],
                product["selling_days"]
            )

            demand = product_forecast[
                "predicted_demand_next_7_days"
            ]
            stock = int(product["stock_quantity"] or 0)

            product["stock_quantity"] = stock
            product["price"] = float(product["price"] or 0)
            product["total_sold"] = int(product["total_sold"] or 0)
            product["predicted_demand"] = demand
            product["recommended_order"] = max(
                0, demand - stock
            )
            product["status"] = (
                "REORDER REQUIRED"
                if demand > stock
                else "STOCK AVAILABLE"
            )

        return jsonify({
            "total_products": int(total_products or 0),
            "total_sales": float(
                sales_summary["total_sales"] or 0
            ),
            "total_sales_records": int(
                sales_summary["sales_records"] or 0
            ),
            "total_units_sold": int(
                sales_summary["total_units_sold"] or 0
            ),
            "current_stock": int(current_stock or 0),
            "forecast_demand": forecast[
                "predicted_demand_next_7_days"
            ],
            "selling_days": forecast["selling_days"],
            "products": products_summary
        }), 200

    except Exception:
        app.logger.exception("Reports summary error")
        return jsonify({
            "error": "Unable to generate report"
        }), 500

    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# ==========================================
# INVENTORY API
# ==========================================

@app.route("/api/inventory", methods=["GET"])
def get_inventory():
    db = None
    cursor = None

    try:
        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                p.id,
                p.product_name,
                p.stock_quantity,
                p.price,
                COALESCE(SUM(s.quantity_sold), 0) AS total_sold,
                COUNT(DISTINCT s.sale_date) AS selling_days
            FROM products p
            LEFT JOIN sales s ON s.product_id = p.id
            GROUP BY
                p.id, p.product_name, p.stock_quantity, p.price
            ORDER BY p.id
        """)

        items = cursor.fetchall()

        for item in items:
            forecast = calculate_forecast(
                item["total_sold"],
                item["selling_days"]
            )

            stock = int(item["stock_quantity"] or 0)
            demand = forecast[
                "predicted_demand_next_7_days"
            ]

            item["stock_quantity"] = stock
            item["price"] = float(item["price"] or 0)
            item["predicted_demand"] = demand
            item["recommended_order"] = max(
                0, demand - stock
            )
            item["status"] = (
                "REORDER REQUIRED"
                if demand > stock
                else "STOCK AVAILABLE"
            )

        return jsonify(items), 200

    except Exception:
        app.logger.exception("Inventory error")
        return jsonify({
            "error": "Unable to retrieve inventory"
        }), 500

    finally:
        if cursor:
            cursor.close()
        if db:
            db.close()


# ==========================================
# DATABASE CONNECTION TEST
# ==========================================

@app.route("/test-db")
def test_db():
    db = None

    try:
        db = get_db_connection()
        return "MySQL Database Connected Successfully!", 200

    except Exception:
        app.logger.exception("Database connection error")
        return "MySQL connection failed. Check Flask terminal.", 500

    finally:
        if db:
            db.close()


# ==========================================
# FORECAST BUTTON TEST PAGE
# ==========================================

@app.route("/forecast-test")
def forecast_test():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Forecast Button Test</title>
    </head>
    <body>
        <h1>Forecast Test Page</h1>
        <button type="button"
                onclick="alert('BUTTON WORKS!')">
            TEST BUTTON
        </button>
    </body>
    </html>
    """
# ==========================================
# START APPLICATION
# ==========================================

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )