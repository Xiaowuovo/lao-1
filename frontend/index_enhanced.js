const API_BASE_URL = 'http://localhost:5000/api';
const USER_ID = 1;

let extractedEvents = [];
let pendingConfirmation = [];

// 文件上传处理
function handleFileSelect(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    document.getElementById('fileName').textContent = `已选择文件: ${file.name}`;
    
    const ext = file.name.split('.').pop().toLowerCase();
    
    if (['jpg', 'jpeg', 'png', 'gif', 'pdf', 'docx'].includes(ext)) {
        // 多格式文件上传
        uploadFile(file);
    } else if (ext === 'txt') {
        // 文本文件直接读取
        const reader = new FileReader();
        reader.onload = function (e) {
            document.getElementById('inputText').value = e.target.result;
        };
        reader.readAsText(file, 'UTF-8');
    } else {
        alert('不支持的文件格式');
    }
}

// 上传文件到后端处理
async function uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('user_id', USER_ID);
    
    showLoading('正在处理文件，请稍候...');
    
    try {
        const response = await fetch(`${API_BASE_URL}/uploadFile`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.success) {
            document.getElementById('inputText').value = result.text;
            showMessage('文件处理成功！', 'success');
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        console.error('文件上传失败:', error);
        showMessage('文件处理失败，请检查网络连接', 'error');
    } finally {
        hideLoading();
    }
}

// URL解析
async function parseUrlText() {
    const url = prompt('请输入校园通知链接：', 'https://');
    if (!url) return;
    
    showLoading('正在解析网页，请稍候...');
    
    try {
        const response = await fetch(`${API_BASE_URL}/parseUrl`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, user_id: USER_ID })
        });
        
        const result = await response.json();
        
        if (result.success) {
            document.getElementById('inputText').value = result.text;
            showMessage(`网页解析成功：${result.title}`, 'success');
        } else {
            showMessage(result.message, 'error');
        }
    } catch (error) {
        console.error('网页解析失败:', error);
        showMessage('网页解析失败', 'error');
    } finally {
        hideLoading();
    }
}

// 增强版事件提取
async function extractEvents() {
    const inputText = document.getElementById('inputText').value;
    if (!inputText.trim()) {
        alert("请输入或上传文本内容");
        return;
    }

    const eventsContainer = document.getElementById('eventsContainer');
    eventsContainer.innerHTML = '<div class="empty-state"><p>正在提取事件，请稍候...</p></div>';

    try {
        const response = await fetch(`${API_BASE_URL}/extractEventsEnhanced`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: inputText,
                user_id: USER_ID,
                auto_confirm: false
            })
        });

        const result = await response.json();

        if (result.success) {
            extractedEvents = result.events;
            displayEventsWithConfirmation(extractedEvents);
            document.getElementById('addAllBtn').style.display = 'block';
        } else {
            eventsContainer.innerHTML = `<div class="empty-state"><p>${result.message}</p></div>`;
        }
    } catch (error) {
        console.error('提取事件失败:', error);
        eventsContainer.innerHTML = '<div class="empty-state"><p>提取失败，请检查后端服务</p></div>';
    }
}

