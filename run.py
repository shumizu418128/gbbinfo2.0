import os

from app.app import app

if __name__ == "__main__":
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
