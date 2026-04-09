/**
 * 前端认证检查模块
 * 用于所有需要登录的页面
 */

const API_BASE_URL = 'http://localhost:5000/api';

// 获取当前用户信息
function getCurrentUser() {
    const userInfoStr = localStorage.getItem('userInfo');
    if (!userInfoStr) return null;
    
    try {
        return JSON.parse(userInfoStr);
    } catch {
        return null;
    }
}

// 获取会话令牌
function getSessionToken() {
    return localStorage.getItem('sessionToken');
}

// 检查是否已登录
function checkAuth() {
    const token = getSessionToken();
    const userInfo = getCurrentUser();
    
    if (!token || !userInfo) {
        // 未登录，跳转到登录页面
        window.location.href = 'login.html';
        return false;
    }
    
    return true;
}

// 验证会话是否有效（可选，异步）
async function verifySession() {
    const token = getSessionToken();
    
    if (!token) {
        return false;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/profile`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        });
        
        const result = await response.json();
        
        if (!result.success || result.require_login) {
            // 会话已失效
            logout();
            return false;
        }
        
        return true;
    } catch (error) {
        console.error('验证会话失败:', error);
        return false;
    }
}

// 登出
function logout() {
    const token = getSessionToken();
    
    // 调用后端登出接口
    if (token) {
        fetch(`${API_BASE_URL}/auth/logout`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            credentials: 'include'
        }).catch(err => console.error('登出请求失败:', err));
    }
    
    // 清除本地存储
    localStorage.removeItem('userInfo');
    localStorage.removeItem('sessionToken');
    
    // 跳转到登录页
    window.location.href = 'login.html';
}

// 带认证的API请求
async function authFetch(url, options = {}) {
    const token = getSessionToken();
    
    if (!token) {
        logout();
        throw new Error('未登录');
    }
    
    // 添加认证头
    const headers = {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...options.headers
    };
    
    const response = await fetch(url, {
        ...options,
        headers,
        credentials: 'include'
    });
    
    const result = await response.json();
    
    // 检查是否需要重新登录
    if (result.require_login) {
        logout();
        throw new Error('会话已过期');
    }
    
    return result;
}

// 更新用户信息显示
function updateUserDisplay() {
    const userInfo = getCurrentUser();
    
    if (!userInfo) return;
    
    // 更新用户名显示
    const userNameElements = document.querySelectorAll('.user-display-name, #userName');
    userNameElements.forEach(el => {
        el.textContent = userInfo.real_name || userInfo.username;
    });
    
    // 更新学院显示
    const collegeElements = document.querySelectorAll('.user-college');
    collegeElements.forEach(el => {
        el.textContent = userInfo.college_name || '';
    });
    
    // 更新学号显示
    const studentIdElements = document.querySelectorAll('.user-student-id');
    studentIdElements.forEach(el => {
        el.textContent = userInfo.student_id || '';
    });
}

// 创建用户菜单
function createUserMenu() {
    const userInfo = getCurrentUser();
    if (!userInfo) return '';
    
    return `
        <div class="user-menu-dropdown">
            <button class="user-menu-btn" onclick="toggleUserMenu()">
                <span class="user-avatar">${(userInfo.real_name || userInfo.username).charAt(0)}</span>
                <span class="user-name">${userInfo.real_name || userInfo.username}</span>
                <span class="dropdown-arrow">▼</span>
            </button>
            <div class="user-menu-content" id="userMenuContent" style="display:none;">
                <div class="user-menu-header">
                    <div class="user-menu-name">${userInfo.real_name || userInfo.username}</div>
                    <div class="user-menu-info">${userInfo.student_id}</div>
                    <div class="user-menu-info">${userInfo.college_name || ''}</div>
                </div>
                <div class="user-menu-divider"></div>
                <a href="profile.html" class="user-menu-item">
                    <span>👤</span> 个人资料
                </a>
                <a href="setting.html" class="user-menu-item">
                    <span>⚙️</span> 系统设置
                </a>
                <div class="user-menu-divider"></div>
                <a href="#" onclick="logout(); return false;" class="user-menu-item logout">
                    <span>🚪</span> 退出登录
                </a>
            </div>
        </div>
    `;
}

// 切换用户菜单
function toggleUserMenu() {
    const menuContent = document.getElementById('userMenuContent');
    if (menuContent) {
        menuContent.style.display = menuContent.style.display === 'none' ? 'block' : 'none';
    }
}

// 点击外部关闭菜单
document.addEventListener('click', function(e) {
    const userMenu = document.querySelector('.user-menu-dropdown');
    const menuContent = document.getElementById('userMenuContent');
    
    if (userMenu && menuContent && !userMenu.contains(e.target)) {
        menuContent.style.display = 'none';
    }
});

// 页面加载时检查认证
document.addEventListener('DOMContentLoaded', function() {
    // 检查是否在登录或注册页面
    const currentPage = window.location.pathname.split('/').pop();
    
    if (currentPage !== 'login.html' && currentPage !== 'register.html') {
        // 需要登录的页面，检查认证
        if (!checkAuth()) {
            return;
        }
        
        // 更新用户信息显示
        updateUserDisplay();
        
        // 可选：异步验证会话
        verifySession().then(valid => {
            if (!valid) {
                console.log('会话已失效，需要重新登录');
            }
        });
    }
});

// 添加用户菜单样式
const userMenuStyles = `
<style>
.user-menu-dropdown {
    position: relative;
    display: inline-block;
}

.user-menu-btn {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: white;
    border: 1px solid #ddd;
    border-radius: 20px;
    cursor: pointer;
    transition: all 0.3s;
}

.user-menu-btn:hover {
    background: #f5f5f5;
    border-color: #999;
}

.user-avatar {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: bold;
    font-size: 14px;
}

.user-name {
    font-size: 14px;
    color: #333;
}

.dropdown-arrow {
    font-size: 10px;
    color: #999;
}

.user-menu-content {
    position: absolute;
    right: 0;
    top: 100%;
    margin-top: 8px;
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    min-width: 220px;
    z-index: 1000;
}

.user-menu-header {
    padding: 15px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border-radius: 8px 8px 0 0;
}

.user-menu-name {
    font-weight: bold;
    font-size: 16px;
    margin-bottom: 4px;
}

.user-menu-info {
    font-size: 12px;
    opacity: 0.9;
    margin: 2px 0;
}

.user-menu-divider {
    height: 1px;
    background: #e0e0e0;
    margin: 8px 0;
}

.user-menu-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 12px 15px;
    color: #333;
    text-decoration: none;
    transition: background 0.2s;
}

.user-menu-item:hover {
    background: #f5f5f5;
}

.user-menu-item.logout {
    color: #f44336;
}

.user-menu-item span {
    font-size: 18px;
}
</style>
`;

// 自动注入样式
if (document.head) {
    document.head.insertAdjacentHTML('beforeend', userMenuStyles);
}
