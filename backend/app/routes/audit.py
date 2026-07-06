from flask import Blueprint, request, jsonify
from app.models.audit_log import AuditLog
from app.models.user import User
from app.utils import require_permission, get_current_company_id
from app.utils.validators import parse_pagination
from app.utils.constants import MAX_PER_PAGE
from app.utils.audit import get_user_activity, get_audit_summary
from datetime import datetime, timedelta

audit_bp = Blueprint('audit', __name__)

@audit_bp.route('/logs', methods=['GET'])
@require_permission('AuditLogs', 'view')
def get_audit_logs():
    """Get audit logs with filtering and pagination"""
    from app.utils import is_administrator
    filter_company_id = request.args.get('company_id', type=int)
    
    # Query parameters
    page, per_page, error = parse_pagination(request)
    if error:
        return error
    user_id = request.args.get('user_id', type=int)
    action = request.args.get('action')
    module = request.args.get('module')
    success = request.args.get('success')
    try:
        days = int(request.args.get('days', 30))
    except ValueError:
        return jsonify({'error': 'Invalid days parameter'}), 400
    
    # Build query
    if is_administrator():
        if filter_company_id:
            query = AuditLog.query.filter_by(company_id=filter_company_id)
        else:
            query = AuditLog.query
    else:
        company_id = get_current_company_id()
        query = AuditLog.query.filter_by(company_id=company_id)
    
    # Apply filters
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    if action:
        query = query.filter(AuditLog.action.ilike(f'%{action}%'))
    
    if module:
        query = query.filter(AuditLog.module.ilike(f'%{module}%'))
    
    if success is not None:
        success_bool = success.lower() in ['true', '1', 'yes']
        query = query.filter_by(success=success_bool)
    
    # Date filter
    if days:
        start_date = datetime.now() - timedelta(days=days)
        query = query.filter(AuditLog.created_at >= start_date)
    
    # Pagination
    pagination = query.order_by(AuditLog.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    logs = pagination.items
    
    user_ids = list({log.user_id for log in logs if log.user_id})
    users_map = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()}
    
    # Format response
    formatted_logs = []
    for log in logs:
        user = users_map.get(log.user_id) if log.user_id else None
        
        formatted_logs.append({
            'id': log.id,
            'user': {
                'id': user.id if user else None,
                'name': user.name if user else 'System',
                'email': user.email if user else None
            },
            'action': log.action,
            'module': log.module,
            'target_type': log.target_type,
            'target_id': log.target_id,
            'description': log.description,
            'success': log.success,
            'error_message': log.error_message,
            'ip_address': log.ip_address,
            'user_agent': log.user_agent,
            'method': log.method,
            'endpoint': log.endpoint,
            'timestamp': log.created_at.isoformat(),
            'metadata': log.extra_data
        })
    
    return jsonify({
        'logs': formatted_logs,
        'pagination': {
            'page': pagination.page,
            'pages': pagination.pages,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        },
        'filters_applied': {
            'user_id': user_id,
            'action': action,
            'module': module,
            'success': success,
            'days': days
        }
    })

@audit_bp.route('/summary', methods=['GET'])
@require_permission('AuditLogs', 'view')
def get_audit_summary_api():
    """Get audit summary statistics"""
    from app.utils import is_administrator
    filter_company_id = request.args.get('company_id', type=int)
    try:
        days = int(request.args.get('days', 30))
    except ValueError:
        return jsonify({'error': 'Invalid days parameter'}), 400
    
    if is_administrator():
        company_id = filter_company_id
    else:
        company_id = get_current_company_id()
        
    summary = get_audit_summary(company_id, days)
    
    return jsonify({
        'summary': summary,
        'period_days': days,
        'company_id': company_id
    })

@audit_bp.route('/user/<int:user_id>', methods=['GET'])
@require_permission('Users', 'view')
def get_user_audit_logs(user_id):
    """Get audit logs for specific user"""
    from app.utils import is_administrator
    if is_administrator():
        user = User.query.filter_by(id=user_id).first_or_404()
        company_id = user.company_id
    else:
        company_id = get_current_company_id()
        user = User.query.filter_by(id=user_id, company_id=company_id).first_or_404()
        
    try:
        limit = int(request.args.get('limit', 50))
        limit = min(limit, MAX_PER_PAGE)
    except ValueError:
        return jsonify({'error': 'Invalid limit parameter'}), 400
    action_filter = request.args.get('action')
    success_filter = request.args.get('success')
    
    if success_filter is not None:
        success_filter = success_filter.lower() in ['true', '1', 'yes']
    
    logs = get_user_activity(
        user_id=user_id,
        company_id=company_id,
        limit=limit,
        action_filter=action_filter,
        success_filter=success_filter
    )
    
    # Get user info
    user = User.query.filter_by(id=user_id, company_id=company_id).first_or_404()
    
    formatted_logs = []
    for log in logs:
        formatted_logs.append({
            'id': log.id,
            'action': log.action,
            'module': log.module,
            'description': log.description,
            'success': log.success,
            'error_message': log.error_message,
            'ip_address': log.ip_address,
            'method': log.method,
            'endpoint': log.endpoint,
            'timestamp': log.created_at.isoformat()
        })
    
    return jsonify({
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email
        },
        'logs': formatted_logs,
        'total_logs': len(formatted_logs),
        'filters': {
            'action': action_filter,
            'success': success_filter,
            'limit': limit
        }
    })

