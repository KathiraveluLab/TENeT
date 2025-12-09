from flask import Flask, jsonify, g
from flask_cors import CORS
from database.config import init_db, get_db
from routes.cat_routes import cat_bp

app = Flask(__name__)
CORS(app)

# Initialize database on startup
with app.app_context():
    init_db()
    print("Database initialized successfully")

# Setup database session teardown
@app.teardown_appcontext
def shutdown_session(exception=None):
    """Close database session at the end of each request"""
    db = g.pop('db', None)
    if db is not None:
        db.close()

# Register CAT routes
app.register_blueprint(cat_bp)

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "message": "TENeT Backend is running"})

if __name__ == '__main__':
    print("Starting TENeT Backend on http://localhost:5000")
    print("CAT API available at http://localhost:5000/api/cat")
    app.run(debug=True, port=5000)
