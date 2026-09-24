# ============================================================
# APPLICATION ENTRY POINT
# ============================================================
# This file starts the Flask development server. It is the
# only file that lives at the project root; everything else
# belongs to the app package.
#
# Running locally:
#     python run.py
#
# The server listens on http://127.0.0.1:5000 by default.
#
# In production (Vercel), this file is ignored. Instead, the
# platform uses the WSGI callable exported below.

import os

from app import create_app

# Determine which configuration to load. The FLASK_ENV
# environment variable controls this. If it is not set, the
# factory falls back to the default (development) config.
config_name = os.getenv("FLASK_ENV", "development")

# Create the application instance.
app = create_app(config_name)


if __name__ == "__main__":
    # Read the port from the environment. Defaults to 5000.
    port = int(os.getenv("PORT", 5001))

    # Run the development server. The debug flag is handled
    # by the configuration class, so it is not set explicitly
    # here. Auto reload is enabled in development mode.
    app.run(host="0.0.0.0", port=port)