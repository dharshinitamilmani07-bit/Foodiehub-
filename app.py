import json
import random
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

from database import get_db, init_db

app = Flask(__name__)
app.secret_key = "foodiehub-dev-secret-key-change-me"

STATUS_STEPS = [
    "Order Confirmed",
    "Kitchen Started",
    "Food Ready",
    "Rider Picked Up",
    "Almost There",
    "Delivered",
]

DELIVERY_NAMES = ["Arun", "Priya", "Karthik", "Divya", "Suresh", "Meena"]

MOODS = [
    {"key": "spicy", "label": "Spicy 🌶️"},
    {"key": "sweet", "label": "Sweet 🍩"},
    {"key": "healthy", "label": "Healthy 🥗"},
    {"key": "filling", "label": "Filling 🍛"},
    {"key": "quick", "label": "Quick ⚡"},
]

BUDGETS = [100, 150, 200, 250]

# Every food query joins restaurants so each dish card can show/link its restaurant.
FOOD_SELECT = """
    SELECT foods.*, restaurants.name AS restaurant_name, restaurants.area AS restaurant_area
    FROM foods JOIN restaurants ON foods.restaurant_id = restaurants.id
"""


# ---------- helpers ----------

def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    conn.close()
    return user


def login_required(view):
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("login"))
        if current_user() is None:
            # Session cookie points to a user that no longer exists in this
            # database (e.g. the db file was reset or replaced). Log out
            # cleanly instead of crashing.
            session.clear()
            flash("Your session has expired. Please log in again.", "error")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    wrapped.__name__ = view.__name__
    return wrapped


def get_cart():
    return session.setdefault("cart", {})  # {food_id_str: qty}


def food_match_percent(food, moods_selected):
    tags = set(food["tags"].split(","))
    if not moods_selected:
        return min(99, 70 + int(food["rating"] * 5))
    overlap = len(tags.intersection(moods_selected))
    base = 55 + overlap * 15
    base += int(food["rating"] * 2)
    return min(base, 99)


def foods_to_cards(foods, moods_selected=None):
    moods_selected = moods_selected or set()
    cards = []
    for f in foods:
        cards.append({
            "id": f["id"],
            "name": f["name"],
            "restaurant": f["restaurant_name"],
            "restaurant_id": f["restaurant_id"],
            "price": f["price"],
            "rating": f["rating"],
            "prep_time": f["prep_time"],
            "veg": f["veg"],
            "tags": f["tags"].split(","),
            "image": f["image_url"],
            "match": food_match_percent(f, moods_selected),
        })
    return cards


def restaurants_to_cards(restaurants):
    cards = []
    for r in restaurants:
        cards.append({
            "id": r["id"],
            "name": r["name"],
            "area": r["area"],
            "cuisines": r["cuisines"].split(", "),
            "rating": r["rating"],
            "delivery_time_min": r["delivery_time_min"],
            "cost_for_two": r["cost_for_two"],
            "image": r["banner_image"],
            "is_pure_veg": r["is_pure_veg"],
            "promoted": r["promoted"],
        })
    return cards


# ---------- routes ----------

