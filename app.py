from flask_cors import CORS
from app import create_app
import nltk

app = create_app()

CORS(app)

nltk.download('punkt_tab')

if __name__ == '__main__':
    app.run(debug=True)