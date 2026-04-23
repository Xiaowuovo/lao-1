// API_BASE_URL 和 getAuthHeaders 已在 auth-check.js 中声明

let remindersData = [];
let currentStatusFilter = 'all';
let currentTimeFilter = 'all';

const statusMap = {
    "pending": { text: "待提醒", class: "status-pending" },
    "sent":    { text: "已发送", class: "status-reminded" },
    "completed": { text: "已完成", class: "status-completed" },
    "cancelled": { text: "已取消", class: "status-postponed" }
};

async function loadReminders() {
    try {
        const response = await fetch(`${API_BASE_URL}/getReminders?status=${currentStatusFilter}&time_range=${currentTimeFilter}`, {
            headers: getAuthHeaders()
        });
        const result = await response.json();

        if (result.require_login) {
            window.location.href = 'login.html';
            return;
        }

        if (result.success) {
            remindersData = result.reminders || [];
            displayReminders(remindersData);
            updateStatistics();
        } else {
            console.error('加载提醒失败:', result.message);
        }
    } catch (error) {
        console.error('加载提醒失败:', error);
        document.getElementById('remindersContainer').innerHTML = 
            '<div class="empty-state"><p>加载失败，请检查后端服务是否启动</p></div>';
    }
}

function displayReminders(reminders) {
    const container = document.getElementById('remindersContainer');
    
    if (reminders.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>暂无提醒事项</p></div>';
        return;
    }

    let remindersHTML = '';

    reminders.forEach(reminder => {
        const statusKey = reminder.status || 'pending';
        const status = statusMap[statusKey] || { text: statusKey, class: 'status-pending' };
        const advanceText = reminder.advance_minutes ? `提前${reminder.advance_minutes}分钟提醒` : '无提醒任务';
        const cardId = reminder.task_id ? `reminder-${reminder.task_id}` : `event-${reminder.event_id}`;
        const reminderTimeDisplay = reminder.reminder_time ? `提醒时间: ${reminder.reminder_time} &nbsp;|&nbsp; ` : '';

        remindersHTML += `
            <div class="reminder-card ${statusKey}" id="${cardId}">
                <div class="reminder-header">
                    <div class="reminder-time">${reminderTimeDisplay}事件时间: ${reminder.event_time}</div>
                    <div class="reminder-status ${status.class}">${status.text}</div>
                </div>
                <div class="reminder-title">${reminder.event_title}</div>
                <div class="reminder-details">
                    <div><strong>地点:</strong> ${reminder.event_location || '未指定'}</div>
                    <div><strong>对象:</strong> ${reminder.event_target || '相关人员'}</div>
                    <div><strong>提醒方式:</strong> ${advanceText}</div>
                </div>
                <div class="action-buttons">
                    ${reminder.task_id && statusKey !== 'completed' ? `<button class="action-btn complete-btn" onclick="markComplete(${reminder.task_id})">标记完成</button>` : ''}
                    <button class="action-btn delete-btn" onclick="deleteEventById(${reminder.event_id})">删除事件</button>
                </div>
            </div>
        `;
    });

    container.innerHTML = remindersHTML;
}

function filterReminders(status) {
    currentStatusFilter = status;
    
    document.querySelectorAll('.filter-bar .filter-group:first-child .filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');

    loadReminders();
}

function filterByTime(timeRange) {
    currentTimeFilter = timeRange;
    
    document.querySelectorAll('.filter-bar .filter-group:last-child .filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');

    loadReminders();
}

async function markComplete(id) {
    try {
        const response = await fetch(`${API_BASE_URL}/updateReminderStatus`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ task_id: id, status: 'completed' })
        });

        const result = await response.json();

        if (result.success) {
            alert('提醒已标记为完成！');
            loadReminders();
        } else {
            alert(`操作失败: ${result.message}`);
        }
    } catch (error) {
        console.error('标记完成失败:', error);
        alert('操作失败，请检查网络连接');
    }
}

async function deleteEventById(eventId) {
    if (!confirm('确定要删除这个事件吗？相关提醒任务也会一并删除。')) return;

    try {
        const response = await fetch(`${API_BASE_URL}/xtu/deleteEvent`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ event_id: eventId })
        });
        const result = await response.json();
        if (result.success) {
            loadReminders();
        } else {
            alert('删除失败：' + result.message);
        }
    } catch (error) {
        console.error('删除事件失败:', error);
        alert('删除失败，请检查网络连接');
    }
}

async function deleteReminder(id) {
    if (!confirm("确定要删除这个提醒吗？")) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/deleteReminder`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ task_id: id })
        });

        const result = await response.json();

        if (result.success) {
            alert('提醒已删除！');
            loadReminders();
        } else {
            alert(`操作失败: ${result.message}`);
        }
    } catch (error) {
        console.error('删除提醒失败:', error);
        alert('操作失败，请检查网络连接');
    }
}

async function updateStatistics() {
    try {
        const response = await fetch(`${API_BASE_URL}/getStatistics`, {
            headers: getAuthHeaders()
        });
        const result = await response.json();

        if (result.success && result.data) {
            const stats = result.data;
            document.getElementById('totalReminders').textContent = stats.total_reminders || 0;
            document.getElementById('completedReminders').textContent = stats.completed_reminders || 0;
            document.getElementById('pendingReminders').textContent = stats.pending_reminders || 0;
            const rate = stats.total_reminders > 0 ? Math.round(stats.completed_reminders * 100 / stats.total_reminders) : 0;
            document.getElementById('completionRate').textContent = rate + '%';
        }
    } catch (error) {
        console.error('更新统计失败:', error);
    }
}

// 自动刷新（每60秒）
setInterval(loadReminders, 60000);
