"""Flask routes for the F.2 web application and recipe API."""

from flask import Blueprint, current_app, jsonify, render_template, request

from llm_api_interface import get_recipe_generation_mode
from llm_api_interface.errors import RecipeGenerationServiceError
from recipe_service import (
    RecipeRequestValidationError,
    format_and_validate_api_request,
    specify_already_owned_recipe_ingredients,
    submit_recipe_and_pricing_requests,
)

web = Blueprint("web", __name__, template_folder="templates")


@web.get("/")
def home():
    """Render the dashboard with the configured recipe-generation disclosure."""
    return render_template(
        "index.html",
        recipe_generation_mode=get_recipe_generation_mode(),
    )


@web.post("/api/v1/recipes")
def generate_recipes():
    """F.2.4.4: return recipe results from the configured generation mode."""
    payload = request.get_json(silent=True)
    try:
        recipe_request = format_and_validate_api_request(payload)
    except RecipeRequestValidationError as error:
        return (
            jsonify(
                {
                    "error": {
                        "code": "invalid_request",
                        "message": str(error),
                        "field_errors": error.field_errors,
                    }
                }
            ),
            400,
        )

    request_with_ownership = specify_already_owned_recipe_ingredients(
        recipe_request
    )
    try:
        response = submit_recipe_and_pricing_requests(request_with_ownership)
    except RecipeGenerationServiceError as error:
        current_app.logger.warning(
            "Recipe-generation provider failure: %s", error.log_message
        )
        return (
            jsonify(
                {
                    "error": {
                        "code": "backend_failure",
                        "message": error.public_message,
                    }
                }
            ),
            error.status_code,
        )
    return jsonify(response)


@web.errorhandler(500)
def handle_internal_server_error(_error):
    """Return the contract's safe backend-failure response for server errors."""
    del _error
    return (
        jsonify(
            {
                "error": {
                    "code": "backend_failure",
                    "message": (
                        "Recipe generation is temporarily unavailable. "
                        "Please try again."
                    ),
                }
            }
        ),
        500,
    )
