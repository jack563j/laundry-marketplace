import os

# Load a local .env file if present (for `python run.py` during development).
# In real deployments, set these as actual environment variables in the
# hosting dashboard instead of shipping a .env file.
if os.path.exists(".env"):
    from dotenv import load_dotenv
    load_dotenv()

from app import create_app

app = create_app()

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_ENV") != "production"
    app.run(debug=debug_mode, host="0.0.0.0", port=int(os.environ.get("PORT", 5050)))
