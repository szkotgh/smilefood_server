import sqlite3
import db
import db.session
import src.utils as utils
import src.email

def set_profile_url(session_id: str, profile_url: str) -> utils.ResultDTO:
    # Validate session ID
    session_info = db.session.get_info(session_id)
    if not session_info:
        return utils.ResultDTO(code=405, message="Invalid session ID", result=False)
    if not session_info['is_active']:
        return utils.ResultDTO(code=401, message="Inactive session ID", result=False)

    uid = session_info['uid']
    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE users SET profile_url = ? WHERE uid = ?", (profile_url, uid))
    conn.commit()
    
    if cursor.rowcount == 0:
        db.close_db_connection(conn)
        return utils.ResultDTO(code=400, message="Failed to update profile URL", result=False)

    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="Profile URL updated successfully", result=True)

def validate_user(email: str, password: str) -> utils.ResultDTO:
    if not utils.is_valid_email(email):
        return utils.ResultDTO(code=400, message="유효하지 않은 이메일 형식입니다.", result=False)
    if not password:
        return utils.ResultDTO(code=400, message="비밀번호가 필요합니다.", result=False)

    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()

    if not row or row['password'] != utils.str_to_hash(password + row['salt']):
        db.close_db_connection(conn)
        return utils.ResultDTO(code=401, message="이메일 또는 비밀번호를 확인하십시오.", result=False)

    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="인증에 성공했습니다.", data={'uid': row['uid']}, result=True)

def validate_user_by_uid(uid: str, password: str) -> utils.ResultDTO:
    if not uid:
        return utils.ResultDTO(code=400, message="UID가 필요합니다.", result=False)
    if not password:
        return utils.ResultDTO(code=400, message="비밀번호가 필요합니다.", result=False)

    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE uid = ?", (uid,))
    row = cursor.fetchone()

    if not row or row['password'] != utils.str_to_hash(password + row['salt']):
        db.close_db_connection(conn)
        return utils.ResultDTO(code=401, message="UID 또는 비밀번호를 확인하십시오.", result=False)

    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="인증에 성공했습니다.", data={'uid': row['uid']}, result=True)

def get_info(uid: str) -> utils.ResultDTO:
    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE uid = ?", (uid,))
    row = cursor.fetchone()

    if not row:
        db.close_db_connection(conn)
        return utils.ResultDTO(code=404, message="유저를 찾을 수 없습니다.", result=False)

    user_info = {
        'uid': row['uid'],
        'email': row['email'],
        'name': row['name'],
        'profile_url': row['profile_url'],
        'created_at': row['created_at']
    }

    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="유저 정보를 성공적으로 조회했습니다.", data={'user_info': user_info}, result=True)

def get_info_by_email(email: str) -> utils.ResultDTO:
    if not utils.is_valid_email(email):
        return utils.ResultDTO(code=400, message="유효하지 않은 이메일 형식입니다.", result=False)

    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()

    if not row:
        db.close_db_connection(conn)
        return utils.ResultDTO(code=404, message="가입된 계정 정보를 찾을 수 없습니다.", result=False)

    user_info = {
        'uid': row['uid'],
        'email': row['email'],
        'name': row['name'],
        'profile_url': row['profile_url'],
        'created_at': row['created_at']
    }

    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="유저 정보를 성공적으로 조회했습니다.", data={'user_info': user_info}, result=True)

