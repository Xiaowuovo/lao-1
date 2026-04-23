// 湘潭大学智慧校园任务管理系统 - 集成版

let currentEventCard = null;

// 文件选择处理 - 支持多种格式
async function handleFileSelect(event) {
    console.log('文件选择:', event);
    const file = event.target.files[0];
    
    if (!file) {
        return;
    }
    
    console.log('选择的文件:', file.name, '类型:', file.type, '大小:', file.size);
    
    const fileExt = file.name.substring(file.name.lastIndexOf('.')).toLowerCase();
    const fileName = file.name;
    
    document.getElementById('fileName').textContent = `已选择文件: ${fileName}`;
    document.getElementById('uploadProgress').style.display = 'block';
    document.getElementById('uploadProgress').textContent = '⏳ 正在处理文件...';
    
    try {
        let text = '';
        
        // 根据文件类型选择处理方式
        if (fileExt === '.txt') {
            // 文本文件直接读取
            text = await readTextFile(file);
        } else if (fileExt === '.pdf') {
            // PDF文件上传到后端处理
            text = await uploadFileToBackend(file, 'pdf');
        } else if (fileExt === '.doc' || fileExt === '.docx') {
            // Word文件上传到后端处理
            text = await uploadFileToBackend(file, 'word');
        } else if (['.jpg', '.jpeg', '.png', '.gif', '.bmp'].includes(fileExt)) {
            // 图片文件进行OCR
            text = await uploadFileToBackend(file, 'image');
        } else {
            throw new Error('不支持的文件格式');
        }
        
        if (text && text.trim()) {
            document.getElementById('inputText').value = text;
            document.getElementById('uploadProgress').textContent = `文件处理成功！提取了 ${text.length} 个字符`;
            document.getElementById('uploadProgress').style.background = '#d4edda';
            document.getElementById('uploadProgress').style.color = '#155724';
            
            setTimeout(() => {
                document.getElementById('uploadProgress').style.display = 'none';
            }, 3000);
        } else {
            throw new Error('未能从文件中提取到文本内容');
        }
    } catch (error) {
        console.error('文件处理错误:', error);
        document.getElementById('uploadProgress').textContent = `处理失败: ${error.message}`;
        document.getElementById('uploadProgress').style.background = '#f8d7da';
        document.getElementById('uploadProgress').style.color = '#721c24';
        alert(`文件处理失败：${error.message}`);
    }
}

// 读取文本文件
function readTextFile(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        
        reader.onload = function(e) {
            resolve(e.target.result);
        };
        
        reader.onerror = function(e) {
            reject(new Error('文件读取失败'));
        };
        
        reader.readAsText(file, 'UTF-8');
    });
}

