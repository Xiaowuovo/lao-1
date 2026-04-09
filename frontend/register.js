const API_BASE_URL = 'http://localhost:5000/api';

// 学号实时验证
document.getElementById('studentId').addEventListener('blur', async function(e) {
    const studentId = e.target.value.trim();
    const errorEl = document.getElementById('studentIdError');
    const successEl = document.getElementById('studentIdSuccess');
    
    errorEl.classList.remove('show');
    successEl.classList.remove('show');
    e.target.classList.remove('error', 'success');
    
    if (!studentId) return;
    
    if (studentId.length !== 12) {
        e.target.classList.add('error');
        errorEl.textContent = '学号必须为12位';
        errorEl.classList.add('show');
        return;
    }
    
    if (!/^\d{12}$/.test(studentId)) {
        e.target.classList.add('error');
        errorEl.textContent = '学号只能包含数字';
        errorEl.classList.add('show');
        return;
    }
    
    // 调用后端验证学号格式
    try {
        const response = await fetch(`${API_BASE_URL}/auth/validateStudentId`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ student_id: studentId })
        });
        
        const result = await response.json();
        
        if (result.success && result.valid) {
            e.target.classList.add('success');
            successEl.textContent = '✓ 学号格式正确';
            successEl.classList.add('show');
        } else {
            e.target.classList.add('error');
            errorEl.textContent = result.message || '学号格式错误';
            errorEl.classList.add('show');
        }
    } catch (error) {
        console.error('验证学号失败:', error);
    }
});

// 密码强度检测
document.getElementById('password').addEventListener('input', function(e) {
    const password = e.target.value;
    const strengthEl = document.getElementById('passwordStrength');
    const bar = strengthEl.querySelector('.password-strength-bar');
    
    if (password.length === 0) {
        strengthEl.classList.remove('show');
        return;
    }
    
    strengthEl.classList.add('show');
    
    let strength = 0;
    if (password.length >= 6) strength++;
    if (password.length >= 10) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[a-z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^A-Za-z0-9]/.test(password)) strength++;
    
    bar.className = 'password-strength-bar';
    if (strength <= 2) {
        bar.classList.add('weak');
    } else if (strength <= 4) {
        bar.classList.add('medium');
    } else {
        bar.classList.add('strong');
    }
});

// 确认密码验证
document.getElementById('confirmPassword').addEventListener('input', function(e) {
    const password = document.getElementById('password').value;
    const confirmPassword = e.target.value;
    const errorEl = document.getElementById('confirmPasswordError');
    
    errorEl.classList.remove('show');
    e.target.classList.remove('error', 'success');
    
    if (confirmPassword.length === 0) return;
    
    if (password !== confirmPassword) {
        e.target.classList.add('error');
        errorEl.textContent = '两次输入的密码不一致';
        errorEl.classList.add('show');
    } else {
        e.target.classList.add('success');
    }
});

// 邮箱格式验证
document.getElementById('email').addEventListener('blur', function(e) {
    const email = e.target.value.trim();
    const errorEl = document.getElementById('emailError');
    
    errorEl.classList.remove('show');
    e.target.classList.remove('error');
    
    if (email && !/^[\w\.-]+@[\w\.-]+\.\w+$/.test(email)) {
        e.target.classList.add('error');
        errorEl.textContent = '邮箱格式不正确';
        errorEl.classList.add('show');
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
    const registerBtn = document.getElementById('registerBtn');
    
    if (isLoading) {
        loadingEl.classList.add('show');
        registerBtn.disabled = true;
        registerBtn.textContent = '注册中...';
    } else {
        loadingEl.classList.remove('show');
        registerBtn.disabled = false;
        registerBtn.textContent = '立即注册';
    }
}

// 处理注册
async function handleRegister(event) {
    event.preventDefault();
    
    const studentId = document.getElementById('studentId').value.trim();
    const username = document.getElementById('username').value.trim();
    const realName = document.getElementById('realName').value.trim();
    const email = document.getElementById('email').value.trim();
    const phone = document.getElementById('phone').value.trim();
    const password = document.getElementById('password').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    // 基础验证
    if (studentId.length !== 12 || !/^\d{12}$/.test(studentId)) {
        showAlert('请输入正确的12位学号');
        return;
    }
    
    if (username.length < 2) {
        showAlert('用户名长度至少2位');
        return;
    }
    
    if (!realName) {
        showAlert('请输入真实姓名');
        return;
    }
    
    if (!/^[\w\.-]+@[\w\.-]+\.\w+$/.test(email)) {
        showAlert('邮箱格式不正确');
        return;
    }
    
    if (password.length < 6) {
        showAlert('密码长度至少6位');
        return;
    }
    
    if (password !== confirmPassword) {
        showAlert('两次输入的密码不一致');
        return;
    }
    
    setLoading(true);
    
    try {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                student_id: studentId,
                username: username,
                real_name: realName,
                email: email,
                phone: phone,
                password: password
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showAlert('注册成功！3秒后跳转到登录页面...', 'success');
            
            setTimeout(() => {
                window.location.href = 'login.html';
            }, 3000);
        } else {
            showAlert(result.message || '注册失败');
        }
    } catch (error) {
        console.error('注册错误:', error);
        showAlert('网络错误，请检查后端服务是否启动');
    } finally {
        setLoading(false);
    }
}
