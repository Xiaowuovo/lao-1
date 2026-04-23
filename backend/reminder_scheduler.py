"""
邮件提醒定时任务
每分钟检查一次是否有需要发送的提醒邮件
"""
import time
import requests
from datetime import datetime

API_URL = 'http://localhost:5000/api/sendPendingReminders'

def send_reminders():
    """调用API发送待发送的提醒"""
    try:
        response = requests.post(API_URL, timeout=30)
        result = response.json()
        
        if result.get('success'):
            sent = result.get('sent_count', 0)
            failed = result.get('failed_count', 0)
            if sent > 0 or failed > 0:
                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 发送提醒: 成功{sent}条, 失败{failed}条")
        else:
            print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 发送失败: {result.get('message')}")
    
    except Exception as e:
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 错误: {e}")

if __name__ == '__main__':
    print("=" * 60)
    print("邮件提醒定时任务已启动")
    print("每分钟检查一次待发送的提醒")
    print("=" * 60)
    
    while True:
        send_reminders()
        time.sleep(60)  # 每60秒检查一次
