import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "foodiehub.db")

# Real food photographs (not AI-generated), served from a public, permanently-hosted
# image set via jsDelivr's GitHub CDN — free, no API key, no rate limit.
IMG_BASE = "https://cdn.jsdelivr.net/gh/surhud004/Foodish@master/public/assets/images"

# How many distinct real photos exist per category in that image set, so we can
# cycle through them without ever reusing the exact same photo too often.
CATEGORY_IMAGE_COUNT = {
    "biryani": 81, "burger": 87, "butter-chicken": 22, "dessert": 36,
    "dosa": 83, "idly": 77, "pasta": 34, "pizza": 95, "rice": 35, "samosa": 22,
}

# category -> (mood tags, price range, prep-time range)
CATEGORY_META = {
    "burger":         ("spicy,filling,quick", (99, 219), (12, 18)),
    "pizza":          ("filling,quick", (179, 329), (18, 26)),
    "pasta":          ("filling,quick", (159, 249), (15, 22)),
    "biryani":        ("spicy,filling", (159, 269), (20, 30)),
    "butter-chicken": ("filling,spicy", (169, 249), (18, 26)),
    "dosa":           ("quick,healthy", (69, 139), (10, 16)),
    "idly":           ("healthy,quick", (59, 109), (8, 13)),
    "rice":           ("healthy,quick", (79, 149), (12, 18)),
    "samosa":         ("spicy,quick", (39, 89), (6, 11)),
    "dessert":        ("sweet,quick", (59, 139), (8, 13)),
}

