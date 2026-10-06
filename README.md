# Tax Computational Tool for Individual Taxpayers

A web-based tool for estimating and comparing Philippine individual income tax computations for individual taxpayers. Create an account, enter income, deductions, and business/professional details relevant to your filing status, compare the available tax treatments, and save or export your results.

> **Disclaimer:** This application provides estimates for informational purposes only. It is not tax, legal, or accounting advice. Tax rules and eligibility can change; verify the applicable BIR guidance and consult a qualified tax professional before filing or making financial decisions.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tax Computation Methods](#tax-computation-methods)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [User Guide](#user-guide)
- [Deployment](#deployment)
- [Project Structure](#project-structure)
- [Development Notes](#development-notes)

## Overview

The application is built with Flask and provides a guided calculator for individual taxpayers, including purely business or professional taxpayers and mixed-income earners. It calculates three tax scenarios and identifies the scenario with the lowest estimated total tax based on the information entered.

The application uses SQLite by default for local development. PostgreSQL can be configured for deployment through the `DATABASE_URL` environment variable.

## Features

- Account registration, login, and logout
- Guided tax-computation workflow for pure and mixed-income taxpayers
- Comparison of graduated-tax, Optional Standard Deduction (OSD), itemized-deduction, and optional 8% scenarios
- Business income inputs for cash and accrual sales, costs, and other income
- Itemized deduction and Net Operating Loss Carry Over (NOLCO) inputs
- Saved computations, dashboard, and computation history
- PDF and CSV exports for saved computations
- Responsive web interface

## Tax Computation Methods

For each computation, the tool compares these scenarios:

1. **Graduated income tax with OSD and percentage tax**
2. **Graduated income tax with itemized deductions and percentage tax**
3. **Optional 8% income tax rate**

The calculator also supports mixed-income entries, including taxable compensation. Some rates and tax-table details are configurable in the calculator. Confirm the applicable rates, thresholds, taxpayer eligibility, and filing treatment against current BIR rules before relying on an estimate.

## Getting Started

### Requirements

- Python 3.10 or later
- `pip`

### 1. Clone the repository

```bash
git clone https://github.com/AlaizaNicoleCaranto/tax-computational-tool.git
cd tax-computational-tool
```

### 2. Create and activate a virtual environment

**Windows PowerShell**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows Command Prompt**

```bat
python -m venv .venv
.venv\Scripts\activate.bat
```

**macOS or Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Run the application

```bash
python run.py
```

Open [http://localhost:5001](http://localhost:5001). The development server uses port `5001` by default. Set the `PORT` environment variable to use another port.

## Configuration

The application loads environment variables from the environment or a local `.env` file. The `.env` file is ignored by Git; do not commit secrets.

| Variable | Purpose | Default |
| --- | --- | --- |
| `SECRET_KEY` | Signs session cookies and security tokens. Set a long, random value outside local development. | `dev-secret-change-me` |
| `DATABASE_URL` | SQLAlchemy database connection URL. | SQLite database |
| `FLASK_ENV` | Selects the application configuration: `development` or `production`. | `development` |
| `PORT` | Port used by `python run.py`. | `5001` |

For example, a local `.env` file can contain:

```dotenv
FLASK_ENV=development
SECRET_KEY=replace-with-a-long-random-secret
# Optional: leave unset to use the default SQLite database.
# DATABASE_URL=postgresql://username:password@host:5432/database
```

Generate a random secret key with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

In production, set `FLASK_ENV=production`, configure a strong `SECRET_KEY`, and provide a PostgreSQL `DATABASE_URL`. Do not use the development secret or rely on temporary local storage for production data.

## User Guide

1. **Create an account** using the registration page, then sign in.
2. **Start a computation** from the calculator. Choose whether you are a purely business/professional taxpayer or a mixed-income earner.
3. **Enter income and deduction details.** Add applicable compensation, business income, costs, deductions, and NOLCO information. Use zero or leave optional amounts blank when they do not apply.
4. **Review the comparison.** Check the results for each scenario and the lowest-tax estimate. The recommendation is based on the values entered and does not confirm that a method is legally available to you.
5. **Save and revisit your work.** Saved computations appear in the dashboard and history. You can open a saved result or use it as the starting point for a new computation.
6. **Export a saved computation** as a PDF or CSV from its saved-computation view.

## Deployment

This repository includes a [`vercel.json`](./vercel.json) configuration for Vercel's Python runtime. Before deploying, configure these environment variables in the deployment environment:

- `FLASK_ENV=production`
- `SECRET_KEY` set to a secure, randomly generated value
- `DATABASE_URL` set to a reachable PostgreSQL database

Review your hosting provider's current Python runtime and database instructions before deployment. The default SQLite database is intended for local development, not persistent production storage.

## Project Structure

```text
.
├── app/
│   ├── api.py              # Calculation, save, and history API routes
│   ├── auth.py             # Registration, login, and logout
│   ├── config.py           # Environment-specific configuration
│   ├── exports.py          # PDF and CSV exports
│   ├── main.py             # Calculator, dashboard, and history pages
│   ├── models.py           # User and computation database models
│   ├── static/             # CSS and JavaScript
│   ├── tax/                # Tax calculations and input helpers
│   └── templates/          # Jinja templates and calculator partials
├── requirements.txt        # Python dependencies
├── run.py                  # Local server entry point and WSGI app
└── vercel.json             # Vercel deployment configuration
```

## Development Notes

- The Flask application is created by `app.create_app()`.
- Database tables are created when the application starts if they do not already exist.
- Tax calculations are implemented under `app/tax/`; update and verify the relevant tax logic when applicable rules change.
- Keep credentials and local environment files out of version control.
