import os

from flask import Flask, jsonify, g
from flask_cors import CORS
from database.config import init_db, get_db
from routes.cat_routes import cat_bp
from routes.performance_routes import performance_bp

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

# Register blueprints
app.register_blueprint(cat_bp)
app.register_blueprint(performance_bp)

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "message": "TENeT Backend is running"})

if __name__ == '__main__':
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', '5001'))
    debug = os.getenv('FLASK_DEBUG', '1') == '1'
    print(f"Starting TENeT Backend on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
