"""
湘潭大学地点标准化模块
用于将各种地点表述统一映射到标准化地点名称
"""

class XTULocationMapper:
    def __init__(self):
        # 湘潭大学标准地点数据库
        self.location_database = {
            # 教学楼
            '逸夫楼': {
                'standard': '逸夫楼',
                'aliases': ['逸夫', 'YF'],
                'rooms': {
                    '一阶': '逸夫楼第一阶梯教室',
                    '二阶': '逸夫楼第二阶梯教室',
                    '三阶': '逸夫楼第三阶梯教室',
                    '1阶': '逸夫楼第一阶梯教室',
                    '2阶': '逸夫楼第二阶梯教室',
                    '3阶': '逸夫楼第三阶梯教室',
                }
            },
            '信科北': {
                'standard': '信息科技大楼北楼',
                'aliases': ['信科北楼', '信科北', '信息科技北', '信科大楼北'],
                'pattern': r'(\d{3,4})',  # 匹配房间号
                'room_format': '信息科技大楼北{room}'
            },
            '信科南': {
                'standard': '信息科技大楼南楼',
                'aliases': ['信科南楼', '信科南', '信息科技南'],
                'pattern': r'(\d{3,4})',
                'room_format': '信息科技大楼南{room}'
            },
            '研A': {
                'standard': '研究生院A楼',
                'aliases': ['研A楼', '研究生A', '研A'],
                'pattern': r'(\d{3,4})',
                'room_format': '研究生院A{room}'
            },
            '研B': {
                'standard': '研究生院B楼',
                'aliases': ['研B楼', '研究生B', '研B'],
                'pattern': r'(\d{3,4})',
                'room_format': '研究生院B{room}'
            },
            '第一教学楼': {
                'standard': '第一教学楼',
                'aliases': ['一教', '1教', '第1教学楼'],
                'pattern': r'(\d{3,4})',
                'room_format': '第一教学楼{room}'
            },
            '第二教学楼': {
                'standard': '第二教学楼',
                'aliases': ['二教', '2教', '第2教学楼'],
                'pattern': r'(\d{3,4})',
                'room_format': '第二教学楼{room}'
            },
            '第三教学楼': {
                'standard': '第三教学楼',
                'aliases': ['三教', '3教', '第3教学楼'],
                'pattern': r'(\d{3,4})',
                'room_format': '第三教学楼{room}'
            },
            '第四教学楼': {
                'standard': '第四教学楼',
                'aliases': ['四教', '4教', '第4教学楼'],
                'pattern': r'(\d{3,4})',
                'room_format': '第四教学楼{room}'
            },
            
            # 图书馆
            '图书馆': {
                'standard': '图书馆',
                'aliases': ['图书馆', '校图书馆', '图'],
                'rooms': {
                    '报告厅': '图书馆报告厅',
                    '多功能厅': '图书馆多功能厅',
                    '学术报告厅': '图书馆学术报告厅'
                }
            },
            
            # 体育场馆
            '新体育馆': {
                'standard': '体育馆',
                'aliases': ['体育馆', '校体育馆']
            },
            '游泳馆': {
                'standard': '游泳馆',
                'aliases': ['游泳馆', '校游泳馆']
            },
            '第一田径场': {
                'standard': '第一田径场',
                'aliases': ['一田']
            },
            '第二田径场': {
                'standard': '第二田径场',
                'aliases': ['二田']
            },
            '第三田径场': {
                'standard': '第三田径场',
                'aliases': ['三田']
            },

            # 学院楼
            '数学院': {
                'standard': '数学与计算科学学院',
                'aliases': ['数学院', '数计院', '数学与计算科学学院'],
                'pattern': r'(\d{3,4})',
                'room_format': '数学与计算科学学院{room}'
            },
            '化工学院': {
                'standard': '化工学院',
                'aliases': ['化工', '化工学院大楼'],
                'pattern': r'(\d{3,4})',
                'room_format': '化工学院{room}'
            },
            '材料学院': {
                'standard': '材料科学与工程学院',
                'aliases': ['材料学院', '材料院'],
                'pattern': r'(\d{3,4})',
                'room_format': '材料科学与工程学院{room}'
            },
            
            # 学生活动中心
            '学生活动中心': {
                'standard': '学生活动中心',
                'aliases': ['学活', '学生活动中心', '活动中心'],
                'rooms': {
                    '大礼堂': '学生活动中心大礼堂',
                    '多功能厅': '学生活动中心多功能厅',
                    '会议室': '学生活动中心会议室'
                }
            },
            
            # 行政办公楼
            '行政楼': {
                'standard': '行政办公楼',
                'aliases': ['行政楼', '行政办公楼', '办公楼'],
                'pattern': r'(\d{3,4})',
                'room_format': '行政办公楼{room}'
            },
            
            # 食堂
            '南苑食堂': {
                'standard': '南苑食堂',
                'aliases': ['南苑']
            },
            '兴湘食堂': {
                'standard': '兴湘食堂',
                'aliases': ['二食堂', '2食堂', '第二食堂']
            },
            '金翰林食堂': {
                'standard': '兴湘食堂',
                'aliases': ['三食堂', '3食堂', '第三食堂']
            },
            '北五食堂': {
                'standard': '北五食堂',
                'aliases': ['北五']
            },
             '雅园食堂': {
                'standard': '雅园食堂',
                'aliases': ['雅园']
            },
            
            # 其他常用地点
            '南门': {
                'standard': '校门口',
                'aliases': ['校门口', '学校门口', '正门', '南门']
            },
            '东门': {
                'standard': '东门',
                'aliases': ['东门']
            },
        }
    
    def standardize_location(self, location_text):
        """
        标准化地点名称
        
        Args:
            location_text: 原始地点文本
            
        Returns:
            dict: {
                'standard_name': 标准化后的地点名称,
                'confidence': 匹配置信度 (0-1),
                'is_xtu_location': 是否是湘大校内地点,
                'warning': 警告信息（如果有）
            }
        """
        import re
        
        if not location_text:
            return {
                'standard_name': '待补充',
                'confidence': 0,
                'is_xtu_location': False,
                'warning': '地点信息缺失'
            }
        
        location_text = location_text.strip()
        
        # 遍历地点数据库进行匹配
        for building_key, building_data in self.location_database.items():
            # 检查是否匹配建筑物别名
            for alias in building_data.get('aliases', []):
                if alias in location_text:
                    # 如果有具体房间号的模式
                    if 'pattern' in building_data:
                        match = re.search(building_data['pattern'], location_text)
                        if match:
                            room = match.group(1)
                            standard_name = building_data['room_format'].format(room=room)
                            return {
                                'standard_name': standard_name,
                                'confidence': 0.95,
                                'is_xtu_location': True,
                                'warning': None
                            }
                    
                    # 检查是否有预定义的房间
                    if 'rooms' in building_data:
                        for room_alias, room_standard in building_data['rooms'].items():
                            if room_alias in location_text:
                                return {
                                    'standard_name': room_standard,
                                    'confidence': 0.95,
                                    'is_xtu_location': True,
                                    'warning': None
                                }
                    
                    # 只匹配到建筑物，没有具体房间
                    return {
                        'standard_name': building_data['standard'],
                        'confidence': 0.85,
                        'is_xtu_location': True,
                        'warning': None
                    }
        
        # 如果没有匹配到任何湘大地点
        # 检查是否包含湘大关键词
        xtu_keywords = ['湘潭大学', '湘大', 'XTU', 'xtu']
        has_xtu_keyword = any(keyword in location_text for keyword in xtu_keywords)
        
        if has_xtu_keyword:
            # 包含湘大关键词但未匹配，可能是新地点或拼写错误
            return {
                'standard_name': location_text,
                'confidence': 0.5,
                'is_xtu_location': True,
                'warning': '⚠️ 该地点可能是湘大校内新地点，请确认准确性'
            }
        else:
            # 可能不是湘大校内地点
            return {
                'standard_name': location_text,
                'confidence': 0.3,
                'is_xtu_location': False,
                'warning': '⚠️ 该地点可能不在湘大校内，请再次确认'
            }
    
    def get_all_locations(self):
        """获取所有标准地点列表"""
        locations = []
        for building_data in self.location_database.values():
            locations.append(building_data['standard'])
        return locations
    
    def search_location(self, keyword):
        """根据关键词搜索地点"""
        results = []
        keyword = keyword.lower()
        
        for building_key, building_data in self.location_database.items():
            # 检查标准名称
            if keyword in building_data['standard'].lower():
                results.append(building_data['standard'])
                continue
            
            # 检查别名
            for alias in building_data.get('aliases', []):
                if keyword in alias.lower():
                    results.append(building_data['standard'])
                    break
        
        return results


# 单例实例
_location_mapper_instance = None

def get_location_mapper():
    """获取地点映射器单例"""
    global _location_mapper_instance
    if _location_mapper_instance is None:
        _location_mapper_instance = XTULocationMapper()
    return _location_mapper_instance


if __name__ == '__main__':
    # 设置UTF-8编码
    import sys
    import io
    if sys.platform == 'win32':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    # 测试代码
    mapper = XTULocationMapper()
    
    test_cases = [
        "逸夫楼一阶",
        "信科北501",
        "研A611",
        "图书馆报告厅",
        "体育馆",
        "数学院202",
        "学活大礼堂",
        "北京天安门",  # 非湘大地点
        "待定",
    ]
    
    print("=" * 60)
    print("湘潭大学地点标准化测试")
    print("=" * 60)
    
    for location in test_cases:
        result = mapper.standardize_location(location)
        print(f"\n原始地点: {location}")
        print(f"标准地点: {result['standard_name']}")
        print(f"置信度: {result['confidence']:.2f}")
        print(f"是否校内: {result['is_xtu_location']}")
        if result['warning']:
            print(f"警告: {result['warning']}")
