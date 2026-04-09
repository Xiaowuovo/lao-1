const API_BASE_URL = 'http://localhost:5000/api';
const USER_ID = 1;

let archives = [];
let currentFilter = 'all';

async function loadArchive() {
    try {
        const search = document.getElementById('searchInput').value;
        const url = `${API_BASE_URL}/getArchive?user_id=${USER_ID}&limit=100${search ? '&search=' + search : ''}`;
        
        const response = await fetch(url);
        const result = await response.json();
        
        if (result.success) {
            archives = result.archives;
            displayArchive();
            updateStatistics();
        }
    } catch (error) {
        console.error('加载归档失败:', error);
    }
}

function displayArchive() {
    const container = document.getElementById('archiveContainer');
    
    let filteredArchives = archives;
    if (currentFilter !== 'all') {
        filteredArchives = archives.filter(a => a.completion_status === currentFilter);
    }
    
    if (filteredArchives.length === 0) {
        container.innerHTML = '<div class="empty-state"><p>暂无归档记录</p></div>';
        return;
    }
    
    let html = '';
    
    filteredArchives.forEach(archive => {
        const statusText = {
            'completed': '✓ 已完成',
            'cancelled': '✗ 已取消',
            'expired': '⏱ 已过期'
        }[archive.completion_status] || archive.completion_status;
        
        html += `
            <div class="archive-card ${archive.completion_status}">
                <div class="archive-header">
                    <div class="archive-title">${archive.event_title}</div>
                    <div class="archive-date">${archive.completion_time}</div>
                </div>
                
                <div class="archive-details">
                    <div><strong>事件时间:</strong> ${archive.event_time}</div>
                    <div><strong>地点:</strong> ${archive.event_location || '未指定'}</div>
                    <div><strong>状态:</strong> ${statusText}</div>
                    ${archive.deadline_time ? `<div><strong>截止时间:</strong> ${archive.deadline_time}</div>` : ''}
                    ${archive.organizer ? `<div><strong>主办:</strong> ${archive.organizer}</div>` : ''}
                    ${archive.activity_type ? `<div><strong>类型:</strong> ${getActivityTypeName(archive.activity_type)}</div>` : ''}
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

function getActivityTypeName(type) {
    const typeMap = {
        'competition': '竞赛',
        'lecture': '讲座',
        'recruitment': '招聘',
        'meeting': '会议',
        'payment': '缴费',
        'health_check': '体检',
        'other': '其他'
    };
    return typeMap[type] || type;
}

function filterArchive(status) {
    currentFilter = status;
    
    document.querySelectorAll('.archive-filters .filter-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    displayArchive();
}

function searchArchive() {
    loadArchive();
}

function updateStatistics() {
    const total = archives.length;
    const completed = archives.filter(a => a.completion_status === 'completed').length;
    const cancelled = archives.filter(a => a.completion_status === 'cancelled').length;
    
    document.getElementById('totalArchive').textContent = total;
    document.getElementById('completedArchive').textContent = completed;
    document.getElementById('cancelledArchive').textContent = cancelled;
}

async function exportArchive() {
    try {
        const response = await fetch(`${API_BASE_URL}/exportArchive?user_id=${USER_ID}`);
        const result = await response.json();
        
        if (result.success) {
            // 创建下载链接
            const blob = new Blob([result.data], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = result.filename;
            link.click();
            
            alert('导出成功！');
        } else {
            alert(`导出失败: ${result.message}`);
        }
    } catch (error) {
        console.error('导出失败:', error);
        alert('导出失败');
    }
}

document.addEventListener('DOMContentLoaded', function () {
    loadArchive();
});
