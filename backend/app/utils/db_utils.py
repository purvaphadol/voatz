from flask import jsonify
from app import db
from flask import current_app

def safe_commit(success_tuple, error_message, logger=None):
    """
    Safely commits a database transaction.
    If successful, returns the success_tuple (e.g., (jsonify({...}), 200)).
    If an exception occurs, rolls back, logs the error, and returns a 500 error tuple.
    """
    try:
        db.session.commit()
        return success_tuple
    except Exception as e:
        db.session.rollback()
        log = logger if logger else current_app.logger
        log.error(f"{error_message}: {str(e)}")
        return jsonify({'error': error_message}), 500
