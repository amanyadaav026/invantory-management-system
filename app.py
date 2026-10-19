
from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect("inventory.db")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL
        )
    """)

    conn.commit()
    conn.close()

init_db()


@app.route("/")
def home():
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row

    products = conn.execute(
        "SELECT * FROM products ORDER BY id DESC"
    ).fetchall()

    total_products = len(products)
    low_stock = sum(1 for product in products if 0 < product["quantity"] <= 5)
    out_of_stock = sum(1 for product in products if product["quantity"] == 0)

    conn.close()

    return render_template(
        "index.html",
        products=products,
        total_products=total_products,
        low_stock=low_stock,
        out_of_stock=out_of_stock
    )


@app.route("/add-product", methods=["POST"])
def add_product():
    name = request.form["name"]
    category = request.form["category"]
    quantity = int(request.form["quantity"])
    price = float(request.form["price"])

    conn = sqlite3.connect("inventory.db")

    conn.execute(
        "INSERT INTO products (name, category, quantity, price) VALUES (?, ?, ?, ?)",
        (name, category, quantity, price)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("home"))



@app.route("/delete-product/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    conn = sqlite3.connect("inventory.db")

    conn.execute(
        "DELETE FROM products WHERE id = ?",
        (product_id,)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("home"))


@app.route("/edit-product/<int:product_id>", methods=["POST"])
def edit_product(product_id):
    name = request.form["name"]
    category = request.form["category"]
    quantity = int(request.form["quantity"])
    price = float(request.form["price"])

    conn = sqlite3.connect("inventory.db")

    conn.execute(
        """UPDATE products
           SET name = ?, category = ?, quantity = ?, price = ?
           WHERE id = ?""",
        (name, category, quantity, price, product_id)
    )

    conn.commit()
    conn.close()

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)

