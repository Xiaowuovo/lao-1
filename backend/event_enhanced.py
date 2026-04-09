import re
from datetime import datetime, timedelta
import jieba
import jieba.posseg as pseg
from typing import Dict, List, Optional, Tuple

class EnhancedEventExtractor:
    def __init__(self):
        self.time_patterns = [
            r'(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2})[::：](\d{2})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2})[::：](\d{2})',
            r'(\d{1,2})月(\d{1,2})日\s*(\d{1,2})[::：](\d{2})',
            r'(\d{4})/(\d{1,2})/(\d{1,2})\s+(\d{1,2})[::：](\d{2})',
        ]
        
        # 截止时间模式
        self.deadline_patterns = [
            r'(\d{1,2})月(\d{1,2})日[之前前]*[截止结束]',
            r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})日?[之前前]*[截止结束]',
            r'[截止结束]时间[：:]\s*(\d{1,2})月(\d{1,2})日',
            r'[截止结束]日期[：:]\s*(\d{1,2})月(\d{1,2})日',
        ]
        
        # 循环时间模式
        self.recurring_patterns = {
            r'每(周|星期)([一二三四五六日天1-7])': 'weekly',
            r'每天': 'daily',
            r'每月(\d{1,2})号': 'monthly',
            r'每年(\d{1,2})月(\d{1,2})日': 'yearly',
        }
        
        self.location_keywords = ['教室', '楼', '馆', '厅', '室', '场', '中心', '广场', '操场', '礼堂', '报告厅', '会议室']
        
        # 活动类型关键词
        self.activity_type_keywords = {
            'competition': ['竞赛', '比赛', '大赛', '挑战赛', '选拔赛', '初赛', '复赛', '决赛'],
            'lecture': ['讲座', '报告', '演讲', '宣讲', '培训', '研讨'],
            'recruitment': ['招聘', '面试', '宣讲会', '双选会', '招聘会'],
            'meeting': ['会议', '座谈', '交流会', '例会', '大会'],
            'payment': ['缴费', '收费', '交费', '费用', '学费', '报名费'],
            'health_check': ['体检', '检查', '健康', '医疗'],
        }
        
        # 待办分类关键词
        self.task_category_keywords = {
            'study': ['课程', '作业', '考试', '测验', '复习', '学习', '答辩'],
            'competition': ['竞赛', '比赛', '大赛'],
            'administrative': ['通知', '会议', '报名', '审核', '申请'],
            'life': ['缴费', '体检', '领取', '办理'],
        }
        
        # 面向人群模式
        self.audience_patterns = [
            r'(全体[\u4e00-\u9fff]+)',
            r'([\u4e00-\u9fff]+学院[\u4e00-\u9fff]*)',
            r'([\u4e00-\u9fff]+专业[\u4e00-\u9fff]*)',
            r'([\u4e00-\u9fff]+班[\u4e00-\u9fff]*)',
            r'(\d{4}级[\u4e00-\u9fff]*)',
            r'([大一二三四][\u4e00-\u9fff]*)',
            r'([\u4e00-\u9fff]*[研本专]科生)',
        ]
        
        # 联系方式模式
        self.contact_patterns = {
            'phone': r'1[3-9]\d{9}',
            'qq': r'QQ[群号：:\s]*(\d{5,})',
            'email': r'[\w\.-]+@[\w\.-]+\.\w+',
            'wechat': r'微信[号：:\s]*([\w-]+)',
            'url': r'https?://[^\s]+',
        }
        
        jieba.initialize()
    
    def extract_events(self, text: str) -> List[Dict]:
        """提取多个事件"""
        events = []
        lines = text.split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            event = self._extract_single_event(line, text)
            if event:
                events.append(event)
        
        return events
    
    def _extract_single_event(self, line: str, full_text: str = None) -> Optional[Dict]:
        """提取单个事件的增强版本"""
        time_info = self._extract_time(line)
        if not time_info:
            return None
        
        # 基础信息提取
        location = self._extract_location(line)
        target = self._extract_target(line)
        title = self._extract_title(line, time_info)
        
        # 新增字段提取
        deadline_time = self._extract_deadline(line)
        organizer = self._extract_organizer(line)
        activity_type = self._classify_activity_type(line)
        task_category = self._classify_task_category(line)
        target_audience = self._extract_audience(line)
        contact_info = self._extract_contact_info(line)
        
        # 检查循环模式
        recurring_info = self._extract_recurring_pattern(line)
        
        # 必填字段检查
        missing_fields = self._check_missing_fields({
            'time': time_info,
            'title': title,
            'location': location,
        })
        
        confidence = self._calculate_confidence(
            time_info, location, title, organizer, activity_type
        )
        
        event = {
            'time': time_info['datetime'].strftime('%Y-%m-%d %H:%M'),
            'title': title,
            'location': location,
            'target': target,
            'deadline_time': deadline_time,
            'organizer': organizer,
            'activity_type': activity_type,
            'task_category': task_category,
            'target_audience': target_audience,
            'contact_info': contact_info,
            'is_recurring': recurring_info['is_recurring'],
            'recurring_pattern': recurring_info['pattern'],
            'confidence': confidence,
            'original_text': line,
            'missing_fields': missing_fields,
            'needs_confirmation': len(missing_fields) > 0 or confidence < 0.7
        }
        
        return event
    
    def _extract_deadline(self, text: str) -> Optional[str]:
        """提取截止时间"""
        current_year = datetime.now().year
        
        for pattern in self.deadline_patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                try:
                    if len(groups) == 2:
                        month, day = int(groups[0]), int(groups[1])
                        deadline = datetime(current_year, month, day, 23, 59)
                    elif len(groups) == 3:
                        year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
                        deadline = datetime(year, month, day, 23, 59)
                    else:
                        continue
                    
                    return deadline.strftime('%Y-%m-%d %H:%M')
                except ValueError:
                    continue
        
        return None
    
    def _extract_organizer(self, text: str) -> str:
        """提取主办/承办单位"""
        organizer_patterns = [
            r'[主承协]办[单位方]*[：:]\s*([\u4e00-\u9fff]+)',
            r'([\u4e00-\u9fff]*学院)主办',
            r'([\u4e00-\u9fff]*部门?)举办',
            r'由([\u4e00-\u9fff]+)[主承]办',
        ]
        
        for pattern in organizer_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return '待确认'
    
    def _classify_activity_type(self, text: str) -> str:
        """分类活动类型"""
        for activity_type, keywords in self.activity_type_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return activity_type
        return 'other'
    
    def _classify_task_category(self, text: str) -> str:
        """分类待办事务"""
        for category, keywords in self.task_category_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return category
        return 'custom'
    
    def _extract_audience(self, text: str) -> str:
        """提取面向人群"""
        for pattern in self.audience_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return '相关人员'
    
    def _extract_contact_info(self, text: str) -> Dict[str, List[str]]:
        """提取联系方式"""
        contacts = {}
        
        for contact_type, pattern in self.contact_patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                if isinstance(matches[0], tuple):
                    contacts[contact_type] = [m for m in matches if m]
                else:
                    contacts[contact_type] = matches
        
        return contacts if contacts else {}
    
    def _extract_recurring_pattern(self, text: str) -> Dict:
        """提取循环模式"""
        for pattern, pattern_type in self.recurring_patterns.items():
            match = re.search(pattern, text)
            if match:
                if pattern_type == 'weekly':
                    weekday_map = {
                        '一': 1, '二': 2, '三': 3, '四': 4, 
                        '五': 5, '六': 6, '日': 7, '天': 7,
                        '1': 1, '2': 2, '3': 3, '4': 4,
                        '5': 5, '6': 6, '7': 7
                    }
                    weekday = weekday_map.get(match.group(2), 1)
                    return {
                        'is_recurring': True,
                        'pattern': f'weekly_{weekday}',
                        'description': f'每周{match.group(2)}'
                    }
                elif pattern_type == 'daily':
                    return {
                        'is_recurring': True,
                        'pattern': 'daily',
                        'description': '每天'
                    }
                elif pattern_type == 'monthly':
                    day = match.group(1)
                    return {
                        'is_recurring': True,
                        'pattern': f'monthly_{day}',
                        'description': f'每月{day}号'
                    }
        
        return {'is_recurring': False, 'pattern': None, 'description': None}
    
    def _check_missing_fields(self, fields: Dict) -> List[str]:
        """检查缺失的必填字段"""
        missing = []
        
        if not fields.get('time'):
            missing.append('time')
        
        if not fields.get('title') or fields.get('title') == '未命名事件':
            missing.append('title')
        
        location = fields.get('location', '')
        if not location or location == '待确认':
            missing.append('location')
        
        return missing
    
    def _extract_time(self, text: str) -> Optional[Dict]:
        """提取时间（原有方法）"""
        current_year = datetime.now().year
        
        for pattern in self.time_patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                
                if len(groups) == 5:
                    year = int(groups[0])
                    month = int(groups[1])
                    day = int(groups[2])
                    hour = int(groups[3])
                    minute = int(groups[4])
                elif len(groups) == 4:
                    year = current_year
                    month = int(groups[0])
                    day = int(groups[1])
                    hour = int(groups[2])
                    minute = int(groups[3])
                else:
                    continue
                
                try:
                    dt = datetime(year, month, day, hour, minute)
                    return {
                        'datetime': dt,
                        'matched_text': match.group(0)
                    }
                except ValueError:
                    continue
        
        relative_time = self._extract_relative_time(text)
        if relative_time:
            return relative_time
        
        return None
    
    def _extract_relative_time(self, text: str) -> Optional[Dict]:
        """提取相对时间"""
        now = datetime.now()
        
        if '今天' in text or '今日' in text:
            match = re.search(r'(\d{1,2})[::：](\d{2})', text)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2))
                dt = datetime(now.year, now.month, now.day, hour, minute)
                return {'datetime': dt, 'matched_text': match.group(0)}
        
        if '明天' in text:
            tomorrow = now + timedelta(days=1)
            match = re.search(r'(\d{1,2})[::：](\d{2})', text)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2))
                dt = datetime(tomorrow.year, tomorrow.month, tomorrow.day, hour, minute)
                return {'datetime': dt, 'matched_text': match.group(0)}
        
        if '下周' in text:
            next_week = now + timedelta(days=7)
            match = re.search(r'(\d{1,2})[::：](\d{2})', text)
            if match:
                hour = int(match.group(1))
                minute = int(match.group(2))
                dt = datetime(next_week.year, next_week.month, next_week.day, hour, minute)
                return {'datetime': dt, 'matched_text': match.group(0)}
        
        return None
    
    def _extract_location(self, text: str) -> str:
        """提取地点"""
        for keyword in self.location_keywords:
            pattern = r'[\w\u4e00-\u9fff]*' + keyword
            matches = re.findall(pattern, text)
            if matches:
                longest_match = max(matches, key=len)
                if len(longest_match) > len(keyword):
                    return longest_match
        
        loc_patterns = [
            r'([A-Z]\d+|[A-Z]-\d+)',
            r'(\d+号楼\d+)',
            r'(第[一二三四五六七八九十]+教学楼)',
        ]
        
        for pattern in loc_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return '待确认'
    
    def _extract_target(self, text: str) -> str:
        """提取对象"""
        target_patterns = [
            r'(全体[\u4e00-\u9fff]+)',
            r'([\u4e00-\u9fff]+学院[\u4e00-\u9fff]*)',
            r'([\u4e00-\u9fff]+专业[\u4e00-\u9fff]*)',
            r'([\u4e00-\u9fff]+班[\u4e00-\u9fff]*)',
            r'(\d+级[\u4e00-\u9fff]*)',
        ]
        
        for pattern in target_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        
        return '相关人员'
    
    def _extract_title(self, text: str, time_info: Dict) -> str:
        """提取标题"""
        time_text = time_info['matched_text']
        
        parts = re.split(r'[，。,\.]', text)
        for part in parts:
            if time_text in part:
                cleaned = part.replace(time_text, '').strip()
                cleaned = re.sub(r'^[：:、\s]+', '', cleaned)
                cleaned = re.sub(r'[：:、\s]+$', '', cleaned)
                
                if len(cleaned) > 2 and len(cleaned) < 50:
                    return cleaned
        
        words = pseg.cut(text)
        nouns = []
        for word, flag in words:
            if flag.startswith('n') or flag.startswith('v'):
                nouns.append(word)
        
        if nouns:
            title_candidates = ''.join(nouns[:5])
            if len(title_candidates) > 2:
                return title_candidates[:30]
        
        cleaned_text = text.replace(time_text, '').strip()
        if len(cleaned_text) > 2:
            return cleaned_text[:30]
        
        return '未命名事件'
    
    def _calculate_confidence(self, time_info, location, title, organizer, activity_type) -> float:
        """计算置信度"""
        confidence = 0.3
        
        if time_info:
            confidence += 0.25
        
        if location and location != '待确认':
            confidence += 0.15
        
        if title and title != '未命名事件' and len(title) > 2:
            confidence += 0.15
        
        if organizer and organizer != '待确认':
            confidence += 0.1
        
        if activity_type and activity_type != 'other':
            confidence += 0.05
        
        return min(confidence, 1.0)
