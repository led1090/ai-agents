from swarm import Agent


def get_daily_data(context_variables: dict) -> str:
    """Retrieve all meals logged today for the user, including macros."""
    phone = context_variables.get("phone_number")
    user = context_variables["get_or_create_user"](phone)
    meals = context_variables["get_user_meals_today"](user["id"])
    goal = user["daily_goal"]

    if not meals:
        return f"No meals logged today. Daily goal: {goal} cal."

    daily = context_variables["get_user_today_macros"](user["id"])
    meal_details = "\n".join(
        f"- Meal at {m['logged_at']}: {m['total_calories']} cal "
        f"(P:{m.get('protein_g', 0)}g C:{m.get('carbs_g', 0)}g S:{m.get('sugar_g', 0)}g) "
        f"({m['food_items']})"
        for m in meals
    )
    return (
        f"Daily goal: {goal} cal\n"
        f"Total consumed: {daily['total_calories']} cal\n"
        f"Total protein: {daily['total_protein']}g | "
        f"Total carbs: {daily['total_carbs']}g | "
        f"Total sugar: {daily['total_sugar']}g\n"
        f"Meals ({len(meals)}):\n{meal_details}"
    )


summary_agent = Agent(
    name="Summary Agent",
    model="gpt-4o-mini",
    instructions="""You generate end-of-day calorie summary reports.

When asked to generate a summary, first call get_daily_data to retrieve the day's meal data.
Then create a concise Telegram-friendly summary:
1. Total calories consumed vs daily goal
2. Whether the user was over or under their goal
3. Brief breakdown of meals
4. Macronutrient totals (protein, carbs, sugar)
5. An encouraging or cautionary note based on performance
6. A motivational closing line

Keep it under 500 characters. Use emojis sparingly for readability.
You may use basic markdown (bold, italic) as Telegram supports it.""",
    functions=[get_daily_data],
)
