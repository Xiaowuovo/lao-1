// 日历视图JavaScript

let currentDate = new Date();
let currentEvents = [];

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    if (!checkAuth()) {
        return;
    }
    
    const userInfo = getCurrentUser();
    if (userInfo) {
        document.getElementById('userName').textContent = userInfo.real_name || userInfo.username;
        
        const userMenu = document.querySelector('.user-menu');
        userMenu.style.cursor = 'pointer';
        userMenu.onclick = function() {
            if (confirm('确定要退出登录吗？')) {
                logout();
            }
        };
    }
    
    // 加载当月日历和事件
    loadCalendar();
    loadEvents();
});

// 加载日历
function loadCalendar() {
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth();
    
    // 更新标题
    document.getElementById('calendarTitle').textContent = `${year}年${month + 1}月`;
    
    // 获取当月第一天和最后一天
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    
    // 获取当月第一天是星期几
    const firstDayOfWeek = firstDay.getDay();
    
    // 获取上月最后几天
    const prevMonthLastDay = new Date(year, month, 0).getDate();
    
    const gridContainer = document.getElementById('calendarGrid');
    
    // 清空现有的日期（保留星期头）
    const headers = gridContainer.querySelectorAll('.calendar-day-header');
    gridContainer.innerHTML = '';
    headers.forEach(header => gridContainer.appendChild(header));
    
    // 添加上月的日期
    for (let i = firstDayOfWeek - 1; i >= 0; i--) {
        const dayDiv = createDayDiv(prevMonthLastDay - i, true);
        gridContainer.appendChild(dayDiv);
    }
    
    // 添加当月的日期
    for (let day = 1; day <= lastDay.getDate(); day++) {
        const isToday = new Date().toDateString() === new Date(year, month, day).toDateString();
        const dayDiv = createDayDiv(day, false, isToday);
        gridContainer.appendChild(dayDiv);
    }
    
    // 添加下月的日期
    const remainingDays = 42 - (firstDayOfWeek + lastDay.getDate());
    for (let day = 1; day <= remainingDays; day++) {
        const dayDiv = createDayDiv(day, true);
        gridContainer.appendChild(dayDiv);
    }
}

// 创建日期格子
function createDayDiv(dayNumber, isOtherMonth, isToday = false) {
    const dayDiv = document.createElement('div');
    dayDiv.className = 'calendar-day';
    if (isOtherMonth) dayDiv.classList.add('other-month');
    if (isToday) dayDiv.classList.add('today');
    
    dayDiv.innerHTML = `
        <div class="day-number">${dayNumber}</div>
        <div class="event-dots" id="dots-${dayNumber}"></div>
        <div class="calendar-day-tooltip" id="tooltip-${dayNumber}"></div>
    `;
    
    // 点击日期显示当天所有事件
    dayDiv.onclick = function(e) {
        const events = getEventsByDay(dayNumber);
        if (events && events.length > 0) {
            showDayEvents(dayNumber, events);
        }
    };
    
    return dayDiv;
}

// 加载事件
async function loadEvents() {
    try {
        const year = currentDate.getFullYear();
        const month = currentDate.getMonth() + 1;
        
        // 获取当月所有事件
        const response = await fetch(`${API_BASE_URL}/getEventsByMonth`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                year: year,
                month: month
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            currentEvents = result.events || [];
            displayEventsOnCalendar();
        }
    } catch (error) {
        console.error('加载事件失败:', error);
    }
}

// 在日历上显示事件
function displayEventsOnCalendar() {
    // 清空所有日期的事件
    document.querySelectorAll('.event-dots').forEach(el => el.innerHTML = '');
    document.querySelectorAll('.calendar-day-tooltip').forEach(el => el.innerHTML = '');
    
    // 按日期分组事件
    const eventsByDay = {};
    
    currentEvents.forEach(event => {
        if (!event.event_time) return;
        
        const eventDate = new Date(event.event_time);
        const day = eventDate.getDate();
        
        // 检查是否是当前月份
        if (eventDate.getMonth() === currentDate.getMonth() && 
            eventDate.getFullYear() === currentDate.getFullYear()) {
            
            if (!eventsByDay[day]) {
                eventsByDay[day] = [];
            }
            eventsByDay[day].push(event);
        }
    });
    
    // 显示事件标记点和提示
    for (const day in eventsByDay) {
        const dotsContainer = document.getElementById(`dots-${day}`);
        const tooltipContainer = document.getElementById(`tooltip-${day}`);
        
        if (dotsContainer && tooltipContainer) {
            const events = eventsByDay[day];
            
            // 显示标记点（最多显示5个）
            events.slice(0, 5).forEach(event => {
                const dot = document.createElement('div');
                dot.className = 'event-dot';
                
                // 检查是否有冲突
                if (event.has_conflict) {
                    dot.classList.add('conflict');
                }
                
                dotsContainer.appendChild(dot);
            });
            
            // 如果超过5个事件，添加计数标记
            if (events.length > 5) {
                const parentDay = dotsContainer.parentElement;
                const count = document.createElement('div');
                count.className = 'event-count';
                count.textContent = `${events.length}`;
                parentDay.appendChild(count);
            }
            
            // 生成悬停提示内容
            let tooltipHTML = '';
            events.slice(0, 3).forEach(event => {
                const eventTime = new Date(event.event_time);
                const timeStr = `${eventTime.getHours().toString().padStart(2, '0')}:${eventTime.getMinutes().toString().padStart(2, '0')}`;
                const conflictIcon = event.has_conflict ? '⚠️ ' : '';
                
                tooltipHTML += `
                    <div class="tooltip-event">
                        <span class="tooltip-time">${timeStr}</span>
                        ${conflictIcon}${event.event_title}
                    </div>
                `;
            });
            
            if (events.length > 3) {
                tooltipHTML += `<div class="tooltip-event" style="color:#3498db; font-weight:600;">还有 ${events.length - 3} 个事件...</div>`;
            }
            
            tooltipContainer.innerHTML = tooltipHTML;
        }
    }
}

