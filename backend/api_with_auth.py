from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pymysql
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
from functools import wraps
import os
import sys
import json
from dotenv import load_dotenv

# 设置输出编码为UTF-8（解决Windows控制台编码问题）
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 加载环境变量
load_dotenv()

from auth import AuthManager
from event_enhanced import EnhancedEventExtractor
from location_matcher import LocationMatcher
from conflict_detector import ConflictDetector, ScheduleManager
from file_processor import FileProcessor, BatchTextSplitter
from xtu_event_extractor import get_extractor as get_xtu_extractor
from xtu_location_mapper import get_location_mapper
from file_processor_enhanced import get_file_processor
from email_sender import EmailSender

app = Flask(__name__)
CORS(app, supports_credentials=True)

# 配置
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'jpg', 'jpeg', 'png', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'campus_reminder_system'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# 初始化组件
auth_manager = AuthManager(DB_CONFIG)
extractor = EnhancedEventExtractor()
location_matcher = LocationMatcher(DB_CONFIG)
conflict_detector = ConflictDetector(DB_CONFIG)
schedule_manager = ScheduleManager(DB_CONFIG)
file_processor = FileProcessor(DB_CONFIG, UPLOAD_FOLDER)
email_sender = EmailSender()

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ==================== 认证装饰器 ====================

def login_required(f):
    """需要登录的接口装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # OPTIONS请求直接放行（CORS预检）
        if request.method == 'OPTIONS':
            return '', 200
        
        # 从请求头或cookie获取token
        token = request.headers.get('Authorization')
        if not token and request.cookies.get('session_token'):
            token = request.cookies.get('session_token')
        
        if token and token.startswith('Bearer '):
            token = token[7:]
        
        if not token:
            return jsonify({'success': False, 'message': '未登录', 'require_login': True}), 401
        
        # 验证token
        is_valid, user_info = auth_manager.verify_session(token)
        if not is_valid:
            return jsonify({'success': False, 'message': '会话已过期，请重新登录', 'require_login': True}), 401
        
        # 将用户信息注入到request中
        request.current_user = user_info
        return f(*args, **kwargs)
    
    return decorated_function


# ==================== 用户认证接口 ====================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.json
        student_id = data.get('student_id', '')
        username = data.get('username', '')
        real_name = data.get('real_name', '')
        password = data.get('password', '')
        email = data.get('email', '')
        phone = data.get('phone', '')
        
        result = auth_manager.register(student_id, username, real_name, password, email, phone)
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'注册失败: {str(e)}'}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.json
        student_id = data.get('student_id', '')
        password = data.get('password', '')
        
        # 获取客户端信息
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent', '')
        
        result = auth_manager.login(student_id, password, ip_address, user_agent)
        
        if result['success']:
            # 设置cookie
            response = jsonify(result)
            response.set_cookie('session_token', result['session_token'], 
                              max_age=24*3600, httponly=True, samesite='Lax')
            return response
        else:
            return jsonify(result), 401
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'登录失败: {str(e)}'}), 500


@app.route('/api/auth/logout', methods=['POST'])
@login_required
def logout():
    """用户登出"""
    try:
        token = request.headers.get('Authorization', '').replace('Bearer ', '')
        if not token:
            token = request.cookies.get('session_token')
        
        auth_manager.logout(token)
        
        response = jsonify({'success': True, 'message': '登出成功'})
        response.set_cookie('session_token', '', expires=0)
        return response
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'登出失败: {str(e)}'}), 500


@app.route('/api/auth/profile', methods=['GET'])
@login_required
def get_profile():
    """获取用户资料"""
    try:
        user_id = request.current_user['user_id']
        profile = auth_manager.get_user_profile(user_id)
        
        if profile:
            return jsonify({'success': True, 'profile': profile})
        else:
            return jsonify({'success': False, 'message': '获取失败'}), 404
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'}), 500


@app.route('/api/auth/profile', methods=['PUT'])
@login_required
def update_profile():
    """更新用户资料"""
    try:
        user_id = request.current_user['user_id']
        updates = request.json
        
        result = auth_manager.update_profile(user_id, updates)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'}), 500


@app.route('/api/auth/changePassword', methods=['POST'])
@login_required
def change_password():
    """修改密码"""
    try:
        user_id = request.current_user['user_id']
        data = request.json
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')
        
        result = auth_manager.change_password(user_id, old_password, new_password)
        return jsonify(result)
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'修改失败: {str(e)}'}), 500


@app.route('/api/auth/validateStudentId', methods=['POST'])
def validate_student_id():
    """验证学号格式"""
    try:
        data = request.json
        student_id = data.get('student_id', '')
        
        is_valid, message = auth_manager.validate_student_id(student_id)
        
        return jsonify({
            'success': True,
            'valid': is_valid,
            'message': message
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'验证失败: {str(e)}'}), 500


# ==================== 事件提取接口（需要登录） ====================

@app.route('/api/extractEventsEnhanced', methods=['POST'])
@login_required
def extract_events_enhanced():
    """增强版事件提取（需要登录）"""
    try:
        data = request.json
        text = data.get('text', '')
        user_id = request.current_user['user_id']
        auto_confirm = data.get('auto_confirm', False)
        
        if not text.strip():
            return jsonify({'success': False, 'message': '文本内容不能为空'}), 400
        
        text_parts = BatchTextSplitter.split_multiple_events(text)
        all_events = []
        
        for part in text_parts:
            events = extractor.extract_events(part)
            all_events.extend(events)
        
        if not all_events:
            return jsonify({
                'success': False,
                'message': '未识别到有效事件',
                'events': []
            })
        
        for event in all_events:
            location_result = location_matcher.match_location(event['location'])
            event['location_match'] = location_result
            if location_result['matched']:
                event['standard_location'] = location_result['standard_name']
        
        if not auto_confirm:
            return jsonify({
                'success': True,
                'message': f'成功提取 {len(all_events)} 个事件，请确认',
                'events': all_events,
                'needs_confirmation': True
            })
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        event_ids = []
        for event in all_events:
            cursor.execute("""
                INSERT INTO text_events 
                (user_id, original_text, event_title, event_time, deadline_time,
                 event_location, standard_location, event_target, target_audience,
                 organizer, event_type, activity_type, task_category, contact_info,
                 is_recurring, recurring_pattern, extraction_confidence, is_confirmed,
                 missing_fields)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id, event['original_text'], event['title'], event['time'],
                event.get('deadline_time'), event['location'], 
                event.get('standard_location', event['location']),
                event['target'], event['target_audience'], event['organizer'],
                'other', event['activity_type'], event['task_category'],
                json.dumps(event['contact_info']), event['is_recurring'],
                event['recurring_pattern'], event['confidence'], False,
                json.dumps(event['missing_fields'])
            ))
            event_ids.append(cursor.lastrowid)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        for i, event in enumerate(all_events):
            event['event_id'] = event_ids[i]
        
        return jsonify({
            'success': True,
            'message': f'成功提取并保存 {len(all_events)} 个事件',
            'events': all_events
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'提取失败: {str(e)}'}), 500