// 上传文件到后端处理（PDF/Word/图片OCR）
async function uploadFileToBackend(file, fileType) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('file_type', fileType);
    
    try {
        const response = await fetch(`${API_BASE_URL}/processFile`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${getSessionToken()}`
            },
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const result = await response.json();
        
        if (result.require_login) {
            alert('会话已过期，请重新登录');
            window.location.href = 'login.html';
            return '';
        }
        
        if (result.success && result.text) {
            return result.text;
        } else {
            throw new Error(result.message || '文件处理失败');
        }
    } catch (error) {
        console.error('上传文件失败:', error);
        throw error;
    }
}

// 提取事件 - 使用湘大增强提取器（单个）
async function extractEvents() {
    const inputText = document.getElementById('inputText').value;
    
    if (!inputText.trim()) {
        alert("请输入或上传文本内容");
        return;
    }

    const container = document.getElementById('eventsContainer');
    container.innerHTML = '<div class="empty-state"><p>正在智能提取事件信息...</p></div>';

    try {
        const response = await fetch(`${API_BASE_URL}/xtu/extractEvents`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ text: inputText })
        });

        const result = await response.json();
        console.log('提取结果:', result);

        if (result.require_login) {
            alert('会话已过期，请重新登录');
            window.location.href = 'login.html';
            return;
        }

        if (result.success && result.event_card) {
            currentEventCard = result.event_card;
            
            // 检查时间冲突
            if (result.event_card.time) {
                await checkConflicts(result.event_card.time);
            }
            
            displayConfirmationCard(result.event_card);
        } else {
            container.innerHTML = `<div class="empty-state"><p>${result.message || '提取失败'}</p></div>`;
            alert(`提取失败: ${result.message || '未知错误'}`);
        }
    } catch (error) {
        console.error('提取事件失败:', error);
        container.innerHTML = '<div class="empty-state"><p>提取失败，请检查网络连接</p></div>';
        alert(`提取失败：${error.message}`);
    }
}

// 批量提取事件
async function extractBatchEvents() {
    console.log('批量提取函数被调用');
    
    const inputText = document.getElementById('inputText').value;
    console.log('输入文本长度:', inputText.length);
    
    if (!inputText.trim()) {
        alert("请输入或上传文本内容");
        return;
    }

    const container = document.getElementById('eventsContainer');
    container.innerHTML = '<div class="empty-state"><p>正在批量提取事件...</p></div>';
    console.log('开始调用API...');

    try {
        console.log('API URL:', `${API_BASE_URL}/xtu/extractBatch`);
        const response = await fetch(`${API_BASE_URL}/xtu/extractBatch`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ text: inputText })
        });

        console.log('响应状态:', response.status);
        const result = await response.json();
        console.log('批量提取结果:', result);

        if (result.require_login) {
            alert('会话已过期，请重新登录');
            window.location.href = 'login.html';
            return;
        }

        if (result.success && result.event_cards && result.event_cards.length > 0) {
            displayBatchCards(result.event_cards);
        } else {
            container.innerHTML = `<div class="empty-state"><p>${result.message || '未提取到事件'}</p></div>`;
        }
    } catch (error) {
        console.error('批量提取失败:', error);
        container.innerHTML = '<div class="empty-state"><p>批量提取失败</p></div>';
        alert(`批量提取失败：${error.message}`);
    }
}

// 显示批量事件卡片
function displayBatchCards(eventCards) {
    const container = document.getElementById('eventsContainer');
    
    let html = `<div style="padding:20px; background:#e3f2fd; border-radius:8px; margin-bottom:20px;">
        <h3>成功提取 ${eventCards.length} 个事件</h3>
        <p>请逐一确认并保存</p>
    </div>`;
    
    eventCards.forEach((card, index) => {
        const hasErrors = card.required_fields_missing && card.required_fields_missing.length > 0;
        const confidenceClass = card.confidence >= 0.8 ? 'high' : card.confidence >= 0.6 ? 'medium' : 'low';
        
        html += `
            <div class="confirmation-card ${hasErrors ? 'has-errors' : ''}" style="margin-bottom:20px;" id="batch-card-${index}">
                <div class="card-header">
                    <div class="card-title">📋 事件 ${index + 1}/${eventCards.length}</div>
                    <span class="confidence-badge confidence-${confidenceClass}">
                        置信度: ${(card.confidence * 100).toFixed(0)}%
                    </span>
                </div>
                
                <div class="field-group">
                    <div class="field-label">标题 ${!card.title || card.title === '待补充' ? '<span class="required-tag">必填</span>' : ''}</div>
                    <div class="field-value ${!card.title || card.title === '待补充' ? 'missing' : ''}">${card.title || '待补充'}</div>
                </div>
                
                <div class="field-group">
                    <div class="field-label">时间 ${!card.time ? '<span class="required-tag">必填</span>' : ''}</div>
                    <div class="field-value ${!card.time ? 'missing' : ''}">${card.time || '待补充'}</div>
                </div>
                
                <div class="field-group">
                    <div class="field-label">地点</div>
                    <div class="field-value">${card.location.standard || '待补充'}</div>
                </div>
                
                <div class="field-group">
                    <div class="field-label">活动类型</div>
                    <div class="field-value"><span class="activity-type-badge type-${card.activity_type}">${card.activity_type}</span></div>
                </div>
                
                <div class="action-buttons">
                    <button class="btn-confirm" onclick="confirmBatchEvent(event, ${index})" ${hasErrors ? 'disabled' : ''} data-event='${JSON.stringify(card).replace(/'/g, "&#39;")}'>
                        确认保存
                    </button>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// 确认批量事件中的单个事件
