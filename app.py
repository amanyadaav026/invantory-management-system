from flask import Flask, render_template, request, redirect, url_for, flash, Response, g, jsonify
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
            db.execute("PRAGMA foreign_keys = ON")
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
        # Add SKU column if it does not exist
        product_columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(products)"
            ).fetchall()
        }

        if "sku" not in product_columns:
            conn.execute(
                "ALTER TABLE products ADD COLUMN sku TEXT"
            )

        # Generate SKU for existing products
        conn.execute("""
            UPDATE products
            SET sku = 'ST-' || printf('%04d', id)
            WHERE sku IS NULL OR sku = ''
        """)

        # Prevent duplicate SKUs
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_products_sku
            ON products(sku)
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER,
                original_product_id INTEGER NOT NULL,
                product_name TEXT NOT NULL,
                action TEXT NOT NULL,
                quantity_change INTEGER NOT NULL,
                previous_quantity INTEGER NOT NULL,
                new_quantity INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id)
                ON DELETE SET NULL
            )
        """)

        columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(stock_movements)"
            ).fetchall()
        }

        if "original_product_id" not in columns:
            conn.execute("BEGIN IMMEDIATE")

            conn.execute("""
                CREATE TABLE stock_movements_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER,
                    original_product_id INTEGER NOT NULL,
                    product_name TEXT NOT NULL,
                    action TEXT NOT NULL,
                    quantity_change INTEGER NOT NULL,
                    previous_quantity INTEGER NOT NULL,
                    new_quantity INTEGER NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id)
                    ON DELETE SET NULL
                )
            """)

            conn.execute("""
                INSERT INTO stock_movements_new (
                    id, product_id, original_product_id, product_name,
                    action, quantity_change, previous_quantity,
                    new_quantity, created_at
                )
                SELECT
                    sm.id,
                    CASE WHEN p.id IS NOT NULL THEN sm.product_id ELSE NULL END,
                    sm.product_id,
                    sm.product_name,
                    sm.action,
                    sm.quantity_change,
                    sm.previous_quantity,
                    sm.new_quantity,
                    sm.created_at
                FROM stock_movements sm
                LEFT JOIN products p ON p.id = sm.product_id
            """)

            conn.execute("DROP TABLE stock_movements")

            conn.execute("""
                ALTER TABLE stock_movements_new
                RENAME TO stock_movements
            """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_products_name_category
            ON products(LOWER(name), LOWER(category))
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_movements_product_id
            ON stock_movements(product_id, id DESC)
        """)

        conn.commit()

    except sqlite3.Error:
        if "conn" in locals():
            conn.rollback()

        logging.exception("Database initialization failed.")
        raise

with app.app_context():
    init_db()


