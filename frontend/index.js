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

            // 检查时间冲突（内部会调用 displayConfirmationCard）
            if (result.event_card.time) {
                await checkConflicts(result.event_card.time);
            } else {
                displayConfirmationCard(result.event_card);
            }
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

// 将文本分段
function splitTextIntoSegments(text) {
    // 先尝试双换行分段
    let segments = text.split(/\n\n+/).map(s => s.trim()).filter(s => s.length >= 15);
    if (segments.length > 1) return segments;
    
    // 尝试数字/中文序号分段
    const numberedSplit = text.split(/(?=(?:\d+[、\.\)）]|[一二三四五六七八九十]+[、\.]))/);
    segments = numberedSplit.map(s => s.trim()).filter(s => s.length >= 15);
    if (segments.length > 1) return segments;
    
    // 尝试单换行分段（每行作为一个候选）
    const lineSplit = text.split(/\n/).map(s => s.trim()).filter(s => s.length >= 15);
    if (lineSplit.length > 1) return lineSplit;
    
    // 无法分段，整体作为一段
    return [text.trim()];
}

// 批量提取事件 - 前端分段后逐段调用智能提取
async function extractBatchEvents() {
    const inputText = document.getElementById('inputText').value;
    
    if (!inputText.trim()) {
        alert("请输入或上传文本内容");
        return;
    }

    const container = document.getElementById('eventsContainer');
    const segments = splitTextIntoSegments(inputText);
    
    if (segments.length <= 1) {
        // 只有一段，直接走单事件提取
        extractEvents();
        return;
    }
    
    container.innerHTML = `<div class="empty-state"><p>正在批量提取 ${segments.length} 个片段...</p></div>`;

    try {
        const eventCards = [];
        
        for (let i = 0; i < segments.length; i++) {
            const seg = segments[i];
            container.innerHTML = `<div class="empty-state"><p>正在提取第 ${i + 1}/${segments.length} 个片段...</p></div>`;
            
            const response = await fetch(`${API_BASE_URL}/xtu/extractEvents`, {
                method: 'POST',
                headers: getAuthHeaders(),
                body: JSON.stringify({ text: seg })
            });
            
            const result = await response.json();
            
            if (result.require_login) {
                alert('会话已过期，请重新登录');
                window.location.href = 'login.html';
                return;
            }
            
            if (result.success && result.event_card) {
                result.event_card.original_text = seg;
                eventCards.push(result.event_card);
            }
        }
        
        if (eventCards.length > 0) {
            displayBatchCards(eventCards);
        } else {
            container.innerHTML = `<div class="empty-state"><p>未能从文本中提取到事件，请尝试智能提取</p></div>`;
        }
    } catch (error) {
        console.error('批量提取失败:', error);
        container.innerHTML = '<div class="empty-state"><p>批量提取失败</p></div>';
        alert(`批量提取失败：${error.message}`);
    }
}

// 批量卡片的事件数据存储（用index索引）
let batchEventCards = [];

// 显示批量事件卡片（与智能提取卡片字段一致，支持内联编辑）
function displayBatchCards(eventCards) {
    batchEventCards = eventCards.map(c => JSON.parse(JSON.stringify(c)));
    renderBatchCards();
}

