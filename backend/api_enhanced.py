from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pymysql
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import os
import json

from event_enhanced import EnhancedEventExtractor
from location_matcher import LocationMatcher
from conflict_detector import ConflictDetector, ScheduleManager
from file_processor import FileProcessor, BatchTextSplitter

app = Flask(__name__)
CORS(app)

# 配置
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'jpg', 'jpeg', 'png', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'campus_reminder_system'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# 初始化组件
extractor = EnhancedEventExtractor()
location_matcher = LocationMatcher(DB_CONFIG)
conflict_detector = ConflictDetector(DB_CONFIG)
schedule_manager = ScheduleManager(DB_CONFIG)
file_processor = FileProcessor(DB_CONFIG, UPLOAD_FOLDER)

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ==================== 增强版事件提取接口 ====================

@app.route('/api/extractEventsEnhanced', methods=['POST'])
def extract_events_enhanced():
    """增强版事件提取（支持所有新字段）"""
    try:
        data = request.json
        text = data.get('text', '')
        user_id = data.get('user_id', 1)
        auto_confirm = data.get('auto_confirm', False)
        
        if not text.strip():
            return jsonify({'success': False, 'message': '文本内容不能为空'}), 400
        
        # 批量拆分（如果包含多条）
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
        
        # 地点标准化
        for event in all_events:
            location_result = location_matcher.match_location(event['location'])
            event['location_match'] = location_result
            if location_result['matched']:
                event['standard_location'] = location_result['standard_name']
        
        # 如果不是自动确认，返回待确认数据
        if not auto_confirm:
            return jsonify({
                'success': True,
                'message': f'成功提取 {len(all_events)} 个事件，请确认',
                'events': all_events,
                'needs_confirmation': True
            })
        
        # 自动确认模式：直接保存到数据库
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
def confirm_events():
    """用户确认事件并保存"""
    try:
        data = request.json
        events = data.get('events', [])
        user_id = data.get('user_id', 1)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        saved_events = []
        for event in events:
            # 用户可能修改了某些字段
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


# ==================== 增强版提醒创建（支持冲突检测） ====================

@app.route('/api/createReminderEnhanced', methods=['POST'])
def create_reminder_enhanced():
    """创建提醒（支持冲突检测和多级提醒）"""
    try:
        data = request.json
        event_id = data.get('event_id')
        user_id = data.get('user_id', 1)
        advance_minutes = data.get('advance_minutes', 30)
        reminder_levels = data.get('reminder_levels', [60, 180, 1440])  # 1小时、3小时、1天
        check_conflict = data.get('check_conflict', True)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM text_events WHERE event_id = %s", (event_id,))
        event = cursor.fetchone()
        
        if not event:
            return jsonify({'success': False, 'message': '事件不存在'}), 404
        
        event_time = event['event_time']
        
        # 冲突检测
        conflict_info = {'has_conflict': False}
        if check_conflict:
            conflict_info = conflict_detector.check_conflicts(
                user_id, event_time, 120, event_id
            )
            
            # 更新事件冲突状态
            if conflict_info['has_conflict']:
                cursor.execute("""
                    UPDATE text_events 
                    SET has_conflict = TRUE, conflict_level = %s
                    WHERE event_id = %s
                """, (conflict_info['conflict_level'], event_id))
                conn.commit()
        
        # 创建提醒
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
        
        # 如果是截止时间提醒
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


# ==================== 文件上传接口 ====================

