"""
湘潭大学增强API路由
"""

from flask import request, jsonify
from functools import wraps
import json
from datetime import datetime, timedelta
from xtu_event_extractor import get_extractor as get_xtu_extractor
from xtu_location_mapper import get_location_mapper


def _parse_event_time(time_str):
    """解析事件时间字符串为datetime对象，支持多种格式"""
    if not time_str:
        return None
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
        '%Y-%m-%d',
        '%Y/%m/%d %H:%M:%S',
        '%Y/%m/%d %H:%M',
        '%Y/%m/%d',
        '%Y年%m月%d日 %H:%M',
        '%Y年%m月%d日',
    ]
    for fmt in formats:
        try:
            return datetime.strptime(str(time_str).strip(), fmt)
        except ValueError:
            continue
    return None


def add_xtu_routes(app, auth_manager, get_db_connection, login_required, conflict_detector=None):
    """添加湘大增强路由"""
    
    @app.route('/api/xtu/extractEvents', methods=['POST'])
    @login_required
    def xtu_extract_events():
        """湘大增强版事件提取"""
        try:
            data = request.json
            text = data.get('text', '')
            user_id = request.current_user['user_id']
            
            if not text.strip():
                return jsonify({'success': False, 'message': '文本内容不能为空'}), 400
            
            # 使用湘大增强提取器
            extractor = get_xtu_extractor()
            result = extractor.extract_enhanced(text)
            
            # 添加临时ID
            result['temp_id'] = f"temp_{user_id}_{int(__import__('time').time() * 1000)}"
            result['original_text'] = text
            
            # 构建返回的事件卡片
            event_card = {
                'temp_id': result['temp_id'],
                'title': result['title'],
                'time': result['time'],
                'deadline': result['deadline'],
                'location': {
                    'original': result['location'],
                    'standard': result['location_standard'],
                    'confidence': result['location_confidence'],
                    'warning': result['location_warning'],
                    'is_xtu_location': result.get('location_warning') != '⚠️ 该地点可能不在湘大校内，请再次确认'
                },
                'organizer': result['organizer'],
                'activity_type': result['activity_type'],
                'audience': result['audience'],
                'contact': result['contact'],
                'is_recurring': result['is_recurring'],
                'recurring_pattern': result['recurring_pattern'],
                'required_fields_missing': result['required_fields_missing'],
                'confidence': result['confidence'],
                'original_text': text
            }
            
            return jsonify({
                'success': True,
                'message': '事件提取成功，请确认信息',
                'event_card': event_card,
                'needs_confirmation': True
            })
        
        except Exception as e:
            return jsonify({'success': False, 'message': f'提取失败: {str(e)}'}), 500
    
    
    @app.route('/api/xtu/extractBatch', methods=['POST'])
    @login_required
    def xtu_extract_batch():
        """湘大批量事件提取"""
        try:
            data = request.json
            text = data.get('text', '')
            user_id = request.current_user['user_id']
            
            if not text or not text.strip():
                return jsonify({'success': False, 'message': '文本内容不能为空'}), 400
            
            # 使用湘大增强提取器进行批量提取
            extractor = get_xtu_extractor()
            events = extractor.extract_batch(text)
            
            # 构建返回的事件卡片列表
            event_cards = []
            for idx, result in enumerate(events):
                # 添加临时ID
                temp_id = f"temp_{user_id}_{int(__import__('time').time() * 1000)}_{idx}"
                
                event_card = {
                    'temp_id': temp_id,
                    'title': result['title'],
                    'time': result['time'],
                    'deadline': result['deadline'],
                    'location': {
                        'original': result['location'],
                        'standard': result['location_standard'],
                        'confidence': result['location_confidence'],
                        'warning': result['location_warning'],
                        'is_xtu_location': result.get('location_warning') != '⚠️ 该地点可能不在湘大校内，请再次确认'
                    },
                    'organizer': result['organizer'],
                    'activity_type': result['activity_type'],
                    'audience': result['audience'],
                    'contact': result['contact'],
                    'is_recurring': result['is_recurring'],
                    'recurring_pattern': result['recurring_pattern'],
                    'required_fields_missing': result['required_fields_missing'],
                    'confidence': result['confidence'],
                    'original_text': result.get('original_text', '')
                }
                event_cards.append(event_card)
            
            return jsonify({
                'success': True,
                'message': f'成功提取 {len(event_cards)} 个事件，请逐一确认',
                'event_cards': event_cards,
                'count': len(event_cards),
                'needs_confirmation': True
            })
        
        except Exception as e:
            return jsonify({'success': False, 'message': f'批量提取失败: {str(e)}'}), 500
    
    
    @app.route('/api/xtu/confirmEvent', methods=['POST'])
    @login_required
    def xtu_confirm_event():
        """确认并保存湘大事件"""
        try:
            data = request.json
            event_data = data.get('event_data', {})
            user_id = request.current_user['user_id']
            
            # 验证必填字段
            if not event_data.get('title'):
                return jsonify({'success': False, 'message': '标题不能为空'}), 400
            
            if not event_data.get('time'):
                return jsonify({'success': False, 'message': '时间不能为空'}), 400
            
            conn = get_db_connection()
            cursor = conn.cursor()

            # 标准化时间字符串为 datetime 对象，再存入DB
            event_time_str = event_data.get('time')
            event_time_obj = _parse_event_time(event_time_str) if event_time_str else None
            # 用标准化后的字符串替换原始值
            if event_time_obj:
                event_data['time'] = event_time_obj.strftime('%Y-%m-%d %H:%M:%S')

            # 重复事件检测：相同标题 + 时间窗口 ±5分钟
            existing_event = None
            if event_time_obj:
                window_start = event_time_obj - timedelta(minutes=5)
                window_end = event_time_obj + timedelta(minutes=5)
                cursor.execute("""
                    SELECT event_id FROM text_events
                    WHERE user_id = %s
                    AND event_title = %s
                    AND event_time BETWEEN %s AND %s
                    LIMIT 1
                """, (user_id, event_data['title'], window_start, window_end))
            else:
                cursor.execute("""
                    SELECT event_id FROM text_events
                    WHERE user_id = %s AND event_title = %s AND event_time IS NULL
                    LIMIT 1
                """, (user_id, event_data['title']))
            
            existing_event = cursor.fetchone()
            
            if existing_event:
                # 已存在相同事件，更新信息
                event_id = existing_event['event_id']
                cursor.execute("""
                    UPDATE text_events 
                    SET event_location = %s,
                        standard_location = %s,
                        event_target = %s,
                        target_audience = %s,
                        organizer = %s,
                        activity_type = %s,
                        contact_info = %s,
                        deadline_time = %s,
                        extraction_confidence = %s,
                        is_confirmed = TRUE
                    WHERE event_id = %s
                """, (
                    event_data.get('location', {}).get('original', ''),
                    event_data.get('location', {}).get('standard', ''),
                    event_data.get('audience', '相关人员'),
                    event_data.get('audience', '相关人员'),
                    event_data.get('organizer', ''),
                    event_data.get('activity_type', '通知'),
                    event_data.get('contact', ''),
                    event_data.get('deadline'),
                    event_data.get('confidence', 0.5),
                    event_id
                ))
                
                # 检查是否已有提醒任务，没有则创建
                cursor.execute("""
                    SELECT task_id FROM reminder_tasks 
                    WHERE event_id = %s AND user_id = %s
                    LIMIT 1
                """, (event_id, user_id))
                
                if not cursor.fetchone():
                    event_time_str = event_data.get('time')
                    if event_time_str:
                        try:
                            event_time = _parse_event_time(event_time_str)
                            if event_time:
                                reminder_time = event_time - timedelta(minutes=30)
                                cursor.execute("""
                                    INSERT INTO reminder_tasks 
                                    (event_id, user_id, reminder_time, advance_minutes, reminder_method)
                                    VALUES (%s, %s, %s, %s, %s)
                                """, (event_id, user_id, reminder_time, 30, 'web'))
                        except:
                            pass
                
                # 同步更新归档表中的记录
                try:
                    cursor.execute("""
                        SELECT archive_id FROM event_archive
                        WHERE user_id = %s AND event_id = %s LIMIT 1
                    """, (user_id, event_id))
                    if not cursor.fetchone():
                        cursor.execute("""
                            INSERT INTO event_archive 
                            (user_id, event_id, event_title, event_time, event_location,
                             completion_status, completion_time, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                        """, (
                            user_id, event_id,
                            event_data['title'],
                            event_data.get('time'),
                            event_data.get('location', {}).get('standard', '') or event_data.get('location', {}).get('original', ''),
                            'completed'
                        ))
                except:
                    pass  # 归档表写入失败不影响主流程

                # 冲突检测（在 commit 之前，conflict_detector 自己开独立连接）
                conflict_info = {'has_conflict': False, 'conflict_level': 'none', 'conflicts': [], 'message': ''}
                if conflict_detector and event_time_obj:
                    try:
                        conflict_info = conflict_detector.check_conflicts(user_id, event_time_obj, 120, event_id)
                        if conflict_info['has_conflict']:
                            cursor.execute("UPDATE text_events SET has_conflict = TRUE WHERE event_id = %s", (event_id,))
                    except Exception as ce:
                        print(f'冲突检测失败: {ce}')

                conn.commit()
                cursor.close()
                conn.close()

                return jsonify({
                    'success': True,
                    'message': '检测到重复事件，已更新信息',
                    'event_id': event_id,
                    'is_duplicate': True,
                    'has_conflict': conflict_info['has_conflict'],
                    'conflict_level': conflict_info.get('conflict_level', 'none'),
                    'conflict_message': conflict_info.get('message', ''),
                    'conflicts': conflict_info.get('conflicts', [])
                })
            else:
                # 新事件，插入数据库
                cursor.execute("""
                    INSERT INTO text_events 
                    (user_id, original_text, event_title, event_time, deadline_time,
                     event_location, standard_location, event_target, target_audience,
                     organizer, event_type, activity_type, contact_info,
                     is_recurring, recurring_pattern, extraction_confidence, is_confirmed)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                """, (
                    user_id,
                    event_data.get('original_text', ''),
                    event_data['title'],
                    event_data.get('time'),
                    event_data.get('deadline'),
                    event_data.get('location', {}).get('original', ''),
                    event_data.get('location', {}).get('standard', ''),
                    event_data.get('audience', '相关人员'),
                    event_data.get('audience', '相关人员'),
                    event_data.get('organizer', ''),
                    'other',
                    event_data.get('activity_type', '通知'),
                    event_data.get('contact', ''),
                    event_data.get('is_recurring', False),
                    json.dumps(event_data.get('recurring_pattern')) if event_data.get('recurring_pattern') else None,
                    event_data.get('confidence', 0.5)
                ))
                
                event_id = cursor.lastrowid
                
                # 自动创建提醒任务
                event_time_str = event_data.get('time')
                if event_time_str:
                    try:
                        event_time = _parse_event_time(event_time_str)
                        if event_time:
                            reminder_time = event_time - timedelta(minutes=30)
                            cursor.execute("""
                                INSERT INTO reminder_tasks 
                                (event_id, user_id, reminder_time, advance_minutes, reminder_method)
                                VALUES (%s, %s, %s, %s, %s)
                            """, (event_id, user_id, reminder_time, 30, 'web'))
                    except:
                        pass  # 如果时间解析失败，跳过创建提醒
                
                # 写入归档表
                try:
                    cursor.execute("""
                        INSERT INTO event_archive 
                        (user_id, event_id, event_title, event_time, event_location,
                         completion_status, completion_time, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW(), NOW())
                    """, (
                        user_id, event_id,
                        event_data['title'],
                        event_data.get('time'),
                        event_data.get('location', {}).get('standard', '') or event_data.get('location', {}).get('original', ''),
                        'completed'
                    ))
                except:
                    pass  # 归档表写入失败不影响主流程

                # 冲突检测（在 commit 之前）
                conflict_info = {'has_conflict': False, 'conflict_level': 'none', 'conflicts': [], 'message': ''}
                if conflict_detector and event_time_obj:
                    try:
                        conflict_info = conflict_detector.check_conflicts(user_id, event_time_obj, 120, event_id)
                        if conflict_info['has_conflict']:
                            cursor.execute("UPDATE text_events SET has_conflict = TRUE WHERE event_id = %s", (event_id,))
                    except Exception as ce:
                        print(f'冲突检测失败: {ce}')

                conn.commit()
                cursor.close()
                conn.close()

                return jsonify({
                    'success': True,
                    'message': '事件已确认并保存',
                    'event_id': event_id,
                    'is_duplicate': False,
                    'has_conflict': conflict_info['has_conflict'],
                    'conflict_level': conflict_info.get('conflict_level', 'none'),
                    'conflict_message': conflict_info.get('message', ''),
                    'conflicts': conflict_info.get('conflicts', [])
                })
        
        except Exception as e:
            return jsonify({'success': False, 'message': f'保存失败: {str(e)}'}), 500
    
    
    @app.route('/api/xtu/checkConflict', methods=['POST'])
    @login_required
    def xtu_check_conflict():
        """检查事件时间冲突"""
        try:
            user_id = request.current_user['user_id']
            event_time_str = request.json.get('event_time')
            event_id = request.json.get('event_id')  # 排除自身（更新时用）

            if not event_time_str:
                return jsonify({'success': True, 'has_conflict': False, 'conflicts': []})

            event_time_obj = _parse_event_time(event_time_str)
            if not event_time_obj:
                return jsonify({'success': True, 'has_conflict': False, 'conflicts': []})

            if not conflict_detector:
                return jsonify({'success': True, 'has_conflict': False, 'conflicts': []})

            result = conflict_detector.check_conflicts(user_id, event_time_obj, 120, event_id)
            return jsonify({
                'success': True,
                'has_conflict': result['has_conflict'],
                'conflict_level': result.get('conflict_level', 'none'),
                'conflicts': result.get('conflicts', []),
                'message': result.get('message', '')
            })
        except Exception as e:
            return jsonify({'success': False, 'message': f'冲突检测失败: {str(e)}'}), 500


    @app.route('/api/xtu/deleteEvent', methods=['POST'])
    @login_required
    def xtu_delete_event():
        """删除事件（同时删除关联的提醒任务和归档记录）"""
        try:
            user_id = request.current_user['user_id']
            event_id = request.json.get('event_id')
            if not event_id:
                return jsonify({'success': False, 'message': '缺少 event_id'}), 400

            conn = get_db_connection()
            cursor = conn.cursor()

            # 验证归属
            cursor.execute("SELECT event_id FROM text_events WHERE event_id = %s AND user_id = %s", (event_id, user_id))
            if not cursor.fetchone():
                cursor.close()
                conn.close()
                return jsonify({'success': False, 'message': '事件不存在或无权限'}), 404

            # 级联删除（外键 ON DELETE CASCADE 会自动删 reminder_tasks，但归档表用软删除）
            cursor.execute("DELETE FROM event_archive WHERE event_id = %s AND user_id = %s", (event_id, user_id))
            cursor.execute("DELETE FROM text_events WHERE event_id = %s AND user_id = %s", (event_id, user_id))

            conn.commit()
            cursor.close()
            conn.close()

            return jsonify({'success': True, 'message': '事件已删除'})

        except Exception as e:
            return jsonify({'success': False, 'message': f'删除失败: {str(e)}'}), 500


    @app.route('/api/xtu/searchLocation', methods=['GET'])
    @login_required
    def xtu_search_location():
        """搜索湘大地点"""
        try:
            keyword = request.args.get('keyword', '')
            
            if not keyword:
                return jsonify({'success': False, 'message': '搜索关键词不能为空'}), 400
            
            mapper = get_location_mapper()
            results = mapper.search_location(keyword)
            
            return jsonify({
                'success': True,
                'results': results
            })
        
        except Exception as e:
            return jsonify({'success': False, 'message': f'搜索失败: {str(e)}'}), 500
    
    
    @app.route('/api/xtu/getAllLocations', methods=['GET'])
    @login_required
    def xtu_get_all_locations():
        """获取所有湘大标准地点"""
        try:
            mapper = get_location_mapper()
            locations = mapper.get_all_locations()
            
            return jsonify({
                'success': True,
                'locations': locations
            })
        
        except Exception as e:
            return jsonify({'success': False, 'message': f'获取地点列表失败: {str(e)}'}), 500
    
    
    @app.route('/api/xtu/statistics', methods=['GET'])
    @login_required
    def xtu_get_statistics():
        """获取湘大任务统计"""
        try:
            user_id = request.current_user['user_id']
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # 获取事件统计
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN is_confirmed = TRUE THEN 1 ELSE 0 END) as confirmed,
                    SUM(CASE WHEN is_confirmed = FALSE THEN 1 ELSE 0 END) as pending
                FROM text_events 
                WHERE user_id = %s
            """, (user_id,))
            
            event_stats = cursor.fetchone()
            
            # 获取提醒统计
            cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'reminded' THEN 1 ELSE 0 END) as reminded
                FROM reminders 
                WHERE user_id = %s AND deleted_at IS NULL
            """, (user_id,))
            
            reminder_stats = cursor.fetchone()
            
            # 获取活动类型分布
            cursor.execute("""
                SELECT activity_type, COUNT(*) as count
                FROM text_events
                WHERE user_id = %s AND deleted_at IS NULL
                GROUP BY activity_type
                ORDER BY count DESC
                LIMIT 10
            """, (user_id,))
            
            activity_distribution = [
                {'type': row[0], 'count': row[1]} 
                for row in cursor.fetchall()
            ]
            
            # 计算完成率
            completion_rate = 0
            if reminder_stats and reminder_stats[0] > 0:
                completion_rate = round((reminder_stats[1] / reminder_stats[0]) * 100, 1)
            
            cursor.close()
            conn.close()
            
            return jsonify({
                'success': True,
                'data': {
                    'events': {
                        'total': event_stats[0] if event_stats else 0,
                        'confirmed': event_stats[1] if event_stats else 0,
                        'pending': event_stats[2] if event_stats else 0
                    },
                    'reminders': {
                        'total': reminder_stats[0] if reminder_stats else 0,
                        'completed': reminder_stats[1] if reminder_stats else 0,
                        'pending': reminder_stats[2] if reminder_stats else 0,
                        'reminded': reminder_stats[3] if reminder_stats else 0
                    },
                    'completion_rate': completion_rate,
                    'activity_distribution': activity_distribution
                }
            })
        
        except Exception as e:
            return jsonify({'success': False, 'message': f'获取统计失败: {str(e)}'}), 500
    
    
