import re
from datetime import datetime, timedelta
import jieba
import jieba.posseg as pseg

class EventExtractor:
    def __init__(self):
        self.time_patterns = [
            r'(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2})[::：](\d{2})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2})[::：](\d{2})',
            r'(\d{1,2})月(\d{1,2})日\s*(\d{1,2})[::：](\d{2})',
            r'(\d{4})/(\d{1,2})/(\d{1,2})\s+(\d{1,2})[::：](\d{2})',
        ]
        
        self.location_keywords = ['教室', '楼', '馆', '厅', '室', '场', '中心', '广场', '操场', '礼堂', '报告厅', '会议室']
        self.event_keywords = {
            'academic': ['讲座', '报告', '课程', '培训', '研讨', '论坛', '学术'],
            'meeting': ['会议', '座谈', '交流会', '班会', '例会'],
            'exam': ['考试', '测验', '考核', '答辩', '复试'],
            'activity': ['活动', '比赛', '竞赛', '演出', '表演', '典礼', '晚会', '运动会'],
            'other': []
        }
        
        jieba.initialize()
    
    def extract_events(self, text):
        events = []
        lines = text.split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            event = self._extract_single_event(line)
            if event:
                events.append(event)
        
        return events
    
    def _extract_single_event(self, text):
        time_info = self._extract_time(text)
        if not time_info:
            return None
        
        location = self._extract_location(text)
        target = self._extract_target(text)
        title = self._extract_title(text, time_info)
        event_type = self._classify_event_type(text)
        
        confidence = self._calculate_confidence(time_info, location, title)
        
        return {
            'time': time_info['datetime'].strftime('%Y-%m-%d %H:%M'),
            'title': title,
            'location': location,
            'target': target,
            'event_type': event_type,
            'confidence': confidence,
            'original_text': text
        }
    
    def _extract_time(self, text):
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
    
    def _extract_relative_time(self, text):
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
    
    def _extract_location(self, text):
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
    
    def _extract_target(self, text):
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
    
    def _extract_title(self, text, time_info):
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
    
    def _classify_event_type(self, text):
        for event_type, keywords in self.event_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return event_type
        return 'other'
    
    def _calculate_confidence(self, time_info, location, title):
        confidence = 0.5
        
        if time_info:
            confidence += 0.3
        
        if location and location != '待确认':
            confidence += 0.1
        
        if title and title != '未命名事件' and len(title) > 2:
            confidence += 0.1
        
        return min(confidence, 1.0)