@app.route('/api/uploadFile', methods=['POST'])
def upload_file():
    """上传文件（图片/PDF/Word）"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': '没有文件'}), 400
        
        file = request.files['file']
        user_id = request.form.get('user_id', 1)
        
        if file.filename == '':
            return jsonify({'success': False, 'message': '没有选择文件'}), 400
        
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            # 根据文件类型处理
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


@app.route('/api/parseUrl', methods=['POST'])
def parse_url():
    """解析网页URL"""
    try:
        data = request.json
        url = data.get('url', '')
        user_id = data.get('user_id', 1)
        
        if not url:
            return jsonify({'success': False, 'message': 'URL不能为空'}), 400
        
        result = file_processor.process_url(url, user_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': '网页解析成功',
                'text': result['text'],
                'title': result['title'],
                'url': result['url']
            })
        else:
            return jsonify({
                'success': False,
                'message': result['error']
            }), 400
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'解析失败: {str(e)}'}), 500


# ==================== 课表管理接口 ====================

@app.route('/api/addCourse', methods=['POST'])
def add_course():
    """添加课程到课表"""
    try:
        data = request.json
        user_id = data.get('user_id', 1)
        
        result = schedule_manager.add_course(user_id, data)
        
        if result:
            return jsonify({'success': True, 'message': '课程添加成功'})
        else:
            return jsonify({'success': False, 'message': '课程添加失败'}), 400
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'添加失败: {str(e)}'}), 500


@app.route('/api/getSchedule', methods=['GET'])
def get_schedule():
    """获取用户课表"""
    try:
        user_id = request.args.get('user_id', 1)
        schedules = schedule_manager.get_user_schedule(user_id)
        
        return jsonify({
            'success': True,
            'schedules': schedules
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'}), 500


@app.route('/api/deleteCourse', methods=['POST'])
def delete_course():
    """删除课程"""
    try:
        data = request.json
        schedule_id = data.get('schedule_id')
        
        result = schedule_manager.delete_course(schedule_id)
        
        if result:
            return jsonify({'success': True, 'message': '课程删除成功'})
        else:
            return jsonify({'success': False, 'message': '课程删除失败'}), 400
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500


# ==================== 历史归档接口 ====================

@app.route('/api/archiveEvent', methods=['POST'])
def archive_event():
    """归档已完成的事件"""
    try:
        data = request.json
        event_id = data.get('event_id')
        user_id = data.get('user_id', 1)
        completion_status = data.get('completion_status', 'completed')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取事件信息
        cursor.execute("SELECT * FROM text_events WHERE event_id = %s", (event_id,))
        event = cursor.fetchone()
        
        if not event:
            return jsonify({'success': False, 'message': '事件不存在'}), 404
        
        # 插入归档表
        cursor.execute("""
            INSERT INTO event_archive 
            (event_id, user_id, event_title, event_time, deadline_time,
             event_location, event_target, organizer, activity_type, task_category,
             original_data, completion_status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            event_id, user_id, event['event_title'], event['event_time'],
            event['deadline_time'], event['event_location'], event['event_target'],
            event['organizer'], event['activity_type'], event['task_category'],
            json.dumps(dict(event)), completion_status
        ))
        
        # 删除原事件
        cursor.execute("DELETE FROM text_events WHERE event_id = %s", (event_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': '事件已归档'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'归档失败: {str(e)}'}), 500


@app.route('/api/getArchive', methods=['GET'])
def get_archive():
    """获取归档记录"""
    try:
        user_id = request.args.get('user_id', 1)
        limit = int(request.args.get('limit', 50))
        search = request.args.get('search', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = "SELECT * FROM event_archive WHERE user_id = %s"
        params = [user_id]
        
        if search:
            query += " AND (event_title LIKE %s OR event_location LIKE %s)"
            search_pattern = f'%{search}%'
            params.extend([search_pattern, search_pattern])
        
        query += " ORDER BY completion_time DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        archives = cursor.fetchall()
        
        for archive in archives:
            if archive['completion_time']:
                archive['completion_time'] = archive['completion_time'].strftime('%Y-%m-%d %H:%M')
            if archive['event_time']:
                archive['event_time'] = archive['event_time'].strftime('%Y-%m-%d %H:%M')
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'archives': archives
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'}), 500


@app.route('/api/exportArchive', methods=['GET'])
def export_archive():
    """导出归档数据"""
    try:
        user_id = request.args.get('user_id', 1)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM event_archive 
            WHERE user_id = %s
            ORDER BY completion_time DESC
        """, (user_id,))
        
        archives = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # 转换为CSV格式
        import csv
        import io
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # 写入表头
        writer.writerow(['事件标题', '事件时间', '截止时间', '地点', '主办单位', 
                        '活动类型', '完成时间', '完成状态'])
        
        # 写入数据
        for archive in archives:
            writer.writerow([
                archive['event_title'],
                archive['event_time'],
                archive['deadline_time'] or '',
                archive['event_location'],
                archive['organizer'],
                archive['activity_type'],
                archive['completion_time'],
                archive['completion_status']
            ])
        
        output.seek(0)
        
        return jsonify({
            'success': True,
            'data': output.getvalue(),
            'filename': f'archive_{datetime.now().strftime("%Y%m%d")}.csv'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'导出失败: {str(e)}'}), 500


if __name__ == '__main__':
    print("增强版校园事务自动提醒系统后端服务启动！")
    print("访问地址: http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