# category -> list of (name, veg(1/0), description, ingredients)
DISH_TEMPLATES = {
    "burger": [
        ("Classic Zinger Burger", 0, "A crunchy fried chicken fillet with spicy mayo in a soft bun.", "Chicken fillet, spicy mayo, lettuce, bun"),
        ("Double Cheese Burger", 0, "Two juicy chicken patties loaded with melted cheddar.", "Chicken patty, cheddar cheese, onion, bun"),
        ("Smoky BBQ Chicken Burger", 0, "Grilled chicken patty glazed with smoky BBQ sauce.", "Chicken patty, BBQ sauce, caramelized onion, bun"),
        ("Crunchy Veg Burger", 1, "A crispy vegetable patty with tangy tomato relish.", "Veg patty, tomato relish, lettuce, bun"),
        ("Paneer Tikka Burger", 1, "Spiced paneer patty with mint mayo and fresh veggies.", "Paneer, mint mayo, lettuce, bun"),
        ("Mushroom Melt Burger", 1, "Sauteed mushrooms with melted cheese in a toasted bun.", "Mushroom, cheese, garlic butter, bun"),
        ("Peri Peri Chicken Burger", 0, "Fiery peri-peri marinated chicken with a cooling slaw.", "Chicken fillet, peri-peri sauce, slaw, bun"),
        ("Egg Mayo Burger", 0, "Boiled egg slices with creamy mayo and fresh lettuce.", "Boiled egg, mayo, lettuce, bun"),
    ],
    "pizza": [
        ("Margherita Pizza", 1, "Classic cheese and tomato pizza on a thin crust.", "Mozzarella, tomato sauce, basil, pizza base"),
        ("Farmhouse Pizza", 1, "Loaded with capsicum, onion, tomato and mushroom.", "Capsicum, onion, tomato, mushroom, cheese"),
        ("Peppy Paneer Pizza", 1, "Spiced paneer cubes with crunchy capsicum.", "Paneer, capsicum, red paprika, cheese"),
        ("Chicken Tikka Pizza", 0, "Smoky chicken tikka chunks with onions and peppers.", "Chicken tikka, onion, capsicum, cheese"),
        ("Cheese Burst Pizza", 1, "Extra cheesy pizza with a molten cheese core.", "Mozzarella, cheese core, tomato sauce, base"),
        ("BBQ Chicken Pizza", 0, "Tender BBQ chicken with a smoky tangy sauce.", "Chicken, BBQ sauce, onion, cheese"),
        ("Mexican Green Wave Pizza", 1, "Jalapenos, capsicum and corn with a spicy kick.", "Jalapeno, capsicum, corn, cheese"),
        ("Pepperoni Pizza", 0, "Classic pepperoni slices over gooey mozzarella.", "Pepperoni, mozzarella, tomato sauce, base"),
    ],
    "pasta": [
        ("Creamy Alfredo Pasta", 1, "Penne tossed in a rich, creamy Alfredo sauce.", "Penne, cream, garlic, parmesan"),
        ("Arrabiata Penne", 1, "Penne in a spicy tomato and chili sauce.", "Penne, tomato, chili flakes, garlic"),
        ("Mushroom Pasta", 1, "Sauteed mushrooms in a light white sauce.", "Pasta, mushroom, cream, herbs"),
        ("Chicken Alfredo Pasta", 0, "Grilled chicken strips in creamy Alfredo sauce.", "Pasta, chicken, cream, parmesan"),
        ("Pesto Pasta", 1, "Pasta tossed in fresh basil pesto and pine nuts.", "Pasta, basil pesto, pine nuts, parmesan"),
        ("Spicy Red Sauce Pasta", 1, "Pasta in a tangy, spiced tomato sauce.", "Pasta, tomato sauce, chili, oregano"),
    ],
    "biryani": [
        ("Hyderabadi Chicken Biryani", 0, "Slow-cooked dum biryani with tender chicken and saffron rice.", "Basmati rice, chicken, saffron, fried onion"),
        ("Veg Dum Biryani", 1, "Fragrant basmati rice dum-cooked with mixed vegetables.", "Basmati rice, mixed vegetables, mint, spices"),
        ("Mutton Biryani", 0, "Rich and spicy biryani with slow-cooked mutton pieces.", "Basmati rice, mutton, whole spices, fried onion"),
        ("Egg Biryani", 0, "Boiled eggs layered in fragrant spiced rice.", "Basmati rice, boiled egg, spices, fried onion"),
        ("Paneer Biryani", 1, "Soft paneer cubes layered in aromatic dum rice.", "Basmati rice, paneer, mint, spices"),
        ("Chicken 65 Biryani", 0, "Spicy Chicken 65 pieces mixed with flavorful biryani rice.", "Basmati rice, chicken 65, curry leaves, spices"),
    ],
    "butter-chicken": [
        ("Butter Chicken Bowl", 0, "Creamy butter chicken in a rich tomato gravy, served with rice.", "Chicken, tomato gravy, butter, cream"),
        ("Paneer Butter Masala Bowl", 1, "Soft paneer cubes in a velvety tomato-butter gravy.", "Paneer, tomato gravy, butter, cream"),
        ("Dal Makhani Bowl", 1, "Slow-cooked black lentils in a creamy buttery gravy.", "Black lentils, butter, cream, spices"),
        ("Butter Chicken with Naan", 0, "Classic butter chicken served with soft buttered naan.", "Chicken, tomato gravy, butter, naan"),
    ],
    "dosa": [
        ("Crispy Masala Dosa", 1, "A golden, crispy rice crepe filled with spiced potato masala.", "Rice batter, urad dal, potato masala, chutney"),
        ("Plain Dosa", 1, "A thin, crispy classic dosa served with sambar and chutney.", "Rice batter, urad dal, sambar, chutney"),
        ("Onion Rava Dosa", 1, "A crispy semolina dosa topped with onions.", "Rava, onion, green chili, chutney"),
        ("Paneer Dosa", 1, "Dosa stuffed with a spiced paneer filling.", "Rice batter, paneer, spices, chutney"),
        ("Mysore Masala Dosa", 1, "Dosa spread with spicy red chutney and potato masala.", "Rice batter, red chutney, potato masala"),
        ("Cheese Dosa", 1, "Crispy dosa loaded with melted cheese.", "Rice batter, cheese, butter"),
    ],
    "idly": [
        ("Steamed Idly Sambar", 1, "Soft steamed rice cakes served with hot sambar.", "Rice, urad dal, sambar, chutney"),
        ("Mini Idly Platter", 1, "Bite-sized idlis tossed in ghee and podi.", "Rice, urad dal, ghee, podi"),
        ("Rava Idly", 1, "Soft semolina idlis served with coconut chutney.", "Semolina, curd, chutney"),
        ("Ghee Podi Idly", 1, "Idlis coated in aromatic ghee and spiced lentil podi.", "Rice, urad dal, ghee, podi"),
    ],
    "rice": [
        ("Ghee Jeera Rice Bowl", 1, "Fragrant basmati rice tempered with ghee and roasted cumin.", "Basmati rice, ghee, cumin, bay leaf"),
        ("Curd Rice Bowl", 1, "Cooling curd rice tempered with mustard and curry leaves.", "Rice, curd, mustard seeds, curry leaves"),
        ("Lemon Rice Bowl", 1, "Tangy rice tempered with lemon, peanuts and curry leaves.", "Rice, lemon, peanuts, curry leaves"),
        ("Tamarind Rice Bowl", 1, "Tangy tamarind-flavored rice with roasted spices.", "Rice, tamarind, roasted spices, peanuts"),
        ("Chicken Fried Rice", 0, "Wok-tossed rice with chicken and vegetables.", "Rice, chicken, soy sauce, vegetables"),
    ],
    "samosa": [
        ("Crispy Veg Samosa (2 pcs)", 1, "Golden, flaky pastry stuffed with a spiced potato-pea filling.", "Maida, potato, green peas, spices"),
        ("Paneer Samosa (2 pcs)", 1, "Crispy samosa filled with spiced paneer.", "Maida, paneer, spices"),
        ("Chicken Keema Samosa (2 pcs)", 0, "Crispy samosa filled with spiced minced chicken.", "Maida, chicken keema, spices"),
        ("Mini Samosa Platter", 1, "Bite-sized samosas perfect for sharing.", "Maida, potato, peas, spices"),
    ],
    "dessert": [
        ("Choco Dessert Delight", 1, "A rich, indulgent chocolate dessert to satisfy any sweet craving.", "Dark chocolate, cream, sugar, butter"),
        ("Gulab Jamun (2 pcs)", 1, "Soft milk dumplings soaked in rose-cardamom syrup.", "Milk solids, sugar syrup, cardamom"),
        ("Rasmalai Bowl", 1, "Soft paneer discs soaked in sweetened, saffron milk.", "Paneer, milk, saffron, sugar"),
        ("Brownie with Ice Cream", 1, "Warm fudgy brownie served with vanilla ice cream.", "Chocolate, flour, butter, vanilla ice cream"),
        ("Fruit Custard", 1, "Chilled custard loaded with fresh seasonal fruits.", "Milk, custard powder, mixed fruits"),
        ("Kesari Halwa", 1, "Warm semolina halwa flavored with saffron and ghee.", "Semolina, ghee, sugar, saffron"),
    ],
}

