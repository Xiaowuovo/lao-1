const API_BASE_URL = 'http://localhost:5000/api';

// 获取认证token
function getAuthHeaders() {
    const token = localStorage.getItem('sessionToken');
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
    };
}

function handleFileSelect(event) {
    const file = event.target.files[0];
    if (file) {
        document.getElementById('fileName').textContent = `已选择文件: ${file.name}`;

        const reader = new FileReader();
        reader.onload = function (e) {
            document.getElementById('inputText').value = e.target.result;
        };
        reader.readAsText(file, 'UTF-8');
    }
}

async function extractEvents() {
    const inputText = document.getElementById('inputText').value;
    if (!inputText.trim()) {
        alert("请输入或上传文本内容");
        return;
    }

    const eventsContainer = document.getElementById('eventsContainer');
    eventsContainer.innerHTML = '<div class="empty-state"><p>正在提取事件，请稍候...</p></div>';

    try {
        const response = await fetch(`${API_BASE_URL}/extractEvents`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                text: inputText
            })
        });

        const result = await response.json();

        if (result.require_login) {
            window.location.href = 'login.html';
            return;
        }

        if (result.success) {
            displayEvents(result.events || []);
            document.getElementById('addAllBtn').style.display = 'block';
        } else {
            eventsContainer.innerHTML = `<div class="empty-state"><p>${result.message}</p></div>`;
        }
    } catch (error) {
        console.error('提取事件失败:', error);
        eventsContainer.innerHTML = '<div class="empty-state"><p>提取失败，请检查网络连接或后端服务是否启动</p></div>';
    }
}

function displayEvents(events) {
    const eventsContainer = document.getElementById('eventsContainer');

    if (events.length === 0) {
        eventsContainer.innerHTML = '<div class="empty-state"><p>未识别到事件信息</p></div>';
        return;
    }

    let eventsHTML = '';

    events.forEach((event, index) => {
        const confidencePercent = Math.round(event.confidence * 100);
        const confidenceClass = confidencePercent >= 80 ? 'high' : confidencePercent >= 60 ? 'medium' : 'low';
        
        eventsHTML += `
            <div class="event-card" id="event-${event.event_id}">
                <h3>${event.title}</h3>
                <div class="event-detail"><strong>时间:</strong> ${event.time}</div>
                <div class="event-detail"><strong>地点:</strong> ${event.location}</div>
                <div class="event-detail"><strong>对象:</strong> ${event.target}</div>
                <div class="event-detail"><strong>类型:</strong> ${getEventTypeName(event.event_type)}</div>
                <div class="event-detail"><strong>识别置信度:</strong> <span class="confidence ${confidenceClass}">${confidencePercent}%</span></div>
                <button class="add-btn" onclick="addReminder(${event.event_id})">添加到提醒</button>
            </div>
        `;
    });

    eventsContainer.innerHTML = eventsHTML;
}

function getEventTypeName(type) {
    const typeMap = {
        'academic': '学术活动',
        'meeting': '会议',
        'exam': '考试',
        'activity': '活动',
        'other': '其他'
    };
    return typeMap[type] || '其他';
}

async function addReminder(eventId) {
    const eventCard = document.getElementById(`event-${eventId}`);
    const button = eventCard.querySelector('.add-btn');
    
    button.textContent = '添加中...';
    button.disabled = true;

    try {
        const response = await fetch(`${API_BASE_URL}/createReminderEnhanced`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                event_id: eventId,
                advance_minutes: 30
            })
        });

        const result = await response.json();

        if (result.success) {
            eventCard.style.backgroundColor = '#e8f5e9';
            button.textContent = '已添加';
            button.style.backgroundColor = '#95a5a6';
            alert('提醒添加成功！');
        } else {
            button.textContent = '添加到提醒';
            button.disabled = false;
            alert(`添加失败: ${result.message}`);
        }
    } catch (error) {
        console.error('添加提醒失败:', error);
        button.textContent = '添加到提醒';
        button.disabled = false;
        alert('添加失败，请检查网络连接');
    }
}

async function addAllReminders() {
    const addButtons = document.querySelectorAll('.add-btn:not([disabled])');
    
    if (addButtons.length === 0) {
        alert('所有事件都已添加！');
        return;
    }

    for (const button of addButtons) {
        const eventCard = button.closest('.event-card');
        const eventId = eventCard.id.replace('event-', '');
        await addReminder(parseInt(eventId));
        await new Promise(resolve => setTimeout(resolve, 300));
    }

    alert('所有提醒已成功添加！');
}

document.addEventListener('DOMContentLoaded', function () {
    console.log('校园事务自动提醒系统 - 首页已加载');
});
