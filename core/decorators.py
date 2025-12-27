"""
Permission decorators for role-based access control in the ReDIB COA Portal.
"""
from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required


def role_required(*roles):
    """
    Decorator to check if user has one of the required roles.

    Usage:
        @role_required('coordinator')
        @role_required('coordinator', 'admin')

    Args:
        *roles: Variable number of role names that are allowed

    Returns:
        Decorator function that checks user roles
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            # Get user's active roles
            user_roles = request.user.roles.filter(is_active=True).values_list('role', flat=True)

            # Check if user has any of the required roles or is superuser
            if request.user.is_superuser or any(role in user_roles for role in roles):
                return view_func(request, *args, **kwargs)

            # User doesn't have permission
            messages.error(request, "You don't have permission to access this page.")
            return redirect('core:dashboard')

        return _wrapped_view
    return decorator


def applicant_required(view_func):
    """Shortcut decorator for applicant role"""
    return role_required('applicant')(view_func)


def node_coordinator_required(view_func):
    """Shortcut decorator for node coordinator role"""
    return role_required('node_coordinator')(view_func)


def evaluator_required(view_func):
    """Shortcut decorator for evaluator role"""
    return role_required('evaluator')(view_func)


def coordinator_required(view_func):
    """Shortcut decorator for ReDIB coordinator role"""
    return role_required('coordinator')(view_func)


def admin_or_coordinator_required(view_func):
    """Shortcut decorator for admin or coordinator roles"""
    return role_required('admin', 'coordinator')(view_func)
