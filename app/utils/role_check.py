from flask import redirect, url_for, flash, session
from functools import wraps
from ..models import User, Organizations
from langchain_community.llms.ollama import Ollama
from functools import wraps

def role_required(roles=None):
    def decorator(func):
        @wraps(func)
        def inner(*args, **kwargs):
            # Common variables
            user_id = session.get('user_id')
            org_id = session.get('org_id')

            # Ensure roles is iterable
            roles_to_check = roles if isinstance(roles, (list, tuple)) else [roles]

            # Role-specific checks
            if "organization" in roles_to_check and org_id:
                organization = Organizations.query.filter_by(orgid=org_id).first()
                if organization:
                    return func(*args, **kwargs)

            if "moderator" in roles_to_check and user_id:
                moderator = User.query.filter_by(userid=user_id).first()
                if moderator and moderator.role == "moderator":
                    return func(*args, **kwargs)

            if "user" in roles_to_check and user_id:
                user = User.query.filter_by(userid=user_id).first()
                if user:
                    return func(*args, **kwargs)

            # If no matching role, deny access
            flash("You do not have permission to access this page.")
            return redirect(url_for('user.login'))
        return inner
    return decorator