async function confirmBatchEvent(evt, index) {
    try {
        console.log('确认批量事件', index);
        // 从按钮的data属性获取事件数据
        const button = evt.target;
        const eventCard = JSON.parse(button.getAttribute('data-event').replace(/&#39;/g, "'"));
        
        const response = await fetch(`${API_BASE_URL}/xtu/confirmEvent`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ event_data: eventCard })
        });
        
        const result = await response.json();
        
        if (result.success) {
            // 移除该卡片
            const cardElement = document.getElementById(`batch-card-${index}`);
            if (cardElement) {
                cardElement.style.background = '#d4edda';
                cardElement.innerHTML = '<div style="padding:20px; text-align:center; color:#155724;"><h3>已保存</h3></div>';
                
                setTimeout(() => {
                    cardElement.remove();
                    
                    // 检查是否还有未确认的卡片
                    const remaining = document.querySelectorAll('.confirmation-card').length;
                    if (remaining === 0) {
                        document.getElementById('eventsContainer').innerHTML = `
                            <div class="empty-state" style="background:#d4edda; color:#155724;">
                                <p>所有事件已成功保存！</p>
                            </div>
                        `;
                        loadMiniStats();
                    }
                }, 1500);
            }
        } else {
            alert('保存失败：' + result.message);
        }
    } catch (error) {
        console.error('确认事件失败:', error);
        alert('确认失败：' + error.message);
    }
}

// 检查时间冲突
async function checkConflicts(eventTime) {
    if (!eventTime) return;
    
    try {
        const response = await fetch(`${API_BASE_URL}/xtu/checkConflict`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ event_time: eventTime })
        });
        
        const result = await response.json();
        
        if (result.success && result.has_conflict) {
            // 存储冲突信息以便显示
            currentEventCard.conflicts = result.conflicts;
            currentEventCard.has_conflict = true;
        }
    } catch (error) {
        console.error('冲突检测失败:', error);
    }
}

