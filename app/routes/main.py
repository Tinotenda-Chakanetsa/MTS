from flask import Blueprint, redirect, url_for

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Redirect root URL to dashboard"""
    return redirect(url_for('dashboard.index'))
