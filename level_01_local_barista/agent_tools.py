"""
AgentCore Café — Level 01: Local Barista Tools
Menu and ordering tools with local data (no AWS infra needed).
"""

from strands import tool

# ☕ Local café data — no DynamoDB yet, just Python dicts
MENU = {
    "Espresso": {"price": 2.50, "ingredients": ["coffee"], "strength": "strong", "category": "hot"},
    "Americano": {"price": 3.00, "ingredients": ["coffee", "water"], "strength": "strong", "category": "hot"},
    "Latte": {"price": 4.00, "ingredients": ["coffee", "milk"], "strength": "mild", "category": "hot"},
    "Cappuccino": {"price": 4.00, "ingredients": ["coffee", "milk"], "strength": "medium", "category": "hot"},
    "Mocha": {"price": 4.50, "ingredients": ["coffee", "milk", "chocolate"], "strength": "strong", "category": "hot"},
    "Matcha Latte": {"price": 5.00, "ingredients": ["matcha", "milk"], "strength": "mild", "category": "hot"},
    "Cold Brew": {"price": 3.50, "ingredients": ["coffee", "ice"], "strength": "strong", "category": "cold"},
    "Iced Latte": {"price": 4.50, "ingredients": ["coffee", "milk", "ice"], "strength": "mild", "category": "cold"},
    "Frappuccino": {"price": 5.50, "ingredients": ["coffee", "milk", "ice", "vanilla_syrup"], "strength": "mild", "category": "cold"},
}

MILK_OPTIONS = ["whole", "oat", "almond", "soy"]

EXTRAS = {
    "Extra shot": 0.75,
    "Vanilla syrup": 0.50,
    "Caramel syrup": 0.50,
    "Whipped cream": 0.75,
    "Chocolate chip cookie": 2.00,
    "Blueberry muffin": 2.50,
}

# Simple in-memory order tracking
orders = []


@tool
def get_menu(category: str = "all"):
    """Get the café menu. Can filter by category.
    :param category: Filter by 'hot', 'cold', or 'all' (default: all)
    """
    if category == "all":
        items = MENU
    else:
        items = {k: v for k, v in MENU.items() if v["category"] == category}

    if not items:
        return f"No drinks found for category '{category}'. Try 'hot', 'cold', or 'all'."

    result = "☕ AgentCore Café Menu:\n"
    for name, info in items.items():
        result += f"  - {name}: ${info['price']:.2f} ({info['strength']}, {info['category']})\n"
    result += f"\nMilk options: {', '.join(MILK_OPTIONS)}"
    result += f"\nExtras: {', '.join(f'{k} (+${v:.2f})' for k, v in EXTRAS.items())}"
    return result


@tool
def place_order(drink_name: str, size: str = "medium", milk_type: str = "whole", extras: str = ""):
    """Place an order for a drink.
    :param drink_name: Name of the drink (e.g. 'Mocha', 'Latte', 'Cold Brew')
    :param size: Size: small, medium, or large
    :param milk_type: Milk type: whole, oat, almond, or soy
    :param extras: Comma-separated extras (e.g. 'Extra shot, Whipped cream')
    """
    if drink_name not in MENU:
        suggestions = [n for n in MENU if drink_name.lower() in n.lower()]
        if suggestions:
            return f"We don't have '{drink_name}'. Did you mean: {', '.join(suggestions)}?"
        return f"Sorry, '{drink_name}' is not on our menu. Use get_menu to see what's available!"

    if milk_type not in MILK_OPTIONS:
        return f"We don't have '{milk_type}' milk. Options: {', '.join(MILK_OPTIONS)}"

    # Calculate price
    base_price = MENU[drink_name]["price"]
    size_modifier = {"small": -0.50, "medium": 0, "large": 1.00}
    price = base_price + size_modifier.get(size, 0)

    # Process extras
    extra_list = []
    if extras:
        for extra in [e.strip() for e in extras.split(",")]:
            if extra in EXTRAS:
                price += EXTRAS[extra]
                extra_list.append(extra)

    # Record order
    order = {
        "order_id": len(orders) + 1,
        "drink": drink_name,
        "size": size,
        "milk": milk_type,
        "extras": extra_list,
        "total": price,
    }
    orders.append(order)

    receipt = f"✅ Order #{order['order_id']} confirmed!\n"
    receipt += f"  {size.capitalize()} {drink_name} with {milk_type} milk\n"
    if extra_list:
        receipt += f"  Extras: {', '.join(extra_list)}\n"
    receipt += f"  Total: ${price:.2f}\n"
    receipt += "  Brewing now... ☕"
    return receipt
