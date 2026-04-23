const API_BASE_URL = 'http://localhost:5000/api';

// 获取认证token
function getAuthHeaders() {
    const token = localStorage.getItem('sessionToken');
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
    };
}

let archives = [];
let currentFilter = 'all';

async function loadArchive() {
    try {
        const search = document.getElementById('searchInput').value;
        let url = `${API_BASE_URL}/getArchive?page=1&page_size=100`;
        
        if (search) {
            url = `${API_BASE_URL}/searchArchive?keyword=${encodeURIComponent(search)}`;
        }
        
        const response = await fetch(url, {
            headers: getAuthHeaders()
        });
        const result = await response.json();
        
        if (result.require_login) {
            window.location.href = 'login.html';
            return;
        }
        
        if (result.success) {
            archives = search ? result.data : (result.data.events || []);
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
        const token = localStorage.getItem('sessionToken');
        const response = await fetch(`${API_BASE_URL}/exportArchive`, {
            headers: {
                'Authorization': token ? `Bearer ${token}` : ''
            }
        });
        
        if (response.ok) {
            const csvContent = await response.text();
            // 创建下载链接
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = 'archive.csv';
            link.click();
            
            alert('导出成功！');
        } else {
            alert('导出失败');
        }
    } catch (error) {
        console.error('导出失败:', error);
        alert('导出失败');
    }
}

document.addEventListener('DOMContentLoaded', function () {
    // 检查登录状态
    if (typeof checkAuth !== 'undefined' && !checkAuth()) {
        return;
    }
    
    // 更新用户信息显示
    if (typeof getCurrentUser !== 'undefined') {
        const userInfo = getCurrentUser();
        if (userInfo) {
            document.getElementById('userName').textContent = userInfo.real_name || userInfo.username;
            
            // 添加点击退出功能
            const userMenu = document.querySelector('.user-menu');
            userMenu.style.cursor = 'pointer';
            userMenu.onclick = function() {
                if (confirm('确定要退出登录吗？')) {
                    if (typeof logout !== 'undefined') {
                        logout();
                    }
                }
            };
        }
    }
    
    loadArchive();
});