@audit_bp.route('/export', methods=['GET'])
@require_permission('AuditLogs', 'view')
def export_audit_logs():
    """Export audit logs as CSV"""
    from app.utils import is_administrator
    filter_company_id = request.args.get('company_id', type=int)
    try:
        days = int(request.args.get('days', 30))
    except ValueError:
        return jsonify({'error': 'Invalid days parameter'}), 400
    
    start_date = datetime.now() - timedelta(days=days)
    
    if is_administrator():
        if filter_company_id:
            query = AuditLog.query.filter(
                AuditLog.company_id == filter_company_id,
                AuditLog.created_at >= start_date
            )
        else:
            query = AuditLog.query.filter(
                AuditLog.created_at >= start_date
            )
    else:
        company_id = get_current_company_id()
        query = AuditLog.query.filter(
            AuditLog.company_id == company_id,
            AuditLog.created_at >= start_date
        )
        
    logs = query.order_by(AuditLog.created_at.desc()).all()
    
    # Create CSV data
    csv_data = []
    csv_data.append([
        'Timestamp', 'User', 'Action', 'Module', 'Target Type', 
        'Target ID', 'Success', 'IP Address', 'Method', 'Endpoint', 'Description'
    ])
    
    user_ids = list({log.user_id for log in logs if log.user_id})
    users_map = {u.id: u for u in User.query.filter(User.id.in_(user_ids)).all()}
    
    for log in logs:
        user = users_map.get(log.user_id) if log.user_id else None
        user_name = user.name if user else 'System'
        
        csv_data.append([
            log.created_at.isoformat(),
            user_name,
            log.action or '',
            log.module or '',
            log.target_type or '',
            log.target_id or '',
            'Success' if log.success else 'Failed',
            log.ip_address or '',
            log.method or '',
            log.endpoint or '',
            log.description or ''
        ])
    
    return jsonify({
        'csv_data': csv_data,
        'total_records': len(csv_data) - 1,  # Exclude header
        'export_timestamp': datetime.now().isoformat(),
        'period_days': days
    })

@audit_bp.route('/stats', methods=['GET'])
@require_permission('AuditLogs', 'view')
def get_audit_stats():
    """Get detailed audit statistics"""
    from app.utils import is_administrator
    filter_company_id = request.args.get('company_id', type=int)
    try:
        days = int(request.args.get('days', 7))
    except ValueError:
        return jsonify({'error': 'Invalid days parameter'}), 400
    
    start_date = datetime.now() - timedelta(days=days)
    
    # Get logs for the period
    if is_administrator():
        if filter_company_id:
            query = AuditLog.query.filter(
                AuditLog.company_id == filter_company_id,
                AuditLog.created_at >= start_date
            )
        else:
            query = AuditLog.query.filter(
                AuditLog.created_at >= start_date
            )
    else:
        company_id = get_current_company_id()
        query = AuditLog.query.filter(
            AuditLog.company_id == company_id,
            AuditLog.created_at >= start_date
        )
        
    logs = query.all()
    
    # Calculate statistics
    stats = {
        'total_activities': len(logs),
        'success_rate': 0,
        'unique_users': len(set(l.user_id for l in logs if l.user_id)),
        'top_actions': {},
        'top_modules': {},
        'daily_activity': {},
        'hourly_activity': [0] * 24,
        'failure_analysis': []
    }
    
    if logs:
        successful = len([l for l in logs if l.success])
        stats['success_rate'] = round((successful / len(logs)) * 100, 2)
        
        # Count actions and modules
        for log in logs:
            # Actions
            action = log.action
            stats['top_actions'][action] = stats['top_actions'].get(action, 0) + 1
            
            # Modules
            module = log.module or 'System'
            stats['top_modules'][module] = stats['top_modules'].get(module, 0) + 1
            
            # Daily activity
            day = log.created_at.strftime('%Y-%m-%d')
            stats['daily_activity'][day] = stats['daily_activity'].get(day, 0) + 1
            
            # Hourly activity
            hour = log.created_at.hour
            stats['hourly_activity'][hour] += 1
            
            # Failure analysis
            if not log.success and len(stats['failure_analysis']) < 20:
                stats['failure_analysis'].append({
                    'action': log.action,
                    'module': log.module,
                    'error': log.error_message,
                    'timestamp': log.created_at.isoformat(),
                    'user_id': log.user_id
                })
    
    return jsonify({
        'stats': stats,
        'period': {
            'days': days,
            'start_date': start_date.isoformat(),
            'end_date': datetime.now().isoformat()
        }
    }) 