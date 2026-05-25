from flask import request, jsonify
from app import db
from app.models.audit_log import AuditLog
from app.utils import get_current_user, get_current_company_id
from functools import wraps
import json
from datetime import datetime

def set_audit_fields(obj, is_create=False):
    """Auto-fill created_by and updated_by fields using JWT identity."""
    try:
        from app.utils import get_current_user
        user = get_current_user()
        if user:
            if is_create and hasattr(obj, 'created_by'):
                obj.created_by = user.id
            if hasattr(obj, 'updated_by'):
                obj.updated_by = user.id
    except Exception:
        pass

def log_activity(action, module=None, target_type=None, target_id=None, 
                description=None, success=True, error_message=None, metadata=None, auto_commit=False):
    """Log an activity to the audit trail"""
    try:
        user = get_current_user()
        company_id = get_current_company_id()
        
        if not company_id:
            return  # Skip logging if no company context
        
        audit_log = AuditLog()
        audit_log.user_id = user.id if user else None
        audit_log.company_id = company_id
        audit_log.action = action
        audit_log.module = module
        audit_log.target_type = target_type
        audit_log.target_id = target_id
        audit_log.description = description
        audit_log.success = success
        audit_log.error_message = error_message
        audit_log.extra_data = metadata
        
        # Request context
        if request:
            audit_log.ip_address = request.remote_addr
            audit_log.user_agent = request.headers.get('User-Agent', '')[:500]
            audit_log.method = request.method
            audit_log.endpoint = request.endpoint
        
        db.session.add(audit_log)
        try:
            db.session.flush()
            if auto_commit:
                db.session.commit()
        except Exception as e:
            print(f"Audit flush error: {e}")
            return
        
    except Exception as e:
        # Don't let audit logging break the main functionality
        print(f"Audit logging error: {e}")

def audit_action(action, module=None, target_type=None, get_target_id=None, description=None):
    """Decorator to automatically log API actions"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            start_time = datetime.now()
            target_id = None
            success = True
            error_message = None
            metadata = {}
            
            try:
                # Extract target_id if function provided
                if get_target_id:
                    if callable(get_target_id):
                        target_id = get_target_id(*args, **kwargs)
                    else:
                        target_id = get_target_id
                
                # Execute the function
                result = f(*args, **kwargs)
                
                return result
                
            except Exception as e:
                success = False
                error_message = str(e)
                metadata['error_details'] = str(e)
                raise
                
            finally:
                # Log the activity
                end_time = datetime.now()
                duration = (end_time - start_time).total_seconds()
                
                metadata.update({
                    'duration_seconds': duration,
                    'timestamp': start_time.isoformat(),
                    'args_count': len(args),
                    'kwargs_keys': list(kwargs.keys())
                })
                
                log_activity(
                    action=action,
                    module=module,
                    target_type=target_type,
                    target_id=target_id,
                    description=description or f"{action} action performed",
                    success=success,
                    error_message=error_message,
                    metadata=metadata,
                    auto_commit=True
                )
        
        return decorated_function
    return decorator

def log_login_attempt(user_email, success, error_message=None, user_id=None, company_id=None):
    """Log user login attempts"""
    try:
        audit_log = AuditLog()
        audit_log.user_id = user_id
        audit_log.company_id = company_id
        audit_log.action = 'login_attempt'
        audit_log.module = 'Authentication'
        audit_log.description = f"Login attempt for {user_email}"
        audit_log.success = success
        audit_log.error_message = error_message
        
        # Request context
        if request:
            audit_log.ip_address = request.remote_addr
            audit_log.user_agent = request.headers.get('User-Agent', '')[:500]
            audit_log.method = request.method
            audit_log.endpoint = 'auth.login'
        
        audit_log.extra_data = {
            'email': user_email,
            'timestamp': datetime.now().isoformat()
        }
        
        db.session.add(audit_log)
        try:
            db.session.flush()
            db.session.commit()
        except Exception as e:
            print(f"Audit flush error: {e}")
            return
        
    except Exception as e:
        print(f"Login audit logging error: {e}")

def log_permission_check(module, action, allowed, user_id=None, company_id=None):
    """Log permission check attempts"""
    try:
        if not company_id:
            return
            
        audit_log = AuditLog()
        audit_log.user_id = user_id
        audit_log.company_id = company_id
        audit_log.action = 'permission_check'
        audit_log.module = module
        audit_log.description = f"Permission check: {module}.{action}"
        audit_log.success = allowed
        audit_log.error_message = None if allowed else f"Access denied to {module}.{action}"
        
        if request:
            audit_log.ip_address = request.remote_addr
            audit_log.endpoint = request.endpoint
            audit_log.method = request.method
        
        audit_log.extra_data = {
            'permission_module': module,
            'permission_action': action,
            'access_granted': allowed,
            'timestamp': datetime.now().isoformat()
        }
        
        db.session.add(audit_log)
        try:
            db.session.flush()
            db.session.commit()
        except Exception as e:
            print(f"Audit flush error: {e}")
            return
        
    except Exception as e:
        print(f"Permission audit logging error: {e}")

def get_user_activity(user_id=None, company_id=None, limit=50, action_filter=None, success_filter=None):
    """Get user activity logs with filtering"""
    if company_id is None:
        return []
        
    query = AuditLog.query
    
    if company_id:
        query = query.filter_by(company_id=company_id)
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    if action_filter:
        query = query.filter(AuditLog.action.ilike(f'%{action_filter}%'))
    
    if success_filter is not None:
        query = query.filter_by(success=success_filter)
    
    return query.order_by(AuditLog.created_at.desc()).limit(limit).all()

def get_audit_summary(company_id, days=30):
    """Get audit summary statistics"""
    from datetime import datetime, timedelta
    
    start_date = datetime.now() - timedelta(days=days)
    
    logs = AuditLog.query.filter(
        AuditLog.company_id == company_id,
        AuditLog.created_at >= start_date
    ).all()
    
    summary = {
        'total_activities': len(logs),
        'successful_actions': len([l for l in logs if l.success]),
        'failed_actions': len([l for l in logs if not l.success]),
        'unique_users': len(set(l.user_id for l in logs if l.user_id)),
        'actions_by_module': {},
        'actions_by_type': {},
        'recent_failures': []
    }
    
    for log in logs:
        # Count by module
        module = log.module or 'System'
        summary['actions_by_module'][module] = summary['actions_by_module'].get(module, 0) + 1
        
        # Count by action type
        summary['actions_by_type'][log.action] = summary['actions_by_type'].get(log.action, 0) + 1
        
        # Collect recent failures
        if not log.success and len(summary['recent_failures']) < 10:
            summary['recent_failures'].append({
                'action': log.action,
                'module': log.module,
                'error': log.error_message,
                'timestamp': log.created_at.isoformat()
            })
    
    return summary 