import json
from swarm import Agent


def get_calorie_status(context_variables: dict) -> str:
    """Get the user's calorie and macro intake so far today."""
    phone = context_variables.get("phone_number")
    user = context_variables["get_or_create_user"](phone)
    daily = context_variables["get_user_today_macros"](user["id"])

    limit_data = context_variables["compute_daily_calorie_limit"](user["id"])
    goal = limit_data["daily_limit"]
    remaining = goal - daily["total_calories"]

    result = (
        f"Today so far: {daily['total_calories']} calories consumed out of {goal} goal.\n"
        f"Remaining: {remaining} calories.\n"
        f"Protein: {daily['total_protein']}g | "
        f"Carbs: {daily['total_carbs']}g | "
        f"Sugar: {daily['total_sugar']}g"
    )

    if daily["avg_health_rating"] > 0:
        result += f"\nAvg health rating today: {daily['avg_health_rating']}/10"

    if limit_data["has_weight_goal"]:
        result += (
            f"\n(Computed from weight goal: {limit_data['current_weight']}kg -> "
            f"{limit_data['target_weight']}kg, {limit_data['days_remaining']} days left)"
        )

    return result


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
        health_rating=meal.get("health_rating", 0),
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
    limit_data = context_variables["compute_daily_calorie_limit"](user["id"])
    goal = limit_data["daily_limit"]
    remaining = goal - daily["total_calories"]

    meal_lines = []
    for i, m in enumerate(meals, 1):
        meal_lines.append(
            f"{i}. {m['food_items']} - {m['total_calories']} cal "
            f"(P:{m.get('protein_g', 0)}g C:{m.get('carbs_g', 0)}g S:{m.get('sugar_g', 0)}g) "
            f"[Health: {m.get('health_rating', 0)}/10]"
        )

    return (
        f"Today's meals ({len(meals)}):\n"
        + "\n".join(meal_lines)
        + f"\n\nDaily total: {daily['total_calories']}/{goal} cal (Remaining: {remaining})\n"
        f"Protein: {daily['total_protein']}g | Carbs: {daily['total_carbs']}g | Sugar: {daily['total_sugar']}g"
    )


def save_text_meal(
    context_variables: dict,
    food_items_json: str,
    total_calories: int,
    total_protein: float,
    total_carbs: float,
    total_sugar: float,
    health_rating: int,
    notes: str = "",
) -> str:
    """Log a meal described via text (no photo). Estimate macros based on the description.

    Args:
        food_items_json: JSON array of items, e.g.
            '[{"name":"2 eggs","quantity":"2 large","calories":140,
               "protein_g":12,"carbs_g":1,"sugar_g":0}]'
        total_calories: Total estimated calories
        total_protein: Total protein in grams
        total_carbs: Total carbohydrates in grams
        total_sugar: Total sugar in grams
        health_rating: Health rating 1-10 (1=very unhealthy, 10=very healthy)
        notes: Optional notes
    """
    phone = context_variables.get("phone_number")
    user = context_variables["get_or_create_user"](phone)

    context_variables["log_meal"](
        user_id=user["id"],
        food_items=food_items_json,
        total_calories=total_calories,
        image_id=None,
        notes=notes,
        protein_g=total_protein,
        carbs_g=total_carbs,
        sugar_g=total_sugar,
        health_rating=health_rating,
    )

    daily = context_variables["get_user_today_macros"](user["id"])
    limit_data = context_variables["compute_daily_calorie_limit"](user["id"])
    goal = limit_data["daily_limit"]
    remaining = goal - daily["total_calories"]

    return (
        f"Meal logged: {total_calories} cal | "
        f"P:{total_protein}g C:{total_carbs}g S:{total_sugar}g | "
        f"Health: {health_rating}/10\n"
        f"Daily totals: {daily['total_calories']}/{goal} cal "
        f"(Remaining: {remaining})"
    )


def record_weight(context_variables: dict, weight_kg: float) -> str:
    """Record the user's current weight.

    Args:
        weight_kg: Weight in kilograms
    """
    phone = context_variables.get("phone_number")
    user = context_variables["get_or_create_user"](phone)
    context_variables["log_weight"](user["id"], weight_kg)

    limit_data = context_variables["compute_daily_calorie_limit"](user["id"])
    if limit_data["has_weight_goal"]:
        diff = weight_kg - limit_data["target_weight"]
        direction = "to lose" if diff > 0 else "to gain"
        return (
            f"Weight recorded: {weight_kg} kg.\n"
            f"Target: {limit_data['target_weight']} kg "
            f"({abs(diff):.1f} kg {direction})\n"
            f"Days remaining: {limit_data['days_remaining']}\n"
            f"Computed daily limit: {limit_data['daily_limit']} cal"
        )
    return f"Weight recorded: {weight_kg} kg."


