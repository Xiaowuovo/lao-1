-- ========================================
-- 校园事务自动提醒系统 - 完整数据库初始化脚本
-- 版本: v2.0 (带用户认证)
-- 执行: mysql -u root -p < init_database.sql
-- ========================================

SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- 创建数据库
DROP DATABASE IF EXISTS campus_reminder_system;
CREATE DATABASE campus_reminder_system CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE campus_reminder_system;

-- ========================================
-- 1. 用户表
-- ========================================
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(12) UNIQUE COMMENT '学号',
    username VARCHAR(50) UNIQUE NOT NULL,
    real_name VARCHAR(50) COMMENT '真实姓名',
    password_hash VARCHAR(255) NOT NULL,
    email VARCHAR(100),
    phone VARCHAR(20),
    college_code VARCHAR(4) COMMENT '学院代码',
    class_code VARCHAR(4) COMMENT '班级代码',
    grade VARCHAR(4) COMMENT '年级',
    role ENUM('admin', 'user') DEFAULT 'user',
    avatar_url VARCHAR(255),
    last_login_time DATETIME,
    login_count INT DEFAULT 0,
    account_status ENUM('active', 'inactive', 'locked') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_student_id (student_id),
    INDEX idx_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 2. 学院代码表
-- ========================================
CREATE TABLE college_codes (
    college_code VARCHAR(4) PRIMARY KEY,
    college_name VARCHAR(100) NOT NULL,
    college_short_name VARCHAR(50)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO college_codes VALUES
('0557', '信息工程学院', '信科院'),
('0558', '计算机学院', '计院'),
('0501', '文学与新闻学院', '文新院'),
('0502', '外国语学院', '外语院'),
('0503', '法学院', '法学院'),
('0504', '公共管理学院', '公管院'),
('0505', '商学院', '商学院'),
('0506', '数学与计算科学学院', '数计院');

-- ========================================
-- 3. 文本事件表
-- ========================================
CREATE TABLE text_events (
    event_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    original_text TEXT NOT NULL,
    event_title VARCHAR(500),
    event_time DATETIME,
    deadline_time DATETIME,
    event_location VARCHAR(200),
    standard_location VARCHAR(200),
    event_target VARCHAR(200),
    target_audience VARCHAR(200),
    organizer VARCHAR(200),
    event_type VARCHAR(50) DEFAULT 'other',
    activity_type ENUM('competition', 'lecture', 'recruitment', 'meeting', 'payment', 'health_check', 'other') DEFAULT 'other',
    task_category ENUM('study', 'competition', 'administrative', 'life', 'custom') DEFAULT 'custom',
    contact_info TEXT,
    is_recurring BOOLEAN DEFAULT FALSE,
    recurring_pattern VARCHAR(100),
    has_conflict BOOLEAN DEFAULT FALSE,
    conflict_level ENUM('none', 'warning', 'critical') DEFAULT 'none',
    is_confirmed BOOLEAN DEFAULT FALSE,
    missing_fields JSON,
    extraction_confidence DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_event_time (event_time),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 4. 提醒任务表
-- ========================================
CREATE TABLE reminder_tasks (
    task_id INT AUTO_INCREMENT PRIMARY KEY,
    event_id INT NOT NULL,
    user_id INT NOT NULL,
    reminder_time DATETIME NOT NULL,
    advance_minutes INT DEFAULT 30,
    reminder_method VARCHAR(50) DEFAULT 'web',
    reminder_levels JSON,
    is_deadline_reminder BOOLEAN DEFAULT FALSE,
    status ENUM('pending', 'sent', 'completed', 'cancelled') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    INDEX idx_event_id (event_id),
    INDEX idx_reminder_time (reminder_time),
    INDEX idx_status (status),
    FOREIGN KEY (event_id) REFERENCES text_events(event_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 5. 用户设置表
-- ========================================
CREATE TABLE user_settings (
    setting_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT UNIQUE NOT NULL,
    reminder_advance_time INT DEFAULT 30,
    email_notification BOOLEAN DEFAULT FALSE,
    web_notification BOOLEAN DEFAULT TRUE,
    sound_notification BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 6. 地点标准化表
-- ========================================
CREATE TABLE xtu_locations (
    location_id INT AUTO_INCREMENT PRIMARY KEY,
    standard_name VARCHAR(200) NOT NULL,
    building_name VARCHAR(100),
    room_number VARCHAR(50),
    aliases TEXT,
    location_type ENUM('classroom', 'office', 'lab', 'hall', 'outdoor', 'other') DEFAULT 'other',
    campus_area VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_standard_name (standard_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO xtu_locations (standard_name, building_name, room_number, aliases, location_type, campus_area) VALUES
('信息科技大楼北501', '信息科技大楼', 'N501', '信科楼北501,信科楼N501,信科北501', 'classroom', '本部'),
('研究生院A611', '研究生院', 'A611', '研院A611,研A611', 'classroom', '本部'),
('逸夫楼第一阶梯教室', '逸夫楼', '一阶', '逸夫楼一阶,逸夫一阶', 'classroom', '本部'),
('图书馆报告厅', '图书馆', '报告厅', '图书馆报告厅', 'hall', '本部'),
('学生活动中心', '学生活动中心', '', '学活,学活中心', 'hall', '本部'),
('体育馆', '体育馆', '', '体育馆,校体育馆', 'hall', '本部'),
('大礼堂', '大礼堂', '', '学校大礼堂,礼堂', 'hall', '本部');

-- ========================================
-- 7. 用户课表表
-- ========================================
CREATE TABLE user_schedules (
    schedule_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    course_name VARCHAR(200) NOT NULL,
    course_location VARCHAR(200),
    weekday TINYINT NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    teacher_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 8. 事件归档表
-- ========================================
CREATE TABLE event_archive (
    archive_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    event_id INT,
    event_title VARCHAR(500),
    event_time DATETIME,
    event_location VARCHAR(200),
    completion_status ENUM('completed', 'cancelled', 'expired') DEFAULT 'completed',
    completion_time DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 9. 用户会话表
-- ========================================
CREATE TABLE user_sessions (
    session_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    ip_address VARCHAR(45),
    user_agent VARCHAR(500),
    login_time DATETIME DEFAULT CURRENT_TIMESTAMP,
    expire_time DATETIME NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_user_id (user_id),
    INDEX idx_token (session_token),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 10. 用户操作日志表
-- ========================================
CREATE TABLE user_activity_logs (
    log_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    action_type VARCHAR(50) NOT NULL,
    action_detail TEXT,
    ip_address VARCHAR(45),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 11. 文件上传记录表
-- ========================================
CREATE TABLE uploaded_files (
    file_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50),
    extracted_text TEXT,
    processing_status ENUM('pending', 'success', 'failed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ========================================
-- 插入测试用户（密码: xtu123456）
-- ========================================
INSERT INTO users (user_id, student_id, username, real_name, password_hash, email, college_code, class_code, grade, phone, role, account_status) VALUES
(1, '202205570601', 'admin', '系统管理员', MD5('xtu123456'), 'admin@xtu.edu.cn', '0557', '0601', '2022', '13800000001', 'admin', 'active'),
(2, '202205570603', 'zhangsan', '张三', MD5('xtu123456'), 'zhangsan@xtu.edu.cn', '0557', '0603', '2022', '13800000002', 'user', 'active'),
(3, '202205570610', 'lisi', '李四', MD5('xtu123456'), 'lisi@xtu.edu.cn', '0557', '0610', '2022', '13800000003', 'user', 'active'),
(4, '202205580501', 'wangwu', '王五', MD5('xtu123456'), 'wangwu@xtu.edu.cn', '0558', '0501', '2022', '13800000004', 'user', 'active');

-- 为测试用户创建默认设置
INSERT INTO user_settings (user_id, reminder_advance_time, email_notification, web_notification, sound_notification)
VALUES (1, 30, FALSE, TRUE, TRUE), (2, 30, FALSE, TRUE, TRUE), (3, 30, FALSE, TRUE, TRUE), (4, 30, FALSE, TRUE, TRUE);

-- ========================================
-- 完成
-- ========================================
SELECT '数据库初始化完成！' AS status,
       '数据库名称: campus_reminder_system' AS db_name,
       '测试用户数: 4' AS users,
       '默认密码: xtu123456' AS password;
