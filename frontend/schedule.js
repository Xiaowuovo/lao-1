// API_BASE_URL 和 getAuthHeaders 已在 auth-check.js 中声明

let schedules = [];
let currentCourseId = null;

// 11节次定义
const PERIODS = [
    { p: 1,  start: '08:00', end: '08:45', section: 'am' },
    { p: 2,  start: '08:55', end: '09:40', section: 'am' },
    { p: 3,  start: '10:00', end: '10:45', section: 'am' },
    { p: 4,  start: '10:55', end: '11:40', section: 'am' },
    { p: 5,  start: '14:00', end: '14:45', section: 'pm' },
    { p: 6,  start: '14:55', end: '15:40', section: 'pm' },
    { p: 7,  start: '16:00', end: '16:45', section: 'pm' },
    { p: 8,  start: '16:55', end: '17:40', section: 'pm' },
    { p: 9,  start: '19:00', end: '19:45', section: 'ev' },
    { p: 10, start: '19:55', end: '20:40', section: 'ev' },
    { p: 11, start: '20:50', end: '21:35', section: 'ev' },
];

const SECTION_LABELS = { am: '上午', pm: '下午', ev: '晚上' };
const SECTION_SIZES  = { am: 4, pm: 4, ev: 3 };

// ===== 节次同步到时间 =====
function syncTimeFromPeriod() {
    const ps = parseInt(document.getElementById('periodSelect').value);
    const pe = parseInt(document.getElementById('periodEndSelect').value);
    const startPeriod = PERIODS[ps - 1];
    const endPeriod   = PERIODS[Math.max(ps, pe) - 1];
    if (startPeriod) document.getElementById('startTime').value = startPeriod.start;
    if (endPeriod)   document.getElementById('endTime').value   = endPeriod.end;
}

// ===== 加载课表 =====
async function loadSchedule() {
    try {
        const response = await fetch(`${API_BASE_URL}/getSchedule`, { headers: getAuthHeaders() });
        const result = await response.json();
        if (result.require_login) { window.location.href = 'login.html'; return; }
        if (result.success) {
            schedules = result.data || [];
            renderTimetable();
        }
    } catch (e) {
        console.error('加载课表失败:', e);
    }
}

// ===== 获取某节次某天的课 =====
function getCoursesForPeriod(day, period) {
    const pStart = period.start;
    const pEnd   = period.end;
    return schedules.filter(c => {
        if (c.day_of_week !== day) return false;
        if (!c.start_time || !c.end_time) return false;
        const cs = c.start_time.substring(0, 5).padStart(5, '0');
        const ce = c.end_time.substring(0, 5).padStart(5, '0');
        // 课程与节次有重叠即显示
        return cs <= pEnd && ce >= pStart;
    });
}

// ===== 渲染课表 =====
function renderTimetable() {
    const tbody = document.getElementById('scheduleBody');
    let html = '';
    const sections = ['am', 'pm', 'ev'];

    sections.forEach(sec => {
        const periodsInSec = PERIODS.filter(p => p.section === sec);
        periodsInSec.forEach((period, idx) => {
            html += '<tr>';
            // 左侧"时间段"大格（只在第一行合并）
            if (idx === 0) {
                html += `<td class="section-label" rowspan="${periodsInSec.length}">${SECTION_LABELS[sec]}</td>`;
            }
            // 节次列
            html += `<td class="period-cell">${period.p}</td>`;
            // 7天
            for (let day = 1; day <= 7; day++) {
                const courses = getCoursesForPeriod(day, period);
                html += `<td class="course-td row-${sec}">`;
                courses.forEach(c => {
                    // 计算跨节提示
                    const startP = timeToPeriod(c.start_time);
                    const endP   = timeToPeriod(c.end_time);
                    const spanStr = startP && endP ? `(${startP}-${endP}节)` : '';
                    const weeksStr = c.weeks || '';
                    const examStr  = c.exam_type || '';

                    html += `<div class="course-card" onclick="showCourseDetail(${c.schedule_id})">
                        <div class="cc-name">${c.course_name}</div>
                        <div class="cc-row"><span class="cc-icon">🕐</span><span>${spanStr}${weeksStr ? ' ' + weeksStr : ''}</span></div>
                        <div class="cc-row"><span class="cc-icon">📍</span><span>${c.location || '未排地点'}</span></div>
                        <div class="cc-row"><span class="cc-icon">👤</span><span>${c.teacher || '未知'}</span></div>
                        ${examStr ? `<div class="cc-row"><span class="cc-icon">📋</span><span>${examStr}</span></div>` : ''}
                    </div>`;
                });
                html += '</td>';
            }
            html += '</tr>';
        });
    });

    tbody.innerHTML = html;
}

