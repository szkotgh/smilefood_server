import os
from flask import Flask
from dotenv import load_dotenv
load_dotenv()
from router import router_bp
import src.utils as utils

app = Flask(__name__)
app.register_blueprint(router_bp)

app.config['SECRET_KEY'] = os.environ['SECRET_KEY']

@app.errorhandler(404)
def not_found_error(error):
    return utils.ResultDTO(code=404, message="잘못된 URL 요청입니다.", result=False).to_response()

@app.errorhandler(405)
def method_not_allowed_error(error):
    return utils.ResultDTO(code=405, message="잘못된 METHOD 요청입니다.", result=False).to_response()

@app.errorhandler(500)
def internal_error(error):
    return utils.ResultDTO(code=500, message="서버 내부 오류가 발생했습니다.", result=False).to_response()

@app.errorhandler(Exception)
def unhandled_exception(error):
    return utils.ResultDTO(code=500, message=f"오류가 발생했습니다: {str(error)}", result=False).to_response()

if __name__ == '__main__':
    app.run(os.environ['SERVER_IP'], os.environ['SERVER_PORT'])