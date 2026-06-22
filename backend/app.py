import os

from flask import Flask, jsonify, g
from flask_cors import CORS
from database.config import init_db, get_db
from routes.cat_routes import cat_bp
from routes.performance_routes import performance_bp

app = Flask(__name__)
cors_origins = os.getenv("CORS_ALLOWED_ORIGINS", "*")
CORS(app, origins=cors_origins.split(",") if cors_origins != "*" else "*")

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
    return jsonify({"status": "ok", "service": "tenet-api"})

if __name__ == '__main__':
    os.makedirs(os.path.join('data', 'uploads'), exist_ok=True)
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    try:
        port = int(os.getenv('FLASK_PORT', '5001'))
    except ValueError:
        port = 5001
    debug = os.getenv('FLASK_DEBUG', '1') == '1'
    display_host = 'localhost' if host == '0.0.0.0' else host
    print(f"Starting TENeT Backend on http://{display_host}:{port}")
    app.run(host=host, port=port, debug=debug)
