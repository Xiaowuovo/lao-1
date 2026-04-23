import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class EmailSender:
    """邮件发送器"""
    
    def __init__(self):
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.qq.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.from_email = os.getenv('SMTP_FROM_EMAIL', self.smtp_username)
        
    def send_reminder_email(self, to_email: str, event_title: str, 
                           event_time: str, event_location: str = '',
                           advance_minutes: int = 30) -> bool:
        """
        发送提醒邮件
        
        Args:
            to_email: 收件人邮箱
            event_title: 事件标题
            event_time: 事件时间
            event_location: 事件地点
            advance_minutes: 提前提醒分钟数
        
        Returns:
            是否发送成功
        """
        if not self.smtp_username or not self.smtp_password:
            print("邮件配置未设置，跳过邮件发送")
            return False
        
        try:
            # 创建邮件
            msg = MIMEMultipart('alternative')
            msg['Subject'] = f'【湘大提醒】{event_title}'
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            # 纯文本内容
            text_content = f"""
湘潭大学智慧校园任务管理系统 - 事件提醒

事件：{event_title}
时间：{event_time}
地点：{event_location or '待定'}
提醒：提前{advance_minutes}分钟提醒

请及时关注并做好准备！

---
湘潭大学智慧校园任务管理系统
            """
            
            # HTML内容
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 24px; }}
        .content {{ padding: 30px; }}
        .event-info {{ background: #f8f9fa; border-left: 4px solid #667eea; padding: 20px; margin: 20px 0; border-radius: 4px; }}
        .info-row {{ margin: 10px 0; font-size: 16px; }}
        .info-label {{ font-weight: bold; color: #333; display: inline-block; width: 80px; }}
        .info-value {{ color: #555; }}
        .reminder-badge {{ background: #ffeaa7; color: #d63031; padding: 8px 15px; border-radius: 20px; display: inline-block; margin: 15px 0; font-weight: bold; }}
        .footer {{ background: #f8f9fa; padding: 20px; text-align: center; color: #999; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔔 事件提醒</h1>
            <p>湘潭大学智慧校园任务管理系统</p>
        </div>
        <div class="content">
            <p style="font-size: 16px; color: #333;">您好！</p>
            <p style="font-size: 14px; color: #666;">以下事件即将开始，请及时关注：</p>
            
            <div class="event-info">
                <div class="info-row">
                    <span class="info-label">📋 事件：</span>
                    <span class="info-value">{event_title}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">🕐 时间：</span>
                    <span class="info-value">{event_time}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">📍 地点：</span>
                    <span class="info-value">{event_location or '待定'}</span>
                </div>
            </div>
            
            <div class="reminder-badge">
                ⏰ 提前 {advance_minutes} 分钟提醒
            </div>
            
            <p style="font-size: 14px; color: #666; margin-top: 20px;">
                请做好相应准备，准时参加！
            </p>
        </div>
        <div class="footer">
            <p>湘潭大学智慧校园任务管理系统</p>
            <p>此邮件由系统自动发送，请勿回复</p>
        </div>
    </div>
</body>
</html>
            """
            
            # 添加文本和HTML部分
            part1 = MIMEText(text_content, 'plain', 'utf-8')
            part2 = MIMEText(html_content, 'html', 'utf-8')
            msg.attach(part1)
            msg.attach(part2)
            
            # 连接SMTP服务器并发送
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            print(f"邮件发送成功: {to_email}")
            return True
            
        except Exception as e:
            print(f"邮件发送失败: {e}")
            return False
    
    def test_connection(self) -> bool:
        """测试邮件服务器连接"""
        if not self.smtp_username or not self.smtp_password:
            return False
        
        try:
            with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
            return True
        except Exception as e:
            print(f"邮件服务器连接测试失败: {e}")
            return False