@app.route('/api/confirmEvents', methods=['POST'])
@login_required
def confirm_events():
    """用户确认事件并保存"""
    try:
        data = request.json
        events = data.get('events', [])
        user_id = request.current_user['user_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        saved_events = []
        for event in events:
            cursor.execute("""
                INSERT INTO text_events 
                (user_id, original_text, event_title, event_time, deadline_time,
                 event_location, standard_location, event_target, target_audience,
                 organizer, event_type, activity_type, task_category, contact_info,
                 is_recurring, recurring_pattern, extraction_confidence, is_confirmed)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
            """, (
                user_id, event.get('original_text', ''), event['title'], 
                event['time'], event.get('deadline_time'),
                event.get('location', '待确认'), 
                event.get('standard_location', event.get('location', '待确认')),
                event.get('target', '相关人员'), event.get('target_audience', '相关人员'),
                event.get('organizer', '待确认'), 'other',
                event.get('activity_type', 'other'), event.get('task_category', 'custom'),
                json.dumps(event.get('contact_info', {})), 
                event.get('is_recurring', False),
                event.get('recurring_pattern'), event.get('confidence', 0.7)
            ))
            event_id = cursor.lastrowid
            saved_events.append({'event_id': event_id, 'title': event['title']})
            event_time = event['time']
            if isinstance(event_time,str):
                from dateutil import parser
                try:
                    event_time = parser.parser(event_time)
                except:
                    event_time = datetime.now() + timedelta(hours=1)
            reminder_time = event_time - timedelta(minutes=30)

            cursor.execute("""
                INSERT INTO reminder_tasks 
                (event_id, user_id, reminder_time, advance_minutes, reminder_method)
                VALUES (%s, %s, %s, %s, %s)
            """, (event_id, user_id, reminder_time, 30, 'web'))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'成功保存 {len(saved_events)} 个事件',
            'events': saved_events
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'保存失败: {str(e)}'}), 500


