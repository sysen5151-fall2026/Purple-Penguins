(() => {
  const form = document.querySelector("#recipe-form");
  if (!form) {
    return;
  }

  const ingredientsInput = document.querySelector("#ingredients");
  const budgetInput = document.querySelector("#budget");
  const restrictionsInput = document.querySelector("#dietary-restrictions");
  const generateButton = document.querySelector("#generate-button");
  const buttonLabel = generateButton.querySelector(".button-label");
  const formStatus = document.querySelector("#form-status");
  const resultsSection = document.querySelector(".results");
  const resultsList = document.querySelector("#results-list");
  const currency = new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  });

  const fields = {
    ingredients: {
      input: ingredientsInput,
      error: document.querySelector("#ingredients-error"),
    },
    budget: {
      input: budgetInput,
      error: document.querySelector("#budget-error"),
    },
    dietary_restrictions: {
      input: restrictionsInput,
      error: document.querySelector("#dietary-error"),
    },
  };

  function splitValues(value) {
    return value
      .split(/[,\n]/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  function clearErrors() {
    Object.values(fields).forEach(({ input, error }) => {
      input.setAttribute("aria-invalid", "false");
      error.textContent = "";
    });
    formStatus.textContent = "";
    formStatus.dataset.state = "";
  }

  function setFieldError(name, message) {
    const field = fields[name];
    field.input.setAttribute("aria-invalid", "true");
    field.error.textContent = message;
  }

  function showError(message) {
    formStatus.textContent = message;
    formStatus.dataset.state = "error";
  }

  function applyApiValidationErrors(fieldErrors) {
    const unassignedMessages = [];
    Object.entries(fieldErrors).forEach(([name, message]) => {
      const fieldName = name.split(".")[0];
      if (Object.hasOwn(fields, fieldName)) {
        setFieldError(fieldName, message);
      } else {
        unassignedMessages.push(message);
      }
    });

    if (unassignedMessages.length > 0) {
      showError(unassignedMessages.join(" "));
    } else {
      showError("Please check the highlighted fields and try again.");
    }
  }

  function appendEmptyState() {
    const emptyState = document.createElement("div");
    emptyState.className = "empty-state";

    const icon = document.createElement("span");
    icon.className = "empty-icon";
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = "✦";

    const heading = document.createElement("h3");
    heading.textContent = "No recipes returned";

    const message = document.createElement("p");
    message.textContent =
      "Try again later. The demonstration service returned an empty recipe list.";

    emptyState.append(icon, heading, message);
    resultsList.append(emptyState);
  }

  function renderRecipes(recipes) {
    resultsList.replaceChildren();
    if (recipes.length === 0) {
      appendEmptyState();
      return;
    }

    recipes.forEach((recipe) => {
      const card = document.createElement("article");
      card.className = "recipe-card";

      const title = document.createElement("h3");
      title.textContent = recipe.name;

      const ingredientsHeading = document.createElement("h4");
      ingredientsHeading.textContent = "Ingredients";

      const ingredientList = document.createElement("ul");
      ingredientList.className = "ingredient-list";
      recipe.ingredients.forEach((ingredient) => {
        const row = document.createElement("li");
        row.className = `ingredient-row ${
          ingredient.owned ? "is-owned" : "needs-purchase"
        }`;

        const name = document.createElement("span");
        name.className = "ingredient-name";
        name.textContent = ingredient.name;

        const price = document.createElement("span");
        price.className = "ingredient-price";
        price.textContent = currency.format(ingredient.estimated_price);

        const ownership = document.createElement("span");
        ownership.className = `ingredient-ownership ${
          ingredient.owned ? "owned" : "to-purchase"
        }`;
        ownership.textContent = ingredient.owned ? "Owned" : "Buy";

        row.append(name, price, ownership);
        ingredientList.append(row);
      });

      const costSummary = document.createElement("div");
      costSummary.className = "recipe-cost-summary";

      const fullCost = document.createElement("p");
      fullCost.className = "recipe-total";
      const fullCostLabel = document.createElement("span");
      fullCostLabel.textContent = "Full recipe cost";
      const fullCostPrice = document.createElement("span");
      fullCostPrice.textContent = currency.format(recipe.estimated_total_cost);
      fullCost.append(fullCostLabel, fullCostPrice);

      const purchaseCost = document.createElement("p");
      purchaseCost.className = "recipe-total";
      const purchaseCostLabel = document.createElement("span");
      purchaseCostLabel.textContent = "Additional purchase cost";
      const purchaseCostPrice = document.createElement("span");
      purchaseCostPrice.textContent = currency.format(
        recipe.additional_purchase_cost
      );
      purchaseCost.append(purchaseCostLabel, purchaseCostPrice);

      const budgetStatus = document.createElement("p");
      budgetStatus.className = `budget-status ${
        recipe.within_budget ? "within-budget" : "over-budget"
      }`;
      budgetStatus.textContent = recipe.within_budget
        ? "Within your budget"
        : "Over your budget";

      costSummary.append(fullCost, purchaseCost, budgetStatus);
      card.append(title, ingredientsHeading, ingredientList, costSummary);
      resultsList.append(card);
    });
  }

  Object.entries(fields).forEach(([name, { input }]) => {
    input.addEventListener("input", () => {
      input.setAttribute("aria-invalid", "false");
      fields[name].error.textContent = "";
      formStatus.textContent = "";
      formStatus.dataset.state = "";
    });
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (generateButton.disabled) {
      return;
    }
    clearErrors();

    const ingredients = splitValues(ingredientsInput.value);
    const budget = Number(budgetInput.value);
    const dietaryRestrictions = splitValues(restrictionsInput.value);
    let hasValidationError = false;

    if (ingredients.length === 0) {
      setFieldError("ingredients", "Enter at least one ingredient.");
      hasValidationError = true;
    }
    if (!Number.isFinite(budget) || budget <= 0) {
      setFieldError("budget", "Enter a positive budget in US dollars.");
      hasValidationError = true;
    }

    if (hasValidationError) {
      showError("Correct the highlighted fields before generating recipes.");
      form.querySelector('[aria-invalid="true"]').focus();
      return;
    }

    generateButton.disabled = true;
    resultsSection.setAttribute("aria-busy", "true");
    buttonLabel.textContent = "Spinning...";
    formStatus.textContent = "Requesting demonstration recipes...";
    formStatus.dataset.state = "";

    try {
      const response = await fetch("/api/v1/recipes", {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          ingredients,
          budget,
          dietary_restrictions: dietaryRestrictions,
        }),
      });

      let payload;
      try {
        payload = await response.json();
      } catch {
        showError("The server returned an unreadable response. Please try again.");
        return;
      }

      if (!response.ok) {
        const apiError = payload && payload.error;
        if (
          response.status === 400 &&
          apiError &&
          apiError.field_errors &&
          typeof apiError.field_errors === "object"
        ) {
          applyApiValidationErrors(apiError.field_errors);
        } else {
          showError(
            (apiError && apiError.message) ||
              "Recipe generation is unavailable. Please try again."
          );
        }
        return;
      }

      if (!payload || !Array.isArray(payload.recipes)) {
        showError("The server response did not contain a recipe list.");
        return;
      }

      renderRecipes(payload.recipes);
      formStatus.textContent =
        payload.recipes.length === 0
          ? "No demonstration recipes were returned."
          : `Showing ${payload.recipes.length} demonstration recipe(s).`;
    } catch {
      showError(
        "Could not reach Recipe Roulette. Check your connection and try again."
      );
    } finally {
      generateButton.disabled = false;
      resultsSection.setAttribute("aria-busy", "false");
      buttonLabel.textContent = "Spin for Recipes";
    }
  });
})();