// 显示确认卡片
function displayConfirmationCard(eventCard) {
    const container = document.getElementById('eventsContainer');
    
    const hasErrors = eventCard.required_fields_missing && eventCard.required_fields_missing.length > 0;
    const confidenceClass = eventCard.confidence >= 0.8 ? 'high' : eventCard.confidence >= 0.6 ? 'medium' : 'low';
    
    // 准备冲突警告HTML
    let conflictWarningHtml = '';
    if (eventCard.has_conflict && eventCard.conflicts && eventCard.conflicts.length > 0) {
        const criticalConflicts = eventCard.conflicts.filter(c => c.conflict_level === 'critical');
        const warningConflicts = eventCard.conflicts.filter(c => c.conflict_level === 'warning');
        
        let conflictText = '';
        if (criticalConflicts.length > 0) {
            conflictText = `<strong style="color:#e74c3c;">严重冲突！</strong>该时间段有 ${criticalConflicts.length} 个事件时间非常接近（30分钟内）`;
        } else if (warningConflicts.length > 0) {
            conflictText = `<strong style="color:#f39c12;">时间冲突警告！</strong>该时间段有 ${warningConflicts.length} 个事件时间较接近（1小时内）`;
        }
        
        conflictWarningHtml = `
            <div class="warning-badge" style="display:block; margin-bottom:15px; background:#fff3cd; border-left-color:#ffc107;">
                ⚠️ ${conflictText}<br>
                <div style="margin-top:8px; font-size:13px;">
                    ${eventCard.conflicts.slice(0, 3).map(c => `
                        <div style="margin:5px 0;">
                            • ${c.event_title} - ${c.event_time} (相差${c.time_diff_minutes}分钟)
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    let html = `
        <div class="confirmation-card ${hasErrors ? 'has-errors' : ''}">
            <div class="card-header">
                <div class="card-title">📋 事件信息确认</div>
                <span class="confidence-badge confidence-${confidenceClass}">
                    置信度: ${(eventCard.confidence * 100).toFixed(0)}%
                </span>
            </div>
            
            ${conflictWarningHtml}
            
            <div class="field-group">
                <div class="field-label">
                    标题 
                    ${!eventCard.title || eventCard.title === '待补充' ? '<span class="required-tag">必填</span>' : ''}
                </div>
                <div class="field-value editable ${!eventCard.title || eventCard.title === '待补充' ? 'missing' : ''}" 
                     onclick="editField('title')">
                    ${eventCard.title || '待补充 - 点击编辑'}
                </div>
            </div>
            
            <div class="field-group">
                <div class="field-label">
                    时间
                    ${!eventCard.time ? '<span class="required-tag">必填</span>' : ''}
                </div>
                <div class="field-value editable ${!eventCard.time ? 'missing' : ''}" 
                     onclick="editField('time')">
                    ${eventCard.time || '待补充 - 点击编辑'}
                    ${eventCard.is_recurring ? '<span class="recurring-badge">循环事件</span>' : ''}
                </div>
            </div>
            
            ${eventCard.deadline ? `
            <div class="field-group">
                <div class="field-label">截止时间</div>
                <div class="field-value">${eventCard.deadline}</div>
            </div>
            ` : ''}
            
            <div class="field-group">
                <div class="field-label">
                    地点
                    ${eventCard.location.standard === '待补充' ? '<span class="required-tag">必填</span>' : ''}
                </div>
                <div class="field-value editable ${eventCard.location.standard === '待补充' ? 'missing' : ''}" 
                     onclick="editField('location')">
                    <div class="location-info">
                        <div class="location-standard">${eventCard.location.standard || '待补充 - 点击编辑'}</div>
                        ${eventCard.location.original && eventCard.location.original !== eventCard.location.standard ? 
                            `<div class="location-original">原始: ${eventCard.location.original}</div>` : ''}
                        ${eventCard.location.warning ? 
                            `<div class="warning-badge">${eventCard.location.warning}</div>` : ''}
                    </div>
                </div>
            </div>
            
            <div class="field-group">
                <div class="field-label">主办单位</div>
                <div class="field-value editable" onclick="editField('organizer')">
                    ${eventCard.organizer || '待补充'}
                </div>
            </div>
            
            <div class="field-group">
                <div class="field-label">活动类型</div>
                <div class="field-value">
                    <span class="activity-type-badge type-${eventCard.activity_type}">
                        ${eventCard.activity_type}
                    </span>
                </div>
            </div>
            
            <div class="field-group">
                <div class="field-label">面向人群</div>
                <div class="field-value editable" onclick="editField('audience')">
                    ${eventCard.audience}
                </div>
            </div>
            
            <div class="field-group">
                <div class="field-label">联系方式</div>
                <div class="field-value editable" onclick="editField('contact')">
                    ${eventCard.contact}
                </div>
            </div>
            
            ${hasErrors ? `
            <div class="warning-badge" style="display:block; margin-top:15px;">
                ⚠️ 请补充以下必填信息：${eventCard.required_fields_missing.join('、')}
            </div>
            ` : ''}
            
            <div class="action-buttons">
                <button class="btn-cancel" onclick="cancelConfirmation()">取消</button>
                <button class="btn-modify" onclick="modifyEvent()">修改</button>
                <button class="btn-confirm" onclick="confirmEvent()" ${hasErrors ? 'disabled' : ''}>
                    确认并保存
                </button>
            </div>
        </div>
    `;
    
    container.innerHTML = html;
}

// 编辑字段
function editField(fieldName) {
    if (!currentEventCard) return;
    
    const fieldLabels = {
        'title': '标题',
        'time': '时间 (格式: YYYY-MM-DD HH:MM:SS)',
        'location': '地点',
        'organizer': '主办单位',
        'audience': '面向人群',
        'contact': '联系方式'
    };
    
    let currentValue = '';
    if (fieldName === 'location') {
        currentValue = currentEventCard.location.standard;
    } else {
        currentValue = currentEventCard[fieldName] || '';
    }
    
    const newValue = prompt(`请输入${fieldLabels[fieldName]}：`, currentValue);
    
    if (newValue !== null && newValue.trim() !== '') {
        if (fieldName === 'location') {
            currentEventCard.location.standard = newValue.trim();
            currentEventCard.location.original = newValue.trim();
        } else {
            currentEventCard[fieldName] = newValue.trim();
        }
        
        // 重新计算缺失字段
        currentEventCard.required_fields_missing = [];
        if (!currentEventCard.title || currentEventCard.title === '待补充') {
            currentEventCard.required_fields_missing.push('标题');
        }
        if (!currentEventCard.time) {
            currentEventCard.required_fields_missing.push('时间');
        }
        if (!currentEventCard.location.standard || currentEventCard.location.standard === '待补充') {
            currentEventCard.required_fields_missing.push('地点');
        }
        
        displayConfirmationCard(currentEventCard);
    }
}

// 确认事件
async function confirmEvent() {
    if (!currentEventCard) {
        alert('没有待确认的事件');
        return;
    }
    
    if (currentEventCard.required_fields_missing && currentEventCard.required_fields_missing.length > 0) {
        alert('请先补充必填信息：' + currentEventCard.required_fields_missing.join('、'));
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/xtu/confirmEvent`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ event_data: currentEventCard })
        });
        
        const result = await response.json();
        
        if (result.success) {
            if (result.is_duplicate) {
                alert('检测到重复事件！\n已更新事件信息，提醒已自动创建。\n事件ID: ' + result.event_id);
            } else {
                alert('事件已确认并保存！\n提醒已自动创建。\n事件ID: ' + result.event_id);
            }
            
            // 清空表单
            document.getElementById('inputText').value = '';
            document.getElementById('fileInput').value = '';
            document.getElementById('fileName').textContent = '';
            document.getElementById('eventsContainer').innerHTML = `
                <div class="empty-state">
                    <p style="color:#27ae60;">事件已成功保存${result.is_duplicate ? '（已更新）' : ''}</p>
                    <p>继续输入新的通知内容进行提取</p>
                </div>
            `;
            
            currentEventCard = null;
            
            // 刷新统计
            loadMiniStats();
        } else {
            alert('保存失败：' + result.message);
        }
    } catch (error) {
        console.error('确认事件失败:', error);
        alert('确认失败：' + error.message);
    }
}

// 创建提醒
async function createReminder(eventId) {
    try {
        const response = await fetch(`${API_BASE_URL}/createReminderEnhanced`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({
                event_id: eventId,
                advance_minutes: 60
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('提醒创建成功！');
        } else {
            alert('提醒创建失败：' + result.message);
        }
    } catch (error) {
        console.error('创建提醒失败:', error);
    }
}

// 修改事件
function modifyEvent() {
    if (!currentEventCard) return;
    alert('💡 提示：点击任意字段即可编辑该内容');
}

// 取消确认
function cancelConfirmation() {
    if (confirm('确定要取消吗？提取的信息将丢失。')) {
        currentEventCard = null;
        document.getElementById('eventsContainer').innerHTML = `
            <div class="empty-state">
                <p>暂无待确认事件</p>
                <p>请在左侧输入或上传校园通知</p>
            </div>
        `;
        document.getElementById('inputText').value = '';
        document.getElementById('fileInput').value = '';
        document.getElementById('fileName').textContent = '';
    }
}

// 加载迷你统计数据
async function loadMiniStats() {
    try {
        const response = await fetch(`${API_BASE_URL}/xtu/statistics`, {
            headers: getAuthHeaders()
        });
        
        const result = await response.json();
        
        if (result.success) {
            const data = result.data;
            
            document.getElementById('miniTotalEvents').textContent = data.events.total;
            document.getElementById('miniPendingEvents').textContent = data.events.pending;
            document.getElementById('miniReminders').textContent = data.reminders.total;
            document.getElementById('miniCompletionRate').textContent = data.completion_rate + '%';
            
            // 显示统计卡片
            document.getElementById('statsMini').style.display = 'flex';
        }
    } catch (error) {
        console.error('加载统计失败:', error);
    }
}

// 页面加载完成
console.log('湘潭大学智慧校园任务管理系统已加载 - 集成版');