// 时间字符串 -> 节次编号
function timeToPeriod(timeStr) {
    if (!timeStr) return null;
    const t = timeStr.substring(0, 5).padStart(5, '0');
    const p = PERIODS.find(p => p.start <= t && t <= p.end);
    return p ? p.p : null;
}

// ===== 课程详情弹窗 =====
function showCourseDetail(scheduleId) {
    const c = schedules.find(x => x.schedule_id === scheduleId);
    if (!c) return;

    currentCourseId = scheduleId;
    const weekdays = ['', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日'];
    const startP = timeToPeriod(c.start_time);
    const endP   = timeToPeriod(c.end_time);
    const spanStr = startP && endP ? `(${startP}-${endP}节)` : '';

    document.getElementById('cmTitle').textContent = c.course_name;
    document.getElementById('cmBody').innerHTML = `
        <div class="cm-row"><span class="cm-icon">🕐</span><span>${weekdays[c.day_of_week]} ${spanStr} ${c.start_time ? c.start_time.substring(0,5) : ''}–${c.end_time ? c.end_time.substring(0,5) : ''}</span></div>
        <div class="cm-row"><span class="cm-icon">🗓</span><span>${c.weeks || '全学期'}</span></div>
        <div class="cm-row"><span class="cm-icon">📍</span><span>${c.location || '未排地点'}</span></div>
        <div class="cm-row"><span class="cm-icon">👤</span><span>${c.teacher || '未知教师'}</span></div>
        <div class="cm-row"><span class="cm-icon">📋</span><span>${c.exam_type || '未知'}</span></div>
    `;
    document.getElementById('cmDeleteBtn').onclick = () => deleteCourse(scheduleId);
    document.getElementById('courseModal').classList.add('show');
}

function closeCourseModal(e) {
    if (!e || e.target === document.getElementById('courseModal')) {
        document.getElementById('courseModal').classList.remove('show');
    }
}

// ===== 添加课程 =====
function toggleAddCourseForm() {
    const form = document.getElementById('addCourseForm');
    form.style.display = form.style.display === 'none' ? 'block' : 'none';
}

async function addCourse() {
    const courseName = document.getElementById('courseName').value.trim();
    const teacher    = document.getElementById('teacher').value.trim();
    const dayOfWeek  = parseInt(document.getElementById('dayOfWeek').value);
    const location   = document.getElementById('location').value.trim();
    const startTime  = document.getElementById('startTime').value;
    const endTime    = document.getElementById('endTime').value;
    const weeks      = document.getElementById('weeks').value.trim();
    const examType   = document.getElementById('examType').value;

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
                teacher, day_of_week: dayOfWeek,
                location, start_time: startTime, end_time: endTime,
                weeks, exam_type: examType
            })
        });
        const result = await response.json();
        if (result.success) {
            toggleAddCourseForm();
            clearForm();
            loadSchedule();
        } else {
            alert('添加失败: ' + result.message);
        }
    } catch (e) {
        console.error('添加课程失败:', e);
        alert('添加失败，请检查网络连接');
    }
}

function clearForm() {
    document.getElementById('courseName').value = '';
    document.getElementById('teacher').value = '';
    document.getElementById('location').value = '';
    document.getElementById('weeks').value = '1-18周';
    document.getElementById('examType').value = '';
    document.getElementById('periodSelect').value = '1';
    document.getElementById('periodEndSelect').value = '1';
    syncTimeFromPeriod();
}

// ===== 删除课程 =====
async function deleteCourse(scheduleId) {
    if (!confirm('确定要删除该课程吗？')) return;
    try {
        const response = await fetch(`${API_BASE_URL}/deleteCourse`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ schedule_id: scheduleId })
        });
        const result = await response.json();
        if (result.success) {
            closeCourseModal();
            loadSchedule();
        } else {
            alert('删除失败: ' + result.message);
        }
    } catch (e) {
        console.error('删除课程失败:', e);
        alert('删除失败');
    }
}

// ===== 初始化 =====
document.addEventListener('DOMContentLoaded', function () {
    const userInfo = getCurrentUser();
    if (userInfo) {
        document.getElementById('userName').textContent = userInfo.real_name || userInfo.username;
        document.getElementById('scheduleTitle').textContent = `${userInfo.real_name || userInfo.username} 的课表`;
        const userMenu = document.querySelector('.user-menu');
        userMenu.style.cursor = 'pointer';
        userMenu.onclick = () => { if (confirm('确定要退出登录吗？')) logout(); };
    }
    syncTimeFromPeriod();
    loadSchedule();
});