def create_user(email:str, password:str, name:str) -> utils.ResultDTO:
    if not utils.is_valid_email(email):
        return utils.ResultDTO(code=400, message="이메일이 올바르지 않습니다.", result=False)
    if not utils.is_valid_password(password):
        return utils.ResultDTO(code=400, message="비밀번호 형식이 올바르지 않습니다. (영문, 숫자, 기호 8~256자)", result=False)
    if not utils.is_valid_username(name):
        return utils.ResultDTO(code=400, message="올바르지 않은 이름입니다. (한글, 영어 1~20자)", result=False)

    salt = utils.gen_hash(16)
    hashed_password = utils.str_to_hash(password + salt)

    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    # Check Email
    ## If email already exists
    cursor.execute("SELECT email FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        db.close_db_connection(conn)
        return utils.ResultDTO(code=409, message="이미 가입된 이메일입니다.", result=False)

    ## If email verification is not done
    cursor.execute("SELECT is_verified FROM email_verification WHERE email = ?", (email,))
    row = cursor.fetchone()
    if not row or not row[0]:
        db.close_db_connection(conn)
        return utils.ResultDTO(code=400, message="이메일 인증이 완료되지 않았습니다.", result=False)

    try:
        uid = utils.gen_hash(16)
        cursor.execute("INSERT INTO users (uid, email, password, salt, name) VALUES (?, ?, ?, ?, ?)",
                       (uid, email, hashed_password, salt, name))
        conn.commit()
        src.email.service.send_welcome_email(email, get_info(uid))
        return utils.ResultDTO(code=200, message="성공적으로 가입되었습니다.", result=True)
    except sqlite3.IntegrityError:
        return utils.ResultDTO(code=409, message="이미 가입된 이메일입니다.", result=False)
    finally:
        db.close_db_connection(conn)

def delete_user(email: str, password: str) -> utils.ResultDTO:
    # 사용자 인증
    validate_info = validate_user(email, password)
    if not validate_info.result:
        return validate_info

    uid = validate_info.data['uid']
    user_info = get_info(uid)
    
    # 관련 정보 모두 삭제. 세션 정보는 uid로 조회 후 모두 비활성화 처리
    conn = db.get_db_connection()
    cursor = conn.cursor()

    try:
        # Delete user sessions
        cursor.execute("UPDATE user_sessions SET is_active = 0 WHERE uid = ?", (uid,))
        
        # Delete user foods
        cursor.execute("DELETE FROM foods WHERE uid = ?", (uid,))
        
        # Delete user
        cursor.execute("DELETE FROM users WHERE uid = ?", (uid,))
        
        conn.commit()
        
        src.email.service.send_deleted_account_email(email, user_info)
        
        return utils.ResultDTO(code=200, message="탈퇴가 완료되었습니다.\n이용해주셔서 감사합니다.", result=True)
    except sqlite3.Error as e:
        return utils.ResultDTO(code=500, message=f"탈퇴에 실패했습니다: {str(e)}", result=False)
    finally:
        db.close_db_connection(conn)

# 이메일 인증 생성
def send_email_verify_code(user_email: str) -> utils.ResultDTO:
    verification_code = utils.gen_number(6)
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT created_at, is_verified FROM email_verification WHERE email = ?", (user_email,))
    row = cursor.fetchone()
    
    # 만약 이메일이 이미 존재한다면, 기존 레코드를 업데이트(create_at이 3분이 지났을 경우 재설정 가능)
    if row:
        created_at, is_verified = row
        
        # 이미 가입된 이메일이라면 실패 처리
        cursor.execute("SELECT email FROM users WHERE email = ?", (user_email,))
        if cursor.fetchone():
            db.close_db_connection(conn)
            return utils.ResultDTO(code=409, message="이미 가입된 이메일입니다. 다른 이메일을 사용하십시오.", result=False)
        # 만약 created_at이 1분이 지났다면, 새로운 인증 코드를 생성하고 이메일을 재전송
        if utils.is_minutes_passed(created_at, 1):
            cursor.execute("UPDATE email_verification SET verification_code = ?, is_verified = 0, try_count = 0, updated_at = (datetime('now', '+9 hours')), created_at = (datetime('now', '+9 hours')) WHERE email = ?", (verification_code, user_email))
            conn.commit()
            db.close_db_connection(conn)
            src.email.service.send_verification_code_email(user_email, verification_code)
            return utils.ResultDTO(code=200, message=f"{user_email}으로 인증 코드가 전송되었습니다.", result=True)
        # 만약 created_at이 1분이 지나지 않았다면, 인증 코드를 재전송하지 않고 실패 처리
        else:
            created_at_datetime = utils.str_to_datetime(created_at)
            now = utils.get_current_datetime()
            diff_datetime = created_at_datetime + utils.timedelta(minutes=1) - now
            total_seconds = max(0, int(diff_datetime.total_seconds()))
            diff_str = f"{total_seconds // 60}:{total_seconds % 60:02d}"

            db.close_db_connection(conn)
            return utils.ResultDTO(code=400, message=f"잠시 후 다시 시도하세요. (남은 시간: {diff_str})", result=False)

    # 만약 이메일이 존재하지 않는다면, 새로운 레코드를 생성
    else:
        cursor.execute("INSERT INTO email_verification (email, verification_code) VALUES (?, ?)", (user_email, verification_code))
        conn.commit()
        db.close_db_connection(conn)
        src.email.service.send_verification_code_email(user_email, verification_code)
        return utils.ResultDTO(code=200, message=f"{user_email}으로 인증 코드가 전송되었습니다.", result=True)

# 이메일 인증코드 확인
def verify_code(user_email: str, verification_code: str) -> utils.ResultDTO:
    if not utils.is_valid_email(user_email):
        return utils.ResultDTO(code=400, message="이메일 형식이 올바르지 않습니다.", result=False)
    if not verification_code:
        return utils.ResultDTO(code=400, message="인증코드가 필요합니다.", result=False)
    
    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT verification_code, is_verified, try_count, created_at FROM email_verification WHERE email = ?", (user_email,))
    row = cursor.fetchone()

    if row:
        stored_code, is_verified, try_count, created_at = row

        # 이미 인증된 이메일이면 실패 처리
        if is_verified:
            db.close_db_connection(conn)
            return utils.ResultDTO(code=400, message="이미 인증된 이메일입니다.", result=False)
        # try_count 증가 updated_at 갱신
        cursor.execute("UPDATE email_verification SET try_count = try_count + 1, updated_at = (datetime('now', '+9 hours')) WHERE email = ?", (user_email,))
        conn.commit()
        # created_at이 3분이 지나면 실패 처리
        if utils.is_minutes_passed(created_at, 3):
            db.close_db_connection(conn)
            return utils.ResultDTO(code=400, message="인증 코드가 만료되었습니다. 재발송 후 다시 시도하세요.", result=False)
        # try_count가 5 이상이면 실패 처리
        if try_count >= 5:
            db.close_db_connection(conn)
            return utils.ResultDTO(code=429, message="재발송 후 다시 시도하세요.", result=False)

        # 인증 코드가 일치하지 않으면 실패 처리
        if not is_verified and stored_code == verification_code:
            cursor.execute("UPDATE email_verification SET is_verified = 1 WHERE email = ?", (user_email,))
            conn.commit()
            db.close_db_connection(conn)
            return utils.ResultDTO(code=200, message="이메일 인증이 완료되었습니다.", result=True)
        else:
            db.close_db_connection(conn)
            return utils.ResultDTO(code=400, message="인증 코드가 일치하지 않습니다.", result=False)

    db.close_db_connection(conn)
    return utils.ResultDTO(code=404, message="올바르지 않은 이메일입니다.", result=False)

def get_find_password_link_info(link_hash: str) -> utils.ResultDTO:
    if not link_hash:
        return utils.ResultDTO(code=400, message="해쉬 정보가 필요합니다.", result=False)

    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM user_password_find_link WHERE link_hash = ?", (link_hash,))
    row = cursor.fetchone()

    if not row:
        db.close_db_connection(conn)
        return utils.ResultDTO(code=404, message="해당 링크 정보를 찾을 수 없습니다.", result=False)

    # create_at이 3분이 지난 is_used가 False이고 is_active가 True인 경우 is_active를 False로 변경
    if utils.is_minutes_passed(row['created_at'], 3) and row['is_active']:
        cursor.execute("UPDATE user_password_find_link SET is_active = 0 WHERE link_hash = ?", (link_hash,))
        conn.commit()

    deactive_info = {
        'email': row['email'],
        'link_hash': row['link_hash'],
        'is_used': row['is_used'],
        'is_active': row['is_active'],
        'created_at': row['created_at']
    }

    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="링크 정보 조회 성공", data={'pw_find_info': deactive_info}, result=True)

