const API_BASE_URL = 'http://localhost:5000/api';
const USER_ID = 1;

async function loadSettings() {
    try {
        const response = await fetch(`${API_BASE_URL}/getSettings?user_id=${USER_ID}`);
        const result = await response.json();

        if (result.success) {
            const settings = result.settings;
            
            document.getElementById('advanceTime').value = settings.default_advance_minutes;
            document.getElementById('webNotify').checked = settings.web_notification;
            document.getElementById('emailNotify').checked = settings.email_notification;
            document.getElementById('smsNotify').checked = settings.sms_notification;
            document.getElementById('emailAddress').value = settings.email_address || '';
            document.getElementById('repeatDaily').checked = settings.repeat_daily;
            document.getElementById('repeatWeekly').checked = settings.repeat_weekly;
            document.getElementById('repeatMonthly').checked = settings.repeat_monthly;

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
        user_id: USER_ID,
        default_advance_minutes: parseInt(document.getElementById('advanceTime').value),
        web_notification: document.getElementById('webNotify').checked,
        email_notification: document.getElementById('emailNotify').checked,
        sms_notification: document.getElementById('smsNotify').checked,
        email_address: document.getElementById('emailAddress').value,
        phone_number: '',
        repeat_daily: document.getElementById('repeatDaily').checked,
        repeat_weekly: document.getElementById('repeatWeekly').checked,
        repeat_monthly: document.getElementById('repeatMonthly').checked
    };

    if (settings.email_notification && !settings.email_address) {
        alert('请输入邮件地址');
        return;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/updateSettings`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
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
        const response = await fetch(`${API_BASE_URL}/getStatistics?user_id=${USER_ID}`);
        const result = await response.json();

        if (result.success) {
            const stats = result.statistics;
            
            document.getElementById('completionRate').textContent = stats.completion_rate + '%';
            document.getElementById('processedCount').textContent = stats.completed;
            document.getElementById('unprocessedCount').textContent = stats.pending;

            renderTrendChart(stats.trend_data);
            renderTypeDistribution(stats.type_distribution);
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

document.addEventListener('DOMContentLoaded', function () {
    loadSettings();
    loadStatistics();

    document.getElementById('emailNotify').addEventListener('change', toggleEmailGroup);
});
