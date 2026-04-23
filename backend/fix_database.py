"""修改数据库字段类型"""
import pymysql
import sys
import io

# 设置UTF-8编码
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    # 连接数据库
    conn = pymysql.connect(
        host='localhost',
        user='root',
        password='098765',
        database='campus_reminder_system',
        charset='utf8mb4'
    )
    
    cursor = conn.cursor()
    
    # 修改activity_type字段为VARCHAR类型
    print("正在修改activity_type字段...")
    cursor.execute("""
        ALTER TABLE text_events 
        MODIFY COLUMN activity_type VARCHAR(50) DEFAULT '通知'
    """)
    
    conn.commit()
    print("✅ activity_type字段已成功修改为VARCHAR(50)类型")
    
    # 验证修改
    cursor.execute("DESCRIBE text_events")
    for row in cursor.fetchall():
        if row[0] == 'activity_type':
            print(f"验证结果: {row}")
    
    cursor.close()
    conn.close()
    
    print("\n数据库修改完成！现在可以直接保存中文活动类型了。")
    
except Exception as e:
    print(f"❌ 错误: {e}")
    sys.exit(1)