def find_password(user_email: str) -> utils.ResultDTO:
    if not utils.is_valid_email(user_email):
        return utils.ResultDTO(code=400, message="이메일 형식이 올바르지 않습니다.", result=False)
    
    user_info = get_info_by_email(user_email)
    if not user_info.result:
        return user_info
    
    # db 생성. user_password_find_link에 이미 is_used가 False인 link_hash가 있다면, 해당 컬럼의 created_at이 3분이 지났을 경우 재설정 가능
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    # 기존 사용되지 않은 링크가 있는지 확인 (3분 이내 생성된 것만)
    cursor.execute("SELECT created_at FROM user_password_find_link WHERE email = ? AND is_used = 0 AND created_at > datetime('now', '-3 minute', '+9 hours')", (user_email,))
    row = cursor.fetchone()
    
    if row:
        created_at = row[0]
        # 3분이 지나지 않았다면 기존 링크 사용
        if not utils.is_minutes_passed(created_at, 3):
            created_at_datetime = utils.str_to_datetime(created_at)
            now = utils.get_current_datetime()
            diff_datetime = created_at_datetime + utils.timedelta(minutes=3) - now
            total_seconds = max(0, int(diff_datetime.total_seconds()))
            diff_str = f"{total_seconds // 60}:{total_seconds % 60:02d}"
            
            db.close_db_connection(conn)
            return utils.ResultDTO(code=400, message=f"잠시 후 다시 시도하세요. (남은 시간: {diff_str})", result=False)
        else:
            # 3분이 지났다면 기존 링크를 비활성화
            cursor.execute("UPDATE user_password_find_link SET is_active = 0, update_at = CURRENT_TIMESTAMP WHERE email = ? AND is_used = 0", (user_email,))
    
    # 새로운 링크 생성
    link_hash = utils.gen_hash(64)
    cursor.execute("INSERT INTO user_password_find_link (email, link_hash) VALUES (?, ?)", (user_email, link_hash))
    conn.commit()
    db.close_db_connection(conn)

    src.email.service.send_password_find_email(user_email, user_info, link_hash)
    return utils.ResultDTO(code=200, message="비밀번호 찾기 이메일이 전송되었습니다.", result=True)