// 获取某一天的事件
function getEventsByDay(day) {
    return currentEvents.filter(event => {
        if (!event.event_time) return false;
        const eventDate = new Date(event.event_time);
        return eventDate.getDate() === day &&
               eventDate.getMonth() === currentDate.getMonth() &&
               eventDate.getFullYear() === currentDate.getFullYear();
    });
}

// 显示事件详情
function showEventDetails(event) {
    const modal = document.getElementById('eventModal');
    const title = document.getElementById('modalTitle');
    const content = document.getElementById('modalContent');
    
    title.textContent = event.event_title || '事件详情';
    
    let conflictHtml = '';
    if (event.has_conflict) {
        conflictHtml = `
            <div class="conflict-warning">
                ⚠️ <strong>时间冲突警告</strong><br>
                此事件与其他事件存在时间冲突，请注意调整时间安排。
            </div>
        `;
    }
    
    content.innerHTML = `
        ${conflictHtml}
        <div class="event-detail-row">
            <div class="event-detail-label">时间：</div>
            <div class="event-detail-value">${event.event_time || '待定'}</div>
        </div>
        <div class="event-detail-row">
            <div class="event-detail-label">地点：</div>
            <div class="event-detail-value">${event.standard_location || event.event_location || '待定'}</div>
        </div>
        <div class="event-detail-row">
            <div class="event-detail-label">活动类型：</div>
            <div class="event-detail-value">${event.activity_type || '通知'}</div>
        </div>
        <div class="event-detail-row">
            <div class="event-detail-label">主办单位：</div>
            <div class="event-detail-value">${event.organizer || '未知'}</div>
        </div>
        <div class="event-detail-row">
            <div class="event-detail-label">面向人群：</div>
            <div class="event-detail-value">${event.target_audience || '全体'}</div>
        </div>
        <div class="event-detail-row">
            <div class="event-detail-label">联系方式：</div>
            <div class="event-detail-value">${event.contact_info || '无'}</div>
        </div>
    `;
    
    modal.classList.add('show');
}

// 显示某一天的所有事件
function showDayEvents(day, events) {
    const modal = document.getElementById('eventModal');
    const title = document.getElementById('modalTitle');
    const content = document.getElementById('modalContent');
    
    const year = currentDate.getFullYear();
    const month = currentDate.getMonth() + 1;
    
    const weekDays = ['日', '一', '二', '三', '四', '五', '六'];
    const date = new Date(year, month - 1, day);
    const weekDay = weekDays[date.getDay()];
    
    title.innerHTML = `📅 ${year}年${month}月${day}日 星期${weekDay} <span style="color:#667eea;">(${events.length}个事件)</span>`;
    
    // 按时间排序
    events.sort((a, b) => new Date(a.event_time) - new Date(b.event_time));
    
    let eventsHtml = '';
    events.forEach((event, index) => {
        const eventTime = new Date(event.event_time);
        const timeStr = `${eventTime.getHours().toString().padStart(2, '0')}:${eventTime.getMinutes().toString().padStart(2, '0')}`;
        const conflictBadge = event.has_conflict ? '<span style="background:#e74c3c; color:white; padding:2px 8px; border-radius:4px; font-size:11px; margin-left:10px;">⚠️ 冲突</span>' : '';
        
        eventsHtml += `
            <div class="event-detail-row" style="cursor:pointer; border-left: 4px solid ${event.has_conflict ? '#e74c3c' : '#667eea'};" onclick='showEventDetails(${JSON.stringify(event)})'>
                <div style="flex:1;">
                    <div style="font-weight:700; font-size:16px; margin-bottom:5px;">
                        ${index + 1}. ${event.event_title} ${conflictBadge}
                    </div>
                    <div style="color:#7f8c8d; font-size:13px; display:flex; gap:15px; flex-wrap:wrap;">
                        <span>� ${timeStr}</span>
                        <span>�📍 ${event.standard_location || event.event_location || '待定'}</span>
                        <span>📋 ${event.activity_type || '通知'}</span>
                    </div>
                </div>
            </div>
        `;
    });
    
    content.innerHTML = eventsHtml;
    modal.classList.add('show');
}

// 关闭弹窗
function closeModal() {
    document.getElementById('eventModal').classList.remove('show');
}

// 上一月
function previousMonth() {
    currentDate.setMonth(currentDate.getMonth() - 1);
    loadCalendar();
    loadEvents();
}

// 下一月
function nextMonth() {
    currentDate.setMonth(currentDate.getMonth() + 1);
    loadCalendar();
    loadEvents();
}

// 今天
function today() {
    currentDate = new Date();
    loadCalendar();
    loadEvents();
}

// 点击弹窗外部关闭
document.addEventListener('click', function(e) {
    const modal = document.getElementById('eventModal');
    if (e.target === modal) {
        closeModal();
    }
});
