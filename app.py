
from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3

app = Flask(__name__)
app.secret_key = "inventory-dev-secret-key"

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
    total_inventory_value = sum(
        product["quantity"] * product["price"]
        for product in products
    )

    conn.close()

    return render_template(
        "index.html",
        products=products,
        total_products=total_products,
        low_stock=low_stock,
        out_of_stock=out_of_stock,
        total_inventory_value=total_inventory_value
    )



@app.route("/add-product", methods=["POST"])
def add_product():
    name = request.form["name"].strip()
    category = request.form["category"].strip()
    if not name or not category:
        flash("Product name and category cannot be empty.", "error")
        return redirect(url_for("home"))

    try:
        quantity = int(request.form["quantity"])
        price = float(request.form["price"])
    except ValueError:
        flash("Quantity must be a whole number and price must be a valid number.", "error")
        return redirect(url_for("home"))
    
    if quantity < 0 or price < 0:
        flash("Quantity and price cannot be negative.", "error")
        return redirect(url_for("home"))


    conn = sqlite3.connect("inventory.db")

    existing_product = conn.execute(
        """SELECT id FROM products
           WHERE LOWER(name) = LOWER(?)
           AND LOWER(category) = LOWER(?)""",
        (name, category)
    ).fetchone()

    if existing_product:
        conn.close()
        flash("Duplicate product! This product already exists in this category.", "error")
        return redirect(url_for("home"))

    conn.execute(
        """INSERT INTO products (name, category, quantity, price)
           VALUES (?, ?, ?, ?)""",
        (name, category, quantity, price)
    )

    conn.commit()
    conn.close()
    flash("Product added successfully!", "success")
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
    flash("Product deleted successfully!", "success")
    return redirect(url_for("home"))


@app.route("/edit-product/<int:product_id>", methods=["POST"])
def edit_product(product_id):
    name = request.form["name"]
    category = request.form["category"]
    
    if not name or not category:
        flash("Product name and category cannot be empty.", "error")
        return redirect(url_for("home"))
    
    try:
        quantity = int(request.form["quantity"])
        price = float(request.form["price"])
    except ValueError:
        flash("Quantity must be a whole number and price must be a valid number.", "error")
        return redirect(url_for("home"))
    
    if quantity < 0 or price < 0:
        flash("Quantity and price cannot be negative.", "error")
        return redirect(url_for("home"))

    conn = sqlite3.connect("inventory.db")
    existing_product = conn.execute(
        """SELECT id FROM products
           WHERE LOWER(name) = LOWER(?)
           AND LOWER(category) = LOWER(?)
           AND id != ?""",
        (name, category, product_id)
    ).fetchone()
    
    if existing_product:
        conn.close()
        flash("Duplicate product! This product already exists in this category.", "error")
        return redirect(url_for("home"))

    conn.execute(
        """UPDATE products
           SET name = ?, category = ?, quantity = ?, price = ?
           WHERE id = ?""",
        (name, category, quantity, price, product_id)
    )

    conn.commit()
    conn.close()
    flash("Product updated successfully!", "success")
    return redirect(url_for("home"))

@app.route("/update-stock/<int:product_id>", methods=["POST"])
def update_stock(product_id):
    try:
        quantity_change = int(request.form["quantity_change"])
    except (ValueError, KeyError):
        flash("Please enter a valid whole number.", "error")
        return redirect(url_for("home"))

    if quantity_change <= 0:
        flash("Quantity must be greater than zero.", "error")
        return redirect(url_for("home"))

    action = request.form.get("action")

    if action not in ("in", "out"):
        flash("Invalid stock action.", "error")
        return redirect(url_for("home"))

    conn = sqlite3.connect("inventory.db")

    product = conn.execute(
        "SELECT quantity FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if product is None:
        conn.close()
        flash("Product not found.", "error")
        return redirect(url_for("home"))

    current_quantity = product[0]

    if action == "out" and quantity_change > current_quantity:
        conn.close()
        flash("Stock out quantity cannot exceed available stock.", "error")
        return redirect(url_for("home"))

    if action == "in":
        new_quantity = current_quantity + quantity_change
    else:
        new_quantity = current_quantity - quantity_change

    conn.execute(
        "UPDATE products SET quantity = ? WHERE id = ?",
        (new_quantity, product_id)
    )

    conn.commit()
    conn.close()

    flash("Stock updated successfully!", "success")
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)

