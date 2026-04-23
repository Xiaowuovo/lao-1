import hashlib
import secrets
import pymysql
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

class AuthManager:
    """用户认证管理器"""
    
    def __init__(self, db_config: dict):
        self.db_config = db_config
        self.session_expire_hours = 24  # 会话有效期24小时
    
    def _get_connection(self):
        """获取数据库连接"""
        return pymysql.connect(**self.db_config)
    
    def _hash_password(self, password: str) -> str:
        """密码加密（使用MD5，实际应用建议用bcrypt）"""
        return hashlib.md5(password.encode('utf-8')).hexdigest()
    
    def _generate_session_token(self) -> str:
        """生成会话令牌"""
        return secrets.token_urlsafe(32)
    
    def validate_student_id(self, student_id: str) -> Tuple[bool, str]:
        """
        验证学号格式
        
        格式：202205570603
        - 前4位：年份（2020-2030）
        - 中间4位：学院代码
        - 后4位：班级代码+个人序号
        """
        if not student_id or len(student_id) != 12:
            return False, "学号长度必须为12位"
        
        if not student_id.isdigit():
            return False, "学号只能包含数字"
        
        year = student_id[:4]
        college_code = student_id[4:8]
        
        # 验证年份
        try:
            year_int = int(year)
            if year_int < 2015 or year_int > 2030:
                return False, "年份无效（应在2015-2030之间）"
        except:
            return False, "年份格式错误"
        
        # 验证学院代码是否存在
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT college_name FROM college_codes WHERE college_code = %s", (college_code,))
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if not result:
                return True, f"警告：学院代码 {college_code} 未在系统中登记，但允许继续"
        except Exception as e:
            return True, f"警告：无法验证学院代码: {str(e)}"
        
        return True, "验证通过"
    
    def register(self, student_id: str, username: str, real_name: str, 
                password: str, email: str, phone: str = '') -> Dict:
        """
        用户注册
        
        Returns:
            {
                'success': True/False,
                'message': '提示信息',
                'user_id': 用户ID（成功时）
            }
        """
        # 验证学号格式
        is_valid, msg = self.validate_student_id(student_id)
        if not is_valid:
            return {'success': False, 'message': msg}
        
        # 验证密码强度
        if len(password) < 6:
            return {'success': False, 'message': '密码长度至少6位'}
        
        # 验证用户名
        if not username or len(username) < 2:
            return {'success': False, 'message': '用户名长度至少2位'}
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 检查学号是否已存在
            cursor.execute("SELECT user_id FROM users WHERE student_id = %s", (student_id,))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return {'success': False, 'message': '该学号已注册'}
            
            # 检查用户名是否已存在
            cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                cursor.close()
                conn.close()
                return {'success': False, 'message': '该用户名已被使用'}
            
            # 解析学号
            grade = student_id[:4]
            college_code = student_id[4:8]
            class_code = student_id[8:12]
            
            # 加密密码
            password_hash = self._hash_password(password)
            
            # 插入用户
            cursor.execute("""
                INSERT INTO users 
                (student_id, username, real_name, password_hash, email, phone, 
                 college_code, class_code, grade, role, account_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'user', 'active')
            """, (student_id, username, real_name, password_hash, email, phone,
                  college_code, class_code, grade))
            
            user_id = cursor.lastrowid
            
            # 创建默认设置
            cursor.execute("""
                INSERT INTO user_settings 
                (user_id, reminder_advance_time, email_notification, web_notification, sound_notification)
                VALUES (%s, 30, FALSE, TRUE, TRUE)
            """, (user_id,))
            
            # 记录操作日志
            cursor.execute("""
                INSERT INTO user_activity_logs (user_id, action_type, action_detail)
                VALUES (%s, 'register', %s)
            """, (user_id, f'新用户注册，学号: {student_id}'))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {
                'success': True,
                'message': '注册成功',
                'user_id': user_id
            }
        
        except Exception as e:
            return {
                'success': False,
                'message': f'注册失败: {str(e)}'
            }
    
    def login(self, student_id: str, password: str, ip_address: str = '', 
             user_agent: str = '') -> Dict:
        """
        用户登录
        
        Returns:
            {
                'success': True/False,
                'message': '提示信息',
                'session_token': '会话令牌',
                'user_info': {...}  # 用户信息
            }
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # 查询用户
            cursor.execute("""
                SELECT 
                    u.user_id, u.student_id, u.username, u.real_name, u.email, u.phone,
                    u.college_code, u.class_code, u.grade, u.role, u.account_status,
                    u.password_hash, c.college_name, c.college_short_name
                FROM users u
                LEFT JOIN college_codes c ON u.college_code = c.college_code
                WHERE u.student_id = %s
            """, (student_id,))
            
            user = cursor.fetchone()
            
            if not user:
                cursor.close()
                conn.close()
                return {'success': False, 'message': '学号或密码错误'}
            
            # 检查账户状态
            if user['account_status'] != 'active':
                cursor.close()
                conn.close()
                return {'success': False, 'message': '账户已被锁定或停用'}
            
            # 验证密码
            password_hash = self._hash_password(password)
            if user['password_hash'] != password_hash:
                cursor.close()
                conn.close()
                return {'success': False, 'message': '学号或密码错误'}
            
            # 生成会话令牌
            session_token = self._generate_session_token()
            expire_time = datetime.now() + timedelta(hours=self.session_expire_hours)
            
            # 保存会话
            cursor.execute("""
                INSERT INTO user_sessions 
                (user_id, session_token, ip_address, user_agent, expire_time)
                VALUES (%s, %s, %s, %s, %s)
            """, (user['user_id'], session_token, ip_address, user_agent, expire_time))
            
            # 更新登录信息
            cursor.execute("""
                UPDATE users 
                SET last_login_time = NOW(), login_count = login_count + 1
                WHERE user_id = %s
            """, (user['user_id'],))
            
            # 记录登录日志
            cursor.execute("""
                INSERT INTO user_activity_logs (user_id, action_type, action_detail, ip_address)
                VALUES (%s, 'login', %s, %s)
            """, (user['user_id'], f'用户登录，IP: {ip_address}', ip_address))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            # 移除敏感信息
            del user['password_hash']
            
            return {
                'success': True,
                'message': '登录成功',
                'session_token': session_token,
                'user_info': user
            }
        
        except Exception as e:
            return {
                'success': False,
                'message': f'登录失败: {str(e)}'
            }
    
    def verify_session(self, session_token: str) -> Tuple[bool, Optional[Dict]]:
        """
        验证会话令牌
        
        Returns:
            (是否有效, 用户信息)
        """
        if not session_token:
            return False, None
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # 查询会话
            cursor.execute("""
                SELECT 
                    s.session_id, s.user_id, s.expire_time,
                    u.student_id, u.username, u.real_name, u.email, u.role, u.account_status,
                    u.college_code, c.college_name
                FROM user_sessions s
                JOIN users u ON s.user_id = u.user_id
                LEFT JOIN college_codes c ON u.college_code = c.college_code
                WHERE s.session_token = %s AND s.is_active = TRUE
            """, (session_token,))
            
            session = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            if not session:
                return False, None
            
            # 检查是否过期
            if session['expire_time'] < datetime.now():
                self.logout(session_token)
                return False, None
            
            # 检查账户状态
            if session['account_status'] != 'active':
                return False, None
            
            return True, {
                'user_id': session['user_id'],
                'student_id': session['student_id'],
                'username': session['username'],
                'real_name': session['real_name'],
                'email': session['email'],
                'role': session['role'],
                'college_code': session['college_code'],
                'college_name': session['college_name']
            }
        
        except Exception as e:
            print(f"验证会话失败: {e}")
            return False, None
    
    def logout(self, session_token: str) -> bool:
        """用户登出"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 获取用户ID
            cursor.execute("SELECT user_id FROM user_sessions WHERE session_token = %s", (session_token,))
            result = cursor.fetchone()
            
            # 使会话失效
            cursor.execute("""
                UPDATE user_sessions 
                SET is_active = FALSE
                WHERE session_token = %s
            """, (session_token,))
            
            # 记录登出日志
            if result:
                user_id = result[0]
                cursor.execute("""
                    INSERT INTO user_activity_logs (user_id, action_type, action_detail)
                    VALUES (%s, 'logout', '用户登出')
                """, (user_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return True
        
        except Exception as e:
            print(f"登出失败: {e}")
            return False
    
    def change_password(self, user_id: int, old_password: str, new_password: str) -> Dict:
        """修改密码"""
        if len(new_password) < 6:
            return {'success': False, 'message': '新密码长度至少6位'}
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 验证旧密码
            old_hash = self._hash_password(old_password)
            cursor.execute("SELECT user_id FROM users WHERE user_id = %s AND password_hash = %s",
                         (user_id, old_hash))
            
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                return {'success': False, 'message': '原密码错误'}
            
            # 更新密码
            new_hash = self._hash_password(new_password)
            cursor.execute("""
                UPDATE users 
                SET password_hash = %s
                WHERE user_id = %s
            """, (new_hash, user_id))
            
            # 使所有会话失效
            cursor.execute("""
                UPDATE user_sessions 
                SET is_active = FALSE
                WHERE user_id = %s
            """, (user_id,))
            
            # 记录日志
            cursor.execute("""
                INSERT INTO user_activity_logs (user_id, action_type, action_detail)
                VALUES (%s, 'change_password', '用户修改密码')
            """, (user_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {'success': True, 'message': '密码修改成功，请重新登录'}
        
        except Exception as e:
            return {'success': False, 'message': f'修改失败: {str(e)}'}
    
    def get_user_profile(self, user_id: int) -> Optional[Dict]:
        """获取用户资料"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            cursor.execute("""
                SELECT 
                    u.user_id, u.student_id, u.username, u.real_name, u.email, u.phone,
                    u.college_code, c.college_name, c.college_short_name,
                    u.class_code, u.grade, u.role, u.account_status,
                    u.last_login_time, u.login_count, u.created_at
                FROM users u
                LEFT JOIN college_codes c ON u.college_code = c.college_code
                WHERE u.user_id = %s
            """, (user_id,))
            
            user = cursor.fetchone()
            
            cursor.close()
            conn.close()
            
            return user
        
        except Exception as e:
            print(f"获取用户资料失败: {e}")
            return None
    
    def update_profile(self, user_id: int, updates: Dict) -> Dict:
        """更新用户资料"""
        allowed_fields = ['real_name', 'email', 'phone']
        
        # 过滤允许更新的字段
        update_data = {k: v for k, v in updates.items() if k in allowed_fields}
        
        if not update_data:
            return {'success': False, 'message': '没有可更新的字段'}
        
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 构建更新SQL
            set_clause = ', '.join([f"{k} = %s" for k in update_data.keys()])
            values = list(update_data.values()) + [user_id]
            
            cursor.execute(f"""
                UPDATE users 
                SET {set_clause}
                WHERE user_id = %s
            """, values)
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return {'success': True, 'message': '资料更新成功'}
        
        except Exception as e:
            return {'success': False, 'message': f'更新失败: {str(e)}'}
