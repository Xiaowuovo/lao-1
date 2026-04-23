const API_BASE_URL = 'http://localhost:5000/api';

// 获取认证token
function getAuthHeaders() {
    const token = localStorage.getItem('sessionToken');
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
    };
}

let schedules = [];

const timeSlots = [
    '08:00-09:40',
    '10:00-11:40',
    '14:00-15:40',
    '16:00-17:40',
    '19:00-20:40'
];

const weekdays = ['', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'];

async function loadSchedule() {
    try {
        const response = await fetch(`${API_BASE_URL}/getSchedule`, {
            headers: getAuthHeaders()
        });
        const result = await response.json();
        
        if (result.require_login) {
            window.location.href = 'login.html';
            return;
        }
        
        if (result.success) {
            schedules = result.data || [];
            renderScheduleGrid();
        }
    } catch (error) {
        console.error('加载课表失败:', error);
    }
}

function renderScheduleGrid() {
    const grid = document.getElementById('scheduleGrid');
    let html = '';
    
    // 表头
    html += '<div class="schedule-cell schedule-header">时间</div>';
    for (let i = 1; i <= 7; i++) {
        html += `<div class="schedule-cell schedule-header">${weekdays[i]}</div>`;
    }
    
    // 时间槽
    timeSlots.forEach(timeSlot => {
        html += `<div class="schedule-cell time-slot">${timeSlot}</div>`;
        
        for (let day = 1; day <= 7; day++) {
            const courses = getCoursesForSlot(day, timeSlot);
            html += `<div class="schedule-cell">`;
            
            courses.forEach(course => {
                html += `
                    <div class="course-item" onclick="showCourseDetail(${course.schedule_id})">
                        <div class="course-name">${course.course_name}</div>
                        <div class="course-location">${course.location || '未指定'}</div>
                        ${course.teacher ? `<div class="course-location">${course.teacher}</div>` : ''}
                    </div>
                `;
            });
            
            html += `</div>`;
        }
    });
    
    grid.innerHTML = html;
}

function getCoursesForSlot(day, timeSlot) {
    const [slotStart, slotEnd] = timeSlot.split('-');
    
    return schedules.filter(course => {
        if (course.day_of_week !== day) return false;
        
        const courseStart = course.start_time.substring(0, 5);
        const courseEnd = course.end_time.substring(0, 5);
        
        return courseStart >= slotStart && courseEnd <= slotEnd;
    });
}

function toggleAddCourseForm() {
    const form = document.getElementById('addCourseForm');
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}

async function addCourse() {
    const courseName = document.getElementById('courseName').value;
    const teacher = document.getElementById('teacher').value;
    const dayOfWeek = parseInt(document.getElementById('dayOfWeek').value);
    const location = document.getElementById('location').value;
    const startTime = document.getElementById('startTime').value;
    const endTime = document.getElementById('endTime').value;
    const weeks = document.getElementById('weeks').value;
    
    if (!courseName || !startTime || !endTime) {
        alert('请填写课程名称和上课时间');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/addCourse`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                course_name: courseName,
                teacher: teacher,
                day_of_week: dayOfWeek,
                location: location,
                start_time: startTime,
                end_time: endTime
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('课程添加成功！');
            toggleAddCourseForm();
            clearForm();
            loadSchedule();
        } else {
            alert(`添加失败: ${result.message}`);
        }
    } catch (error) {
        console.error('添加课程失败:', error);
        alert('添加失败，请检查网络连接');
    }
}

function clearForm() {
    document.getElementById('courseName').value = '';
    document.getElementById('teacher').value = '';
    document.getElementById('location').value = '';
    document.getElementById('weeks').value = '1-18';
}

function showCourseDetail(scheduleId) {
    const course = schedules.find(c => c.schedule_id === scheduleId);
    if (!course) return;
    
    const message = `
课程：${course.course_name}
教师：${course.teacher || '未指定'}
时间：${weekdays[course.day_of_week]} ${course.start_time} - ${course.end_time}
地点：${course.location || '未指定'}
周次：${course.weeks || '全学期'}

是否删除该课程？
    `;
    
    if (confirm(message)) {
        deleteCourse(scheduleId);
    }
}

async function deleteCourse(scheduleId) {
    try {
        const response = await fetch(`${API_BASE_URL}/deleteCourse`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ schedule_id: scheduleId })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('课程已删除');
            loadSchedule();
        } else {
            alert(`删除失败: ${result.message}`);
        }
    } catch (error) {
        console.error('删除课程失败:', error);
        alert('删除失败');
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
    
    loadSchedule();
});