def change_password(link_hash: str, new_password: str) -> utils.ResultDTO:
    if not link_hash:
        return utils.ResultDTO(code=400, message="해쉬 정보가 필요합니다.", result=False)
    if not new_password:
        return utils.ResultDTO(code=400, message="새로운 비밀번호가 필요합니다.", result=False)

    link_info = get_find_password_link_info(link_hash)
    if not link_info.result:
        return link_info

    user_email = link_info.data['pw_find_info']['email']

    # 비밀번호 변경
    salt = utils.gen_hash(16)
    hashed_password = utils.str_to_hash(new_password + salt)

    conn = db.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET password = ?, salt = ? WHERE email = ?", (hashed_password, salt, user_email))
        # 링크 사용 처리
        cursor.execute("UPDATE user_password_find_link SET is_used = 1 WHERE link_hash = ?", (link_hash,))
        conn.commit()
    except Exception as e:
        conn.rollback()
        return utils.ResultDTO(code=500, message=f"비밀번호 변경 중 오류가 발생했습니다: {e}", result=False)
    finally:
        db.close_db_connection(conn)

    return utils.ResultDTO(code=200, message="비밀번호를 성공적으로 변경했습니다.", result=True)

def update_password(sid, password, change_password) -> utils.ResultDTO:
    if not sid:
        return utils.ResultDTO(code=400, message="SID가 필요합니다.", result=False)
    if not password:
        return utils.ResultDTO(code=400, message="현재 비밀번호가 필요합니다.", result=False)
    if not change_password:
        return utils.ResultDTO(code=400, message="새로운 비밀번호가 필요합니다.", result=False)
    if not utils.is_valid_password(change_password):
        return utils.ResultDTO(code=400, message="비밀번호 형식이 올바르지 않습니다. (영문, 숫자, 기호 8~256자)", result=False)
    
    session_info = db.session.get_info(sid)
    if not session_info.result:
        return session_info.to_response()
    if not session_info.data['session_info']['is_active']:
        return utils.ResultDTO(code=401, message="비활성화된 세션입니다.", result=False)
    
    uid = session_info.data['session_info']['uid']
    validate_info = validate_user_by_uid(uid, password)
    if not validate_info.result:
        return utils.ResultDTO(code=401, message="현재 비밀번호가 일치하지 않습니다.", result=False)

    salt = utils.gen_hash(16)
    hashed_password = utils.str_to_hash(change_password + salt)

    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE users SET password = ?, salt = ? WHERE uid = ?", (hashed_password, salt, uid))
    conn.commit()

    if cursor.rowcount == 0:
        db.close_db_connection(conn)
        return utils.ResultDTO(code=400, message="비밀번호 변경에 실패했습니다.", result=False)

    db.close_db_connection(conn)
    
    # logout all session
    db.session.deactivate_all_sessions(uid)
    
    return utils.ResultDTO(code=200, message="비밀번호가 성공적으로 변경되었습니다.", result=True)
    
def update_name(sid, change_name) -> utils.ResultDTO:
    if not sid:
        return utils.ResultDTO(code=400, message="SID가 필요합니다.", result=False)
    if not utils.is_valid_username(change_name):
        return utils.ResultDTO(code=400, message="올바르지 않은 이름입니다. (한글, 영어 1~20자)", result=False)
    
    session_info = db.session.get_info(sid)
    if not session_info.result:
        return session_info.to_response()
    if not session_info.data['session_info']['is_active']:
        return utils.ResultDTO(code=401, message="비활성화된 세션입니다.", result=False)

    uid = session_info.data['session_info']['uid']
    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE users SET name = ? WHERE uid = ?", (change_name, uid))
    conn.commit()

    if cursor.rowcount == 0:
        db.close_db_connection(conn)
        return utils.ResultDTO(code=400, message="이름 변경에 실패했습니다.", result=False)

    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="이름이 성공적으로 변경되었습니다.", result=True)

def update_profile_image(sid, profile_url) -> utils.ResultDTO:
    if not sid:
        return utils.ResultDTO(code=400, message="SID가 필요합니다.", result=False)
    if not profile_url:
        return utils.ResultDTO(code=400, message="프로필 이미지 URL이 필요합니다.", result=False)
    
    session_info = db.session.get_info(sid)
    if not session_info:
        return session_info.to_response()
    if not session_info.data['session_info']['is_active']:
        return utils.ResultDTO(code=401, message="비활성화된 세션입니다.", result=False)
    
    uid = session_info.data['session_info']['uid']
    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE users SET profile_url = ? WHERE uid = ?", (profile_url, uid))
    conn.commit()

    if cursor.rowcount == 0:
        db.close_db_connection(conn)
        return utils.ResultDTO(code=400, message="프로필 이미지 URL 변경에 실패했습니다.", result=False)

    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="프로필 이미지 URL이 성공적으로 변경되었습니다.", result=True)