"""
湘潭大学增强事件提取器
支持提取更多维度的信息
"""

import re
from datetime import datetime, timedelta
from xtu_location_mapper import get_location_mapper


class XTUEventExtractor:
    def __init__(self):
        self.location_mapper = get_location_mapper()
        self.batch_separator_patterns = [
            r'\n\n+',  # 双换行分隔
            r'\d+[、\.\)）]',  # 数字序号分隔
            r'[一二三四五六七八九十]+[、\.]',  # 中文序号分隔
        ]
        
        # 活动类型关键词
        self.activity_types = {
            '竞赛': ['竞赛', '比赛', '大赛', '竞技', '挑战赛', '选拔赛'],
            '讲座': ['讲座', '报告', '宣讲', '演讲', '分享会', '座谈'],
            '招聘': ['招聘', '宣讲会', '双选会', '面试', '应聘'],
            '会议': ['会议', '研讨会', '交流会', '讨论会', '座谈会'],
            '缴费': ['缴费', '缴纳', '交费', '费用', '收费'],
            '体检': ['体检', '健康检查', '体格检查', '医疗检查'],
            '考试': ['考试', '测试', '测验', '考核'],
            '培训': ['培训', '训练', '学习班', '研修'],
            '活动': ['活动', '联谊', '文艺', '晚会', '表演'],
            '通知': ['通知', '公告', '说明', '提醒'],
        }
        
        # 主办单位关键词
        self.organizer_keywords = [
            '主办', '承办', '协办', '组织', '发起', '举办',
            '单位', '部门', '学院', '协会', '社团', '中心'
        ]
        
        # 面向人群关键词
        self.audience_keywords = {
            '全体': ['全体', '全校', '全院', '所有'],
            '年级': ['2020级', '2021级', '2022级', '2023级', '2024级', '2025级', '2026级',
                    '大一', '大二', '大三', '大四', '研一', '研二', '研三'],
            '专业': ['计算机', '软件', '数学', '物理', '化学', '生物', '文学', '经济', '管理'],
            '学生': ['学生', '同学', '师生'],
            '教职工': ['教师', '职工', '教职工', '老师'],
        }
        
        # 循环事件关键词
        self.recurring_patterns = {
            '每天': {'type': 'daily', 'interval': 1},
            '每周': {'type': 'weekly', 'interval': 1},
            '每月': {'type': 'monthly', 'interval': 1},
            '每周一': {'type': 'weekly', 'weekday': 0},
            '每周二': {'type': 'weekly', 'weekday': 1},
            '每周三': {'type': 'weekly', 'weekday': 2},
            '每周四': {'type': 'weekly', 'weekday': 3},
            '每周五': {'type': 'weekly', 'weekday': 4},
            '每周六': {'type': 'weekly', 'weekday': 5},
            '每周日': {'type': 'weekly', 'weekday': 6},
        }
    
    def extract_enhanced(self, text):
        """
        增强版事件提取
        
        Args:
            text: 原始文本
            
        Returns:
            dict: 包含所有提取字段的字典
        """
        result = {
            'title': '',
            'deadline': None,
            'time': None,
            'location': '',
            'location_standard': '',
            'location_confidence': 0,
            'location_warning': None,
            'organizer': '',
            'activity_type': '通知',
            'audience': '',
            'contact': '',
            'is_recurring': False,
            'recurring_pattern': None,
            'required_fields_missing': [],
            'confidence': 0.5,
        }
        
        # 1. 提取标题（取第一句或前30个字符）
        result['title'] = self._extract_title(text)
        
        # 2. 提取时间
        time_info = self._extract_time(text)
        result['time'] = time_info.get('time')
        result['deadline'] = time_info.get('deadline')
        result['is_recurring'] = time_info.get('is_recurring', False)
        result['recurring_pattern'] = time_info.get('recurring_pattern')
        
        # 3. 提取地点并标准化
        location_info = self._extract_location(text)
        result['location'] = location_info['original']
        result['location_standard'] = location_info['standard']
        result['location_confidence'] = location_info['confidence']
        result['location_warning'] = location_info['warning']
        
        # 4. 提取主办单位
        result['organizer'] = self._extract_organizer(text)
        
        # 5. 识别活动类型
        result['activity_type'] = self._identify_activity_type(text)
        
        # 6. 识别面向人群
        result['audience'] = self._extract_audience(text)
        
        # 7. 提取联系方式
        result['contact'] = self._extract_contact(text)
        
        # 8. 检查必填项
        result['required_fields_missing'] = self._check_required_fields(result)
        
        # 9. 计算综合置信度
        result['confidence'] = self._calculate_confidence(result)
        
        return result
    
    def extract_batch(self, text):
        """
        批量提取多个事件
        
        Args:
            text: 包含多个事件的文本
            
        Returns:
            list: 包含多个事件字典的列表
        """
        events = []
        
        # 尝试分段
        segments = self._split_text_into_segments(text)
        
        # 如果只有一段，直接提取
        if len(segments) <= 1:
            single_event = self.extract_enhanced(text)
            single_event['original_text'] = text
            return [single_event]
        
        # 对每一段进行提取
        for segment in segments:
            segment = segment.strip()
            if len(segment) < 20:  # 忽略太短的段落
                continue
            
            # 检查是否包含时间信息（用于判断是否是事件）
            if re.search(r'\d{1,2}[月/-]\d{1,2}|\d{1,2}:\d{2}|周[一二三四五六日]', segment):
                event = self.extract_enhanced(segment)
                event['original_text'] = segment
                
                # 如果标题太短或为空，尝试从段落中提取更好的标题
                if not event['title'] or len(event['title']) < 5:
                    event['title'] = self._extract_title_from_segment(segment)
                
                events.append(event)
        
        # 如果没有提取到任何事件，返回整体提取结果
        if not events:
            single_event = self.extract_enhanced(text)
            single_event['original_text'] = text
            return [single_event]
        
        return events
    
    def _split_text_into_segments(self, text):
        """将文本分割成多个段落"""
        # 先按双换行分割
        segments = re.split(r'\n\n+', text)
        
        # 如果段落太少，尝试按序号分割
        if len(segments) <= 1:
            # 尝试数字序号
            if re.search(r'\d+[、\.\)）]', text):
                segments = re.split(r'(?=\d+[、\.\)）])', text)
            # 尝试中文序号
            elif re.search(r'[一二三四五六七八九十]+[、\.]', text):
                segments = re.split(r'(?=[一二三四五六七八九十]+[、\.])', text)
        
        return [s.strip() for s in segments if s.strip()]
    
    def _extract_title_from_segment(self, segment):
        """从段落中提取更好的标题"""
        # 移除序号
        segment = re.sub(r'^[\d一二三四五六七八九十]+[、\.\)）]\s*', '', segment)
        
        # 提取第一句话
        first_sentence = segment.split('。')[0].split('\n')[0].strip()
        
        # 如果太长，截取前30个字符
        if len(first_sentence) > 30:
            first_sentence = first_sentence[:30] + '...'
        
        return first_sentence if first_sentence else '待补充'
    
    def _extract_title(self, text):
        """提取标题"""
        # 去除空白字符
        text = text.strip()
        
        # 尝试识别标题模式
        # 1. 匹配【标题】或《标题》
        title_patterns = [
            r'【([^】]+)】',
            r'《([^》]+)》',
            r'关于(.{5,30})的(?:通知|公告|说明)',
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        # 2. 取第一行或第一句
        first_line = text.split('\n')[0].strip()
        if len(first_line) <= 50 and len(first_line) >= 5:
            return first_line
        
        # 3. 取前30个字符
        return text[:30] + ('...' if len(text) > 30 else '')
    
    def _extract_time(self, text):
        """提取时间信息"""
        import jieba
        
        result = {
            'time': None,
            'deadline': None,
            'is_recurring': False,
            'recurring_pattern': None
        }
        
        # 1. 检查是否是循环事件
        for pattern_text, pattern_info in self.recurring_patterns.items():
            if pattern_text in text:
                result['is_recurring'] = True
                result['recurring_pattern'] = pattern_info
                break
        
        # 2. 提取具体时间
        # 匹配日期时间模式
        date_patterns = [
            r'(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{2})',
            r'(\d{4})-(\d{1,2})-(\d{1,2})\s+(\d{1,2}):(\d{2})',
            r'(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{2})',
            r'(\d{1,2})月(\d{1,2})日',
        ]
        
        current_year = datetime.now().year
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                groups = match.groups()
                try:
                    if len(groups) == 5:
                        # 完整日期时间
                        year, month, day, hour, minute = groups
                        dt = datetime(int(year), int(month), int(day), int(hour), int(minute))
                    elif len(groups) == 4:
                        # 月日时分
                        month, day, hour, minute = groups
                        dt = datetime(current_year, int(month), int(day), int(hour), int(minute))
                    elif len(groups) == 2:
                        # 只有月日
                        month, day = groups
                        dt = datetime(current_year, int(month), int(day), 9, 0)  # 默认9点
                    else:
                        continue
                    
                    result['time'] = dt.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # 检查是否是截止时间
                    if '截止' in text or '之前' in text or '前' in text:
                        result['deadline'] = result['time']
                    
                    break
                except:
                    continue
        
        return result
    
    def _extract_location(self, text):
        """提取并标准化地点"""
        # 常见地点指示词
        location_indicators = ['在', '于', '地点', '位置', '场所', '举行', '举办']
        
        # 尝试提取地点
        location_text = ''
        
        # 方法1: 寻找地点指示词后的内容
        for indicator in location_indicators:
            pattern = f'{indicator}([^。，,;；\n]+?)(?:[。，,;；\n举行举办]|$)'
            match = re.search(pattern, text)
            if match:
                location_text = match.group(1).strip()
                break
        
        # 方法2: 直接匹配常见地点名称模式
        if not location_text:
            location_pattern = r'((?:逸夫|信科|研[AB]|图书馆|体育馆|学活|教学楼|食堂)[^\s。，,;；\n]{0,10})'
            match = re.search(location_pattern, text)
            if match:
                location_text = match.group(1).strip()
        
        # 标准化地点
        if location_text:
            std_result = self.location_mapper.standardize_location(location_text)
            return {
                'original': location_text,
                'standard': std_result['standard_name'],
                'confidence': std_result['confidence'],
                'warning': std_result['warning']
            }
        
        return {
            'original': '',
            'standard': '待补充',
            'confidence': 0,
            'warning': '未识别到地点信息'
        }
    
    def _extract_organizer(self, text):
        """提取主办单位"""
        for keyword in self.organizer_keywords:
            pattern = f'{keyword}[:：]?([^。，,;\n]+)'
            match = re.search(pattern, text)
            if match:
                organizer = match.group(1).strip()
                # 清理过长的内容
                if len(organizer) <= 50:
                    return organizer
        
        # 尝试识别学院名称
        college_pattern = r'([^\s]{2,10}(?:学院|中心|部门|协会|社团))'
        match = re.search(college_pattern, text)
        if match:
            return match.group(1)
        
        return '待补充'
    
    def _identify_activity_type(self, text):
        """识别活动类型"""
        for activity_type, keywords in self.activity_types.items():
            for keyword in keywords:
                if keyword in text:
                    return activity_type
        return '通知'
    
    def _extract_audience(self, text):
        """提取面向人群"""
        audiences = []
        
        for category, keywords in self.audience_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    audiences.append(keyword)
                    break
        
        if audiences:
            return '、'.join(audiences)
        return '相关人员'
    
    def _extract_contact(self, text):
        """提取联系方式"""
        contacts = []
        
        # 1. 提取电话号码
        phone_pattern = r'(?:电话|联系电话|手机|联系方式)[:：]?\s*(\d{11}|\d{3,4}[-\s]?\d{7,8})'
        phone_matches = re.findall(phone_pattern, text)
        contacts.extend(phone_matches)
        
        # 2. 提取QQ号/QQ群
        qq_pattern = r'(?:QQ|qq|扣扣)[群号]?[:：]?\s*(\d{5,12})'
        qq_matches = re.findall(qq_pattern, text)
        contacts.extend([f'QQ:{qq}' for qq in qq_matches])
        
        # 3. 提取邮箱
        email_pattern = r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})'
        email_matches = re.findall(email_pattern, text)
        contacts.extend(email_matches)
        
        # 4. 提取网址
        url_pattern = r'(https?://[^\s]+)'
        url_matches = re.findall(url_pattern, text)
        contacts.extend(url_matches)
        
        if contacts:
            return ' | '.join(contacts[:3])  # 最多返回3个联系方式
        return '待补充'
    
    def _check_required_fields(self, result):
        """检查必填项"""
        missing = []
        
        if not result['title'] or result['title'] == '待补充':
            missing.append('标题')
        
        if not result['time']:
            missing.append('时间')
        
        if result['location_standard'] == '待补充':
            missing.append('地点')
        
        if result['activity_type'] == '通知':
            missing.append('活动类型')
        
        return missing
    
    def _calculate_confidence(self, result):
        """计算综合置信度"""
        score = 0
        total = 0
        
        # 标题 (20分)
        total += 20
        if result['title'] and result['title'] != '待补充':
            score += 20
        
        # 时间 (25分)
        total += 25
        if result['time']:
            score += 25
        
        # 地点 (20分)
        total += 20
        if result['location_standard'] and result['location_standard'] != '待补充':
            score += result['location_confidence'] * 20
        
        # 主办单位 (10分)
        total += 10
        if result['organizer'] != '待补充':
            score += 10
        
        # 活动类型 (10分)
        total += 10
        if result['activity_type'] != '通知':
            score += 10
        
        # 联系方式 (10分)
        total += 10
        if result['contact'] != '待补充':
            score += 10
        
        # 面向人群 (5分)
        total += 5
        if result['audience'] != '相关人员':
            score += 5
        
        return round(score / total, 2) if total > 0 else 0.5