@app.route("/")
def home():
    conn = get_db()
    is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    page = request.args.get("page", 1, type=int)
    per_page = 10
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "all")
    sort = request.args.get("sort", "default")

    if page < 1:
        page = 1

    # Build search and category filters
    filters = []
    filter_params = []

    if search:
        filters.append(
            """
            (
                LOWER(name) LIKE ?
                OR LOWER(category) LIKE ?
                OR LOWER(sku) LIKE ?
            )
            """
        )

        search_value = f"%{search.lower()}%"
        filter_params.extend([
            search_value,
            search_value,
            search_value
        ])

    if category != "all":
        filters.append("LOWER(category) = LOWER(?)")
        filter_params.append(category)

    where_clause = ""
    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    # Count filtered products
    filtered_products_count = conn.execute(
        f"SELECT COUNT(*) FROM products {where_clause}",
        filter_params
    ).fetchone()[0]

    # Global product count
    total_products = conn.execute(
        "SELECT COUNT(*) FROM products"
    ).fetchone()[0]

    # Calculate pagination
    total_pages = (filtered_products_count + per_page - 1) // per_page

    if total_pages > 0 and page > total_pages:
        page = total_pages

    if total_pages == 0:
        page = 1

    offset = (page - 1) * per_page

    # Sorting options
    sort_options = {
        "default": "id DESC",
        "name-asc": "name COLLATE NOCASE ASC",
        "quantity-asc": "quantity ASC",
        "price-asc": "price ASC",
        "price-desc": "price DESC"
    }

    if sort not in sort_options:
        sort = "default"

    order_by = sort_options[sort]

    # Fetch all available categories
    categories = conn.execute("""
        SELECT DISTINCT category
        FROM products
        ORDER BY category COLLATE NOCASE
    """).fetchall()

    # Fetch products for current page
    products = conn.execute(
        f"""
        SELECT * FROM products
        {where_clause}
        ORDER BY {order_by}
        LIMIT ? OFFSET ?
        """,
        (*filter_params, per_page, offset)
    ).fetchall()

    # Return only product rows and pagination for AJAX requests
    if is_ajax:
        rows_html = render_template(
            "_product_rows.html",
            products=products
        )

        pagination_html = render_template(
            "_pagination.html",
            page=page,
            total_pages=total_pages,
            search=search,
            category=category,
            sort=sort
        )

        return jsonify({
            "rows_html": rows_html,
            "pagination_html": pagination_html,
            "result_count": filtered_products_count,
            "page": page,
            "total_pages": total_pages
        })

    # Global low-stock products
    low_stock_products = conn.execute("""
        SELECT * FROM products
        WHERE quantity > 0 AND quantity <= 5
        ORDER BY id DESC
    """).fetchall()

    # Global out-of-stock products
    out_of_stock_products = conn.execute("""
        SELECT * FROM products
        WHERE quantity = 0
        ORDER BY id DESC
    """).fetchall()

    low_stock = conn.execute("""
        SELECT COUNT(*) FROM products
        WHERE quantity > 0 AND quantity <= 5
    """).fetchone()[0]

    out_of_stock = conn.execute("""
        SELECT COUNT(*) FROM products
        WHERE quantity = 0
    """).fetchone()[0]

    total_inventory_value = conn.execute("""
        SELECT COALESCE(SUM(quantity * price), 0)
        FROM products
    """).fetchone()[0]

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
        categories=categories,
        page=page,
        total_pages=total_pages,
        search=search,
        category=category,
        sort=sort,
        total_products=total_products,
        filtered_products_count=filtered_products_count,
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
        "SELECT id, sku, name, category, quantity, price FROM products ORDER BY id ASC"
    ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Product ID",
        "SKU",
        "Product Name",
        "Category",
        "Quantity",
        "Unit Price (INR)",
        "Inventory Value (INR)"
    ])

    for product in products:
        writer.writerow([
            product["id"],
            product["sku"],
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

            cursor = conn.execute(
                """
                INSERT INTO products (name, category, quantity, price)
                VALUES (?, ?, ?, ?)
                """,
                (name, category, quantity, price)
            )

            product_id = cursor.lastrowid
            sku = f"ST-{product_id:04d}"

            conn.execute(
                "UPDATE products SET sku = ? WHERE id = ?",
                (sku, product_id)
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

    cursor = conn.execute(
        """INSERT INTO products (name, category, quantity, price)
           VALUES (?, ?, ?, ?)""",
        (name, category, quantity, price)
    )

    product_id = cursor.lastrowid
    sku = f"ST-{product_id:04d}"

    conn.execute(
        "UPDATE products SET sku = ? WHERE id = ?",
        (sku, product_id)
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
            (product_id, original_product_id, product_name, action,
             quantity_change, previous_quantity, new_quantity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            product_id,
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

    try:
        conn.execute("BEGIN IMMEDIATE")

        product = conn.execute(
            "SELECT name, quantity FROM products WHERE id = ?",
            (product_id,)
        ).fetchone()

        if product is None:
            conn.rollback()
            flash("Product not found.", "error")
            return redirect(url_for("home"))

        product_name, current_quantity = product

        if action == "out" and quantity_change > current_quantity:
            conn.rollback()
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
            (product_id, original_product_id, product_name, action,
             quantity_change, previous_quantity, new_quantity)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            product_id,
            product_id,
            product_name,
            movement_action,
            quantity_change,
            current_quantity,
            new_quantity
        ))

        conn.commit()

    except sqlite3.Error:
        conn.rollback()
        logging.exception("Stock update failed.")
        flash("Unable to update stock. Please try again.", "error")
        return redirect(url_for("home"))

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