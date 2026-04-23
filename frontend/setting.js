// API_BASE_URL 和 getAuthHeaders 已在 auth-check.js 中声明

async function loadSettings() {
    try {
        const response = await fetch(`${API_BASE_URL}/getSettings`, {
            headers: getAuthHeaders()
        });
        const result = await response.json();

        if (result.require_login) {
            window.location.href = 'login.html';
            return;
        }

        if (result.success && result.data) {
            const settings = result.data;
            
            document.getElementById('advanceTime').value = settings.reminder_advance_time || 30;
            document.getElementById('webNotify').checked = settings.web_notification;
            document.getElementById('emailNotify').checked = settings.email_notification;

            toggleEmailGroup();
        }
    } catch (error) {
        console.error('加载设置失败:', error);
    }
}

function toggleEmailGroup() {
    const emailNotify = document.getElementById('emailNotify').checked;
    const emailGroup = document.getElementById('emailGroup');
    
    if (emailNotify) {
        emailGroup.style.display = 'block';
    } else {
        emailGroup.style.display = 'none';
    }
}

async function saveSettings() {
    const settings = {
        reminder_advance_time: parseInt(document.getElementById('advanceTime').value),
        web_notification: document.getElementById('webNotify').checked,
        email_notification: document.getElementById('emailNotify').checked,
        sound_notification: true
    };

    try {
        const response = await fetch(`${API_BASE_URL}/saveSettings`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify(settings)
        });

        const result = await response.json();

        if (result.success) {
            alert('设置已保存！');
        } else {
            alert(`保存失败: ${result.message}`);
        }
    } catch (error) {
        console.error('保存设置失败:', error);
        alert('保存失败，请检查网络连接');
    }
}

async function loadStatistics() {
    try {
        const response = await fetch(`${API_BASE_URL}/getStatistics`, {
            headers: getAuthHeaders()
        });
        const result = await response.json();

        if (result.success && result.data) {
            const stats = result.data;
            
            const rate = stats.total_reminders > 0 ? Math.round(stats.completed_reminders * 100 / stats.total_reminders) : 0;
            document.getElementById('completionRate').textContent = rate + '%';
            document.getElementById('processedCount').textContent = stats.completed_reminders || 0;
            document.getElementById('unprocessedCount').textContent = stats.pending_reminders || 0;
        }
    } catch (error) {
        console.error('加载统计失败:', error);
    }
}

function renderTrendChart(trendData) {
    const chartElement = document.getElementById('trendChart');
    
    if (!trendData || trendData.length === 0) {
        chartElement.innerHTML = '<p style="text-align:center; color:#999;">暂无数据</p>';
        return;
    }

    const maxCount = Math.max(...trendData.map(d => d.count));
    const chartHeight = 200;

    let chartHTML = '<div style="display: flex; align-items: flex-end; justify-content: space-around; height: ' + chartHeight + 'px; padding: 10px;">';
    
    trendData.slice(-10).forEach(data => {
        const barHeight = maxCount > 0 ? (data.count / maxCount * chartHeight * 0.8) : 0;
        const date = data.date ? data.date.substring(5) : '';
        
        chartHTML += `
            <div style="display: flex; flex-direction: column; align-items: center; flex: 1; margin: 0 2px;">
                <div style="font-size: 12px; margin-bottom: 5px;">${data.count}</div>
                <div style="width: 30px; background: #3498db; border-radius: 3px 3px 0 0;" 
                     data-height="${barHeight}" class="chart-bar"></div>
                <div style="font-size: 10px; margin-top: 5px; transform: rotate(-45deg); white-space: nowrap;">${date}</div>
            </div>
        `;
    });
    
    chartHTML += '</div>';
    chartElement.innerHTML = chartHTML;

    document.querySelectorAll('.chart-bar').forEach(bar => {
        const height = bar.getAttribute('data-height');
        setTimeout(() => {
            bar.style.height = height + 'px';
            bar.style.transition = 'height 0.5s ease';
        }, 100);
    });
}

function renderTypeDistribution(typeData) {
    const legendElement = document.getElementById('typeLegend');
    
    if (!typeData || typeData.length === 0) {
        legendElement.innerHTML = '<p style="text-align:center; color:#999;">暂无数据</p>';
        return;
    }

    const typeNames = {
        'academic': '学术活动',
        'meeting': '会议',
        'exam': '考试',
        'activity': '活动',
        'other': '其他'
    };

    const colors = ['#3498db', '#e74c3c', '#f39c12', '#2ecc71', '#9b59b6'];

    let legendHTML = '';
    typeData.forEach((type, index) => {
        const typeName = typeNames[type.event_type] || type.event_type;
        const color = colors[index % colors.length];
        
        legendHTML += `
            <div style="display: flex; align-items: center; margin: 10px 0;">
                <div style="width: 20px; height: 20px; background: ${color}; border-radius: 3px; margin-right: 10px;"></div>
                <div style="flex: 1;">${typeName}</div>
                <div style="font-weight: bold;">${type.count}</div>
            </div>
        `;
    });

    legendElement.innerHTML = legendHTML;
}

function exportStats() {
    alert('导出功能开发中，敬请期待！');
}

// 邮件通知复选框事件监听（延迟绑定，等待DOM加载）
setTimeout(function() {
    const emailNotifyEl = document.getElementById('emailNotify');
    if (emailNotifyEl) {
        emailNotifyEl.addEventListener('change', toggleEmailGroup);
    }
}, 100);
