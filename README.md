# Tax Computational Tool

A Flask web application for estimating and comparing Philippine individual income tax computations. Users can create an account, enter income and deduction details, compare several tax treatments, and save or export results for later review.

> Disclaimer: This application provides estimates for informational purposes only. It is not tax, legal, or accounting advice. Tax rules and eligibility can change; verify the current BIR guidance and consult a qualified tax professional before filing or making financial decisions.

## Overview

The tool is designed for individual taxpayers in the Philippines, including:

- Pure business/professional taxpayers
- Mixed-income taxpayers with compensation income
- Optional standard deduction (OSD), itemized deduction, and 8% tax-rate scenarios

The app compares multiple tax treatment options and identifies the lowest estimated tax among the available calculations. It stores user accounts and saved computations in a local SQLite database by default, with PostgreSQL support available through the `DATABASE_URL` environment variable.

## Features

- User registration, login, and logout
- Guided computation workflow for pure and mixed-income taxpayers
- Side-by-side comparison of tax schemes
- Business income inputs for cash and accrual sales, costs, and other income
- Ordinary deductions, special deductions, and NOLCO support
- Dashboard with recent computations and saved history
- PDF and CSV export for saved calculations
- Tax bracket editor for administrators
- Responsive web interface

## Tax computation methods

Each computation compares the following scenarios:

1. Graduated income tax with optional standard deduction and percentage tax
2. Graduated income tax with itemized deductions and percentage tax
3. Optional 8% income tax rate

The logic is implemented in the `app/tax` package and can be adjusted when BIR tax rules or threshold tables change. Always confirm against the latest official guidance before relying on any estimate.

## Tech stack

- Python 3.10+
- Flask 3.x
- Flask-SQLAlchemy
- Flask-Login
- Flask-Bcrypt
- SQLite for local development
- PostgreSQL for production deployment
- ReportLab for PDF export
- pytest/unittest-based test coverage

## Getting started

### Requirements

- Python 3.10 or later
- `pip`

### 1. Clone the repository

```bash
git clone https://github.com/AlaizaNicoleCaranto/tax-computational-tool.git
cd tax-computational-tool
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Run the app locally

```bash
python run.py
```

Then open: http://localhost:5001

The app listens on port `5001` by default. Override it with the `PORT` environment variable if needed.

## Configuration

The app reads environment variables from the process environment and a local `.env` file when available. Keep secrets out of source control.

| Variable | Purpose | Default |
| --- | --- | --- |
| `SECRET_KEY` | Signs session cookies and security tokens | `dev-secret-change-me` |
| `DATABASE_URL` | SQLAlchemy database connection string | SQLite database in `instance/tax_tool.db` |
| `FLASK_ENV` | App mode: `development`, `production`, or `testing` | `development` |
| `PORT` | Port used by `python run.py` | `5001` |
| `MAIL_SERVER` | SMTP host for password-reset emails | empty |
| `MAIL_PORT` | SMTP port | `587` |
| `MAIL_USERNAME` | SMTP login username | empty |
| `MAIL_PASSWORD` | SMTP password or app password | empty |
| `MAIL_FROM` | Sender address for outgoing mail | empty |
| `MAIL_USE_TLS` | Enables STARTTLS for SMTP | `true` |
| `ADMIN_EMAIL` | Optional admin email allowed to edit the tax table | empty |
| `APP_TIMEZONE` | Local timezone used for timestamps | `Asia/Singapore` |

Example `.env` file:

```dotenv
FLASK_ENV=development
SECRET_KEY=replace-with-a-long-random-secret
MAIL_SERVER=smtp.example.com
MAIL_PORT=587
MAIL_USERNAME=your-email@example.com
MAIL_PASSWORD=your-app-password
MAIL_FROM=your-email@example.com
MAIL_USE_TLS=true
# Optional override for PostgreSQL in production:
# DATABASE_URL=postgresql://user:password@host:5432/database
```

Generate a strong secret key:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

In production, always use a strong secret key and a persistent database such as PostgreSQL. Do not rely on the default local SQLite database for real production data.

## Project structure

```text
.
├── app/
│   ├── __init__.py         # Flask app factory and DB setup
│   ├── api.py              # Tax calculation and save/history endpoints
│   ├── auth.py             # User authentication routes
│   ├── config.py           # Environment configuration
│   ├── exports.py          # CSV and PDF export routes
│   ├── main.py             # Dashboard, calculator, and views
│   ├── models.py           # User, computation, and tax-bracket models
│   ├── static/             # CSS, JavaScript, and frontend assets
│   ├── tax/                # Tax calculation logic and bracket definitions
│   └── templates/          # Jinja templates
├── tests/
│   ├── test_api_and_routes.py
│   └── test_tax_computations.py
├── instance/
│   └── tax_tool.db         # Local SQLite database (created at runtime)
├── .gitignore
├── README.md
├── requirements.txt
├── run.py
├── vercel.json             # Deployment config for Vercel
└── image/
```

## Running tests

This project includes automated tests for tax computations and route behavior.

```bash
pytest
```

If you want to run a specific test file:

```bash
pytest tests/test_api_and_routes.py
pytest tests/test_tax_computations.py
```

## Deployment

This repository includes a `vercel.json` configuration for Vercel deployment. Before deploying, make sure the environment includes:

- `FLASK_ENV=production`
- `SECRET_KEY` with a secure random value
- `DATABASE_URL` pointing to a reachable PostgreSQL database

For local development, SQLite is the default and is intentionally simple. For production, use a persistent database and secure configuration values.

## Development notes

- The application is created via `app.create_app()`.
- Database tables are created automatically when the app starts if they do not already exist.
- Tax bracket data is seeded from the official TRAIN Law defaults and can be edited from the app interface when the admin email matches `ADMIN_EMAIL`.
- Keep credentials and local environment files out of version control.

## License

This project is currently distributed without a formal license file. Before publishing or redistributing it, verify whether a project-specific license should be added.