// 显示事件（带确认界面）
function displayEventsWithConfirmation(events) {
    const eventsContainer = document.getElementById('eventsContainer');

    if (events.length === 0) {
        eventsContainer.innerHTML = '<div class="empty-state"><p>未识别到事件信息</p></div>';
        return;
    }

    let eventsHTML = '';

    events.forEach((event, index) => {
        const confidencePercent = Math.round(event.confidence * 100);
        const confidenceClass = confidencePercent >= 80 ? 'high' : confidencePercent >= 60 ? 'medium' : 'low';
        
        const missingFields = event.missing_fields || [];
        const hasIssues = missingFields.length > 0 || event.location_match?.error_message;
        
        eventsHTML += `
            <div class="event-card ${hasIssues ? 'has-issues' : ''}" id="event-${index}">
                <div class="event-header">
                    <h3>${event.title}</h3>
                    ${hasIssues ? '<span class="issue-badge">⚠️ 需要确认</span>' : ''}
                </div>
                
                <div class="event-details">
                    <div class="detail-row ${missingFields.includes('time') ? 'missing' : ''}">
                        <strong>时间:</strong> 
                        <input type="text" value="${event.time}" id="time-${index}" 
                               ${missingFields.includes('time') ? 'class="field-error" placeholder="请输入时间"' : ''}>
                    </div>
                    
                    ${event.deadline_time ? `
                    <div class="detail-row">
                        <strong>截止时间:</strong> ${event.deadline_time}
                    </div>
                    ` : ''}
                    
                    <div class="detail-row ${missingFields.includes('location') ? 'missing' : ''}">
                        <strong>地点:</strong> 
                        <input type="text" value="${event.location}" id="location-${index}"
                               ${missingFields.includes('location') ? 'class="field-error" placeholder="请输入地点"' : ''}>
                        ${event.location_match?.is_valid === false ? 
                          `<span class="error-hint">${event.location_match.error_message}</span>` : ''}
                        ${event.location_match?.suggestions?.length > 0 ? 
                          `<div class="suggestions">建议: ${event.location_match.suggestions.slice(0, 3).join(', ')}</div>` : ''}
                    </div>
                    
                    <div class="detail-row">
                        <strong>对象:</strong> ${event.target_audience || event.target}
                    </div>
                    
                    <div class="detail-row">
                        <strong>主办单位:</strong> ${event.organizer}
                    </div>
                    
                    <div class="detail-row">
                        <strong>活动类型:</strong> 
                        <select id="activity-type-${index}">
                            <option value="competition" ${event.activity_type === 'competition' ? 'selected' : ''}>竞赛</option>
                            <option value="lecture" ${event.activity_type === 'lecture' ? 'selected' : ''}>讲座</option>
                            <option value="recruitment" ${event.activity_type === 'recruitment' ? 'selected' : ''}>招聘</option>
                            <option value="meeting" ${event.activity_type === 'meeting' ? 'selected' : ''}>会议</option>
                            <option value="payment" ${event.activity_type === 'payment' ? 'selected' : ''}>缴费</option>
                            <option value="health_check" ${event.activity_type === 'health_check' ? 'selected' : ''}>体检</option>
                            <option value="other" ${event.activity_type === 'other' ? 'selected' : ''}>其他</option>
                        </select>
                    </div>
                    
                    <div class="detail-row">
                        <strong>待办分类:</strong> 
                        <select id="task-category-${index}">
                            <option value="study" ${event.task_category === 'study' ? 'selected' : ''}>学习事务</option>
                            <option value="competition" ${event.task_category === 'competition' ? 'selected' : ''}>竞赛活动</option>
                            <option value="administrative" ${event.task_category === 'administrative' ? 'selected' : ''}>行政通知</option>
                            <option value="life" ${event.task_category === 'life' ? 'selected' : ''}>生活服务</option>
                            <option value="custom" ${event.task_category === 'custom' ? 'selected' : ''}>个人自定义</option>
                        </select>
                    </div>
                    
                    ${event.contact_info && Object.keys(event.contact_info).length > 0 ? `
                    <div class="detail-row">
                        <strong>联系方式:</strong> ${formatContactInfo(event.contact_info)}
                    </div>
                    ` : ''}
                    
                    ${event.is_recurring ? `
                    <div class="detail-row recurring">
                        <strong>循环提醒:</strong> ${event.recurring_pattern}
                    </div>
                    ` : ''}
                    
                    <div class="detail-row">
                        <strong>识别置信度:</strong> 
                        <span class="confidence ${confidenceClass}">${confidencePercent}%</span>
                    </div>
                </div>
                
                <div class="event-actions">
                    ${hasIssues ? 
                      `<button class="confirm-btn" onclick="confirmAndAddEvent(${index})">确认并添加</button>` :
                      `<button class="add-btn" onclick="addReminder(${index})">添加到提醒</button>`
                    }
                    <button class="edit-btn" onclick="editEvent(${index})">编辑</button>
                </div>
            </div>
        `;
    });

    eventsContainer.innerHTML = eventsHTML;
}

// 格式化联系方式
function formatContactInfo(contactInfo) {
    const parts = [];
    if (contactInfo.phone) parts.push(`电话: ${contactInfo.phone.join(', ')}`);
    if (contactInfo.qq) parts.push(`QQ: ${contactInfo.qq.join(', ')}`);
    if (contactInfo.email) parts.push(`邮箱: ${contactInfo.email.join(', ')}`);
    if (contactInfo.wechat) parts.push(`微信: ${contactInfo.wechat.join(', ')}`);
    if (contactInfo.url) parts.push(`链接: ${contactInfo.url[0]}`);
    return parts.join(' | ');
}

