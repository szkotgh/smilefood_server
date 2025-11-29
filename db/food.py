import json
import os
import db
import db.session
import src.utils as utils
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()
# import urllib3
# urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def delete_food(sid: str, fid: str) -> utils.ResultDTO:
    session_info = db.session.get_info(sid)
    if not session_info.result:
        return session_info
    
    uid = session_info.data['session_info']['uid']
    
    food_info = get_info(sid, fid)
    if not food_info.result:
        return food_info
    
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    # 식품 ID와 유저 ID가 일치하는 식품 정보 업데이트
    cursor.execute("UPDATE foods SET is_active = FALSE, updated_at = datetime('now', '+9 hours') WHERE fid = ?", (fid,))
    conn.commit()
    
    if cursor.rowcount == 0:
        db.close_db_connection(conn)
        return utils.ResultDTO(code=404, message="등록된 식품 정보를 찾을 수 없습니다.", result=False)
    
    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="성공적으로 삭제되었습니다.", result=True)

def get_info(sid: str, fid: str) -> utils.ResultDTO:
    session_info = db.session.get_info(sid)
    if not session_info.result:
        return session_info
    if session_info.data['session_info']['is_active'] == 0:
        return utils.ResultDTO(code=401, message="비활성화된 세션입니다.", result=False)

    if not fid:
        return utils.ResultDTO(code=400, message="유효하지 않은 식품 ID입니다.", result=False)
    
    conn = db.get_db_connection()
    cursor = conn.cursor()

    # 유저 ID와 식품 ID가 일치하는 식품 정보 조회
    uid = session_info.data['session_info']['uid']
    cursor.execute("SELECT * FROM foods WHERE fid = ? AND uid = ?", (fid, uid))
    row = cursor.fetchone()
    
    if not row:
        cursor.execute("SELECT * FROM foods WHERE fid = ?", (fid,))
        row = cursor.fetchone()
        if row:
            return utils.ResultDTO(code=401, message="본인의 식품 정보만 조회할 수 있습니다.", result=False)
        
        db.close_db_connection(conn)
        return utils.ResultDTO(code=404, message="등록된 식품 정보를 찾을 수 없습니다.", result=False)
    row = dict(row)
    
    # 유통기한까지 남은 일수 계산
    expiration_date = utils.str_to_datetime(row['expiration_date'])
    current_date = datetime.now()
    days_remaining = (expiration_date - current_date).days
    row['days_remaining'] = days_remaining
    
    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="성공적으로 조회되었습니다.", data={'food_info': row}, result=True)

def get_list_info(sid: str) -> utils.ResultDTO:
    session_info = db.session.get_info(sid)
    # 잘못된 세션 ID일 경우 실패 처리
    if not session_info.result:
        return session_info
    if session_info.data['session_info']['is_active'] == 0:
        return utils.ResultDTO(code=401, message="비활성화된 세션입니다.", result=False)
    
    uid = session_info.data['session_info']['uid']
    
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM foods WHERE uid = ?", (uid,))
    rows = cursor.fetchall()
    
    if not rows:
        db.close_db_connection(conn)
        return utils.ResultDTO(code=404, message="등록된 식품 정보가 없습니다.", result=False)
    
    food_list = [dict(row) for row in rows]
    
    # 각 식품의 유통기한까지 남은 일수 계산
    current_date = datetime.now()
    for food in food_list:
        expiration_date = utils.str_to_datetime(food['expiration_date'])
        days_remaining = (expiration_date - current_date).days
        food['days_remaining'] = days_remaining
    
    food_list.sort(key=lambda x: x['expiration_date'])
    
    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="성공적으로 조회되었습니다.", data={'food_list': food_list}, result=True)

def regi_food_with_barcode(sid:str, barcode:str, food_count:int) -> utils.ResultDTO:
    session_info = db.session.get_info(sid)
    # 잘못된 세션 ID일 경우 실패 처리
    if not session_info.result:
        return session_info
    
    # 잘못된 바코드 값일 경우 실패 처리
    if not barcode or not utils.is_valid_barcode(barcode):
        return utils.ResultDTO(code=400, message="유효하지 않은 바코드 형식입니다. (12~13자리 숫자)", result=False)
    
    # 잘못된 식품 수량일 경우 실패 처리
    if food_count <= 0 or food_count > 100:
        return utils.ResultDTO(code=400, message="식품 수량은 1 이상 100 이하이어야 합니다.", result=False)
    
    # 식품의 이름, 종류(유탕면, 음료 등), 유통기한 가져오기
    food_name = None
    food_type = "정보 없음"
    food_expiration_date = datetime.now() + timedelta(days=3*30)
    food_expiration_date_desc = "3개월 이내(소비기한 정보 없음)"
    food_image_url = None
    food_volume = None
    try:
        # get Food name, type, expiration date
        foodsafety_api_url = f"http://openapi.foodsafetykorea.go.kr/api/{os.environ['FOODSAFETYKOREA_API_KEY']}/C005/json/1/100/BAR_CD={barcode}"
        response = requests.get(foodsafety_api_url)
        response.raise_for_status()
        response_json = response.json()
        row = response_json['C005']['row'][0]
        food_name = row['PRDLST_NM']
        food_type = row['PRDLST_DCNM']
        food_expiration_date = datetime.now() + timedelta(days=utils.extract_months(row['POG_DAYCNT'])*30)
        food_expiration_date_desc = row['POG_DAYCNT']
    except:
        # return utils.ResultDTO(code=400, message="식품 정보를 찾을 수 없습니다.", result=False)
        pass
    
    try:
        retaildb_api_url = f"https://www.retaildb.or.kr/service/product_info/search/{barcode}"
        response = requests.get(retaildb_api_url, verify=False)
        response_json = response.json()
        food_name = response_json['baseItems'][0]['value']
        food_volume = response_json['originVolume']
        food_image_url = response_json['images'][0]
    except:
        pass
    
    # Get Ingredients
    ingredients = '정보없음'
    with open(os.path.join(os.path.dirname(__file__), '../static/ingredients_info.json'), 'r', encoding='utf-8') as f:
        ingredients_data = json.load(f)
        if barcode in ingredients_data:
            ingredients = ingredients_data[barcode]
    
    # DB
    fid = utils.gen_hash(16)
    uid = session_info.data['session_info']['uid']
    conn = db.get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO foods (fid, uid, name, type, ingredients, description, count, volume, image_url, barcode, expiration_date_desc, expiration_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (fid, uid, food_name, food_type, ingredients, f"[메모] {food_name}", food_count, food_volume, food_image_url, barcode, food_expiration_date_desc, utils.datetime_to_str(food_expiration_date)))
        conn.commit()
        db.close_db_connection(conn)
    except Exception as e:
        db.close_db_connection(conn)
        return utils.ResultDTO(code=409, message=f"등록 중 오류가 발생했습니다: {str(e)}", result=False)

    return utils.ResultDTO(code=200, message="식품 등록 성공", data=get_info(sid, fid).data, result=True)