# name, area, cuisines(csv), categories drawn from
RESTAURANTS_SEED = [
    ("Aromas of Madurai", "Madurai Town", "South Indian", ["dosa", "idly", "rice"]),
    ("Nawab's Biryani House", "Anna Nagar", "Mughlai, Biryani", ["biryani", "butter-chicken"]),
    ("Grill & Chill", "T Nagar", "American, Fast Food", ["burger", "pizza"]),
    ("Trattoria Bella", "Nungambakkam", "Italian", ["pasta", "pizza"]),
    ("Sweet Treats Bakery", "Adyar", "Desserts, Bakery", ["dessert", "samosa"]),
    ("Punjabi Tadka", "Velachery", "North Indian", ["butter-chicken", "biryani", "rice"]),
    ("Chennai Express", "Mylapore", "South Indian, Street Food", ["dosa", "idly", "samosa"]),
    ("Big Bite Burgers", "Guindy", "Fast Food", ["burger", "dessert"]),
    ("Pasta La Vista", "Besant Nagar", "Italian", ["pasta", "dessert"]),
    ("Biryani Junction", "Porur", "Biryani", ["biryani", "rice"]),
    ("Snack Street Corner", "Kodambakkam", "Street Food", ["samosa", "dosa", "dessert"]),
    ("Cheesy Slice Pizzeria", "OMR", "Pizza, Italian", ["pizza", "pasta"]),
    ("Royal Mughlai", "Egmore", "North Indian, Mughlai", ["biryani", "butter-chicken"]),
    ("South Spice Diner", "Tambaram", "South Indian", ["dosa", "idly", "rice"]),
    ("Burger Barn", "Perungudi", "Fast Food", ["burger", "pizza"]),
    ("Dessert Daze", "Thoraipakkam", "Desserts", ["dessert"]),
    ("Curry Leaf Kitchen", "Vadapalani", "Multi-cuisine", ["biryani", "dosa", "rice", "samosa"]),
    ("Flavours of India", "Nanganallur", "Multi-cuisine, North Indian", ["butter-chicken", "biryani", "dessert", "pizza"]),
]


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    address TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS restaurants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    area TEXT NOT NULL,
    cuisines TEXT NOT NULL,
    rating REAL NOT NULL,
    delivery_time_min INTEGER NOT NULL,
    cost_for_two INTEGER NOT NULL,
    banner_image TEXT NOT NULL,
    is_pure_veg INTEGER DEFAULT 0,
    promoted INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS foods (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    restaurant_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    price INTEGER NOT NULL,
    rating REAL NOT NULL,
    prep_time INTEGER NOT NULL,
    veg INTEGER NOT NULL,
    tags TEXT NOT NULL,
    description TEXT NOT NULL,
    ingredients TEXT NOT NULL,
    image_url TEXT NOT NULL,
    popular INTEGER DEFAULT 0,
    FOREIGN KEY(restaurant_id) REFERENCES restaurants(id)
);