// 确认并添加事件（用户修改后）
async function confirmAndAddEvent(index) {
    const event = extractedEvents[index];
    
    // 获取用户修改的值
    const timeInput = document.getElementById(`time-${index}`);
    const locationInput = document.getElementById(`location-${index}`);
    const activityType = document.getElementById(`activity-type-${index}`);
    const taskCategory = document.getElementById(`task-category-${index}`);
    
    if (timeInput) event.time = timeInput.value;
    if (locationInput) event.location = locationInput.value;
    if (activityType) event.activity_type = activityType.value;
    if (taskCategory) event.task_category = taskCategory.value;
    
    // 验证必填字段
    if (!event.time || !event.title) {
        alert('时间和标题不能为空！');
        return;
    }
    
    // 保存事件
    try {
        const response = await fetch(`${API_BASE_URL}/confirmEvents`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                events: [event],
                user_id: USER_ID
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // 创建提醒
            const eventId = result.events[0].event_id;
            await createReminderWithConflictCheck(eventId);
            
            // 标记为已添加
            const eventCard = document.getElementById(`event-${index}`);
            eventCard.style.backgroundColor = '#e8f5e9';
            eventCard.querySelector('.event-actions').innerHTML = '<span class="added-badge">✓ 已添加</span>';
        } else {
            alert(`添加失败: ${result.message}`);
        }
    } catch (error) {
        console.error('添加事件失败:', error);
        alert('添加失败，请检查网络连接');
    }
}

// 创建提醒（带冲突检测）
async function createReminderWithConflictCheck(eventId) {
    try {
        const response = await fetch(`${API_BASE_URL}/createReminderEnhanced`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                event_id: eventId,
                user_id: USER_ID,
                advance_minutes: 30,
                reminder_levels: [60, 180, 1440],
                check_conflict: true
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            if (result.conflict_info.has_conflict) {
                showConflictDialog(result.conflict_info);
            } else {
                showMessage('提醒创建成功！', 'success');
            }
        } else {
            showMessage(`创建失败: ${result.message}`, 'error');
        }
    } catch (error) {
        console.error('创建提醒失败:', error);
    }
}

// 显示冲突对话框
function showConflictDialog(conflictInfo) {
    const level = conflictInfo.conflict_level;
    const conflicts = conflictInfo.conflicts;
    
    let message = conflictInfo.message + '\n\n冲突详情：\n';
    conflicts.forEach(c => {
        message += `- ${c.title} (${c.time}) @ ${c.location}\n`;
    });
    
    if (level === 'critical') {
        alert('⚠️ 严重冲突！\n' + message);
    } else {
        if (confirm('⚠️ 时间冲突提醒\n' + message + '\n\n是否仍要创建提醒？')) {
            showMessage('提醒已创建，请注意时间安排', 'warning');
        }
    }
}

// 工具函数
function showLoading(message) {
    const eventsContainer = document.getElementById('eventsContainer');
    eventsContainer.innerHTML = `<div class="empty-state"><p>${message}</p></div>`;
}

function hideLoading() {
    // Loading state handled by display functions
}

function showMessage(message, type) {
    // Simple alert for now, can be enhanced with toast notifications
    if (type === 'error') {
        alert('❌ ' + message);
    } else if (type === 'success') {
        alert('✓ ' + message);
    } else if (type === 'warning') {
        alert('⚠️ ' + message);
    } else {
        alert(message);
    }
}

async function addReminder(index) {
    await confirmAndAddEvent(index);
}

async function addAllReminders() {
    for (let i = 0; i < extractedEvents.length; i++) {
        await confirmAndAddEvent(i);
        await new Promise(resolve => setTimeout(resolve, 300));
    }
    alert('所有提醒已成功添加！');
}

function editEvent(index) {
    // Make fields editable
    alert('编辑功能：可以修改上方输入框中的内容后重新确认');
}

document.addEventListener('DOMContentLoaded', function () {
    console.log('增强版校园事务自动提醒系统 - 首页已加载');
});