function renderBatchCards() {
    const container = document.getElementById('eventsContainer');
    const total = batchEventCards.length;
    
    let html = `<div style="padding:15px 20px; background:#e3f2fd; border-radius:8px; margin-bottom:20px;">
        <h3 style="margin:0 0 4px;">成功提取 ${total} 个事件</h3>
        <p style="margin:0; color:#555;">请逐一确认并保存，点击字段可直接编辑</p>
    </div>`;
    
    batchEventCards.forEach((card, index) => {
        const hasErrors = !card.time;
        const confidenceClass = card.confidence >= 0.8 ? 'high' : card.confidence >= 0.6 ? 'medium' : 'low';
        const loc = card.location || {};
        
        html += `
            <div class="confirmation-card ${hasErrors ? 'has-errors' : ''}" style="margin-bottom:20px;" id="batch-card-${index}">
                <div class="card-header">
                    <div class="card-title">📋 事件 ${index + 1}/${total}</div>
                    <span class="confidence-badge confidence-${confidenceClass}">置信度: ${(card.confidence * 100).toFixed(0)}%</span>
                </div>
                
                <div class="field-group">
                    <div class="field-label">标题</div>
                    <div class="field-value editable" id="batch-field-${index}-title" onclick="editBatchField(${index},'title')">
                        ${card.title || '待补充 - 点击编辑'}
                    </div>
                </div>
                
                <div class="field-group">
                    <div class="field-label">时间 ${!card.time ? '<span class="required-tag">必填</span>' : ''}</div>
                    <div class="field-value editable ${!card.time ? 'missing' : ''}" id="batch-field-${index}-time" onclick="editBatchField(${index},'time')">
                        ${card.time || '待补充 - 点击编辑'}
                    </div>
                </div>
                
                <div class="field-group">
                    <div class="field-label">地点</div>
                    <div class="field-value editable" id="batch-field-${index}-location" onclick="editBatchField(${index},'location')">
                        ${loc.standard || '待补充 - 点击编辑'}
                    </div>
                </div>
                
                <div class="field-group">
                    <div class="field-label">主办单位</div>
                    <div class="field-value editable" id="batch-field-${index}-organizer" onclick="editBatchField(${index},'organizer')">
                        ${card.organizer || '待补充'}
                    </div>
                </div>
                
                <div class="field-group">
                    <div class="field-label">活动类型</div>
                    <div class="field-value editable" id="batch-field-${index}-activity_type" onclick="editBatchField(${index},'activity_type')">
                        <span class="activity-type-badge type-${card.activity_type}">${card.activity_type}</span>
                    </div>
                </div>
                
                <div class="field-group">
                    <div class="field-label">面向人群</div>
                    <div class="field-value editable" id="batch-field-${index}-audience" onclick="editBatchField(${index},'audience')">
                        ${card.audience || '相关人员'}
                    </div>
                </div>
                
                <div class="field-group">
                    <div class="field-label">联系方式</div>
                    <div class="field-value editable" id="batch-field-${index}-contact" onclick="editBatchField(${index},'contact')">
                        ${card.contact || '待补充'}
                    </div>
                </div>
                
                ${hasErrors ? `<div class="warning-badge" style="display:block; margin:10px 0;">⚠️ 请补充时间后保存</div>` : ''}
                
                <div class="action-buttons">
                    <button class="btn-confirm" onclick="confirmBatchEventByIndex(${index})" ${hasErrors ? 'disabled' : ''}>
                        确认保存
                    </button>
                </div>
            </div>
        `;
    });
    
    container.innerHTML = html;
}

// 批量卡片内联编辑字段
function editBatchField(index, fieldName) {
    const card = batchEventCards[index];
    const elId = `batch-field-${index}-${fieldName}`;
    const el = document.getElementById(elId);
    if (!el) return;
    
    if (document.getElementById(`batch-inline-${index}-${fieldName}`)) {
        saveBatchInlineEdit(index, fieldName);
        return;
    }
    
    let currentValue = '';
    if (fieldName === 'location') {
        currentValue = (card.location && card.location.standard) || '';
        if (currentValue === '待补充') currentValue = '';
    } else {
        currentValue = card[fieldName] || '';
        if (currentValue === '待补充') currentValue = '';
    }
    
    let inputHtml = '';
    if (fieldName === 'time') {
        const dtVal = toDatetimeLocal(currentValue);
        inputHtml = `<input type="datetime-local" id="batch-inline-${index}-${fieldName}" value="${dtVal}"
            style="width:100%; padding:6px 10px; font-size:14px; border:2px solid #667eea; border-radius:6px; outline:none;"
            onkeydown="if(event.key==='Enter') saveBatchInlineEdit(${index},'${fieldName}')">` ;
    } else {
        inputHtml = `<input type="text" id="batch-inline-${index}-${fieldName}" value="${currentValue.replace(/"/g,'&quot;')}"
            placeholder="请输入内容..."
            style="width:100%; padding:6px 10px; font-size:14px; border:2px solid #667eea; border-radius:6px; outline:none;"
            onkeydown="if(event.key==='Enter') saveBatchInlineEdit(${index},'${fieldName}')">` ;
    }
    
    el.innerHTML = inputHtml + `<div style="margin-top:6px; display:flex; gap:8px;">
        <button onclick="saveBatchInlineEdit(${index},'${fieldName}')" 
            style="padding:4px 12px; background:#667eea; color:white; border:none; border-radius:4px; cursor:pointer; font-size:13px;">保存</button>
        <button onclick="renderBatchCards()" 
            style="padding:4px 12px; background:#95a5a6; color:white; border:none; border-radius:4px; cursor:pointer; font-size:13px;">取消</button>
    </div>`;
    
    const input = document.getElementById(`batch-inline-${index}-${fieldName}`);
    if (input) { input.focus(); input.select && input.select(); }
}

