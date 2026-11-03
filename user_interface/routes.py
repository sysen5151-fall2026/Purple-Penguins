"""Flask routes for the F.2 web application foundation and recipe API.

The recipe-generation endpoint uses deterministic local recipe and pricing stubs.
"""

from flask import Blueprint, jsonify, render_template, request

from recipe_service import (
    RecipeRequestValidationError,
    format_and_validate_api_request,
    submit_recipe_and_pricing_requests,
)

web = Blueprint("web", __name__, template_folder="templates")


@web.get("/")
def home():
    """Render the F.2 homepage foundation without running console prompts."""
    return render_template("index.html")


@web.post("/api/v1/recipes")
def generate_recipes():
    """Receive a validated F.2.4 recipe request and return stub-backed results."""
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

    response = submit_recipe_and_pricing_requests(recipe_request)
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
