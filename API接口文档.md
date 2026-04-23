# API接口文档

## 基础信息

- **Base URL**: `http://localhost:5000/api`
- **认证方式**: Bearer Token（部分接口需要）
- **数据格式**: JSON

## 认证说明

需要登录的接口在请求头中携带Token：
```
Authorization: Bearer <session_token>
```

---

## 1. 用户认证接口

### 1.1 用户注册
- **接口**: `POST /auth/register`
- **说明**: 注册新用户
- **请求体**:
```json
{
  "student_id": "202205570603",
  "username": "zhangsan",
  "password": "xtu123456",
  "real_name": "张三",
  "college_id": 1
}
```
- **响应**:
```json
{
  "success": true,
  "message": "注册成功",
  "user_id": 1
}
```

### 1.2 用户登录
- **接口**: `POST /auth/login`
- **说明**: 用户登录获取Token
- **请求体**:
```json
{
  "student_id": "202205570603",
  "password": "xtu123456"
}
```
- **响应**:
```json
{
  "success": true,
  "message": "登录成功",
  "session_token": "xxx",
  "user_info": {
    "user_id": 1,
    "student_id": "202205570603",
    "username": "zhangsan",
    "real_name": "张三",
    "college_name": "计算机学院",
    "role": "student"
  }
}
```

### 1.3 用户登出
- **接口**: `POST /auth/logout`
- **认证**: 需要
- **响应**:
```json
{
  "success": true,
  "message": "登出成功"
}
```

### 1.4 获取用户资料
- **接口**: `GET /auth/profile`
- **认证**: 需要
- **响应**:
```json
{
  "success": true,
  "user_info": { ... }
}
```

---

## 2. 事件提取接口

### 2.1 提取事件
- **接口**: `POST /extractEvents`
- **认证**: 需要
- **请求体**:
```json
{
  "text": "明天下午2点在图书馆报告厅举办学术讲座"
}
```
- **响应**:
```json
{
  "success": true,
  "message": "成功提取 1 个事件",
  "events": [
    {
      "event_id": 1,
      "title": "学术讲座",
      "time": "2024-04-11 14:00:00",
      "location": "图书馆报告厅",
      "target": "相关人员",
      "confidence": 0.85
    }
  ]
}
```

### 2.2 确认事件
- **接口**: `POST /confirmEvents`
- **认证**: 需要
- **请求体**:
```json
{
  "events": [
    {
      "title": "学术讲座",
      "time": "2024-04-11 14:00:00",
      "location": "图书馆报告厅"
    }
  ]
}
```
- **响应**:
```json
{
  "success": true,
  "message": "成功保存 1 个事件",
  "events": [
    {
      "event_id": 123,
      "title": "学术讲座"
    }
  ]
}
```

---

## 3. 提醒管理接口

### 3.1 创建提醒
- **接口**: `POST /createReminderEnhanced`
- **认证**: 需要
- **请求体**:
```json
{
  "event_id": 123,
  "advance_minutes": 30
}
```
- **响应**:
```json
{
  "success": true,
  "message": "提醒创建成功",
  "reminder_id": 456,
  "conflict_info": {
    "has_conflict": false
  }
}
```

### 3.2 获取提醒列表
- **接口**: `GET /getReminders?status=all&time_range=month`
- **认证**: 需要
- **查询参数**:
  - `status`: all/pending/reminded/completed/postponed
  - `time_range`: today/week/month/all
- **响应**:
```json
{
  "success": true,
  "reminders": [
    {
      "reminder_id": 456,
      "event_title": "学术讲座",
      "event_time": "2024-04-11 14:00:00",
      "reminder_time": "2024-04-11 13:30:00",
      "status": "pending",
      "location": "图书馆报告厅"
    }
  ]
}
```

### 3.3 更新提醒状态
- **接口**: `POST /updateReminderStatus`
- **认证**: 需要
- **请求体**:
```json
{
  "reminder_id": 456,
  "status": "completed"
}
```

### 3.4 删除提醒
- **接口**: `POST /deleteReminder`
- **认证**: 需要
- **请求体**:
```json
{
  "reminder_id": 456
}
```

---

## 4. 设置管理接口

### 4.1 获取设置
- **接口**: `GET /getSettings`
- **认证**: 需要
- **响应**:
```json
{
  "success": true,
  "data": {
    "reminder_advance_time": 30,
    "web_notification": true,
    "email_notification": false
  }
}
```

### 4.2 保存设置
- **接口**: `POST /saveSettings`
- **认证**: 需要
- **请求体**:
```json
{
  "reminder_advance_time": 60,
  "web_notification": true,
  "email_notification": false
}
```

---

## 5. 统计数据接口

### 5.1 获取统计数据
- **接口**: `GET /getStatistics`
- **认证**: 需要
- **响应**:
```json
{
  "success": true,
  "data": {
    "total_reminders": 50,
    "completed_reminders": 35,
    "pending_reminders": 15,
    "event_types": [
      {"type": "academic", "count": 20},
      {"type": "exam", "count": 15}
    ]
  }
}
```

---

## 6. 课表管理接口

### 6.1 获取课表
- **接口**: `GET /getSchedule`
- **认证**: 需要

### 6.2 添加课程
- **接口**: `POST /addCourse`
- **认证**: 需要
- **请求体**:
```json
{
  "course_name": "数据结构",
  "day_of_week": 1,
  "start_time": "08:00",
  "end_time": "09:40",
  "location": "教学楼A101"
}
```

### 6.3 删除课程
- **接口**: `POST /deleteCourse`
- **认证**: 需要

---

## 7. 历史归档接口

### 7.1 获取归档
- **接口**: `GET /getArchive`
- **认证**: 需要

### 7.2 搜索归档
- **接口**: `GET /searchArchive?keyword=讲座`
- **认证**: 需要

---

## 8. 健康检查

### 8.1 健康检查
- **接口**: `GET /health`
- **认证**: 不需要
- **响应**:
```json
{
  "success": true,
  "message": "服务正常运行",
  "database": true
}
```

---

## 错误码说明

- `200`: 成功
- `400`: 请求参数错误
- `401`: 未授权（需要登录）
- `404`: 资源不存在
- `500`: 服务器内部错误

## 通用错误响应

```json
{
  "success": false,
  "message": "错误描述",
  "require_login": true  // 需要重新登录
}
```
