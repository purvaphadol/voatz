from flask import Blueprint, jsonify
from datetime import datetime, timezone

health_bp = Blueprint('health', __name__)

@health_bp.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring and load balancers"""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'service': 'flask-access-control-backend'
    }), 200

@health_bp.route('/api/health/detailed', methods=['GET'])
def detailed_health_check():
    """Detailed health check including database connectivity"""
    from app import db
    
    health_status = {
        'status': 'ok',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'service': 'flask-access-control-backend',
        'checks': {}
    }
    
    # Database connectivity check
    try:
        db.session.execute('SELECT 1')
        health_status['checks']['database'] = 'ok'
    except Exception as e:
        health_status['checks']['database'] = 'error'
        health_status['status'] = 'error'
    
    status_code = 200 if health_status['status'] == 'ok' else 503
    return jsonify(health_status), status_code
