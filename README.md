# README for SYSEN5151 Semester Project

## Project Name - Recipe Roulette
### Team Members - Zachary Adornato, Jacob Brown, Ethan Gates, Stephen Gyurits

## Operational Concept
Meal planning is a time-consuming laborious process that everyone deals with. Dietary constraints and budget can complicate recipe selection and make the process even more difficult. The Recipe Roulette app is a system that generates relevant recipes while keeping budget, dietary restrictions, budget, and preferences in mind. 

Individuals that struggle with the previously mentioned constraints are the primary audience to experience meal planning issues. Existing meal planning leads to a non-nutritional diet, improper budgeting, and meals that take longer to shop for than they do to cook. There is a clear difficulty in balancing: cost, dietary restrictions, and preferences while maintaining a nutritional and healthy diet.

## Development Setup

The project targets Python 3.12. From the repository root, create and activate a virtual environment, then install the project dependencies:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

## Run the Flask Foundation

Start the web application:

```powershell
python -m app
```

Open [http://127.0.0.1:5000](http://127.0.0.1:5000) in a browser. The current page is a branded foundation stating that the web interface is under development; recipe generation is not available through the web application yet.

## Run the Console Walking Skeleton

The original interactive console workflow remains available explicitly:

```powershell
python -m app --cli
```

## Run Automated Tests

Run the test suite from the repository root:

```powershell
python -m pytest
```