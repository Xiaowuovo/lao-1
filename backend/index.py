from flask import Flask, request, jsonify
from flask_cors import CORS
import pymysql
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import os
from event import EventExtractor
import threading
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'campus_reminder_system'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

extractor = EventExtractor()

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

@app.route('/api/uploadText', methods=['POST'])
def upload_text():
    try:
        data = request.json
        text = data.get('text', '')
        user_id = data.get('user_id', 1)
        
        if not text.strip():
            return jsonify({'success': False, 'message': '文本内容不能为空'}), 400
        
        events = extractor.extract_events(text)
        
        if not events:
            return jsonify({
                'success': False, 
                'message': '未识别到有效事件。请确保文本包含时间信息（如：2026年4月18日 14:00）',
                'events': []
            })
        
        return jsonify({
            'success': True,
            'message': f'成功提取 {len(events)} 个事件',
            'events': events
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'处理失败: {str(e)}'}), 500

@app.route('/api/extractEvents', methods=['POST'])
def extract_events():
    try:
        data = request.json
        text = data.get('text', '')
        user_id = data.get('user_id', 1)
        
        if not text.strip():
            return jsonify({'success': False, 'message': '文本内容不能为空'}), 400
        
        events = extractor.extract_events(text)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        event_ids = []
        for event in events:
            cursor.execute("""
                INSERT INTO text_events 
                (user_id, original_text, event_title, event_time, event_location, 
                 event_target, event_type, extraction_confidence)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                event['original_text'],
                event['title'],
                event['time'],
                event['location'],
                event['target'],
                event['event_type'],
                event['confidence']
            ))
            event_ids.append(cursor.lastrowid)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        for i, event in enumerate(events):
            event['event_id'] = event_ids[i]
        
        return jsonify({
            'success': True,
            'message': f'成功提取并保存 {len(events)} 个事件',
            'events': events
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'提取失败: {str(e)}'}), 500

@app.route('/api/createReminder', methods=['POST'])
def create_reminder():
    try:
        data = request.json
        event_id = data.get('event_id')
        user_id = data.get('user_id', 1)
        advance_minutes = data.get('advance_minutes', 30)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM text_events WHERE event_id = %s", (event_id,))
        event = cursor.fetchone()
        
        if not event:
            return jsonify({'success': False, 'message': '事件不存在'}), 404
        
        event_time = event['event_time']
        reminder_time = event_time - timedelta(minutes=advance_minutes)
        
        cursor.execute("SELECT * FROM user_settings WHERE user_id = %s", (user_id,))
        settings = cursor.fetchone()
        
        reminder_methods = []
        if settings:
            if settings['web_notification']:
                reminder_methods.append('web')
            if settings['email_notification']:
                reminder_methods.append('email')
            if settings['sms_notification']:
                reminder_methods.append('sms')
        else:
            reminder_methods = ['web']
        
        reminder_method = ','.join(reminder_methods) if reminder_methods else 'web'
        
        cursor.execute("""
            INSERT INTO reminder_tasks 
            (event_id, user_id, reminder_time, advance_minutes, reminder_method)
            VALUES (%s, %s, %s, %s, %s)
        """, (event_id, user_id, reminder_time, advance_minutes, reminder_method))
        
        reminder_id = cursor.lastrowid
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '提醒创建成功',
            'reminder_id': reminder_id
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'创建失败: {str(e)}'}), 500

@app.route('/api/getReminders', methods=['GET'])
def get_reminders():
    try:
        user_id = request.args.get('user_id', 1)
        status = request.args.get('status', 'all')
        time_range = request.args.get('time_range', 'all')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT 
                rt.reminder_id,
                rt.reminder_time,
                rt.advance_minutes,
                rt.status,
                rt.reminder_method,
                rt.postponed_to,
                te.event_title,
                te.event_time,
                te.event_location,
                te.event_target,
                te.event_type
            FROM reminder_tasks rt
            JOIN text_events te ON rt.event_id = te.event_id
            WHERE rt.user_id = %s
        """
        
        params = [user_id]
        
        if status != 'all':
            query += " AND rt.status = %s"
            params.append(status)
        
        if time_range == 'today':
            query += " AND DATE(rt.reminder_time) = CURDATE()"
        elif time_range == 'week':
            query += " AND rt.reminder_time BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL 7 DAY)"
        elif time_range == 'month':
            query += " AND YEAR(rt.reminder_time) = YEAR(CURDATE()) AND MONTH(rt.reminder_time) = MONTH(CURDATE())"
        
        query += " ORDER BY rt.reminder_time ASC"
        
        cursor.execute(query, params)
        reminders = cursor.fetchall()
        
        for reminder in reminders:
            if reminder['reminder_time']:
                reminder['reminder_time'] = reminder['reminder_time'].strftime('%Y-%m-%d %H:%M')
            if reminder['event_time']:
                reminder['event_time'] = reminder['event_time'].strftime('%Y-%m-%d %H:%M')
            if reminder['postponed_to']:
                reminder['postponed_to'] = reminder['postponed_to'].strftime('%Y-%m-%d %H:%M')
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'reminders': reminders
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取失败: {str(e)}'}), 500

@app.route('/api/markDone', methods=['POST'])
def mark_done():
    try:
        data = request.json
        reminder_id = data.get('reminder_id')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE reminder_tasks 
            SET status = 'completed'
            WHERE reminder_id = %s
        """, (reminder_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '已标记为完成'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'更新失败: {str(e)}'}), 500

@app.route('/api/deleteReminder', methods=['POST'])
def delete_reminder():
    try:
        data = request.json
        reminder_id = data.get('reminder_id')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM reminder_tasks WHERE reminder_id = %s", (reminder_id,))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '提醒已删除'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500

@app.route('/api/postponeReminder', methods=['POST'])
def postpone_reminder():
    try:
        data = request.json
        reminder_id = data.get('reminder_id')
        new_time = data.get('new_time')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE reminder_tasks 
            SET status = 'postponed', postponed_to = %s
            WHERE reminder_id = %s
        """, (new_time, reminder_id))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '提醒已延期'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'延期失败: {str(e)}'}), 500

