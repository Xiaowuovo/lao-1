const API_BASE_URL = 'http://localhost:5000/api';

// 学号实时验证
document.getElementById('studentId').addEventListener('input', function(e) {
    const studentId = e.target.value;
    const errorEl = document.getElementById('studentIdError');
    
    if (studentId.length > 0 && studentId.length !== 12) {
        e.target.classList.add('error');
        errorEl.textContent = '学号必须为12位';
        errorEl.classList.add('show');
    } else if (studentId.length === 12 && !/^\d{12}$/.test(studentId)) {
        e.target.classList.add('error');
        errorEl.textContent = '学号只能包含数字';
        errorEl.classList.add('show');
    } else {
        e.target.classList.remove('error');
        errorEl.classList.remove('show');
    }
});

// 显示提示信息
function showAlert(message, type = 'error') {
    const alertBox = document.getElementById('alertBox');
    alertBox.className = `alert alert-${type} show`;
    alertBox.textContent = message;
    
    setTimeout(() => {
        alertBox.classList.remove('show');
    }, 5000);
}

// 显示加载状态
function setLoading(isLoading) {
    const loadingEl = document.getElementById('loading');
    const loginBtn = document.getElementById('loginBtn');
    
    if (isLoading) {
        loadingEl.classList.add('show');
        loginBtn.disabled = true;
        loginBtn.textContent = '登录中...';
    } else {
        loadingEl.classList.remove('show');
        loginBtn.disabled = false;
        loginBtn.textContent = '登录';
    }
}

// 处理登录
async function handleLogin(event) {
    event.preventDefault();
    
    const studentId = document.getElementById('studentId').value.trim();
    const password = document.getElementById('password').value;
    const rememberMe = document.getElementById('rememberMe').checked;
    
    // 基础验证
    if (!studentId || studentId.length !== 12) {
        showAlert('请输入正确的12位学号');
        return;
    }
    
    if (!password || password.length < 6) {
        showAlert('密码长度至少6位');
        return;
    }
    
    setLoading(true);
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            credentials: 'include',  // 允许发送cookie
            body: JSON.stringify({
                student_id: studentId,
                password: password
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // 保存用户信息到localStorage
            const userInfo = {
                user_id: result.user_info.user_id,
                student_id: result.user_info.student_id,
                username: result.user_info.username,
                real_name: result.user_info.real_name,
                college_name: result.user_info.college_name,
                role: result.user_info.role,
                session_token: result.session_token
            };
            
            localStorage.setItem('userInfo', JSON.stringify(userInfo));
            localStorage.setItem('sessionToken', result.session_token);
            
            if (rememberMe) {
                localStorage.setItem('rememberMe', 'true');
                localStorage.setItem('lastStudentId', studentId);
            } else {
                localStorage.removeItem('rememberMe');
                localStorage.removeItem('lastStudentId');
            }
            
            showAlert('登录成功！正在跳转...', 'success');
            
            // 延迟跳转，让用户看到成功提示
            setTimeout(() => {
                window.location.href = 'index.html';
            }, 1000);
        } else {
            showAlert(result.message || '登录失败，请检查学号和密码');
        }
    } catch (error) {
        console.error('登录错误:', error);
        showAlert('网络错误，请检查后端服务是否启动');
    } finally {
        setLoading(false);
    }
}

// 页面加载时检查是否已登录
window.addEventListener('DOMContentLoaded', function() {
    const sessionToken = localStorage.getItem('sessionToken');
    
    if (sessionToken) {
        // 已登录，直接跳转
        window.location.href = 'index.html';
        return;
    }
    
    // 检查是否记住了学号
    if (localStorage.getItem('rememberMe') === 'true') {
        const lastStudentId = localStorage.getItem('lastStudentId');
        if (lastStudentId) {
            document.getElementById('studentId').value = lastStudentId;
            document.getElementById('rememberMe').checked = true;
        }
    }
});

// 快捷键支持
document.addEventListener('keydown', function(e) {
    // Ctrl+Enter 快速登录
    if (e.ctrlKey && e.key === 'Enter') {
        document.getElementById('loginForm').dispatchEvent(new Event('submit'));
    }
});
