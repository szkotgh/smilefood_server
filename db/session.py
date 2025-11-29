import sqlite3
import db
import db.user
import src.utils as utils
import src.email

def get_session_list(sid: str) -> utils.ResultDTO:
    # 세션 ID가 유효한지 확인
    session_info = get_info(sid)
    if not session_info.result:
        return utils.ResultDTO(code=404, message="유효하지 않은 세션 ID입니다.", result=False)
    # 세션이 비활성화된 경우 실패 처리
    session_info = session_info.data['session_info']
    if not session_info['is_active']:
        return utils.ResultDTO(code=401, message="비활성화된 세션입니다.", result=False)

    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM user_sessions WHERE uid = ? ORDER BY created_at DESC", (session_info['uid'],))
    rows = cursor.fetchall()

    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="세션 목록을 성공적으로 조회했습니다.", data={"sessions_info" : [dict(row) for row in rows]}, result=True)

def deactivate_session(sid: str) -> utils.ResultDTO:
    # 세션 ID가 유효한지 확인
    session_info = get_info(sid)
    if not session_info.result:
        return utils.ResultDTO(code=404, message="유효하지 않은 세션 ID입니다.", result=False)
    # 이미 세션이 비활성화된 경우 실패 처리
    session_info = session_info.data['session_info']
    if not session_info['is_active']:
        return utils.ResultDTO(code=400, message="이미 비활성화(로그아웃)된 세션입니다.", result=False)

    # 세션 비활성화
    conn = db.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE user_sessions SET is_active = 0 WHERE sid = ?", (sid,))
        conn.commit()
        
        return utils.ResultDTO(code=200, message="로그아웃 되었습니다.", result=True)
    except sqlite3.Error as e:
        return utils.ResultDTO(code=500, message=f"로그아웃에 실패했습니다: {e}", result=False)
    finally:
        db.close_db_connection(conn)

def create_session(email: str, password: str, user_agent: str, ip_address: str) -> utils.ResultDTO:
    if not utils.is_valid_email(email):
        return utils.ResultDTO(code=400, message="유효하지 않은 이메일 형식입니다.", result=False)
    if not password:
        return utils.ResultDTO(code=400, message="비밀번호를 입력해주세요.", result=False)

    # 사용자 검증
    uid = db.user.validate_user(email, password)
    if not uid.result:
        return utils.ResultDTO(code=401, message="이메일 또는 비밀번호를 확인하십시오.", result=False)

    conn = db.get_db_connection()
    cursor = conn.cursor()

    sid = utils.gen_hash(16)
    expires_at = utils.get_future_timestamp(days=31)  # 31일 뒤 세션 만료

    try:
        # 세션 생성
        cursor.execute("INSERT INTO user_sessions (sid, uid, user_agent, ip_address, expires_at) VALUES (?, ?, ?, ?, ?)",
                       (sid, uid.data['uid'], user_agent, ip_address, expires_at))
        conn.commit()
        
        # 최신 날짜 순으로 1개 세션만 유지. 나머지는 is_activate를 0으로 설정
        cursor.execute("UPDATE user_sessions SET is_active = 0 WHERE uid = ? AND sid NOT IN (SELECT sid FROM user_sessions WHERE uid = ? ORDER BY created_at DESC LIMIT 1)", (uid.data['uid'], uid.data['uid']))
        conn.commit()
        
        # 세션 비활성화 링크 이메일 첨부
        link_hash = utils.gen_hash(64)
        cursor.execute("INSERT INTO user_session_deactive_link (sid, link_hash) VALUES (?, ?)", (sid, link_hash))
        conn.commit()
        
        # 이메일 알림
        src.email.service.send_session_created_email(email, sid, link_hash)
        
        return utils.ResultDTO(code=200, message="성공적으로 로그인하였습니다.", data={'sid': sid}, result=True)
    except sqlite3.IntegrityError:
        return utils.ResultDTO(code=409, message="세션이 이미 존재합니다.", result=False)
    finally:
        db.close_db_connection(conn)
        
def get_info(sid: str) -> utils.ResultDTO:
    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM user_sessions WHERE sid = ?", (sid,))
    row = cursor.fetchone()

    # 없는 세션 ID인 경우 실패 처리
    if not row:
        db.close_db_connection(conn)
        return utils.ResultDTO(code=401, message="유효하지 않은 세션 ID입니다.", result=False)

    # 현재 시간이 expires_at을 초과한 경우 실패 처리(is_active도 0으로 설정)
    if utils.get_current_datetime() > utils.str_to_datetime(row['expires_at']):
        cursor.execute("UPDATE user_sessions SET is_active = 0 WHERE sid = ?", (sid,))
        db.close_db_connection(conn)
        return utils.ResultDTO(code=401, message="세션이 만료되었습니다.", result=False)

    session_info = {
        'sid': row['sid'],
        'uid': row['uid'],
        'user_agent': row['user_agent'],
        'ip_address': row['ip_address'],
        'is_active': row['is_active'],
        'last_accessed': row['last_accessed'],
        'expires_at': row['expires_at'],
        'created_at': row['created_at']
    }

    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="세션을 성공적으로 조회했습니다.", data={'session_info': session_info}, result=True)

def deactivate_all_sessions(uid: int) -> utils.ResultDTO:
    # 사용자 존재 여부 확인
    user_info = db.user.get_info(uid)
    if not user_info.result:
        return utils.ResultDTO(code=404, message="존재하지 않는 사용자입니다.", result=False)

    conn = db.get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("UPDATE user_sessions SET is_active = 0 WHERE uid = ?", (uid,))
        conn.commit()

        return utils.ResultDTO(code=200, message="모든 세션이 성공적으로 비활성화되었습니다.", result=True)
    except sqlite3.Error as e:
        return utils.ResultDTO(code=500, message=f"세션 비활성화에 실패했습니다: {e}", result=False)
    finally:
        db.close_db_connection(conn)

def get_session_deactive_info(link_hash: str) -> utils.ResultDTO:
    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM user_session_deactive_link WHERE link_hash = ?", (link_hash,))
    row = cursor.fetchone()

    # 없는 링크 해시인 경우 실패 처리
    if not row:
        db.close_db_connection(conn)
        return utils.ResultDTO(code=404, message="유효하지 않은 링크 해시입니다.", result=False)

    deactive_info = {
        'sid': row['sid'],
        'link_hash': row['link_hash'],
        'is_used': row['is_used'],
        'update_at': row['update_at'],
        'created_at': row['created_at']
    }

    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="세션 비활성화 링크 정보를 성공적으로 조회했습니다.", data={'deactive_info': deactive_info}, result=True)

def mark_deactive_link_as_used(link_hash: str) -> utils.ResultDTO:
    conn = db.get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("UPDATE user_session_deactive_link SET is_used = 1, update_at = CURRENT_TIMESTAMP WHERE link_hash = ?", (link_hash,))
        conn.commit()

        if cursor.rowcount == 0:
            return utils.ResultDTO(code=404, message="해당 링크 해시가 존재하지 않습니다.", result=False)

        return utils.ResultDTO(code=200, message="링크가 성공적으로 사용 처리되었습니다.", result=True)
    except sqlite3.Error as e:
        return utils.ResultDTO(code=500, message=f"링크 사용 처리에 실패했습니다: {e}", result=False)
    finally:
        db.close_db_connection(conn)