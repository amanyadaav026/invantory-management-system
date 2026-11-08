from flask import Flask, render_template, request, redirect, url_for, flash, Response, g
from dotenv import load_dotenv
import sqlite3
import csv
import io
import os
import logging

load_dotenv()
logging.basicConfig(
    filename="stocktrack.log",
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

if not app.secret_key:
    raise RuntimeError("SECRET_KEY is missing. Please configure it in the .env file.")

def get_db():
    if "db" not in g:
        try:
            db = sqlite3.connect("inventory.db")
            db.row_factory = sqlite3.Row
            g.db = db

        except sqlite3.Error:
            logging.exception("Database connection failed.")
            raise

    return g.db

@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)

    if db is not None:
        db.close()

def init_db():
    try:
        conn = get_db()

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

    except sqlite3.Error:
        logging.exception("Database initialization failed.")
        raise

with app.app_context():
    init_db()

@app.route("/")
def home():
    conn = get_db()

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
    conn = get_db()

    products = conn.execute(
        "SELECT id, name, category, quantity, price FROM products ORDER BY id ASC"
    ).fetchall()

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

@app.route("/import-inventory", methods=["POST"])
def import_inventory():
    if "file" not in request.files:
        flash("Please select a CSV file.")
        return redirect(url_for("home"))

    file = request.files["file"]

    if file.filename == "":
        flash("No file selected.")
        return redirect(url_for("home"))

    if not file.filename.lower().endswith(".csv"):
        flash("Please upload a valid CSV file.")
        return redirect(url_for("home"))

    try:
        csv_content = file.read().decode("utf-8-sig")

        if not csv_content.strip():
            flash("The CSV file is empty.")
            return redirect(url_for("home"))

        reader = csv.DictReader(io.StringIO(csv_content))

        required_columns = {
            "Product Name",
            "Category",
            "Quantity",
            "Unit Price (INR)"
        }

        if not reader.fieldnames:
            flash("Invalid CSV file: headers are missing.")
            return redirect(url_for("home"))

        reader.fieldnames = [header.strip() for header in reader.fieldnames]

        if not required_columns.issubset(set(reader.fieldnames)):
            flash("Invalid CSV format. Please use a StockTrack inventory CSV.")
            return redirect(url_for("home"))

        conn = get_db()

        imported = 0
        duplicates = 0
        invalid = 0

        for row in reader:
            name = (row.get("Product Name") or "").strip()
            category = (row.get("Category") or "").strip()

            try:
                quantity = int(row.get("Quantity", ""))
                price = float(row.get("Unit Price (INR)", ""))

                if not name or not category or quantity < 0 or not (price >= 0):
                    invalid += 1
                    continue

            except (ValueError, TypeError):
                invalid += 1
                continue

            existing_product = conn.execute(
                """
                SELECT id FROM products
                WHERE LOWER(name) = LOWER(?)
                AND LOWER(category) = LOWER(?)
                """,
                (name, category)
            ).fetchone()

            if existing_product:
                duplicates += 1
                continue

            conn.execute(
                """
                INSERT INTO products (name, category, quantity, price)
                VALUES (?, ?, ?, ?)
                """,
                (name, category, quantity, price)
            )

            imported += 1

        conn.commit()
        flash(
            f"CSV import complete! Imported: {imported}, "
            f"Duplicates skipped: {duplicates}, Invalid rows skipped: {invalid}."
        )

    except UnicodeDecodeError:
        flash("Unable to read this file. Please upload a UTF-8 CSV file.")

    except csv.Error:
        flash("There was an error reading the CSV file.")

    return redirect(url_for("home"))

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


    conn = get_db()

    existing_product = conn.execute(
        """SELECT id FROM products
           WHERE LOWER(name) = LOWER(?)
           AND LOWER(category) = LOWER(?)""",
        (name, category)
    ).fetchone()

    if existing_product:
        flash("Duplicate product! This product already exists in this category.", "error")
        return redirect(url_for("home"))

    conn.execute(
        """INSERT INTO products (name, category, quantity, price)
           VALUES (?, ?, ?, ?)""",
        (name, category, quantity, price)
    )

    conn.commit()
    flash("Product added successfully!", "success")
    return redirect(url_for("home"))


@app.route("/delete-product/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    conn = get_db()

    conn.execute(
        "DELETE FROM products WHERE id = ?",
        (product_id,)
    )

    conn.commit()
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

    conn = get_db()

    existing_product = conn.execute("""
        SELECT id FROM products
        WHERE LOWER(name) = LOWER(?)
        AND LOWER(category) = LOWER(?)
        AND id != ?
    """, (name, category, product_id)).fetchone()

    if existing_product:
        flash("Duplicate product! This product already exists in this category.", "error")
        return redirect(url_for("home"))

    old_product = conn.execute(
        "SELECT name, quantity FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if old_product is None:
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

    conn = get_db()

    product = conn.execute(
        "SELECT name, quantity FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if product is None:
        flash("Product not found.", "error")
        return redirect(url_for("home"))

    product_name, current_quantity = product

    if action == "out" and quantity_change > current_quantity:
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

    flash("Stock updated successfully!", "success")
    return redirect(url_for("home"))


@app.route("/stock-history")
def stock_history():
    conn = get_db()

    movements = conn.execute("""
        SELECT product_id, product_name, action, quantity_change,
               previous_quantity, new_quantity, created_at
        FROM stock_movements
        ORDER BY id DESC
    """).fetchall()


    return render_template("stock_history.html", movements=movements)


@app.route("/product/<int:product_id>")
def product_details(product_id):
    conn = get_db()

    product = conn.execute(
        "SELECT * FROM products WHERE id = ?",
        (product_id,)
    ).fetchone()

    if product is None:
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

    return render_template(
        "product_details.html",
        product=product,
        movements=movements,
        inventory_value=inventory_value
    )

@app.errorhandler(404)
def page_not_found(error):
    return render_template("404.html"), 404

@app.errorhandler(500)
def internal_server_error(error):
    return render_template("500.html"), 500

if __name__ == "__main__":
    app.run(debug=True)