# ==================== 提醒管理接口（需要登录） ====================

@app.route('/api/createReminderEnhanced', methods=['POST'])
@login_required
def create_reminder_enhanced():
    """创建提醒（需要登录）"""
    try:
        data = request.json
        event_id = data.get('event_id')
        user_id = request.current_user['user_id']
        advance_minutes = data.get('advance_minutes', 30)
        reminder_levels = data.get('reminder_levels', [60, 180, 1440])
        check_conflict = data.get('check_conflict', True)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM text_events WHERE event_id = %s AND user_id = %s", 
                      (event_id, user_id))
        event = cursor.fetchone()
        
        if not event:
            return jsonify({'success': False, 'message': '事件不存在或无权限'}), 404
        
        event_time = event['event_time']
        
        conflict_info = {'has_conflict': False}
        if check_conflict:
            conflict_info = conflict_detector.check_conflicts(
                user_id, event_time, 120, event_id
            )
            
            if conflict_info['has_conflict']:
                cursor.execute("""
                    UPDATE text_events 
                    SET has_conflict = TRUE, conflict_level = %s
                    WHERE event_id = %s
                """, (conflict_info['conflict_level'], event_id))
                conn.commit()
        
        reminder_time = event_time - timedelta(minutes=advance_minutes)
        
        cursor.execute("SELECT * FROM user_settings WHERE user_id = %s", (user_id,))
        settings = cursor.fetchone()
        
        reminder_methods = []
        if settings:
            if settings['web_notification']:
                reminder_methods.append('web')
            if settings['email_notification']:
                reminder_methods.append('email')
        else:
            reminder_methods = ['web']
        
        reminder_method = ','.join(reminder_methods) if reminder_methods else 'web'
        
        cursor.execute("""
            INSERT INTO reminder_tasks 
            (event_id, user_id, reminder_time, advance_minutes, reminder_method, reminder_levels)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (event_id, user_id, reminder_time, advance_minutes, reminder_method, 
              json.dumps(reminder_levels)))
        
        reminder_id = cursor.lastrowid
        
        if event['deadline_time']:
            deadline_reminder_time = event['deadline_time'] - timedelta(hours=24)
            cursor.execute("""
                INSERT INTO reminder_tasks 
                (event_id, user_id, reminder_time, advance_minutes, reminder_method, 
                 is_deadline_reminder)
                VALUES (%s, %s, %s, %s, %s, TRUE)
            """, (event_id, user_id, deadline_reminder_time, 1440, reminder_method))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '提醒创建成功',
            'reminder_id': reminder_id,
            'conflict_info': conflict_info
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'创建失败: {str(e)}'}), 500


@app.route('/api/getReminders', methods=['GET'])
@login_required
def get_reminders():
    """获取用户的提醒列表（与日历同源，基于 text_events）"""
    try:
        user_id = request.current_user['user_id']
        status = request.args.get('status', 'all')
        time_range = request.args.get('time_range', 'all')

        conn = get_db_connection()
        cursor = conn.cursor()

        # 以 text_events 为主表，LEFT JOIN reminder_tasks 获取提醒状态
        query = """
            SELECT
                te.event_id,
                te.event_title,
                te.event_time,
                te.event_location,
                te.target_audience AS event_target,
                te.activity_type,
                te.has_conflict,
                te.organizer,
                te.contact_info,
                rt.task_id,
                rt.reminder_time,
                rt.advance_minutes,
                COALESCE(rt.status, 'pending') AS status
            FROM text_events te
            LEFT JOIN reminder_tasks rt ON rt.event_id = te.event_id AND rt.user_id = te.user_id
            WHERE te.user_id = %s AND te.is_confirmed = TRUE
        """
        params = [user_id]

        if status != 'all':
            query += " AND COALESCE(rt.status, 'pending') = %s"
            params.append(status)

        if time_range == 'week':
            query += " AND te.event_time BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 7 DAY)"
        elif time_range == 'month':
            query += " AND te.event_time BETWEEN NOW() AND DATE_ADD(NOW(), INTERVAL 30 DAY)"

        query += " ORDER BY te.event_time ASC"

        cursor.execute(query, params)
        reminders = cursor.fetchall()

        for reminder in reminders:
            if reminder['event_time']:
                t = reminder['event_time']
                reminder['event_time'] = t.strftime('%Y-%m-%d %H:%M') if hasattr(t, 'strftime') else str(t)
            if reminder['reminder_time']:
                t = reminder['reminder_time']
                reminder['reminder_time'] = t.strftime('%Y-%m-%d %H:%M') if hasattr(t, 'strftime') else str(t)

        cursor.close()
        conn.close()

        return jsonify({
            'success': True,
            'reminders': reminders
        })

    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'}), 500


# ==================== 文件上传接口（需要登录） ====================

@app.route('/api/uploadFile', methods=['POST'])
@login_required
def upload_file():
    """上传文件（需要登录）"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有文件'}), 400
        
        file = request.files['file']
        user_id = request.current_user['user_id']
        
        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            ext = filename.rsplit('.', 1)[1].lower()
            
            if ext in ['jpg', 'jpeg', 'png', 'gif']:
                result = file_processor.process_image(filepath, user_id)
            elif ext == 'pdf':
                result = file_processor.process_pdf(filepath, user_id)
            elif ext == 'docx':
                result = file_processor.process_word(filepath, user_id)
            else:
                result = {'success': False, 'error': '不支持的文件格式'}
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': '文件处理成功',
                    'text': result['text'],
                    'filename': filename,
                    'file_type': ext
                })
            else:
                return jsonify({
                    'success': False,
                    'message': result['error']
                }), 400
        
        return jsonify({'success': False, 'message': '不支持的文件类型'}), 400
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'上传失败: {str(e)}'}), 500


