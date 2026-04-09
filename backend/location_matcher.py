import pymysql
from difflib import SequenceMatcher
from typing import Optional, Tuple, List, Dict
import re

class LocationMatcher:
    """湘潭大学地点标准化匹配器"""
    
    def __init__(self, db_config: dict):
        self.db_config = db_config
        self.location_cache = {}
        self._load_locations()
    
    def _load_locations(self):
        """加载地点数据到缓存"""
        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor(pymysql.cursors.DictCursor)
            
            cursor.execute("SELECT * FROM xtu_locations")
            locations = cursor.fetchall()
            
            for loc in locations:
                self.location_cache[loc['location_id']] = {
                    'standard_name': loc['standard_name'],
                    'building_name': loc['building_name'],
                    'room_number': loc['room_number'],
                    'aliases': loc['aliases'].split(',') if loc['aliases'] else [],
                    'location_type': loc['location_type']
                }
            
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"加载地点数据失败: {e}")
            self.location_cache = {}
    
    def match_location(self, input_location: str) -> Dict:
        """
        匹配地点，返回标准化结果
        
        返回格式：
        {
            'matched': True/False,
            'standard_name': '标准地点名称',
            'confidence': 0.95,
            'location_id': 1,
            'suggestions': [],  # 如果不确定，提供建议
            'is_valid': True/False,  # 是否在湘大校园内
            'error_message': ''
        }
        """
        if not input_location or input_location == '待确认':
            return {
                'matched': False,
                'standard_name': None,
                'confidence': 0.0,
                'location_id': None,
                'suggestions': [],
                'is_valid': False,
                'error_message': '未提供地点信息'
            }
        
        # 清理输入
        cleaned_input = self._clean_location_string(input_location)
        
        # 1. 精确匹配
        exact_match = self._exact_match(cleaned_input)
        if exact_match:
            return exact_match
        
        # 2. 别名匹配
        alias_match = self._alias_match(cleaned_input)
        if alias_match:
            return alias_match
        
        # 3. 模糊匹配
        fuzzy_match = self._fuzzy_match(cleaned_input)
        if fuzzy_match:
            return fuzzy_match
        
        # 4. 部分匹配（建筑名+房间号）
        partial_match = self._partial_match(cleaned_input)
        if partial_match:
            return partial_match
        
        # 没有找到匹配
        return {
            'matched': False,
            'standard_name': input_location,
            'confidence': 0.0,
            'location_id': None,
            'suggestions': self._get_suggestions(cleaned_input),
            'is_valid': False,
            'error_message': f'地点"{input_location}"不在湘大校园内，请再次确认'
        }
    
    def _clean_location_string(self, location: str) -> str:
        """清理地点字符串"""
        # 移除多余空格
        location = re.sub(r'\s+', '', location)
        # 统一"一二三"和"123"
        number_map = {'一': '1', '二': '2', '三': '3', '四': '4', '五': '5'}
        for cn, num in number_map.items():
            location = location.replace(cn, num)
        return location
    
    def _exact_match(self, input_location: str) -> Optional[Dict]:
        """精确匹配"""
        for loc_id, loc_data in self.location_cache.items():
            if input_location == loc_data['standard_name']:
                return {
                    'matched': True,
                    'standard_name': loc_data['standard_name'],
                    'confidence': 1.0,
                    'location_id': loc_id,
                    'suggestions': [],
                    'is_valid': True,
                    'error_message': ''
                }
        return None
    
    def _alias_match(self, input_location: str) -> Optional[Dict]:
        """别名匹配"""
        for loc_id, loc_data in self.location_cache.items():
            for alias in loc_data['aliases']:
                if input_location == alias or input_location in alias or alias in input_location:
                    return {
                        'matched': True,
                        'standard_name': loc_data['standard_name'],
                        'confidence': 0.95,
                        'location_id': loc_id,
                        'suggestions': [],
                        'is_valid': True,
                        'error_message': ''
                    }
        return None
    
    def _fuzzy_match(self, input_location: str) -> Optional[Dict]:
        """模糊匹配"""
        best_match = None
        best_ratio = 0.0
        threshold = 0.7  # 相似度阈值
        
        for loc_id, loc_data in self.location_cache.items():
            # 与标准名称比较
            ratio = SequenceMatcher(None, input_location, loc_data['standard_name']).ratio()
            if ratio > best_ratio and ratio >= threshold:
                best_ratio = ratio
                best_match = (loc_id, loc_data)
            
            # 与别名比较
            for alias in loc_data['aliases']:
                ratio = SequenceMatcher(None, input_location, alias).ratio()
                if ratio > best_ratio and ratio >= threshold:
                    best_ratio = ratio
                    best_match = (loc_id, loc_data)
        
        if best_match:
            loc_id, loc_data = best_match
            return {
                'matched': True,
                'standard_name': loc_data['standard_name'],
                'confidence': best_ratio,
                'location_id': loc_id,
                'suggestions': [],
                'is_valid': True,
                'error_message': '' if best_ratio > 0.85 else '地点匹配置信度较低，请确认'
            }
        
        return None
    
    def _partial_match(self, input_location: str) -> Optional[Dict]:
        """部分匹配（建筑名或房间号）"""
        matches = []
        
        for loc_id, loc_data in self.location_cache.items():
            building = loc_data['building_name']
            room = loc_data['room_number']
            
            # 检查是否包含建筑名
            if building and building in input_location:
                # 检查是否也包含房间号
                if room and room in input_location:
                    return {
                        'matched': True,
                        'standard_name': loc_data['standard_name'],
                        'confidence': 0.9,
                        'location_id': loc_id,
                        'suggestions': [],
                        'is_valid': True,
                        'error_message': ''
                    }
                else:
                    matches.append((loc_id, loc_data, 0.6))
        
        # 如果只匹配到建筑，返回建议
        if matches:
            suggestions = [m[1]['standard_name'] for m in matches[:5]]
            return {
                'matched': False,
                'standard_name': input_location,
                'confidence': 0.5,
                'location_id': None,
                'suggestions': suggestions,
                'is_valid': True,
                'error_message': f'找到多个可能的地点，请明确具体房间号'
            }
        
        return None
    
    def _get_suggestions(self, input_location: str) -> List[str]:
        """获取可能的地点建议"""
        suggestions = []
        
        # 提取可能的建筑名关键词
        building_keywords = ['楼', '馆', '厅', '院', '中心']
        for keyword in building_keywords:
            if keyword in input_location:
                for loc_data in self.location_cache.values():
                    if keyword in loc_data['standard_name']:
                        suggestions.append(loc_data['standard_name'])
                        if len(suggestions) >= 5:
                            break
                if suggestions:
                    break
        
        return suggestions[:5]
    
    def log_match_result(self, input_location: str, matched_location_id: Optional[int], 
                        confidence: float, is_correct: Optional[bool] = None):
        """记录匹配日志，用于优化算法"""
        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO location_match_logs 
                (input_location, matched_location_id, match_confidence, is_correct)
                VALUES (%s, %s, %s, %s)
            """, (input_location, matched_location_id, confidence, is_correct))
            
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"记录匹配日志失败: {e}")
    
    def add_new_location(self, standard_name: str, building_name: str, 
                        room_number: str, aliases: str) -> bool:
        """添加新地点（管理员功能）"""
        try:
            conn = pymysql.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO xtu_locations 
                (standard_name, building_name, room_number, aliases, location_type)
                VALUES (%s, %s, %s, %s, 'other')
            """, (standard_name, building_name, room_number, aliases))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            # 重新加载缓存
            self._load_locations()
            return True
        except Exception as e:
            print(f"添加地点失败: {e}")
            return False
    
    def batch_match_locations(self, locations: List[str]) -> List[Dict]:
        """批量匹配地点"""
        results = []
        for location in locations:
            result = self.match_location(location)
            results.append({
                'input': location,
                'result': result
            })
        return results
