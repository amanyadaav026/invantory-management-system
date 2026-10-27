
from flask import Flask, render_template, request, redirect, url_for, flash, Response
import sqlite3
import csv
import io

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

    conn.execute("""
        CREATE TABLE IF NOT EXISTS stock_movements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            action TEXT NOT NULL,
            quantity_change INTEGER NOT NULL,
            previous_quantity INTEGER NOT NULL,
            new_quantity INTEGER NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
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

    low_stock_products = [
        product for product in products
        if 0 < product["quantity"] <= 5
    ]

    out_of_stock_products = [
        product for product in products
        if product["quantity"] == 0
    ]

    total_products = len(products)
    low_stock = sum(
        1 for product in products
        if 0 < product["quantity"] <= 5
    )
    out_of_stock = sum(
        1 for product in products
        if product["quantity"] == 0
    )

    total_inventory_value = sum(
        product["quantity"] * product["price"]
        for product in products
    )

    # Category-wise inventory analytics
    category_analytics = conn.execute("""
        SELECT
            category,
            COUNT(*) AS product_count,
            SUM(quantity) AS total_quantity,
            SUM(quantity * price) AS inventory_value
        FROM products
        GROUP BY category
        ORDER BY inventory_value DESC
    """).fetchall()
    
    conn.close()

    return render_template(
        "index.html",
        products=products,
        total_products=total_products,
        low_stock=low_stock,
        out_of_stock=out_of_stock,
        total_inventory_value=total_inventory_value,
        low_stock_products=low_stock_products,
        out_of_stock_products=out_of_stock_products,
        category_analytics=category_analytics
    )

@app.route("/export-inventory")
def export_inventory():
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row

    products = conn.execute(
        "SELECT id, name, category, quantity, price FROM products ORDER BY id ASC"
    ).fetchall()

    conn.close()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Product ID",
        "Product Name",
        "Category",
        "Quantity",
        "Unit Price (INR)",
        "Inventory Value (INR)"
    ])

    for product in products:
        writer.writerow([
            product["id"],
            product["name"],
            product["category"],
            product["quantity"],
            f'{product["price"]:.2f}',
            f'{product["quantity"] * product["price"]:.2f}'
        ])

    csv_data = "\ufeff" + output.getvalue()
    output.close()

    return Response(
        csv_data,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=stocktrack_inventory.csv"
        }
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

    existing_product = conn.execute("""
        SELECT id FROM products
        WHERE LOWER(name) = LOWER(?)
        AND LOWER(category) = LOWER(?)
        AND id != ?
    """, (name, category, product_id)).fetchone()

    if existing_product:
        conn.close()
        flash("Duplicate product! This product already exists in this category.", "error")
        return redirect(url_for("home"))

    old_product = conn.execute(
        "SELECT name, quantity FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if old_product is None:
        conn.close()
        flash("Product not found.", "error")
        return redirect(url_for("home"))

    old_name, previous_quantity = old_product

    conn.execute("""
        UPDATE products
        SET name = ?, category = ?, quantity = ?, price = ?
        WHERE id = ?
    """, (name, category, quantity, price, product_id))

    if quantity != previous_quantity:
        conn.execute("""
            INSERT INTO stock_movements
            (product_id, product_name, action, quantity_change,
             previous_quantity, new_quantity)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            product_id,
            name,
            "Edit",
            abs(quantity - previous_quantity),
            previous_quantity,
            quantity
        ))

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
        "SELECT name, quantity FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if product is None:
        conn.close()
        flash("Product not found.", "error")
        return redirect(url_for("home"))

    product_name, current_quantity = product

    if action == "out" and quantity_change > current_quantity:
        conn.close()
        flash("Stock out quantity cannot exceed available stock.", "error")
        return redirect(url_for("home"))

    if action == "in":
        new_quantity = current_quantity + quantity_change
        movement_action = "Stock In"
    else:
        new_quantity = current_quantity - quantity_change
        movement_action = "Stock Out"

    conn.execute(
        "UPDATE products SET quantity = ? WHERE id = ?",
        (new_quantity, product_id)
    )

    conn.execute("""
        INSERT INTO stock_movements
        (product_id, product_name, action, quantity_change,
         previous_quantity, new_quantity)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        product_id,
        product_name,
        movement_action,
        quantity_change,
        current_quantity,
        new_quantity
    ))

    conn.commit()
    conn.close()

    flash("Stock updated successfully!", "success")
    return redirect(url_for("home"))


@app.route("/stock-history")
def stock_history():
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row

    movements = conn.execute("""
        SELECT product_id, product_name, action, quantity_change,
               previous_quantity, new_quantity, created_at
        FROM stock_movements
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template("stock_history.html", movements=movements)


@app.route("/product/<int:product_id>")
def product_details(product_id):
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row

    product = conn.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if product is None:
        conn.close()
        flash("Product not found.", "error")
        return redirect(url_for("home"))

    movements = conn.execute("""
        SELECT action, quantity_change, previous_quantity,
               new_quantity, created_at
        FROM stock_movements
        WHERE product_id = ?
        ORDER BY id DESC
    """, (product_id,)).fetchall()

    inventory_value = product["quantity"] * product["price"]

    conn.close()

    return render_template(
        "product_details.html",
        product=product,
        movements=movements,
        inventory_value=inventory_value
    )

if __name__ == "__main__":
    app.run(debug=True)
