import secrets
import hashlib
import re
from datetime import datetime, timedelta

from flask import request

class ResultDTO:
    def __init__(self, code: int | bool, message: str, data=None, result: bool = False):
        self.code = code
        self.message = message
        self.data = data
        self.result = result

    def to_dict(self):
        return {
            'code': self.code,
            'message': self.message,
            'data': self.data,
            'result': self.result
        }
        
    def to_response(self):
        return {
            'code': self.code,
            'message': self.message,
            'data': self.data
        }, self.code

def get_client_ip():
    client_ip = request.headers.get("X-Forwarded-For")
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    else:
        client_ip = request.remote_addr
    return client_ip


# Generate Random
def gen_hash(length: int) -> str:
    return hashlib.sha256(secrets.token_bytes(32)).hexdigest()[:length]

def gen_number(length: int) -> str:
    return ''.join(secrets.choice('0123456789') for _ in range(length)) 

def str_to_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()

# Datetime
def get_current_datetime() -> datetime:
    return datetime.now() 

def get_current_datetime_str() -> str:
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def str_to_datetime(date_str: str) -> datetime:
    return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')

def datetime_to_str(date: datetime) -> str:
    return date.strftime('%Y-%m-%d %H:%M:%S')

def is_minutes_passed(start_time: str, minutes: int) -> bool:
    start_dt = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
    now = datetime.now()
    target_time = start_dt + timedelta(minutes=minutes)
    return now > target_time

def get_future_timestamp(days: int = 0, hours: int = 0, minutes: int = 0, seconds: int = 0) -> str:
    future_time = datetime.now() + timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    return future_time.strftime('%Y-%m-%d %H:%M:%S')


# Verify, Extract (Regex)
EMAIL_RE = re.compile(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$')
USERNAME_RE = re.compile(r'^[\w가-힣]{1,20}$') # 한글과 영어 문자만 지원. 공백 X(1~20자)
PASSWORD_RE = re.compile(r'^(?=.*[A-Za-z])(?=.*\d)(?=.*[\W_]).{8,256}$') # 최소 8자 이상 256자 이하, 영문, 숫자, 특수기호만 허용. 최소 하나씩 포함
VALIDDATE_CODE_RE = re.compile(r'^\d{6}$')  # 6자리 숫자 코드
BARCODE_RE = re.compile(r'^\d{12,13}$')  # 12자리 또는 13자리 숫자 바코드

def is_valid_email(email) -> bool:
    return bool(EMAIL_RE.match(str(email)))

def is_valid_username(username) -> bool:
    return bool(USERNAME_RE.match(str(username)))

def is_valid_password(password) -> bool:
    return bool(PASSWORD_RE.match(str(password)))

def is_valid_verification_code(code) -> bool:
    return bool(VALIDDATE_CODE_RE.match(str(code)))

def is_valid_barcode(barcode) -> bool:
    return bool(BARCODE_RE.match(str(barcode)))

def extract_months(text) -> int | None:
    match = re.search(r'(\d+)\s*개월', text)
    if match:
        return int(match.group(1))
    return None