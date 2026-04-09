const API_BASE_URL = 'http://localhost:5000/api';
const USER_ID = 1;

let remindersData = [];
let currentStatusFilter = 'all';
let currentTimeFilter = 'month';

const statusMap = {
    "pending": { text: "未提醒", class: "status-pending" },
    "reminded": { text: "已提醒", class: "status-reminded" },
    "completed": { text: "已完成", class: "status-completed" },
    "postponed": { text: "已延期", class: "status-postponed" }
};

async function loadReminders() {
    try {
        const response = await fetch(`${API_BASE_URL}/getReminders?user_id=${USER_ID}&status=${currentStatusFilter}&time_range=${currentTimeFilter}`);
        const result = await response.json();

        if (result.success) {
            remindersData = result.reminders;
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
        const status = statusMap[reminder.status];
        const advanceText = `${reminder.advance_minutes}分钟前提醒`;

        remindersHTML += `
            <div class="reminder-card ${reminder.status}" id="reminder-${reminder.reminder_id}">
                <div class="reminder-header">
                    <div class="reminder-time">${reminder.event_time} (${advanceText})</div>
                    <div class="reminder-status ${status.class}">${status.text}</div>
                </div>
                <div class="reminder-title">${reminder.event_title}</div>
                <div class="reminder-details">
                    <div><strong>地点:</strong> ${reminder.event_location}</div>
                    <div><strong>对象:</strong> ${reminder.event_target}</div>
                    ${reminder.postponed_to ? `<div><strong>延期至:</strong> ${reminder.postponed_to}</div>` : ''}
                </div>
                <div class="action-buttons">
                    ${reminder.status !== 'completed' ? `<button class="action-btn complete-btn" onclick="markComplete(${reminder.reminder_id})">标记完成</button>` : ''}
                    ${reminder.status !== 'completed' ? `<button class="action-btn postpone-btn" onclick="postponeReminder(${reminder.reminder_id})">延后提醒</button>` : ''}
                    <button class="action-btn delete-btn" onclick="deleteReminder(${reminder.reminder_id})">删除</button>
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
        const response = await fetch(`${API_BASE_URL}/markDone`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ reminder_id: id })
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

async function postponeReminder(id) {
    const newDate = prompt("请输入新的提醒时间（格式：YYYY-MM-DD HH:MM）：", "2026-05-01 09:00");
    
    if (!newDate) {
        return;
    }

    const dateRegex = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/;
    if (!dateRegex.test(newDate)) {
        alert('时间格式不正确，请使用格式：YYYY-MM-DD HH:MM');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/postponeReminder`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                reminder_id: id,
                new_time: newDate
            })
        });

        const result = await response.json();

        if (result.success) {
            alert('提醒已延后！');
            loadReminders();
        } else {
            alert(`操作失败: ${result.message}`);
        }
    } catch (error) {
        console.error('延后提醒失败:', error);
        alert('操作失败，请检查网络连接');
    }
}

async function deleteReminder(id) {
    if (!confirm("确定要删除这个提醒吗？")) {
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/deleteReminder`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ reminder_id: id })
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
        const response = await fetch(`${API_BASE_URL}/getStatistics?user_id=${USER_ID}`);
        const result = await response.json();

        if (result.success) {
            const stats = result.statistics;
            document.getElementById('totalReminders').textContent = stats.total;
            document.getElementById('completedReminders').textContent = stats.completed;
            document.getElementById('pendingReminders').textContent = stats.pending;
            document.getElementById('completionRate').textContent = stats.completion_rate + '%';
        }
    } catch (error) {
        console.error('更新统计失败:', error);
    }
}

document.addEventListener('DOMContentLoaded', function () {
    loadReminders();
    setInterval(loadReminders, 60000);
});
