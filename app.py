from flask import Flask, jsonify
import logging

# Configure logging
log: logging.Logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/')
def hello_world():
    """Basic hello world endpoint that returns empty JSON."""
    log.info("Hello world endpoint accessed")
    return jsonify({})

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
