import calendar
from datetime import date

from swarm import Agent


def get_daily_data(context_variables: dict) -> str:
    """Retrieve comprehensive daily, weekly, and monthly data for the user."""
    phone = context_variables.get("phone_number")
    user = context_variables["get_or_create_user"](phone)
    meals = context_variables["get_user_meals_today"](user["id"])
    daily = context_variables["get_user_today_macros"](user["id"])
    limit_data = context_variables["compute_daily_calorie_limit"](user["id"])
    weekly = context_variables["get_weekly_consumption"](user["id"])
    monthly = context_variables["get_monthly_consumption"](user["id"])

    daily_limit = limit_data["daily_limit"]
    daily_deviation = daily["total_calories"] - daily_limit

    weekly_budget = daily_limit * 7
    weekly_deviation = weekly["total_calories"] - (daily_limit * weekly["days_elapsed"])

    today = date.today()
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    monthly_budget = daily_limit * days_in_month
    monthly_deviation = monthly["total_calories"] - (daily_limit * monthly["days_elapsed"])

    meal_details = "\n".join(
        f"- Meal at {m['logged_at']}: {m['total_calories']} cal "
        f"(P:{m.get('protein_g', 0)}g C:{m.get('carbs_g', 0)}g S:{m.get('sugar_g', 0)}g) "
        f"[Health: {m.get('health_rating', 0)}/10] "
        f"({m['food_items']})"
        for m in meals
    ) if meals else "No meals logged."

    sections = [
        f"=== DAILY ===",
        f"Daily calorie limit: {daily_limit} cal",
        f"Total consumed: {daily['total_calories']} cal",
        f"Deviation: {'+' if daily_deviation > 0 else ''}{daily_deviation} cal",
        f"Protein: {daily['total_protein']}g | Carbs: {daily['total_carbs']}g | Sugar: {daily['total_sugar']}g",
        f"Avg health rating: {daily['avg_health_rating']}/10",
        f"Meals ({len(meals)}):\n{meal_details}",
        f"",
        f"=== WEEKLY ===",
        f"Week so far ({weekly['days_elapsed']} days): {weekly['total_calories']} cal consumed",
        f"Weekly budget: {weekly_budget} cal ({daily_limit}/day x 7)",
        f"Weekly deviation so far: {'+' if weekly_deviation > 0 else ''}{weekly_deviation} cal",
        f"",
        f"=== MONTHLY ===",
        f"Month so far ({monthly['days_elapsed']} days): {monthly['total_calories']} cal consumed",
        f"Monthly budget: {monthly_budget} cal ({daily_limit}/day x {days_in_month})",
        f"Monthly deviation so far: {'+' if monthly_deviation > 0 else ''}{monthly_deviation} cal",
        f"Monthly avg health rating: {monthly['avg_health_rating']}/10",
    ]

    if limit_data["has_weight_goal"]:
        sections.extend([
            f"",
            f"=== WEIGHT GOAL ===",
            f"Current weight: {limit_data['current_weight']} kg",
            f"Target weight: {limit_data['target_weight']} kg",
            f"Target date: {limit_data['target_date']}",
            f"Days remaining: {limit_data['days_remaining']}",
            f"TDEE: {limit_data['tdee']} cal",
            f"Required daily deficit: {limit_data['daily_deficit']} cal",
        ])

    return "\n".join(sections)


summary_agent = Agent(
    name="Summary Agent",
    model="gpt-4o-mini",
    instructions="""You generate end-of-day calorie summary reports.

Address the user by their first name from `context_variables['user_profile']` if available.

When asked to generate a summary, first call get_daily_data to retrieve comprehensive data.
Then create a Telegram-friendly summary covering:

1. DAILY OVERVIEW:
   - Total calories consumed vs daily limit
   - How much over/under the daily limit (+/- deviation)
   - Macronutrient totals (protein, carbs, sugar)
   - Average health rating for today's meals

2. DIET ANALYSIS:
   - What was missing from the diet (e.g. "not enough protein", "low on vegetables")
   - What could have been avoided (e.g. "the sugary dessert added 400 empty calories")
   - What should be added tomorrow (e.g. "add a serving of vegetables and lean protein")

3. WEEKLY STATUS:
   - Calories consumed this week vs weekly budget
   - Weekly deviation (+/- against budget so far)

4. MONTHLY STATUS:
   - Calories consumed this month vs monthly budget
   - Monthly deviation (+/- against budget so far)
   - Monthly average health rating

5. WEIGHT GOAL (if set):
   - Current weight vs target weight
   - Days remaining
   - Whether on track based on calorie adherence

6. MOTIVATION:
   - An encouraging or cautionary closing note based on overall performance

Keep the summary under 1000 characters. Use emojis sparingly for readability.
You may use basic markdown (bold, italic) as Telegram supports it.
Structure with clear section headers.""",
    functions=[get_daily_data],
)
