"""WSGI entry point for the ACEest Fitness & Gym application.

Local development:  ``python app.py``
Production:         ``gunicorn app:app``
"""

import os

from aceest import create_app

app = create_app()

if __name__ == "__main__":
    app.run(
        host=os.environ.get("ACEEST_HOST", "127.0.0.1"),
        port=int(os.environ.get("ACEEST_PORT", "5000")),
        debug=False,
    )
