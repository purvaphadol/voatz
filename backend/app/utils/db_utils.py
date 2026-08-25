from flask import jsonify, current_app
from sqlalchemy.exc import IntegrityError
from app import db

def safe_commit(success_tuple, error_message, logger=None):
    """
    Safely commits a database transaction.
    If successful, returns the success_tuple (e.g., (jsonify({...}), 200)).
    If an exception occurs, rolls back, logs the error, and returns a 500 or 409 error tuple.
    """
    try:
        db.session.commit()
        return success_tuple
    except IntegrityError as ie:
        db.session.rollback()
        log = logger if logger else current_app.logger
        log.error(f"{error_message} (IntegrityError): {str(ie)}")
        err_str = str(ie).lower()
        if 'unique_vote_per_ballot' in err_str:
            return jsonify({'error': 'You have already voted on this ballot'}), 409
        return jsonify({'error': error_message}), 400
    except Exception as e:
        db.session.rollback()
        log = logger if logger else current_app.logger
        log.error(f"{error_message}: {str(e)}")
        return jsonify({'error': error_message}), 500