@app.route("/")
def splash():
    if session.get("user_id"):
        return redirect(url_for("home"))
    return render_template("splash.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")

        if not name or not email or not phone or not password:
            flash("Please fill in all fields.", "error")
            return render_template("register.html")
        if len(password) < 4:
            flash("Password should be at least 4 characters.", "error")
            return render_template("register.html")

        conn = get_db()
        existing = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        if existing:
            conn.close()
            flash("An account with this email already exists.", "error")
            return render_template("register.html")

        conn.execute(
            "INSERT INTO users (name, email, phone, password_hash) VALUES (?,?,?,?)",
            (name, email, phone, generate_password_hash(password)),
        )
        conn.commit()
        user = conn.execute("SELECT id FROM users WHERE email=?", (email,)).fetchone()
        conn.close()

        session["user_id"] = user["id"]
        flash("Welcome to Foodie Hub!", "success")
        return redirect(url_for("home"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            return redirect(url_for("home"))
        flash("Invalid email or password.", "error")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("splash"))


@app.route("/home")
@login_required
def home():
    user = current_user()
    conn = get_db()
    recommended = conn.execute(FOOD_SELECT + " ORDER BY foods.rating DESC LIMIT 8").fetchall()
    top_restaurants = conn.execute(
        "SELECT * FROM restaurants ORDER BY promoted DESC, rating DESC LIMIT 8"
    ).fetchall()
    recent_orders = conn.execute(
        "SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 3", (user["id"],)
    ).fetchall()
    conn.close()

    recent_items = []
    seen = set()
    for o in recent_orders:
        for item in json.loads(o["items_json"]):
            if item["name"] not in seen:
                seen.add(item["name"])
                recent_items.append(item)

    return render_template(
        "home.html",
        user=user,
        moods=MOODS,
        budgets=BUDGETS,
        restaurants=restaurants_to_cards(top_restaurants),
        recommended=foods_to_cards(recommended),
        recent_items=recent_items[:4],
        cart_count=sum(get_cart().values()),
    )


@app.route("/restaurants")
@login_required
def restaurants_list():
    conn = get_db()
    all_restaurants = conn.execute("SELECT * FROM restaurants ORDER BY promoted DESC, rating DESC").fetchall()
    conn.close()

    q = request.args.get("q", "").strip().lower()
    active = request.args.getlist("f")
    active_set = set(active)

    def matches(r):
        if q and q not in r["name"].lower() and q not in r["cuisines"].lower() and q not in r["area"].lower():
            return False
        if "pureveg" in active_set and not r["is_pure_veg"]:
            return False
        if "fast30" in active_set and r["delivery_time_min"] > 30:
            return False
        if "ratinghigh" in active_set and r["rating"] < 4.3:
            return False
        return True

    filtered = [r for r in all_restaurants if matches(r)]
    return render_template(
        "restaurants.html",
        restaurants=restaurants_to_cards(filtered),
        q=request.args.get("q", ""),
        active=active_set,
        cart_count=sum(get_cart().values()),
    )


@app.route("/restaurant/<int:restaurant_id>")
@login_required
def restaurant_detail(restaurant_id):
    conn = get_db()
    r = conn.execute("SELECT * FROM restaurants WHERE id=?", (restaurant_id,)).fetchone()
    if not r:
        conn.close()
        return redirect(url_for("restaurants_list"))
    dishes = conn.execute(
        FOOD_SELECT + " WHERE foods.restaurant_id=? ORDER BY foods.popular DESC, foods.rating DESC",
        (restaurant_id,),
    ).fetchall()
    conn.close()

    return render_template(
        "restaurant_detail.html",
        restaurant=restaurants_to_cards([r])[0],
        cards=foods_to_cards(dishes),
        cart_count=sum(get_cart().values()),
    )


@app.route("/discover")
@login_required
def discover():
    conn = get_db()
    all_foods = conn.execute(FOOD_SELECT).fetchall()
    conn.close()

    q = request.args.get("q", "").strip().lower()
    active = request.args.getlist("f")
    active_set = set(active)
    moods_selected = active_set.intersection({"spicy", "sweet", "healthy", "filling", "quick"})

    def matches(f):
        if q and q not in f["name"].lower() and q not in f["restaurant_name"].lower():
            return False
        tags = set(f["tags"].split(","))
        if "under100" in active_set and f["price"] > 100:
            return False
        if "under200" in active_set and f["price"] > 200:
            return False
        if "ready20" in active_set and f["prep_time"] > 20:
            return False
        if "veg" in active_set and not f["veg"]:
            return False
        if "nonveg" in active_set and f["veg"]:
            return False
        if "popular" in active_set and not f["popular"]:
            return False
        if moods_selected and not tags.intersection(moods_selected):
            return False
        return True

    filtered = [f for f in all_foods if matches(f)]
    cards = foods_to_cards(filtered, moods_selected)
    cards.sort(key=lambda c: c["match"], reverse=True)

    filters = [
        ("under100", "Under ₹100"),
        ("under200", "Under ₹200"),
        ("ready20", "Ready in 20 mins"),
        ("spicy", "Spicy"),
        ("sweet", "Sweet"),
        ("healthy", "Healthy"),
        ("veg", "Vegetarian"),
        ("nonveg", "Non-Vegetarian"),
        ("popular", "Popular nearby"),
    ]

    return render_template(
        "discover.html",
        cards=cards,
        filters=filters,
        active=active_set,
        q=request.args.get("q", ""),
        cart_count=sum(get_cart().values()),
    )


@app.route("/budget-mode")
@login_required
def budget_mode():
    amount = request.args.get("amount", type=int)
    conn = get_db()
    all_foods = conn.execute(FOOD_SELECT + " ORDER BY foods.price ASC").fetchall()
    conn.close()

    combos = []
    singles_cards = []
    if amount:
        affordable = [f for f in all_foods if f["price"] <= amount]
        used = set()
        for i, a in enumerate(affordable):
            for b in affordable[i + 1:]:
                if a["price"] + b["price"] <= amount and a["id"] not in used and b["id"] not in used:
                    combos.append([a, b])
                    used.add(a["id"])
                    used.add(b["id"])
                    break
        singles = [f for f in affordable if f["id"] not in used]
        combos = [{"dishes": foods_to_cards(c), "total": sum(x["price"] for x in c)} for c in combos]
        singles_cards = foods_to_cards(singles)

    return render_template(
        "budget.html",
        budgets=BUDGETS,
        amount=amount,
        combos=combos,
        singles=singles_cards,
        cart_count=sum(get_cart().values()),
    )


@app.route("/food/<int:food_id>")
@login_required
def food_detail(food_id):
    conn = get_db()
    f = conn.execute(FOOD_SELECT + " WHERE foods.id=?", (food_id,)).fetchone()
    user = current_user()
    is_fav = conn.execute(
        "SELECT 1 FROM favorites WHERE user_id=? AND food_id=?", (user["id"], food_id)
    ).fetchone()
    conn.close()
    if not f:
        return redirect(url_for("discover"))

    card = foods_to_cards([f])[0]
    return render_template(
        "food_detail.html",
        food=card,
        description=f["description"],
        ingredients=f["ingredients"].split(","),
        is_fav=bool(is_fav),
        cart_count=sum(get_cart().values()),
    )


@app.route("/add_to_cart/<int:food_id>", methods=["POST"])
@login_required
def add_to_cart(food_id):
    qty = max(1, request.form.get("qty", 1, type=int))
    cart = get_cart()
    key = str(food_id)
    cart[key] = cart.get(key, 0) + qty
    session.modified = True
    flash("Added to cart!", "success")
    return redirect(url_for("food_detail", food_id=food_id))


@app.route("/cart")
@login_required
def view_cart():
    cart = get_cart()
    conn = get_db()
    items = []
    subtotal = 0
    for food_id, qty in cart.items():
        f = conn.execute(FOOD_SELECT + " WHERE foods.id=?", (food_id,)).fetchone()
        if f:
            line_total = f["price"] * qty
            subtotal += line_total
            items.append({
                "id": f["id"], "name": f["name"], "restaurant": f["restaurant_name"],
                "price": f["price"], "qty": qty, "line_total": line_total, "image": f["image_url"],
            })
    conn.close()

    delivery_fee = 0 if subtotal == 0 or subtotal >= 300 else 29
    discount = 20 if subtotal >= 250 else 0
    total = max(subtotal + delivery_fee - discount, 0)

    return render_template(
        "cart.html",
        items=items,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        discount=discount,
        total=total,
        cart_count=sum(cart.values()),
    )


@app.route("/cart/update/<int:food_id>", methods=["POST"])
@login_required
def update_cart(food_id):
    action = request.form.get("action")
    cart = get_cart()
    key = str(food_id)
    if key in cart:
        if action == "increase":
            cart[key] += 1
        elif action == "decrease":
            cart[key] -= 1
            if cart[key] <= 0:
                del cart[key]
        elif action == "remove":
            del cart[key]
    session.modified = True
    return redirect(url_for("view_cart"))


@app.route("/checkout", methods=["GET", "POST"])
@login_required
def checkout():
    cart = get_cart()
    if not cart:
        return redirect(url_for("view_cart"))

    conn = get_db()
    items = []
    subtotal = 0
    for food_id, qty in cart.items():
        f = conn.execute(FOOD_SELECT + " WHERE foods.id=?", (food_id,)).fetchone()
        if f:
            line_total = f["price"] * qty
            subtotal += line_total
            items.append({"id": f["id"], "name": f["name"], "price": f["price"], "qty": qty, "line_total": line_total})

    delivery_fee = 0 if subtotal >= 300 else 29
    user = current_user()

    if request.method == "POST":
        address = request.form.get("address", "").strip()
        phone = request.form.get("phone", "").strip()
        coupon = request.form.get("coupon", "").strip().upper()
        payment_method = request.form.get("payment_method", "COD")

        discount = 0
        if coupon == "HUB20":
            discount = round(subtotal * 0.2)
        elif subtotal >= 250:
            discount = 20

        total = max(subtotal + delivery_fee - discount, 0)
        eta = random.randint(18, 35)
        rider = random.choice(DELIVERY_NAMES)

        conn.execute(
            """INSERT INTO orders (user_id, items_json, total, address, phone, payment_method,
               delivery_person, eta_minutes, created_at, status)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (user["id"], json.dumps(items), total, address, phone, payment_method,
             rider, eta, datetime.now().isoformat(), STATUS_STEPS[0]),
        )
        conn.commit()
        order_id = conn.execute("SELECT last_insert_rowid() id").fetchone()["id"]
        conn.close()

        session["cart"] = {}
        session.modified = True
        return redirect(url_for("order_tracking", order_id=order_id))

    conn.close()
    return render_template(
        "checkout.html",
        items=items,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        user=user,
        cart_count=sum(cart.values()),
    )


@app.route("/order/<int:order_id>")
@login_required
def order_tracking(order_id):
    user = current_user()
    conn = get_db()
    order = conn.execute(
        "SELECT * FROM orders WHERE id=? AND user_id=?", (order_id, user["id"])
    ).fetchone()
    conn.close()
    if not order:
        return redirect(url_for("order_history"))

    items = json.loads(order["items_json"])
    return render_template(
        "order_tracking.html",
        order=order,
        items=items,
        steps=STATUS_STEPS,
        cart_count=sum(get_cart().values()),
    )


@app.route("/api/order/<int:order_id>/advance", methods=["POST"])
@login_required
def advance_order(order_id):
    user = current_user()
    conn = get_db()
    order = conn.execute(
        "SELECT * FROM orders WHERE id=? AND user_id=?", (order_id, user["id"])
    ).fetchone()
    if not order:
        conn.close()
        return jsonify({"error": "not found"}), 404

    current_index = STATUS_STEPS.index(order["status"]) if order["status"] in STATUS_STEPS else 0
    next_index = min(current_index + 1, len(STATUS_STEPS) - 1)
    new_status = STATUS_STEPS[next_index]
    conn.execute("UPDATE orders SET status=? WHERE id=?", (new_status, order_id))
    conn.commit()
    conn.close()
    return jsonify({"status": new_status, "index": next_index, "done": next_index == len(STATUS_STEPS) - 1})


@app.route("/orders")
@login_required
def order_history():
    user = current_user()
    conn = get_db()
    orders = conn.execute(
        "SELECT * FROM orders WHERE user_id=? ORDER BY id DESC", (user["id"],)
    ).fetchall()
    conn.close()

    history = []
    for o in orders:
        history.append({
            "id": o["id"],
            "dishes": json.loads(o["items_json"]),
            "total": o["total"],
            "status": o["status"],
            "created_at": o["created_at"][:16].replace("T", " "),
        })

    return render_template("order_history.html", orders=history, cart_count=sum(get_cart().values()))


@app.route("/reorder/<int:order_id>", methods=["POST"])
@login_required
def reorder(order_id):
    user = current_user()
    conn = get_db()
    order = conn.execute(
        "SELECT * FROM orders WHERE id=? AND user_id=?", (order_id, user["id"])
    ).fetchone()
    if order:
        items = json.loads(order["items_json"])
        cart = get_cart()
        for item in items:
            food_id = item.get("id")
            if food_id is None:
                # Older orders placed before dishes stored their id — fall back
                # to matching by name so old order history still reorders.
                f = conn.execute("SELECT id FROM foods WHERE name=?", (item["name"],)).fetchone()
                food_id = f["id"] if f else None
            if food_id is not None:
                key = str(food_id)
                cart[key] = cart.get(key, 0) + item["qty"]
        session.modified = True
    conn.close()
    return redirect(url_for("view_cart"))


@app.route("/favorites")
@login_required
def favorites():
    user = current_user()
    conn = get_db()
    foods = conn.execute(
        FOOD_SELECT + " JOIN favorites ON favorites.food_id = foods.id WHERE favorites.user_id=?",
        (user["id"],),
    ).fetchall()
    conn.close()
    return render_template("favorites.html", cards=foods_to_cards(foods), cart_count=sum(get_cart().values()))


@app.route("/favorites/toggle/<int:food_id>", methods=["POST"])
@login_required
def toggle_favorite(food_id):
    user = current_user()
    conn = get_db()
    existing = conn.execute(
        "SELECT id FROM favorites WHERE user_id=? AND food_id=?", (user["id"], food_id)
    ).fetchone()
    if existing:
        conn.execute("DELETE FROM favorites WHERE id=?", (existing["id"],))
    else:
        conn.execute("INSERT INTO favorites (user_id, food_id) VALUES (?,?)", (user["id"], food_id))
    conn.commit()
    conn.close()
    return redirect(request.referrer or url_for("favorites"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()
    if request.method == "POST":
        address = request.form.get("address", "").strip()
        conn = get_db()
        conn.execute("UPDATE users SET address=? WHERE id=?", (address, user["id"]))
        conn.commit()
        conn.close()
        flash("Profile updated!", "success")
        return redirect(url_for("profile"))

    conn = get_db()
    order_count = conn.execute("SELECT COUNT(*) c FROM orders WHERE user_id=?", (user["id"],)).fetchone()["c"]
    fav_count = conn.execute("SELECT COUNT(*) c FROM favorites WHERE user_id=?", (user["id"],)).fetchone()["c"]
    conn.close()

    return render_template(
        "profile.html", user=user, order_count=order_count, fav_count=fav_count,
        cart_count=sum(get_cart().values()),
    )


if __name__ == "__main__":
    init_db()
    app.run(debug=True)