function saveBatchInlineEdit(index, fieldName) {
    const input = document.getElementById(`batch-inline-${index}-${fieldName}`);
    if (!input) return;
    
    let newValue = input.value.trim();
    if (fieldName === 'time' && newValue) {
        newValue = newValue.replace('T', ' ') + ':00';
    }
    
    if (newValue) {
        const card = batchEventCards[index];
        if (fieldName === 'location') {
            card.location = card.location || {};
            card.location.standard = newValue;
            card.location.original = newValue;
        } else {
            card[fieldName] = newValue;
        }
    }
    
    renderBatchCards();
}

// 确认批量事件中的单个事件（通过index从batchEventCards取数据）
async function confirmBatchEventByIndex(index) {
    const card = batchEventCards[index];
    if (!card) return;
    
    if (!card.time) {
        alert('请先填写事件时间');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/xtu/confirmEvent`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ event_data: card })
        });
        
        const result = await response.json();
        
        if (result.success) {
            const cardElement = document.getElementById(`batch-card-${index}`);
            if (cardElement) {
                cardElement.style.background = '#d4edda';
                cardElement.style.border = '1px solid #27ae60';
                cardElement.innerHTML = '<div style="padding:20px; text-align:center; color:#155724;"><h3>✅ 已保存</h3></div>';
                
                setTimeout(() => {
                    cardElement.remove();
                    const remaining = document.querySelectorAll('.confirmation-card').length;
                    if (remaining === 0) {
                        document.getElementById('eventsContainer').innerHTML = `
                            <div class="empty-state" style="background:#d4edda; color:#155724;">
                                <p>所有事件已成功保存！</p>
                            </div>
                        `;
                        loadMiniStats();
                    }
                }, 1200);
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
    if (!eventTime || !currentEventCard) return;
    try {
        const response = await fetch(`${API_BASE_URL}/xtu/checkConflict`, {
            method: 'POST',
            headers: getAuthHeaders(),
            body: JSON.stringify({ event_time: eventTime })
        });
        const result = await response.json();
        if (result.success) {
            currentEventCard.has_conflict = result.has_conflict;
            currentEventCard.conflict_level = result.conflict_level;
            currentEventCard.conflicts = result.conflicts || [];
            currentEventCard.conflict_message = result.message || '';
            displayConfirmationCard(currentEventCard);
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
        const isCritical = eventCard.conflict_level === 'critical';
        const scheduleConflicts = eventCard.conflicts.filter(c => c.type === 'schedule');
        const eventConflicts = eventCard.conflicts.filter(c => c.type === 'event');

        let conflictText = '';
        if (scheduleConflicts.length > 0) {
            conflictText = `<strong style="color:#e74c3c;">❗ 与课表冲突！</strong> 该时间段有 ${scheduleConflicts.length} 门课程`;
        } else if (eventConflicts.length > 0) {
            conflictText = `<strong style="color:#f39c12;">⚠️ 时间冲突警告！</strong> 该时间段已有 ${eventConflicts.length} 个事件`;
        }

        const listItems = eventCard.conflicts.slice(0, 3).map(c =>
            `<div style="margin:4px 0; padding:3px 0; border-bottom:1px solid #ffe08a;">
                ${c.type === 'schedule' ? '📚' : '📌'} <strong>${c.title}</strong>
                ${c.time ? `<span style="color:#666;"> — ${c.time}</span>` : ''}
                ${c.location && c.location !== '未指定' ? `<span style="color:#999;"> 📍${c.location}</span>` : ''}
            </div>`
        ).join('');

        conflictWarningHtml = `
            <div style="margin-bottom:15px; padding:12px 14px; background:${isCritical ? '#fde8e8' : '#fff8e1'};
                border-left:4px solid ${isCritical ? '#e74c3c' : '#ffc107'}; border-radius:4px; font-size:13px;">
                ${conflictText}<br>
                <div style="margin-top:8px;">${listItems}</div>
                <div style="margin-top:8px; color:#666;">保存后仍可在日历中查看冲突标记。</div>
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
                     id="edit-field-title" onclick="editField('title')">
                    ${eventCard.title || '待补充 - 点击编辑'}
                </div>
            </div>
            
            <div class="field-group">
                <div class="field-label">
                    时间
                    ${!eventCard.time ? '<span class="required-tag">必填</span>' : ''}
                </div>
                <div class="field-value editable ${!eventCard.time ? 'missing' : ''}" 
                     id="edit-field-time" onclick="editField('time')">
                    ${eventCard.time || '待补充 - 点击编辑'}
                    ${eventCard.is_recurring ? '<span class="recurring-badge">循环事件</span>' : ''}
                </div>
            </div>
            
            ${eventCard.deadline ? `
            <div class="field-group">
                <div class="field-label">截止时间</div>
                <div class="field-value editable" id="edit-field-deadline" onclick="editField('deadline')">${eventCard.deadline}</div>
            </div>
            ` : ''}
            
            <div class="field-group">
                <div class="field-label">
                    地点
                    ${!eventCard.location || eventCard.location.standard === '待补充' ? '<span class="required-tag">必填</span>' : ''}
                </div>
                <div class="field-value editable ${!eventCard.location || eventCard.location.standard === '待补充' ? 'missing' : ''}" 
                     id="edit-field-location" onclick="editField('location')">
                    <div class="location-info">
                        <div class="location-standard">${(eventCard.location && eventCard.location.standard) || '待补充 - 点击编辑'}</div>
                        ${eventCard.location && eventCard.location.original && eventCard.location.original !== eventCard.location.standard ? 
                            `<div class="location-original">原始: ${eventCard.location.original}</div>` : ''}
                        ${eventCard.location && eventCard.location.warning ? 
                            `<div class="warning-badge">${eventCard.location.warning}</div>` : ''}
                    </div>
                </div>
            </div>
            
            <div class="field-group">
                <div class="field-label">主办单位</div>
                <div class="field-value editable" id="edit-field-organizer" onclick="editField('organizer')">
                    ${eventCard.organizer || '待补充'}
                </div>
            </div>
            
            <div class="field-group">
                <div class="field-label">活动类型</div>
                <div class="field-value editable" id="edit-field-activity_type" onclick="editField('activity_type')">
                    <span class="activity-type-badge type-${eventCard.activity_type}">
                        ${eventCard.activity_type}
                    </span>
                </div>
            </div>
            
            <div class="field-group">
                <div class="field-label">面向人群</div>
                <div class="field-value editable" id="edit-field-audience" onclick="editField('audience')">
                    ${eventCard.audience || '待补充'}
                </div>
            </div>
            
            <div class="field-group">
                <div class="field-label">联系方式</div>
                <div class="field-value editable" id="edit-field-contact" onclick="editField('contact')">
                    ${eventCard.contact || '待补充'}
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

// 将时间字符串转为 datetime-local 可用格式 YYYY-MM-DDTHH:MM
function toDatetimeLocal(timeStr) {
    if (!timeStr) return '';
    const cleaned = timeStr.replace(' ', 'T').substring(0, 16);
    return cleaned;
}

// 内联编辑字段（替代 prompt 弹窗）
function editField(fieldName) {
    if (!currentEventCard) return;
    
    const el = document.getElementById(`edit-field-${fieldName}`);
    if (!el) return;
    
    // 如果已经在编辑中，保存并关闭
    const existing = document.getElementById(`inline-editor-${fieldName}`);
    if (existing) {
        saveInlineEdit(fieldName);
        return;
    }
    
    let currentValue = '';
    if (fieldName === 'location') {
        currentValue = currentEventCard.location.standard;
        if (currentValue === '待补充') currentValue = '';
    } else {
        currentValue = currentEventCard[fieldName] || '';
        if (currentValue === '待补充') currentValue = '';
    }
    
    let inputHtml = '';
    if (fieldName === 'time') {
        const dtVal = toDatetimeLocal(currentValue);
        inputHtml = `<input type="datetime-local" id="inline-editor-${fieldName}" value="${dtVal}" 
            style="width:100%; padding:6px 10px; font-size:14px; border:2px solid #667eea; border-radius:6px; outline:none;"
            onkeydown="if(event.key==='Enter') saveInlineEdit('${fieldName}')">`;
    } else {
        inputHtml = `<input type="text" id="inline-editor-${fieldName}" value="${currentValue.replace(/"/g, '&quot;')}" 
            placeholder="请输入内容..."
            style="width:100%; padding:6px 10px; font-size:14px; border:2px solid #667eea; border-radius:6px; outline:none;"
            onkeydown="if(event.key==='Enter') saveInlineEdit('${fieldName}')">`;
    }
    
    el.innerHTML = inputHtml + `<div style="margin-top:6px; display:flex; gap:8px;">
        <button onclick="saveInlineEdit('${fieldName}')" 
            style="padding:4px 12px; background:#667eea; color:white; border:none; border-radius:4px; cursor:pointer; font-size:13px;">保存</button>
        <button onclick="cancelInlineEdit('${fieldName}')" 
            style="padding:4px 12px; background:#95a5a6; color:white; border:none; border-radius:4px; cursor:pointer; font-size:13px;">取消</button>
    </div>`;
    
    const input = document.getElementById(`inline-editor-${fieldName}`);
    if (input) { input.focus(); input.select && input.select(); }
}

function saveInlineEdit(fieldName) {
    const input = document.getElementById(`inline-editor-${fieldName}`);
    if (!input) return;
    
    let newValue = input.value.trim();
    
    if (fieldName === 'time' && newValue) {
        // datetime-local 返回 YYYY-MM-DDTHH:MM，转为 YYYY-MM-DD HH:MM:SS
        newValue = newValue.replace('T', ' ') + ':00';
    }
    
    if (newValue) {
        if (fieldName === 'location') {
            currentEventCard.location.standard = newValue;
            currentEventCard.location.original = newValue;
        } else {
            currentEventCard[fieldName] = newValue;
        }
    }
    
    // 重新计算缺失字段
    currentEventCard.required_fields_missing = [];
    if (!currentEventCard.title || currentEventCard.title === '待补充') {
        currentEventCard.required_fields_missing.push('标题');
    }
    if (!currentEventCard.time) {
        currentEventCard.required_fields_missing.push('时间');
    }
    if (!currentEventCard.location || !currentEventCard.location.standard || currentEventCard.location.standard === '待补充') {
        currentEventCard.required_fields_missing.push('地点');
    }

    // 时间变更后重新检测冲突
    if (fieldName === 'time' && currentEventCard.time) {
        checkConflicts(currentEventCard.time);
    } else {
        displayConfirmationCard(currentEventCard);
    }
}

function cancelInlineEdit(fieldName) {
    displayConfirmationCard(currentEventCard);
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
            // 冲突提示
            let conflictNotice = '';
            if (result.has_conflict && result.conflicts && result.conflicts.length > 0) {
                const levelText = result.conflict_level === 'critical' ? '❗ 与课表冲突' : '⚠️ 与已有事件冲突';
                const conflictList = result.conflicts.slice(0, 3).map(c =>
                    `  • ${c.title}${c.time ? ' （' + c.time + '）' : ''}`
                ).join('\n');
                conflictNotice = `\n\n${levelText}\n${conflictList}\n\n请注意调整时间安排！`;
            }

            const baseMsg = result.is_duplicate ? '检测到重复事件，已更新信息。' : '事件已确认并保存。';
            alert(baseMsg + conflictNotice);

            // 清空表单
            document.getElementById('inputText').value = '';
            document.getElementById('fileInput').value = '';
            document.getElementById('fileName').textContent = '';
            document.getElementById('eventsContainer').innerHTML = `
                <div class="empty-state">
                    <p style="color:${result.has_conflict ? '#e67e22' : '#27ae60'}">
                        ${result.has_conflict ? '⚠️ 事件已保存，但存在时间冲突，请查看日历确认' : '✅ 事件已成功保存'}
                    </p>
                    <p>继续输入新的通知内容进行提取</p>
                </div>
            `;

            currentEventCard = null;
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