CREATE TABLE IF NOT EXISTS favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    food_id INTEGER NOT NULL,
    UNIQUE(user_id, food_id),
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(food_id) REFERENCES foods(id)
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    items_json TEXT NOT NULL,
    total INTEGER NOT NULL,
    address TEXT NOT NULL,
    phone TEXT NOT NULL,
    payment_method TEXT NOT NULL,
    delivery_person TEXT NOT NULL,
    eta_minutes INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    status TEXT DEFAULT 'Order Confirmed',
    FOREIGN KEY(user_id) REFERENCES users(id)
);
"""


def _img_url(category, n):
    count = CATEGORY_IMAGE_COUNT[category]
    idx = ((n - 1) % count) + 1
    return f"{IMG_BASE}/{category}/{category}{idx}.jpg"


def _build_dataset():
    """Deterministically build many restaurants, each with several real-photo dishes,
    cycling through distinct photo numbers per category so dishes don't repeat the
    same exact image too often."""
    img_counters = {cat: 1 for cat in CATEGORY_IMAGE_COUNT}
    restaurants = []
    foods_by_restaurant = []

    for r_idx, (name, area, cuisines, categories) in enumerate(RESTAURANTS_SEED):
        restaurant_dishes = []
        for c_idx, category in enumerate(categories):
            templates = DISH_TEMPLATES[category]
            tags, price_range, prep_range = CATEGORY_META[category]
            # pick 2-3 dishes from this category, offset per restaurant so the
            # same restaurant doesn't always show the first N dishes
            offset = (r_idx + c_idx) % len(templates)
            pick_count = 3 if len(templates) >= 5 else 2
            for k in range(pick_count):
                dish_name, veg, desc, ingredients = templates[(offset + k) % len(templates)]
                lo, hi = price_range
                price = lo + ((r_idx * 37 + c_idx * 13 + k * 23) % (hi - lo + 1))
                plo, phi = prep_range
                prep_time = plo + ((r_idx + k) % (phi - plo + 1))
                rating = round(4.0 + ((r_idx * 3 + c_idx * 5 + k) % 9) * 0.1, 1)
                popular = 1 if (r_idx + c_idx + k) % 3 == 0 else 0
                image_url = _img_url(category, img_counters[category])
                img_counters[category] += 1
                restaurant_dishes.append({
                    "name": dish_name, "price": price, "rating": rating,
                    "prep_time": prep_time, "veg": veg, "tags": tags,
                    "description": desc, "ingredients": ingredients,
                    "image_url": image_url, "popular": popular,
                })

        is_pure_veg = 1 if all(d["veg"] == 1 for d in restaurant_dishes) else 0
        banner_category = categories[0]
        banner_image = _img_url(banner_category, img_counters[banner_category])
        img_counters[banner_category] += 1
        avg_price = sum(d["price"] for d in restaurant_dishes) / max(len(restaurant_dishes), 1)
        rest_rating = round(4.0 + ((r_idx * 7) % 9) * 0.1, 1)
        delivery_time_min = 20 + ((r_idx * 5) % 26)
        cost_for_two = int(round(avg_price * 2, -1))
        promoted = 1 if r_idx % 4 == 0 else 0

        restaurants.append({
            "name": name, "area": area, "cuisines": cuisines, "rating": rest_rating,
            "delivery_time_min": delivery_time_min, "cost_for_two": cost_for_two,
            "banner_image": banner_image, "is_pure_veg": is_pure_veg, "promoted": promoted,
        })
        foods_by_restaurant.append(restaurant_dishes)

    return restaurants, foods_by_restaurant


def init_db():
    conn = get_db()
    conn.executescript(SCHEMA)

    count = conn.execute("SELECT COUNT(*) c FROM restaurants").fetchone()["c"]
    if count == 0:
        restaurants, foods_by_restaurant = _build_dataset()
        for r, dishes in zip(restaurants, foods_by_restaurant):
            cur = conn.execute(
                """INSERT INTO restaurants
                   (name, area, cuisines, rating, delivery_time_min, cost_for_two,
                    banner_image, is_pure_veg, promoted)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (r["name"], r["area"], r["cuisines"], r["rating"], r["delivery_time_min"],
                 r["cost_for_two"], r["banner_image"], r["is_pure_veg"], r["promoted"]),
            )
            restaurant_id = cur.lastrowid
            conn.executemany(
                """INSERT INTO foods
                   (restaurant_id, name, price, rating, prep_time, veg, tags,
                    description, ingredients, image_url, popular)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                [
                    (restaurant_id, d["name"], d["price"], d["rating"], d["prep_time"],
                     d["veg"], d["tags"], d["description"], d["ingredients"],
                     d["image_url"], d["popular"])
                    for d in dishes
                ],
            )
        conn.commit()
    conn.close()
