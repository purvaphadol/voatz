from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.utils import get_current_user, get_user_permissions_summary, require_company_context, get_current_company_id
from app.models.module import SystemModule, CompanyModule
from app.utils.constants import STATUS_ACTIVE

menu_bp = Blueprint('menu', __name__)

def format_action_label(action_name):
    labels = {
        'view': 'View',
        'create': 'Create',
        'update': 'Edit',
        'delete': 'Delete'
    }
    return labels.get(action_name, action_name.capitalize())

@menu_bp.route('/sidebar', methods=['GET'])
@require_company_context
def get_user_sidebar():
    """Generate dynamic sidebar menu based on user permissions"""
    from app.utils import is_administrator, get_current_user, get_module_keys
    permissions = get_user_permissions_summary()
    
    if is_administrator():
        modules = SystemModule.query.filter(SystemModule.status == STATUS_ACTIVE).order_by(SystemModule.order_index.asc(), SystemModule.module_name.asc()).all()
    else:
        company_id = get_current_company_id()
        modules = SystemModule.query.join(
            CompanyModule, CompanyModule.system_module_id == SystemModule.id
        ).filter(
            CompanyModule.company_id == company_id,
            CompanyModule.status == STATUS_ACTIVE,
            SystemModule.status == STATUS_ACTIVE
        ).order_by(SystemModule.order_index.asc(), SystemModule.module_name.asc()).all()
        if not modules:
            modules = SystemModule.query.filter(SystemModule.status == STATUS_ACTIVE).order_by(SystemModule.order_index.asc(), SystemModule.module_name.asc()).all()
        
    menu_items = []

    for module in modules:
        m_keys = get_module_keys(module)
        mod_actions = None
        for k in m_keys:
            if k in permissions and permissions[k]:
                mod_actions = permissions[k]
                break
        
        if not mod_actions:
            if is_administrator():
                mod_actions = [{'action': act, 'source': 'administrator', 'url': f'/{act}'} for act in ['view', 'create', 'update', 'delete']]
            else:
                continue

        has_view = any(a['action'] == 'view' for a in mod_actions)
        if not has_view:
            continue

        display_route = module.display_route or module.route_name or module.module_name.lower().replace(' ', '-')

        menu_item = {
            'module': module.module_name,
            'route_name': module.route_name,
            'route': display_route,
            'order_index': module.order_index,
            'icon': module.icon if module.icon else 'folder',
            'actions': []
        }

        seen_actions = set()
        for action in mod_actions:
            if action['action'] not in seen_actions:
                seen_actions.add(action['action'])
                menu_item['actions'].append({
                    'name': action['action'],
                    'label': format_action_label(action['action']),
                    'url': f"/{display_route}{action['url']}",
                    'source': action['source']
                })

        menu_items.append(menu_item)
    
    def get_module_order(menu_item):
        return menu_item.get('order_index', 999)
    
    menu_items.sort(key=get_module_order)
    
    current_user = get_current_user()
    if current_user:
        user_data = {
            'id': current_user.id,
            'name': current_user.name,
            'email': current_user.email
        }
    else:
        from app.utils import get_current_administrator
        admin = get_current_administrator()
        user_data = {
            'id': f"admin:{admin.id}" if admin else 'admin',
            'name': admin.name if admin else 'Platform Administrator',
            'email': admin.email if admin else 'admin@gmail.com'
        }
        
    return jsonify({
        'user': user_data,
        'menu': menu_items,
        'total_modules': len(menu_items),
        'total_permissions': sum(len(actions) for actions in permissions.values())
    })

@menu_bp.route('/permissions', methods=['GET'])
@require_company_context
def get_user_permissions():
    """Get detailed user permissions for frontend access control"""
    permissions = get_user_permissions_summary()
    
    # Convert to flat structure for easy frontend checking
    flat_permissions = {}
    for module_name, actions in permissions.items():
        for action in actions:
            key = f"{module_name.lower()}.{action['action']}"
            flat_permissions[key] = {
                'allowed': True,
                'source': action['source'],
                'url': action['url']
            }
    
    return jsonify({
        'permissions': flat_permissions,
        'grouped_permissions': permissions,
        'summary': {
            'total_modules': len(permissions),
            'total_actions': sum(len(actions) for actions in permissions.values()),
            'modules_with_access': list(permissions.keys())
        }
    })

@menu_bp.route('/navigation', methods=['GET'])
@require_company_context
def get_navigation_items():
    """Get navigation items with permission-based visibility"""
    permissions = get_user_permissions_summary()
    
    navigation = []
    
    # Define navigation structure with required permissions
    nav_structure = [
        {
            'name': 'Dashboard',
            'path': '/dashboard',
            'icon': 'dashboard',
            'required_permission': ('Dashboard', 'view')
        },
        {
            'name': 'User Management',
            'path': '/users',
            'icon': 'users',
            'required_permission': ('Users', 'view'),
            'children': [
                {
                    'name': 'All Users',
                    'path': '/users',
                    'required_permission': ('Users', 'view')
                },
                {
                    'name': 'Add User',
                    'path': '/users/create',
                    'required_permission': ('Users', 'create')
                }
            ]
        },
        {
            'name': 'Settings',
            'path': '/settings',
            'icon': 'settings',
            'required_permission': ('Settings', 'view'),
            'children': [
                {
                    'name': 'General',
                    'path': '/settings/general',
                    'required_permission': ('Settings', 'view')
                },
                {
                    'name': 'Security',
                    'path': '/settings/security',
                    'required_permission': ('Settings', 'update')
                }
            ]
        }
    ]
    
    # Filter navigation based on permissions
    for nav_item in nav_structure:
        module, action = nav_item['required_permission']
        if module in permissions and any(a['action'] == action for a in permissions[module]):
            filtered_item = {
                'name': nav_item['name'],
                'path': nav_item['path'],
                'icon': nav_item['icon']
            }
            
            # Filter children if they exist
            if 'children' in nav_item:
                children = []
                for child in nav_item['children']:
                    child_module, child_action = child['required_permission']
                    if child_module in permissions and any(a['action'] == child_action for a in permissions[child_module]):
                        children.append({
                            'name': child['name'],
                            'path': child['path']
                        })
                
                if children:
                    filtered_item['children'] = children
            
            navigation.append(filtered_item)
    
    current_user = get_current_user()
    if current_user:
        user_context = {
            'name': current_user.name,
            'company_id': current_user.company_id
        }
    else:
        from app.utils import get_current_administrator
        admin = get_current_administrator()
        user_context = {
            'name': admin.name if admin else 'Platform Administrator',
            'company_id': None
        }

    return jsonify({
        'navigation': navigation,
        'breadcrumbs_enabled': True,
        'user_context': user_context
    })

def get_module_icon(module_name):
    """Get appropriate icon for module"""
    icons = {
        'Dashboard': 'dashboard',
        'Users': 'users',
        'Settings': 'settings',
        'Reports': 'chart-bar',
        'Security': 'shield',
        'Profile': 'user-circle'
    }
    return icons.get(module_name, 'folder')

def format_action_label(action_name):
    """Format action name for display"""
    labels = {
        'view': 'View',
        'create': 'Create',
        'update': 'Edit',
        'delete': 'Delete'
    }
    return labels.get(action_name, action_name.title())