# ==================== 兼容旧API路由 ====================

@app.route('/api/extractEvents', methods=['POST', 'OPTIONS'])
@login_required
def extract_events():
    """事件提取（兼容旧路由）"""
    return extract_events_enhanced()


@app.route('/api/getSettings', methods=['GET'])
@login_required
def get_settings():
    """获取用户设置"""
    try:
        user_id = request.current_user['user_id']
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT reminder_advance_time, email_notification, web_notification, sound_notification
            FROM user_settings WHERE user_id = %s
        """, (user_id,))
        settings = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if settings:
            return jsonify({'success': True, 'data': settings})
        else:
            return jsonify({'success': True, 'data': {
                'reminder_advance_time': 30,
                'email_notification': False,
                'web_notification': True,
                'sound_notification': True
            }})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/saveSettings', methods=['POST'])
@login_required
def save_settings():
    """保存用户设置"""
    try:
        user_id = request.current_user['user_id']
        data = request.json
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_settings (user_id, reminder_advance_time, email_notification, web_notification, sound_notification)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
            reminder_advance_time = VALUES(reminder_advance_time),
            email_notification = VALUES(email_notification),
            web_notification = VALUES(web_notification),
            sound_notification = VALUES(sound_notification)
        """, (user_id, data.get('reminder_advance_time', 30), 
              data.get('email_notification', False),
              data.get('web_notification', True),
              data.get('sound_notification', True)))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': '设置已保存'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/getStatistics', methods=['GET'])