@app.route('/api/getStatistics', methods=['GET'])
def get_statistics():
    try:
        user_id = request.args.get('user_id', 1)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status IN ('pending', 'reminded') THEN 1 ELSE 0 END) as pending,
                SUM(CASE WHEN status = 'postponed' THEN 1 ELSE 0 END) as postponed
            FROM reminder_tasks
            WHERE user_id = %s 
            AND YEAR(reminder_time) = YEAR(CURDATE()) 
            AND MONTH(reminder_time) = MONTH(CURDATE())
        """, (user_id,))
        
        stats = cursor.fetchone()
        
        cursor.execute("""
            SELECT event_type, COUNT(*) as count
            FROM text_events te
            JOIN reminder_tasks rt ON te.event_id = rt.event_id
            WHERE rt.user_id = %s
            AND YEAR(rt.reminder_time) = YEAR(CURDATE()) 
            AND MONTH(rt.reminder_time) = MONTH(CURDATE())
            GROUP BY event_type
        """, (user_id,))
        
        type_distribution = cursor.fetchall()
        
        cursor.execute("""
            SELECT DATE(reminder_time) as date, COUNT(*) as count
            FROM reminder_tasks
            WHERE user_id = %s
            AND reminder_time >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
            GROUP BY DATE(reminder_time)
            ORDER BY date
        """, (user_id,))
        
        trend_data = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        total = stats['total'] or 0
        completed = stats['completed'] or 0
        completion_rate = round((completed / total * 100), 2) if total > 0 else 0
        
        for item in trend_data:
            if item['date']:
                item['date'] = item['date'].strftime('%Y-%m-%d')
        
        return jsonify({
            'success': True,
            'statistics': {
                'total': total,
                'completed': completed,
                'pending': stats['pending'] or 0,
                'postponed': stats['postponed'] or 0,
                'completion_rate': completion_rate,
                'type_distribution': type_distribution,
                'trend_data': trend_data
            }
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取统计失败: {str(e)}'}), 500

@app.route('/api/getSettings', methods=['GET'])
def get_settings():
    try:
        user_id = request.args.get('user_id', 1)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM user_settings WHERE user_id = %s", (user_id,))
        settings = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if not settings:
            return jsonify({
                'success': True,
                'settings': {
                    'default_advance_minutes': 30,
                    'web_notification': True,
                    'email_notification': False,
                    'sms_notification': False,
                    'email_address': '',
                    'phone_number': '',
                    'repeat_daily': False,
                    'repeat_weekly': False,
                    'repeat_monthly': False
                }
            })
        
        return jsonify({
            'success': True,
            'settings': settings
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'获取设置失败: {str(e)}'}), 500

@app.route('/api/updateSettings', methods=['POST'])
def update_settings():
    try:
        data = request.json
        user_id = data.get('user_id', 1)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO user_settings 
            (user_id, default_advance_minutes, web_notification, email_notification, 
             sms_notification, email_address, phone_number, repeat_daily, repeat_weekly, repeat_monthly)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                default_advance_minutes = VALUES(default_advance_minutes),
                web_notification = VALUES(web_notification),
                email_notification = VALUES(email_notification),
                sms_notification = VALUES(sms_notification),
                email_address = VALUES(email_address),
                phone_number = VALUES(phone_number),
                repeat_daily = VALUES(repeat_daily),
                repeat_weekly = VALUES(repeat_weekly),
                repeat_monthly = VALUES(repeat_monthly)
        """, (
            user_id,
            data.get('default_advance_minutes', 30),
            data.get('web_notification', True),
            data.get('email_notification', False),
            data.get('sms_notification', False),
            data.get('email_address', ''),
            data.get('phone_number', ''),
            data.get('repeat_daily', False),
            data.get('repeat_weekly', False),
            data.get('repeat_monthly', False)
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': '设置已保存'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'保存失败: {str(e)}'}), 500

def check_and_send_reminders():
    while True:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            now = datetime.now()
            
            cursor.execute("""
                SELECT rt.*, te.event_title, te.event_time, te.event_location
                FROM reminder_tasks rt
                JOIN text_events te ON rt.event_id = te.event_id
                WHERE rt.status = 'pending'
                AND rt.reminder_time <= %s
                AND rt.reminder_time > DATE_SUB(%s, INTERVAL 5 MINUTE)
            """, (now, now))
            
            reminders = cursor.fetchall()
            
            for reminder in reminders:
                try:
                    methods = reminder['reminder_method'].split(',')
                    
                    if 'web' in methods:
                        pass
                    
                    if 'email' in methods:
                        cursor.execute("SELECT email_address FROM user_settings WHERE user_id = %s", 
                                     (reminder['user_id'],))
                        user_settings = cursor.fetchone()
                        if user_settings and user_settings['email_address']:
                            pass
                    
                    cursor.execute("""
                        UPDATE reminder_tasks 
                        SET status = 'reminded', notified_at = %s
                        WHERE reminder_id = %s
                    """, (now, reminder['reminder_id']))
                    
                    cursor.execute("""
                        INSERT INTO reminder_logs 
                        (reminder_id, user_id, reminder_time, notification_method, notification_status)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        reminder['reminder_id'],
                        reminder['user_id'],
                        reminder['reminder_time'],
                        reminder['reminder_method'],
                        'success'
                    ))
                    
                    conn.commit()
                    
                except Exception as e:
                    print(f"发送提醒失败: {e}")
                    cursor.execute("""
                        INSERT INTO reminder_logs 
                        (reminder_id, user_id, reminder_time, notification_method, 
                         notification_status, error_message)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        reminder['reminder_id'],
                        reminder['user_id'],
                        reminder['reminder_time'],
                        reminder['reminder_method'],
                        'failed',
                        str(e)
                    ))
                    conn.commit()
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            print(f"检查提醒任务失败: {e}")
        
        time.sleep(60)

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': '系统运行正常'})

if __name__ == '__main__':
    scheduler_thread = threading.Thread(target=check_and_send_reminders, daemon=True)
    scheduler_thread.start()
    
    print("校园事务自动提醒系统后端服务启动成功！")
    print("访问地址: http://localhost:5000")
    print("提醒调度器已启动，每分钟检查一次待发送提醒")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
