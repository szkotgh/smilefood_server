from flask import Blueprint, render_template, send_file
from router.user import user_bp
from router.session import session_bp
from router.food import food_bp

router_bp = Blueprint('router', __name__)
router_bp.register_blueprint(user_bp, url_prefix='/user')
router_bp.register_blueprint(session_bp, url_prefix='/session')
router_bp.register_blueprint(food_bp, url_prefix='/food')

@router_bp.route('/')
def index():
    return render_template('index.html')

@router_bp.route('/favicon.ico')
def favicon():
    return send_file('static/favicon.ico')