@login_required
def get_statistics():
    """获取用户统计数据"""
    try:
        user_id = request.current_user['user_id']
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 统计事件数量
        cursor.execute("""
            SELECT 
                COUNT(*) as total_events,
                SUM(CASE WHEN event_time >= NOW() THEN 1 ELSE 0 END) as upcoming_events,
                SUM(CASE WHEN event_time < NOW() THEN 1 ELSE 0 END) as past_events
            FROM text_events WHERE user_id = %s
        """, (user_id,))
        event_stats = cursor.fetchone()
        
        # 统计提醒数量
        cursor.execute("""
            SELECT 
                COUNT(*) as total_reminders,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_reminders,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_reminders
            FROM reminder_tasks WHERE user_id = %s
        """, (user_id,))
        reminder_stats = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total_events': event_stats['total_events'] or 0,
                'upcoming_events': event_stats['upcoming_events'] or 0,
                'past_events': event_stats['past_events'] or 0,
                'total_reminders': reminder_stats['total_reminders'] or 0,
                'pending_reminders': reminder_stats['pending_reminders'] or 0,
                'completed_reminders': reminder_stats['completed_reminders'] or 0
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/updateReminderStatus', methods=['POST'])
@login_required
def update_reminder_status():
    """更新提醒状态"""
    try:
        user_id = request.current_user['user_id']
        data = request.json
        task_id = data.get('task_id')
        status = data.get('status')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE reminder_tasks SET status = %s 
            WHERE task_id = %s AND user_id = %s
        """, (status, task_id, user_id))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': '状态已更新'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/deleteReminder', methods=['POST'])
@login_required
def delete_reminder():
    """删除提醒"""
    try:
        user_id = request.current_user['user_id']
        data = request.json
        task_id = data.get('task_id')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM reminder_tasks WHERE task_id = %s AND user_id = %s
        """, (task_id, user_id))
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': '提醒已删除'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/getEventsByMonth', methods=['POST'])
@login_required
def get_events_by_month():
    """按月获取事件"""
    try:
        user_id = request.current_user['user_id']
        data = request.json
        year = data.get('year')
        month = data.get('month')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取指定月份的所有事件
        cursor.execute("""
            SELECT event_id, event_title, event_time, event_location, standard_location,
                   organizer, activity_type, target_audience, contact_info,
                   has_conflict, is_confirmed
            FROM text_events
            WHERE user_id = %s
            AND YEAR(event_time) = %s
            AND MONTH(event_time) = %s
            ORDER BY event_time
        """, (user_id, year, month))
        
        events = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # 直接格式化时间（DB存的就是北京时间）
        for event in events:
            if event.get('event_time'):
                t = event['event_time']
                event['event_time'] = t.strftime('%Y-%m-%d %H:%M:%S') if hasattr(t, 'strftime') else str(t)
            event['has_conflict'] = False  # 默认重置，后续实时计算

        # 实时计算事件间冲突（同一天内时间差 < 120 分钟视为冲突）
        from datetime import datetime as _dt
        event_times = []
        for ev in events:
            try:
                et = _dt.strptime(ev['event_time'], '%Y-%m-%d %H:%M:%S') if ev.get('event_time') else None
            except Exception:
                et = None
            event_times.append(et)

        for i in range(len(events)):
            if event_times[i] is None:
                continue
            for j in range(len(events)):
                if i == j or event_times[j] is None:
                    continue
                diff = abs((event_times[i] - event_times[j]).total_seconds() / 60)
                if diff < 120:
                    events[i]['has_conflict'] = True
                    break

        return jsonify({
            'success': True,
            'events': events,
            'count': len(events)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== 课表管理接口 ====================

@app.route('/api/getSchedule', methods=['GET'])
@login_required
def get_schedule():
    """获取用户课表"""
    try:
        user_id = request.current_user['user_id']
        day_of_week = request.args.get('day_of_week')  # 1-7 对应周一到周日
        
        courses = schedule_manager.get_schedule(user_id, int(day_of_week) if day_of_week else None)
        
        return jsonify({
            'success': True,
            'data': courses
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/addCourse', methods=['POST'])
@login_required
def add_course():
    """添加课程"""
    try:
        user_id = request.current_user['user_id']
        data = request.json
        
        result = schedule_manager.add_course(
            user_id,
            course_name=data.get('course_name'),
            day_of_week=data.get('day_of_week'),
            start_time=data.get('start_time'),
            end_time=data.get('end_time'),
            location=data.get('location', ''),
            teacher=data.get('teacher', ''),
            weeks=data.get('weeks', ''),
            exam_type=data.get('exam_type', '')
        )
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/deleteCourse', methods=['POST'])
@login_required
def delete_course():
    """删除课程"""
    try:
        user_id = request.current_user['user_id']
        schedule_id = request.json.get('schedule_id')
        
        result = schedule_manager.delete_course(user_id, int(schedule_id) if schedule_id else None)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/importSchedule', methods=['POST'])
@login_required
def import_schedule():
    """批量导入课表"""
    try:
        user_id = request.current_user['user_id']
        courses = request.json.get('courses', [])
        
        result = schedule_manager.import_schedule(user_id, courses)
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== 历史归档接口 ====================

@app.route('/api/getArchive', methods=['GET'])
@login_required
def get_archive():
    """获取历史归档"""
    try:
        user_id = request.current_user['user_id']
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 20))
        event_type = request.args.get('event_type')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 构建查询条件
        conditions = ["user_id = %s"]
        params = [user_id]
        
        if event_type:
            conditions.append("completion_status = %s")
            params.append(event_type)
        
        if start_date:
            conditions.append("event_time >= %s")
            params.append(start_date)
        
        if end_date:
            conditions.append("event_time <= %s")
            params.append(end_date)
        
        where_clause = " AND ".join(conditions)
        
        # 查询总数
        cursor.execute(f"SELECT COUNT(*) as total FROM event_archive WHERE {where_clause}", params)
        total = cursor.fetchone()['total']
        
        # 分页查询
        offset = (page - 1) * page_size
        params.extend([page_size, offset])
        
        cursor.execute(f"""
            SELECT archive_id, event_id, event_title, event_time, event_location,
                   completion_status, completion_time, created_at
            FROM event_archive 
            WHERE {where_clause}
            ORDER BY event_time DESC
            LIMIT %s OFFSET %s
        """, params)
        
        events = cursor.fetchall()
        
        for event in events:
            if event['event_time']:
                t = event['event_time']
                event['event_time'] = t.strftime('%Y-%m-%d %H:%M') if hasattr(t, 'strftime') else str(t)
            if event['completion_time']:
                t = event['completion_time']
                event['completion_time'] = t.strftime('%Y-%m-%d %H:%M') if hasattr(t, 'strftime') else str(t)
            if event['created_at']:
                t = event['created_at']
                event['created_at'] = t.strftime('%Y-%m-%d %H:%M') if hasattr(t, 'strftime') else str(t)
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'events': events,
                'total': total,
                'page': page,
                'page_size': page_size
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/searchArchive', methods=['GET'])
@login_required
def search_archive():
    """搜索历史归档"""
    try:
        user_id = request.current_user['user_id']
        keyword = request.args.get('keyword', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT archive_id, event_id, event_title, event_time, event_location,
                   completion_status, completion_time, created_at
            FROM event_archive 
            WHERE user_id = %s 
            AND (event_title LIKE %s OR event_location LIKE %s)
            ORDER BY event_time DESC
            LIMIT 100
        """, (user_id, f'%{keyword}%', f'%{keyword}%'))
        
        events = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': events
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/exportArchive', methods=['GET'])
@login_required
def export_archive():
    """导出历史归档为CSV"""
    try:
        user_id = request.current_user['user_id']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT event_title, event_time, event_location,
                   completion_status, completion_time, created_at
            FROM event_archive 
            WHERE user_id = %s
            ORDER BY event_time DESC
        """, (user_id,))
        
        events = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # 生成CSV内容
        import io
        import csv
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow(['事件标题', '事件时间', '地点', '完成状态', '完成时间', '创建时间'])
        
        # 写入数据
        for event in events:
            writer.writerow([
                event['event_title'],
                str(event['event_time']),
                event['event_location'] or '',
                event['completion_status'],
                str(event['completion_time']) if event['completion_time'] else '',
                str(event['created_at'])
            ])
        
        output.seek(0)
        csv_content = '\ufeff' + output.getvalue()
        
        return csv_content, 200, {
            'Content-Type': 'text/csv; charset=utf-8-sig',
            'Content-Disposition': 'attachment; filename=archive.csv'
        }
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ==================== 文件处理 ====================

@app.route('/api/processFile', methods=['POST'])
@login_required
def process_file():
    """处理上传的文件（PDF/Word/图片OCR）"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '未上传文件'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'success': False, 'message': '文件名为空'}), 400
        
        file_type = request.form.get('file_type', '')
        
        # 获取文件处理器
        file_processor = get_file_processor()
        
        # 检查文件是否允许
        if not file_processor.is_allowed_file(file.filename):
            return jsonify({'success': False, 'message': '不支持的文件格式'}), 400
        
        # 处理文件
        try:
            text = file_processor.process_file(file, file_type)
            
            return jsonify({
                'success': True,
                'message': '文件处理成功',
                'text': text,
                'filename': file.filename,
                'file_type': file_type
            })
        
        except ValueError as e:
            return jsonify({'success': False, 'message': str(e)}), 400
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'文件处理失败: {str(e)}'}), 500


# ==================== 湘潭大学增强功能 ====================

from xtu_api_routes import add_xtu_routes
add_xtu_routes(app, auth_manager, get_db_connection, login_required, conflict_detector)


# ==================== 邮件提醒功能 ====================

@app.route('/api/testEmail', methods=['POST'])
@login_required
def test_email():
    """测试邮件发送"""
    try:
        user_id = request.current_user['user_id']
        
        # 获取用户邮箱
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT email FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not user or not user['email']:
            return jsonify({'success': False, 'message': '用户邮箱未设置'}), 400
        
        # 发送测试邮件
        success = email_sender.send_reminder_email(
            to_email=user['email'],
            event_title='测试提醒',
            event_time=datetime.now().strftime('%Y-%m-%d %H:%M'),
            event_location='测试地点',
            advance_minutes=30
        )
        
        if success:
            return jsonify({'success': True, 'message': '测试邮件已发送，请检查邮箱'})
        else:
            return jsonify({'success': False, 'message': '邮件发送失败，请检查邮件配置'}), 500
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'发送失败: {str(e)}'}), 500


@app.route('/api/sendPendingReminders', methods=['POST'])
def send_pending_reminders():
    """发送待发送的提醒邮件（后台定时任务调用）"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询需要发送的提醒（提醒时间已到，但状态还是pending）
        cursor.execute("""
            SELECT rt.task_id, rt.event_id, rt.user_id, rt.advance_minutes,
                   te.event_title, te.event_time, te.event_location,
                   u.email, u.real_name
            FROM reminder_tasks rt
            JOIN text_events te ON rt.event_id = te.event_id
            JOIN users u ON rt.user_id = u.user_id
            JOIN user_settings us ON u.user_id = us.user_id
            WHERE rt.status = 'pending'
            AND rt.reminder_time <= NOW()
            AND us.email_notification = TRUE
            AND u.email IS NOT NULL
            AND u.email != ''
            LIMIT 50
        """)
        
        reminders = cursor.fetchall()
        
        sent_count = 0
        failed_count = 0
        
        for reminder in reminders:
            try:
                # 发送邮件
                success = email_sender.send_reminder_email(
                    to_email=reminder['email'],
                    event_title=reminder['event_title'],
                    event_time=str(reminder['event_time']),
                    event_location=reminder['event_location'] or '',
                    advance_minutes=reminder['advance_minutes']
                )
                
                if success:
                    # 更新状态为已发送
                    cursor.execute("""
                        UPDATE reminder_tasks 
                        SET status = 'sent'
                        WHERE task_id = %s
                    """, (reminder['task_id'],))
                    sent_count += 1
                else:
                    failed_count += 1
                    
            except Exception as e:
                print(f"发送提醒失败 task_id={reminder['task_id']}: {e}")
                failed_count += 1
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'sent_count': sent_count,
            'failed_count': failed_count,
            'message': f'成功发送{sent_count}条提醒，失败{failed_count}条'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'处理失败: {str(e)}'}), 500


# ==================== 健康检查 ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查（不需要登录）"""
    return jsonify({
        'success': True,
        'message': '服务正常',
        'version': '2.0-xtu-enhanced',
        'email_configured': bool(email_sender.smtp_username and email_sender.smtp_password)
    })


if __name__ == '__main__':
    print("=" * 60)
    print("校园事务自动提醒系统 v2.0 - 带用户认证版本")
    print("=" * 60)
    print("功能特性:")
    print("  ✅ 学号登录（12位学号格式）")
    print("  ✅ 用户注册")
    print("  ✅ 会话管理（24小时有效期）")
    print("  ✅ 多用户数据隔离")
    print("  ✅ 操作日志记录")
    print("=" * 60)
    print("测试用户（密码: xtu123456）:")
    print("  - 202205570603 (张三)")
    print("  - 202205570610 (李四)")
    print("  - 202205580501 (王五)")
    print("=" * 60)
    print("访问地址: http://localhost:5000")
    print("=" * 60)
    app.run(debug=True, host='0.0.0.0', port=5000)
