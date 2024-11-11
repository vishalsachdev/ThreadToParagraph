import os
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import twitter_utils


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "a secret key"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
db.init_app(app)

with app.app_context():
    import models
    db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_thread', methods=['POST'])
def process_thread():
    try:
        url = request.json.get('url')
        if not url:
            return jsonify({'error': 'No URL provided'}), 400

        # Check cache first
        cached_thread = models.Thread.query.filter_by(url=url).first()
        if cached_thread:
            return jsonify({
                'text': cached_thread.processed_text,
                'cached': True
            })

        # Fetch and process thread
        thread_text = twitter_utils.fetch_thread(url)
        if not thread_text:
            return jsonify({'error': 'Failed to fetch thread'}), 400

        # Save to cache
        new_thread = models.Thread(url=url, processed_text=thread_text)
        db.session.add(new_thread)
        db.session.commit()

        return jsonify({
            'text': thread_text,
            'cached': False
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