# 单例
_extractor_instance = None

def get_extractor():
    """获取提取器单例"""
    global _extractor_instance
    if _extractor_instance is None:
        _extractor_instance = XTUEventExtractor()
    return _extractor_instance


if __name__ == '__main__':
    # 测试
    extractor = XTUEventExtractor()
    
    test_text = """
    关于举办2026年"互联网+"大学生创新创业大赛的通知
    
    各学院：
    为激发学生创新创业热情，定于2026年4月18日 14:00在逸夫楼一阶举行
    2026年"互联网+"大学生创新创业大赛宣讲会。
    
    主办单位：教务处、创新创业学院
    参加对象：全体本科生
    联系电话：13800138000
    QQ群：123456789
    
    请各学院组织学生准时参加。
    """
    
    result = extractor.extract_enhanced(test_text)
    
    print("=" * 60)
    print("增强事件提取测试")
    print("=" * 60)
    print(f"\n标题: {result['title']}")
    print(f"时间: {result['time']}")
    print(f"地点: {result['location_standard']} (原始: {result['location']})")
    print(f"地点置信度: {result['location_confidence']:.2f}")
    if result['location_warning']:
        print(f"地点警告: {result['location_warning']}")
    print(f"主办单位: {result['organizer']}")
    print(f"活动类型: {result['activity_type']}")
    print(f"面向人群: {result['audience']}")
    print(f"联系方式: {result['contact']}")
    print(f"是否循环: {result['is_recurring']}")
    print(f"综合置信度: {result['confidence']:.2f}")
    print(f"缺失字段: {', '.join(result['required_fields_missing']) if result['required_fields_missing'] else '无'}")
