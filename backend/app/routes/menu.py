from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.utils import get_current_user, get_user_permissions_summary, require_company_context, get_current_company_id
from app.models.module import Module
from app.utils.constants import STATUS_ACTIVE

menu_bp = Blueprint('menu', __name__)

@menu_bp.route('/sidebar', methods=['GET'])
@require_company_context
def get_user_sidebar():
    """Generate dynamic sidebar menu based on user permissions"""
    permissions = get_user_permissions_summary()
    company_id = get_current_company_id()
    
    # Get only active modules with their display routes, ordered by order_index
    modules = Module.query.filter_by(company_id=company_id).filter(Module.status == STATUS_ACTIVE).order_by(Module.order_index.asc(), Module.module_name.asc()).all()
    module_routes = {module.module_name: module.display_route for module in modules}
    module_orders = {module.module_name: module.order_index for module in modules}
    
    menu_items = []
    for module_name, actions in permissions.items():
        # Only include modules that exist and are active
        if module_name not in module_routes:
            continue
            
        # Get the display route for this module
        display_route = module_routes.get(module_name, module_name.lower())
        
        menu_item = {
            'module': module_name,
            'route': display_route,  # Add the dynamic route
            'order_index': module_orders.get(module_name, 999),  # Include order_index
            'icon': get_module_icon(module_name),
            'actions': []
        }
        
        # Group actions for this module
        for action in actions:
            menu_item['actions'].append({
                'name': action['action'],
                'label': format_action_label(action['action']),
                'url': f"/{display_route}{action['url']}",  # Use display_route
                'source': action['source']
            })
        
        # Only include modules with at least 'view' permission
        if any(action['action'] == 'view' for action in actions):
            menu_items.append(menu_item)
    
    # Sort menu items by module order (matching the order in modules query)
    def get_module_order(menu_item):
        module_name = menu_item['module']
        for module in modules:
            if module.module_name == module_name:
                return module.order_index
        return 999  # Put unknown modules at the end
    
    menu_items.sort(key=get_module_order)
    
    return jsonify({
        'user': {
            'id': get_current_user().id,
            'name': get_current_user().name,
            'email': get_current_user().email
        },
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
    
    return jsonify({
        'navigation': navigation,
        'breadcrumbs_enabled': True,
        'user_context': {
            'name': get_current_user().name,
            'company_id': get_current_user().company_id
        }
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
