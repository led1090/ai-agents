import json
from swarm import Agent


def get_calorie_status(context_variables: dict) -> str:
    """Get the user's calorie and macro intake so far today."""
    phone = context_variables.get("phone_number")
    user = context_variables["get_or_create_user"](phone)
    daily = context_variables["get_user_today_macros"](user["id"])
    goal = user["daily_goal"]
    remaining = goal - daily["total_calories"]
    return (
        f"Today so far: {daily['total_calories']} calories consumed out of {goal} goal.\n"
        f"Remaining: {remaining} calories.\n"
        f"Protein: {daily['total_protein']}g | "
        f"Carbs: {daily['total_carbs']}g | "
        f"Sugar: {daily['total_sugar']}g"
    )


def transfer_to_food_analysis(context_variables: dict):
    """Transfer to the Food Analysis agent to analyze a food photo."""
    return context_variables["food_analysis_agent"]


def set_daily_goal(context_variables: dict, calories: int) -> str:
    """Set the user's daily calorie goal.

    Args:
        calories: The new daily calorie target
    """
    phone = context_variables.get("phone_number")
    context_variables["update_user_goal"](phone, calories)
    return f"Daily calorie goal updated to {calories} calories."


def update_last_meal(context_variables: dict, fraction: float) -> str:
    """Scale the most recent meal's calories and macros by a fraction.

    Args:
        fraction: The multiplier to apply (e.g. 0.5 for half, 0.75 for three-quarters)
    """
    phone = context_variables.get("phone_number")
    user = context_variables["get_or_create_user"](phone)
    meal = context_variables["get_last_meal"](user["id"])

    if not meal:
        return "No meals logged today to update."

    old_calories = meal["total_calories"]
    new_calories = round(old_calories * fraction)
    new_protein = round(meal.get("protein_g", 0) * fraction, 1)
    new_carbs = round(meal.get("carbs_g", 0) * fraction, 1)
    new_sugar = round(meal.get("sugar_g", 0) * fraction, 1)

    food_items = json.loads(meal["food_items"])
    for item in food_items:
        item["calories"] = round(item["calories"] * fraction)
        for key in ["protein_g", "carbs_g", "sugar_g"]:
            if key in item:
                item[key] = round(item[key] * fraction, 1)
        if "quantity" in item:
            item["quantity"] = f"~{fraction}x of {item['quantity']}"

    context_variables["update_meal"](
        meal["id"], json.dumps(food_items), new_calories,
        protein_g=new_protein, carbs_g=new_carbs, sugar_g=new_sugar,
    )

    daily = context_variables["get_user_today_macros"](user["id"])
    return (
        f"Updated last meal from {old_calories} to {new_calories} calories (x{fraction}).\n"
        f"Daily totals now: {daily['total_calories']} cal | "
        f"P:{daily['total_protein']}g C:{daily['total_carbs']}g S:{daily['total_sugar']}g"
    )


def delete_last_meal(context_variables: dict) -> str:
    """Delete the most recently logged meal for today."""
    phone = context_variables.get("phone_number")
    user = context_variables["get_or_create_user"](phone)
    meal = context_variables["get_last_meal"](user["id"])

    if not meal:
        return "No meals logged today to delete."

    calories = meal["total_calories"]
    context_variables["delete_meal"](meal["id"])
    return f"Deleted last meal ({calories} calories)."


def get_meals_today(context_variables: dict) -> str:
    """Get a detailed list of all meals logged today, with individual items and macros."""
    phone = context_variables.get("phone_number")
    user = context_variables["get_or_create_user"](phone)
    meals = context_variables["get_user_meals_today"](user["id"])

    if not meals:
        return "No meals logged today yet."

    daily = context_variables["get_user_today_macros"](user["id"])
    goal = user["daily_goal"]
    remaining = goal - daily["total_calories"]

    meal_lines = []
    for i, m in enumerate(meals, 1):
        meal_lines.append(
            f"{i}. {m['food_items']} - {m['total_calories']} cal "
            f"(P:{m.get('protein_g', 0)}g C:{m.get('carbs_g', 0)}g S:{m.get('sugar_g', 0)}g)"
        )

    return (
        f"Today's meals ({len(meals)}):\n"
        + "\n".join(meal_lines)
        + f"\n\nDaily total: {daily['total_calories']}/{goal} cal (Remaining: {remaining})\n"
        f"Protein: {daily['total_protein']}g | Carbs: {daily['total_carbs']}g | Sugar: {daily['total_sugar']}g"
    )


chat_agent = Agent(
    name="Chat Agent",
    model="gpt-4o",
    instructions="""You are HealthEnforcer, a friendly Telegram calorie tracking assistant.

Your responsibilities:
1. Greet users warmly and explain how the bot works when they first message.
2. If the user sends a food photo (you will see it as an image in the conversation),
   IMMEDIATELY call transfer_to_food_analysis to hand off to the specialist.
3. If the user asks about their calorie status today, call get_calorie_status.
4. If the user asks what they have eaten today or wants a list of meals, call get_meals_today.
5. If the user wants to set a daily calorie goal, call set_daily_goal.
6. If the user says they only ate a portion of their last meal (e.g. "I only had half",
   "I ate about 75%", "I only had a third"), call update_last_meal with the appropriate
   fraction (0.5 for half, 0.75 for three-quarters, 0.33 for a third, etc.).
7. If the user wants to remove/undo their last logged meal, call delete_last_meal.
8. For general health questions, provide brief helpful advice.
9. Keep responses concise -- this is a chat message, not an essay.

You do NOT analyze food photos yourself. Always hand off to Food Analysis for that.""",
    functions=[
        get_calorie_status,
        get_meals_today,
        transfer_to_food_analysis,
        set_daily_goal,
        update_last_meal,
        delete_last_meal,
    ],
)
