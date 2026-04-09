const CONFIG = {
    API_BASE_URL: 'http://localhost:5000/api',
    
    DEFAULT_USER_ID: 1,
    
    AUTO_REFRESH_INTERVAL: 60000,
    
    DATE_FORMAT: 'YYYY-MM-DD HH:mm',
    
    EVENT_TYPES: {
        'academic': '学术活动',
        'meeting': '会议',
        'exam': '考试',
        'activity': '活动',
        'other': '其他'
    },
    
    STATUS_MAP: {
        'pending': { text: '未提醒', class: 'status-pending' },
        'reminded': { text: '已提醒', class: 'status-reminded' },
        'completed': { text: '已完成', class: 'status-completed' },
        'postponed': { text: '已延期', class: 'status-postponed' }
    },
    
    CONFIDENCE_LEVELS: {
        high: { min: 0.8, color: '#2ecc71' },
        medium: { min: 0.6, color: '#f39c12' },
        low: { min: 0, color: '#e74c3c' }
    }
};