def set_weight_goal_fn(
    context_variables: dict,
    target_weight: float,
    target_date: str,
    current_weight: float = None,
    tdee: int = None,
) -> str:
    """Set a weight loss or gain goal.

    Args:
        target_weight: Goal weight in kg
        target_date: Target date in YYYY-MM-DD format
        current_weight: Current weight in kg (optional, will record it if provided)
        tdee: Total Daily Energy Expenditure in calories (optional, defaults to 2000)
    """
    phone = context_variables.get("phone_number")
    user = context_variables["get_or_create_user"](phone)

    if current_weight:
        context_variables["log_weight"](user["id"], current_weight)

    context_variables["set_weight_goal"](
        user_id=user["id"],
        target_weight=target_weight,
        target_date=target_date,
        tdee=tdee,
    )

    limit_data = context_variables["compute_daily_calorie_limit"](user["id"])
    return (
        f"Weight goal set!\n"
        f"Current: {limit_data['current_weight'] or current_weight} kg -> "
        f"Target: {target_weight} kg by {target_date}\n"
        f"TDEE: {limit_data['tdee']} cal\n"
        f"Computed daily calorie limit: {limit_data['daily_limit']} cal\n"
        f"Daily {'deficit' if limit_data['daily_deficit'] > 0 else 'surplus'}: "
        f"{abs(limit_data['daily_deficit'])} cal\n"
        f"Days remaining: {limit_data['days_remaining']}"
    )


def update_profile(
    context_variables: dict,
    dietary_preferences: str = None,
    timezone: str = None,
) -> str:
    """Update the user's profile preferences.

    Args:
        dietary_preferences: Free-text dietary preferences/restrictions
            (e.g. "vegetarian, allergic to nuts, lactose intolerant")
        timezone: IANA timezone string (e.g. "UTC", "Europe/London", "Asia/Riyadh")
    """
    phone = context_variables.get("phone_number")
    user = context_variables["get_or_create_user"](phone)

    fields = {}
    if dietary_preferences is not None:
        fields["dietary_preferences"] = dietary_preferences
    if timezone is not None:
        fields["timezone"] = timezone

    updated = context_variables["update_user_profile"](user["id"], **fields)

    parts = []
    if dietary_preferences is not None:
        parts.append(f"Dietary preferences: {dietary_preferences}")
    if timezone is not None:
        parts.append(f"Timezone: {timezone}")
    return "Profile updated! " + " | ".join(parts)


def get_monthly_report(context_variables: dict, month: int = None, year: int = None) -> str:
    """Get a monthly nutrition report.

    Args:
        month: Month number (1-12). Defaults to current month.
        year: Year. Defaults to current year.
    """
    phone = context_variables.get("phone_number")
    user = context_variables["get_or_create_user"](phone)
    monthly = context_variables["get_monthly_consumption"](user["id"], month, year)
    limit_data = context_variables["compute_daily_calorie_limit"](user["id"])

    daily_limit = limit_data["daily_limit"]
    monthly_budget = daily_limit * monthly["days_in_month"]
    deviation = monthly["total_calories"] - (daily_limit * monthly["days_elapsed"])

    return (
        f"Monthly Report ({monthly['month']}/{monthly['year']}):\n"
        f"Days tracked: {monthly['days_elapsed']}/{monthly['days_in_month']}\n"
        f"Total calories: {monthly['total_calories']}\n"
        f"Monthly budget: {monthly_budget} cal ({daily_limit}/day x {monthly['days_in_month']} days)\n"
        f"Deviation so far: {'+' if deviation > 0 else ''}{deviation} cal\n"
        f"Avg health rating: {monthly['avg_health_rating']}/10\n"
        f"Protein: {monthly['total_protein']}g | "
        f"Carbs: {monthly['total_carbs']}g | Sugar: {monthly['total_sugar']}g\n"
        f"Meals logged: {monthly['meal_count']}"
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
10. If the user describes food they ate in text (e.g. "I had 2 eggs and toast",
    "just ate a burger with fries"), estimate calories, protein, carbs, sugar, and a
    health rating (1-10), then call save_text_meal with the estimated values.
    Format food_items_json as a proper JSON array of objects with name, quantity,
    calories, protein_g, carbs_g, sugar_g for each item.
    After logging, respond in this format:
    - A brief 1-sentence commentary about the meal
    - Each item: "• Item (qty) — XXX cal  P:Xg C:Xg S:Xg"
    - Total line: "Total: XXX cal | P:Xg C:Xg S:Xg"
    - Health rating WITH a 1-sentence justification: "Health: X/10 — [reason]"
    - Daily running total from save_text_meal result
11. If the user wants to record their weight (e.g. "my weight is 82 kg",
    "I weigh 80.5"), call record_weight with the weight in kg.
12. If the user wants to set a weight goal (e.g. "I want to reach 75 kg by June"),
    call set_weight_goal_fn. Ask for target weight, target date, and optionally
    current weight and TDEE if not already known.
13. If the user asks for a monthly report or monthly summary, call get_monthly_report.
14. If the user asks about their weight goal or calorie limit, call get_calorie_status
    which includes weight goal information.
15. Use the user's first name from `context_variables['user_profile']` when greeting or in daily summaries.
16. If the user mentions dietary preferences or restrictions (e.g., 'I'm vegetarian',
    'I'm allergic to nuts', 'I don't eat pork'), call update_profile to save them.
17. Consider the user's dietary_preferences from `context_variables['user_profile']`
    when analyzing text meals — flag if a described meal conflicts with their stated preferences.

You do NOT analyze food photos yourself. Always hand off to Food Analysis for that.""",
    functions=[
        get_calorie_status,
        get_meals_today,
        transfer_to_food_analysis,
        set_daily_goal,
        update_last_meal,
        delete_last_meal,
        save_text_meal,
        record_weight,
        set_weight_goal_fn,
        get_monthly_report,
        update_profile,
    ],
)
