from flask import Flask, render_template, request, jsonify
import mysql.connector

app = Flask(__name__, template_folder="../")


def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="thiran",
        database="smart_retail"
    )


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/products")
def products():
    return render_template("products.html")


@app.route("/sales")
def sales():
    return render_template("sales.html")


@app.route("/forecast")
def forecast():
    return render_template("forecast.html")


@app.route("/inventory")
def inventory():
    return render_template("inventory.html")


@app.route("/reports")
def reports():
    return render_template("reports.html")


@app.route("/api/products", methods=["POST"])
def add_product():
    try:
        data = request.get_json()

        product_name = data["product_name"]
        category = data["category"]
        price = data["price"]
        stock_quantity = data["stock_quantity"]

        db = get_db_connection()
        cursor = db.cursor()

        sql = """
        INSERT INTO products
        (product_name, category, price, stock_quantity)
        VALUES (%s, %s, %s, %s)
        """

        values = (
            product_name,
            category,
            price,
            stock_quantity
        )

        cursor.execute(sql, values)
        db.commit()

        cursor.close()
        db.close()

        return jsonify({
            "message": "Product added successfully!"
        }), 201

    except Exception as e:
        return jsonify({
            "error": str(e)
        }), 500


@app.route("/test-db")
def test_db():
    try:
        db = get_db_connection()
        db.close()

        return "MySQL Database Connected Successfully!"

    except Exception as e:
        return f"MySQL Connection Error: {e}"


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False
    )