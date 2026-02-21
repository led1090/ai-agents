from swarm import Agent


def save_meal(
    context_variables: dict,
    food_items_json: str,
    total_calories: int,
    total_protein: float,
    total_carbs: float,
    total_sugar: float,
    notes: str = "",
) -> str:
    """Save the analyzed meal to the database.

    Args:
        food_items_json: JSON string of food items, e.g.
            '[{"name":"grilled chicken","quantity":"150g","calories":250,
               "protein_g":40,"carbs_g":0,"sugar_g":0}]'
        total_calories: Total calories for the entire meal
        total_protein: Total protein in grams for the entire meal
        total_carbs: Total carbohydrates in grams for the entire meal
        total_sugar: Total sugar in grams for the entire meal
        notes: Optional notes about the meal
    """
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
    )

    # Get running daily totals to include in the response
    daily = context_variables["get_user_today_macros"](user["id"])
    goal = user["daily_goal"]
    remaining = goal - daily["total_calories"]

    return (
        f"Meal logged: {total_calories} cal | "
        f"Protein: {total_protein}g | Carbs: {total_carbs}g | Sugar: {total_sugar}g\n"
        f"Daily totals: {daily['total_calories']}/{goal} cal "
        f"(Remaining: {remaining}) | "
        f"Protein: {daily['total_protein']}g | "
        f"Carbs: {daily['total_carbs']}g | Sugar: {daily['total_sugar']}g"
    )


def transfer_back_to_chat(context_variables: dict):
    """Transfer back to the Chat Agent after food analysis is complete."""
    return context_variables["chat_agent"]


food_analysis_agent = Agent(
    name="Food Analysis Agent",
    model="gpt-4o",
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
5. Call save_meal with:
   - food_items_json: a JSON array of objects, each with "name", "quantity", "calories",
     "protein_g", "carbs_g", "sugar_g"
   - total_calories: the sum of all item calories
   - total_protein: the sum of all item protein_g
   - total_carbs: the sum of all item carbs_g
   - total_sugar: the sum of all item sugar_g
   - notes: a brief description of the meal
6. Then respond to the user with a formatted breakdown:
   - List each item with its estimated calories and macros (protein/carbs/sugar)
   - Show the meal total
   - Show the daily running total (from the save_meal result)
   - Add a brief healthiness comment
7. After responding, call transfer_back_to_chat so future messages go to the Chat Agent.

If the image is unclear or not food, say so and transfer back to chat.
Keep your response concise for chat formatting.""",
    functions=[save_meal, transfer_back_to_chat],
)
