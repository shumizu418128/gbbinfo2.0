import os

from app.main import app
from app.modules.translate import translate

if __name__ == "__main__":
    translate()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
