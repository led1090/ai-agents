import logging

from swarm import Agent
from swarm.types import Result

logger = logging.getLogger(__name__)


def save_meal(
    context_variables: dict,
    food_items_json: str,
    total_calories: int,
    total_protein: float,
    total_carbs: float,
    total_sugar: float,
    health_rating: int = 5,
    notes: str = "",
) -> Result:
    """Save the analyzed meal to the database.

    Args:
        food_items_json: JSON string of food items, e.g.
            '[{"name":"grilled chicken","quantity":"150g","calories":250,
               "protein_g":40,"carbs_g":0,"sugar_g":0}]'
        total_calories: Total calories for the entire meal
        total_protein: Total protein in grams for the entire meal
        total_carbs: Total carbohydrates in grams for the entire meal
        total_sugar: Total sugar in grams for the entire meal
        health_rating: Health rating 1-10 (1=very unhealthy, 10=very healthy)
        notes: Optional notes about the meal
    """
    try:
        phone = context_variables.get("phone_number")
        media_id = context_variables.get("media_id")
        user = context_variables["get_or_create_user"](phone)

        context_variables["log_meal"](
            user_id=user["id"],
            food_items=food_items_json,
            total_calories=total_calories,
            image_id=media_id,
            notes=notes,
            protein_g=total_protein,
            carbs_g=total_carbs,
            sugar_g=total_sugar,
            health_rating=health_rating,
        )

        # Get running daily totals to include in the response
        daily = context_variables["get_user_today_macros"](user["id"])
        limit_data = context_variables["compute_daily_calorie_limit"](user["id"])
        goal = limit_data["daily_limit"]
        remaining = goal - daily["total_calories"]

        value = (
            f"Meal logged: {total_calories} cal | "
            f"Protein: {total_protein}g | Carbs: {total_carbs}g | Sugar: {total_sugar}g | "
            f"Health: {health_rating}/10\n"
            f"Daily totals: {daily['total_calories']}/{goal} cal "
            f"(Remaining: {remaining}) | "
            f"Protein: {daily['total_protein']}g | "
            f"Carbs: {daily['total_carbs']}g | Sugar: {daily['total_sugar']}g"
        )

        return Result(value=value, agent=context_variables["chat_agent"])

    except Exception as e:
        logger.error(f"Failed to save meal: {e}", exc_info=True)
        return Result(
            value=(
                f"ERROR: Failed to save meal to database: {e}. "
                f"Tell the user the meal could not be saved and ask them to try again."
            ),
            agent=context_variables["chat_agent"],
        )


def transfer_back_to_chat(context_variables: dict):
    """Transfer back to the Chat Agent after food analysis is complete."""
    return context_variables["chat_agent"]


food_analysis_agent = Agent(
    name="Food Analysis Agent",
    model="gpt-4o",
    tool_choice="required",
    instructions="""You are a food analysis specialist. You will receive an image of food.

Your process:
1. Examine the food photo carefully.
2. Identify ALL food items visible in the image.
3. Estimate the quantity/portion size of each item (use common serving sizes).
4. For each item, estimate:
   - Calories (using standard USDA-style estimates)
   - Protein in grams
   - Carbohydrates in grams
   - Sugar in grams
   If portion size is ambiguous, estimate based on typical restaurant/home serving.
5. Rate the overall meal healthiness on a 1-10 scale:
   - 1-3: Very unhealthy (deep fried, high sugar, processed)
   - 4-5: Below average (some redeeming qualities but mostly unhealthy)
   - 6-7: Average to good (balanced, reasonable portions)
   - 8-9: Very healthy (lean protein, vegetables, whole grains)
   - 10: Exceptionally healthy (nutrient-dense, perfect balance)
6. Call save_meal with:
   - food_items_json: a JSON array of objects, each with "name", "quantity", "calories",
     "protein_g", "carbs_g", "sugar_g"
   - total_calories: the sum of all item calories
   - total_protein: the sum of all item protein_g
   - total_carbs: the sum of all item carbs_g
   - total_sugar: the sum of all item sugar_g
   - health_rating: the 1-10 rating
   - notes: a brief description of the meal
7. Then respond to the user in this exact format:
   - A brief 1-sentence commentary about the meal (what it is, notable qualities)
   - Each item: "• Item (qty) — XXX cal  P:Xg C:Xg S:Xg"
   - Total line: "Total: XXX cal | P:Xg C:Xg S:Xg"
   - Health rating WITH a 1-sentence justification: "Health: X/10 — [reason]"
   - Daily running total from save_meal result: "Daily: XXX/XXX cal (XXX remaining)  P:Xg | C:Xg | S:Xg"
8. After save_meal completes, control automatically returns to the Chat Agent.

9. Check `context_variables['user_profile']['dietary_preferences']`. If the meal
   conflicts with stated preferences (e.g., meat for a vegetarian, nuts for someone
   with nut allergy), mention this prominently in your response as a warning.

If the image is unclear or not food, say so and call transfer_back_to_chat.
Keep your response concise for chat formatting.""",
    functions=[save_meal, transfer_back_to_chat],
)
