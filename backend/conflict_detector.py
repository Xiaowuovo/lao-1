import pymysql
from datetime import datetime, timedelta
from typing import List, Dict, Optional

class ConflictDetector:
    """时间冲突检测器"""
    
    def __init__(self, db_config: dict):
        self.db_config = db_config
    
    def check_conflicts(self, user_id: int, event_time: datetime, 
                       event_duration: int = 120, event_id: Optional[int] = None) -> Dict:
        """
        检查时间冲突
        
        Args:
            user_id: 用户ID
            event_time: 事件时间
            event_duration: 事件持续时间（分钟）
            event_id: 事件ID（更新时用，排除自己）
        
        Returns:
            {
                'has_conflict': True/False,
                'conflict_level': 'none'/'warning'/'critical',
                'conflicts': [
                    {
                        'type': 'event'/'schedule',
                        'id': 123,
                        'title': '已有事件',
                        'time': '2026-04-18 14:00',
                        'location': '逸夫楼一阶'
                    }
                ],
                'message': '提示信息'
            }
        """
        end_time = event_time + timedelta(minutes=event_duration)
        
        conflicts = []
        
        # 1. 检查与其他事件的冲突
        event_conflicts = self._check_event_conflicts(user_id, event_time, end_time, event_id)
        conflicts.extend(event_conflicts)
        
        # 2. 检查与课表的冲突
        schedule_conflicts = self._check_schedule_conflicts(user_id, event_time, end_time)
        conflicts.extend(schedule_conflicts)
        
        # 确定冲突级别
        conflict_level = 'none'
        if conflicts:
            # 如果与课表冲突，级别为critical
            if any(c['type'] == 'schedule' for c in conflicts):
                conflict_level = 'critical'
            else:
                conflict_level = 'warning'
        
        # 生成提示信息
        message = self._generate_conflict_message(conflicts, conflict_level)
        
        return {
            'has_conflict': len(conflicts) > 0,
            'conflict_level': conflict_level,
            'conflicts': conflicts,
            'message': message
        }
    
    def _check_event_conflicts(self, user_id: int, start_time: datetime, 
                               end_time: datetime, exclude_event_id: Optional[int]) -> List[Dict]:
        """检查与其他事件的冲突"""
        conflicts = []
        
        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            query = """
                SELECT 
                    te.event_id,
                    te.event_title,
                    te.event_time,
                    te.event_location,
                    rt.status
                FROM text_events te
                JOIN reminder_tasks rt ON te.event_id = rt.event_id
                WHERE rt.user_id = %s
                AND rt.status NOT IN ('completed', 'cancelled')
                AND (
                    (te.event_time BETWEEN %s AND %s)
                    OR (DATE_ADD(te.event_time, INTERVAL 2 HOUR) BETWEEN %s AND %s)
                    OR (%s BETWEEN te.event_time AND DATE_ADD(te.event_time, INTERVAL 2 HOUR))
                )
            """
            
            params = [user_id, start_time, end_time, start_time, end_time, start_time]
            
            if exclude_event_id:
                query += " AND te.event_id != %s"
                params.append(exclude_event_id)
            
            cursor.execute(query, params)
            events = cursor.fetchall()
            
            for event in events:
                conflicts.append({
                    'type': 'event',
                    'id': event['event_id'],
                    'title': event['event_title'],
                    'time': event['event_time'].strftime('%Y-%m-%d %H:%M'),
                    'location': event['event_location'] or '未指定',
                    'status': event['status']
                })
            
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"检查事件冲突失败: {e}")
        
        return conflicts
    
    def _check_schedule_conflicts(self, user_id: int, start_time: datetime, 
                                  end_time: datetime) -> List[Dict]:
        """检查与课表的冲突"""
        conflicts = []
        
        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            # 获取星期几
            day_of_week = start_time.isoweekday()
            event_start_time = start_time.time()
            event_end_time = end_time.time()
            
            cursor.execute("""
                SELECT 
                    schedule_id,
                    course_name,
                    start_time,
                    end_time,
                    course_location AS location,
                    teacher_name AS teacher
                FROM user_schedules
                WHERE user_id = %s
                AND weekday = %s
                AND (
                    (start_time BETWEEN %s AND %s)
                    OR (end_time BETWEEN %s AND %s)
                    OR (%s BETWEEN start_time AND end_time)
                )
            """, (user_id, day_of_week, event_start_time, event_end_time, 
                  event_start_time, event_end_time, event_start_time))
            
            schedules = cursor.fetchall()
            
            for schedule in schedules:
                conflicts.append({
                    'type': 'schedule',
                    'id': schedule['schedule_id'],
                    'title': schedule['course_name'],
                    'time': f"{schedule['start_time']} - {schedule['end_time']}",
                    'location': schedule['location'] or '未指定',
                    'teacher': schedule['teacher'] or ''
                })
            
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"检查课表冲突失败: {e}")
        
        return conflicts
    
    def _generate_conflict_message(self, conflicts: List[Dict], level: str) -> str:
        """生成冲突提示信息"""
        if not conflicts:
            return '无时间冲突'
        
        if level == 'critical':
            course_conflicts = [c for c in conflicts if c['type'] == 'schedule']
            courses = ', '.join([f"《{c['title']}》" for c in course_conflicts])
            return f'⚠️ 强烈提醒：该时间与课程{courses}冲突！'
        
        elif level == 'warning':
            event_titles = ', '.join([c['title'] for c in conflicts])
            return f'⚠️ 提醒：该时间与以下事件重叠：{event_titles}'
        
        return ''
    
    def record_conflict(self, event_id: int, conflict_with_event_id: Optional[int],
                       conflict_with_schedule_id: Optional[int], conflict_type: str,
                       conflict_level: str, start_time: datetime, end_time: datetime) -> bool:
        """记录冲突到数据库"""
        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO event_conflicts 
                (event_id, conflict_with_event_id, conflict_with_schedule_id, 
                 conflict_type, conflict_level, start_time, end_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (event_id, conflict_with_event_id, conflict_with_schedule_id,
                  conflict_type, conflict_level, start_time, end_time))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"记录冲突失败: {e}")
            return False
    
    def get_user_conflicts(self, user_id: int, days: int = 30) -> List[Dict]:
        """获取用户的所有冲突记录"""
        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            cursor.execute("""
                SELECT 
                    ec.*,
                    te.event_title,
                    te.event_time,
                    te.event_location
                FROM event_conflicts ec
                JOIN text_events te ON ec.event_id = te.event_id
                JOIN reminder_tasks rt ON te.event_id = rt.event_id
                WHERE rt.user_id = %s
                AND ec.start_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
                AND ec.is_resolved = FALSE
                ORDER BY ec.start_time DESC
            """, (user_id, days))
            
            conflicts = cursor.fetchall()
            
            cursor.close()
            conn.close()
            
            return conflicts
        except Exception as e:
            print(f"获取冲突记录失败: {e}")
            return []
    
    def resolve_conflict(self, conflict_id: int) -> bool:
        """标记冲突已解决"""
        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE event_conflicts 
                SET is_resolved = TRUE
                WHERE conflict_id = %s
            """, (conflict_id,))
            
            conn.commit()
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            print(f"解决冲突失败: {e}")
            return False


class ScheduleManager:
    """课表管理器"""
    
    def __init__(self, db_config: dict):
        self.db_config = db_config
    
    def add_course(self, user_id: int, course_name: str = None, day_of_week: int = None,
                   start_time: str = None, end_time: str = None,
                   location: str = '', teacher: str = '',
                   weeks: str = '', exam_type: str = '', **kwargs) -> Dict:
        """添加课程到课表"""
        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor()

            # 确保 weeks/exam_type 字段存在（兼容旧表结构）
            self._ensure_extra_columns(cursor)
            
            cursor.execute("""
                INSERT INTO user_schedules 
                (user_id, course_name, weekday, start_time, end_time, 
                 course_location, teacher_name, weeks, exam_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                course_name,
                day_of_week,
                start_time,
                end_time,
                location,
                teacher,
                weeks or '',
                exam_type or ''
            ))
            
            schedule_id = cursor.lastrowid
            conn.commit()
            cursor.close()
            conn.close()
            return {'success': True, 'message': '课程添加成功', 'schedule_id': schedule_id}
        except Exception as e:
            print(f"添加课程失败: {e}")
            return {'success': False, 'message': f'添加课程失败: {str(e)}'}
    
    def _ensure_extra_columns(self, cursor):
        """确保 weeks/exam_type 字段存在"""
        try:
            cursor.execute("SHOW COLUMNS FROM user_schedules LIKE 'weeks'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE user_schedules ADD COLUMN weeks VARCHAR(50) DEFAULT ''")
            cursor.execute("SHOW COLUMNS FROM user_schedules LIKE 'exam_type'")
            if not cursor.fetchone():
                cursor.execute("ALTER TABLE user_schedules ADD COLUMN exam_type VARCHAR(20) DEFAULT ''")
        except:
            pass

    def get_schedule(self, user_id: int, day_of_week=None) -> List[Dict]:
        """获取用户课表"""
        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor(pymysql.cursors.DictCursor)

            self._ensure_extra_columns(cursor)

            if day_of_week:
                cursor.execute("""
                    SELECT schedule_id, course_name, weekday AS day_of_week,
                           start_time, end_time, course_location AS location, teacher_name AS teacher,
                           COALESCE(weeks,'') AS weeks, COALESCE(exam_type,'') AS exam_type
                    FROM user_schedules
                    WHERE user_id = %s AND weekday = %s
                    ORDER BY start_time
                """, (user_id, day_of_week))
            else:
                cursor.execute("""
                    SELECT schedule_id, course_name, weekday AS day_of_week,
                           start_time, end_time, course_location AS location, teacher_name AS teacher,
                           COALESCE(weeks,'') AS weeks, COALESCE(exam_type,'') AS exam_type
                    FROM user_schedules
                    WHERE user_id = %s
                    ORDER BY weekday, start_time
                """, (user_id,))
            
            schedules = cursor.fetchall()
            
            for s in schedules:
                if s['start_time'] is not None:
                    t = s['start_time']
                    if hasattr(t, 'seconds'):
                        # timedelta: 转为 HH:MM:SS
                        total = int(t.total_seconds())
                        s['start_time'] = f"{total//3600:02d}:{(total%3600)//60:02d}:{total%60:02d}"
                    else:
                        s['start_time'] = str(t)
                if s['end_time'] is not None:
                    t = s['end_time']
                    if hasattr(t, 'seconds'):
                        total = int(t.total_seconds())
                        s['end_time'] = f"{total//3600:02d}:{(total%3600)//60:02d}:{total%60:02d}"
                    else:
                        s['end_time'] = str(t)
            
            cursor.close()
            conn.close()
            
            return schedules
        except Exception as e:
            print(f"获取课表失败: {e}")
            return []
    
    def delete_course(self, user_id: int, schedule_id: int) -> Dict:
        """删除课程"""
        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM user_schedules 
                WHERE schedule_id = %s AND user_id = %s
            """, (schedule_id, user_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            return {'success': True, 'message': '课程已删除'}
        except Exception as e:
            print(f"删除课程失败: {e}")
            return {'success': False, 'message': f'删除课程失败: {str(e)}'}
    
    def import_schedule(self, user_id: int, schedule_data: List[Dict]) -> Dict:
        """批量导入课表"""
        success_count = 0
        failed_count = 0
        errors = []
        
        for course in schedule_data:
            try:
                result = self.add_course(
                    user_id,
                    course_name=course.get('course_name'),
                    day_of_week=course.get('day_of_week'),
                    start_time=course.get('start_time'),
                    end_time=course.get('end_time'),
                    location=course.get('location', ''),
                    teacher=course.get('teacher', '')
                )
                if result['success']:
                    success_count += 1
                else:
                    failed_count += 1
                    errors.append(f"导入课程 {course.get('course_name', '未知')} 失败")
            except Exception as e:
                failed_count += 1
                errors.append(f"导入课程失败: {str(e)}")
        
        return {
            'success': True,
            'success_count': success_count,
            'failed_count': failed_count,
            'total': len(schedule_data),
            'errors': errors
        }
