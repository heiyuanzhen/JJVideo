// ===== 通用辅助函数与状态（设置页专用） =====
window.__settingsState = window.__settingsState || {};
function showLoading(msg){
    try{ return layer.msg(msg||'处理中...', {icon:16, time:0, shade:0.2}); }catch(e){ return null; }
}
function hideLoading(loadingId){ 
    try{ if(loadingId) layer.close(loadingId); }catch(e){} 
}
function apiRequest(url, method, data, onOk, onErr){
    method = (method||'GET').toUpperCase();
    const opts = { method, headers: {} };
    if(method !== 'GET'){
        opts.headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(data||{});
    }
    console.log(`🌐 API请求: ${method} ${url}`);
    fetch(url, opts).then(r=>{
        // console.log(`📡 API响应状态: ${r.status} ${r.statusText}`);
        if(!r.ok) throw new Error(`HTTP ${r.status}: ${r.statusText}`);
        return r.json();
    }).then(json=>{
        // console.log(`✅ API响应数据:`, json);
        if(json && json.code === 0){ onOk && onOk(json); }
        else{ onErr && onErr(json && (json.msg||json.message) || '请求失败', json); }
    }).catch(err=>{
        console.error(`❌ API请求失败:`, err);
        onErr && onErr(err && err.message || '网络错误');
    });
}
function confirmAction(title, message, callback){
    try{
        layer.confirm(message || title || '确认执行该操作吗？', {title: title||'确认操作', icon: 3}, function(index){
            layer.close(index); try{ callback && callback(); }catch(e){}
        });
    }catch(e){ if(confirm((title?title+'\n':'')+(message||''))){ try{ callback&&callback(); }catch(_){} } }
}

// ===== 交互选择：主题 / 颜色 / 语言 / AI质量 =====
function selectTheme(theme){
    window.__settingsState.appearance_theme = theme;
    try{ applyTheme(theme); }catch(e){}
}
function selectColor(color){
    window.__settingsState.appearance_themeColor = color;
    try{ applyThemeColor(color); }catch(e){}
}
function selectLanguage(lang){
    try{ $('select[name="app-language"]').val(lang); form.render('select'); }catch(e){}
}
function selectAIQuality(quality){
    try{ $('select[name="ai-model-quality"]').val(quality); form.render('select'); }catch(e){}
}


// ===== 分页保存：外观 / 语言 / 文件 / 通知 / 性能 / 高级 =====
async function saveAppearance(){
    const payload = {
        appearance: {
            theme: (window.__settingsState.appearance_theme) || ($('.layui-btn-group[lay-filter="theme-group"] .layui-btn-primary').data('theme')) || 'system',
            opacity: $('input[name="opacity"]').val() || 80,
            fontSize: $('select[name="font-size"]').val() || 'normal',
            iconSize: $('select[name="icon-size"]').val() || 'normal',
            animation: $('input[name="animation"]').prop('checked'),
            glassEffect: $('input[name="glass-effect"]').prop('checked'),
            themeColor: (window.__settingsState.appearance_themeColor) || '#1890ff'
        }
    };
    const loading = showLoading('正在保存外观设置...');
    try{
        const res = await fetch('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)}).then(r=>r.json());
        hideLoading(loading);
        if(res && res.code===0){ layer.msg('✅ 外观设置已保存',{icon:1}); }
        else{ layer.msg('❌ 保存失败',{icon:2}); }
    }catch(e){ hideLoading(loading); layer.msg('❌ 保存异常',{icon:2}); }
}
function resetAppearance(){
    window.__settingsState.appearance_theme = 'system';
    window.__settingsState.appearance_themeColor = '#1890ff';
    try{
        $('input[name="opacity"]').val(80);
        $('select[name="font-size"]').val('normal');
        $('select[name="icon-size"]').val('normal');
        $('input[name="animation"]').prop('checked', true);
        $('input[name="glass-effect"]').prop('checked', true);
        form.render();
        applyTheme('system'); applyThemeColor('#1890ff');
    }catch(e){}
    saveAppearance();
}

// 单独保存：编辑器右侧栏默认折叠偏好
async function updateEditorAutoCollapsePref(checked){
    const loading = showLoading('正在保存编辑器布局...');
    const value = !!checked;
    try{
        const res = await fetch('/api/settings/editor_auto_collapse_right_panel', {
            method:'PUT', headers:{'Content-Type':'application/json'}, body: JSON.stringify({value})
        }).then(r=>r.json());
        hideLoading(loading);
        if(res && res.code===0){
            try{ localStorage.setItem('editorAutoCollapsePreference', value ? '1' : '0'); }catch(_){ }
            layer.msg('✅ 已保存：' + (value ? '默认折叠' : '记住上次状态'), {icon:1});
        } else {
            layer.msg('❌ 保存失败', {icon:2});
        }
    }catch(e){ hideLoading(loading); layer.msg('❌ 保存异常', {icon:2}); }
}

async function saveLanguage(){
    const payload = { language: {
        app: $('select[name="app-language"]').val() || 'zh-CN',
        asr: $('select[name="asr-language"]').val() || 'zh-CN',
        tts: $('select[name="tts-language"]').val() || 'zh-CN'
    } };
    const loading = showLoading('正在保存语言设置...');
    try{
        const res = await fetch('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)}).then(r=>r.json());
        hideLoading(loading);
        if(res && res.code===0){ layer.msg('✅ 语言设置已保存',{icon:1}); } else { layer.msg('❌ 保存失败',{icon:2}); }
    }catch(e){ hideLoading(loading); layer.msg('❌ 保存异常',{icon:2}); }
}
async function saveFileSettings(){
    const payload = { file: {
        savePath: $('input[name="save-path"]').val() || '',
        exportFormat: $('select[name="export-format"]').val() || 'mp4',
        exportQuality: $('select[name="export-quality"]').val() || 'medium',
        autoSave: $('input[name="auto-save"]').prop('checked'),
        autoSaveInterval: $('select[name="auto-save-interval"]').val() || '3'
    } };
    const loading = showLoading('正在保存文件设置...');
    try{
        const res = await fetch('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)}).then(r=>r.json());
        hideLoading(loading);
        if(res && res.code===0){ layer.msg('✅ 文件设置已保存',{icon:1}); } else { layer.msg('❌ 保存失败',{icon:2}); }
    }catch(e){ hideLoading(loading); layer.msg('❌ 保存异常',{icon:2}); }
}
async function clearCache(){
    const loading = showLoading('正在清理缓存...');
    try{
        const res = await fetch('/api/settings/clear-cache', {method:'POST'}).then(r=>r.json());
        hideLoading(loading);
        if(res && res.code===0){ layer.msg('✅ 缓存已清理',{icon:1}); } else { layer.msg('❌ 清理失败',{icon:2}); }
    }catch(e){ hideLoading(loading); layer.msg('❌ 清理异常',{icon:2}); }
}
async function saveNotificationSettings(){
    const payload = { notification: {
        desktop: $('input[name="desktop-notification"]').prop('checked'),
        sound: $('input[name="sound-notification"]').prop('checked'),
        taskComplete: $('input[name="task-complete"]').prop('checked'),
        error: $('input[name="error-notification"]').prop('checked'),
        update: $('input[name="update-notification"]').prop('checked'),
        soundType: $('select[name="notification-sound"]').val() || 'default'
    } };
    const loading = showLoading('正在保存通知设置...');
    try{
        const res = await fetch('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)}).then(r=>r.json());
        hideLoading(loading);
        if(res && res.code===0){ layer.msg('✅ 通知设置已保存',{icon:1}); } else { layer.msg('❌ 保存失败',{icon:2}); }
    }catch(e){ hideLoading(loading); layer.msg('❌ 保存异常',{icon:2}); }
}
async function savePerformanceSettings(){
    const payload = { performance: {
        hardwareAcceleration: $('input[name="hardware-acceleration"]').prop('checked'),
        multiThreading: $('input[name="multi-threading"]').prop('checked'),
        aiModelQuality: $('select[name="ai-model-quality"]').val() || 'medium',
        memoryLimit: $('select[name="memory-limit"]').val() || 'auto',
        tempFileCleanup: $('select[name="temp-file-cleanup"]').val() || 'weekly',
        mode: $('select[name="performance-mode"]').val() || 'balanced'
    } };
    const loading = showLoading('正在保存性能设置...');
    try{
        const res = await fetch('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)}).then(r=>r.json());
        hideLoading(loading);
        if(res && res.code===0){ layer.msg('✅ 性能设置已保存',{icon:1}); } else { layer.msg('❌ 保存失败',{icon:2}); }
    }catch(e){ hideLoading(loading); layer.msg('❌ 保存异常',{icon:2}); }
}
async function saveAdvancedSettings(){
    const payload = { advanced: {
        ffmpegPath: $('input[name="ffmpeg-path"]').val() || '',
        proxyEnable: $('input[name="proxy-enable"]').prop('checked') === true,
        proxyServer: $('input[name="proxy-server"]').val() || '',
        logLevel: $('select[name="log-level"]').val() || 'info',
        autoUpdate: $('select[name="auto-update"]').val() || 'stable',
        developerMode: $('input[name="developer-mode"]').prop('checked') === true
    } };
    const loading = showLoading('正在保存高级设置...');
    try{
        const res = await fetch('/api/settings', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(payload)}).then(r=>r.json());
        hideLoading(loading);
        if(res && res.code===0){ layer.msg('✅ 高级设置已保存',{icon:1}); } else { layer.msg('❌ 保存失败',{icon:2}); }
    }catch(e){ hideLoading(loading); layer.msg('❌ 保存异常',{icon:2}); }
}

// ===== API配置：保存与测试 =====
function updateKeySavedIndicators(data){
    try{
        Object.keys(data||{}).forEach(function(k){
            if(!/(api_key|secret)/i.test(k)) return;
            var el=document.querySelector('[name="'+k+'"]');
            if(!el) return;
            var parent=el.parentElement; if(!parent) return;
            var badge=parent.querySelector('.key-status-badge');
            if(!badge){
                badge=document.createElement('span');
                badge.className='key-status-badge';
                badge.textContent='已保存';
                badge.style.marginLeft='8px';
                badge.style.color='#22c55e';
                badge.style.fontSize='12px';
                badge.style.fontWeight='700';
                parent.appendChild(badge);
            }
            if(data[k]){ badge.style.display='inline'; } else { badge.style.display='none'; }
        });
    }catch(_){}
}
function getVal(name){var el=document.querySelector('[name="'+name+'"]');return el?el.value.trim():'';}
function setVal(name,val){var el=document.querySelector('[name="'+name+'"]');if(el&&val!=null){el.value=val;}}
function isMasked(v){return typeof v==='string' && /\*{4,}/.test(v);} // 服务器脱敏值
function addIfValid(obj,key,val){ if(val && !isMasked(val)) obj[key]=val; }

// ===== 实时指标：数据源 /api/system/metrics =====
        function fmtBytes(n){
            const u=['B','KB','MB','GB','TB'];
            let i=0; let v=n||0; while(v>=1024 && i<u.length-1){v/=1024;i++;} return (Math.round(v*100)/100)+' '+u[i];
        }
        function fmtDuration(sec){
            let s=Math.max(0,Math.floor(sec||0));
            const d=Math.floor(s/86400); s%=86400;
            const h=Math.floor(s/3600); s%=3600;
            const m=Math.floor(s/60);
            const parts=[]; if(d) parts.push(d+'天'); if(h) parts.push(h+'小时'); parts.push(m+'分');
            return parts.join('');
        }
        function updateMetricsUI(m){
            if(!m||!m.storage) return;
            const used=m.storage.disk_used||0, total=m.storage.disk_total||1; const pct=Math.max(0,Math.min(100,Math.round(used*100/total)));
            const el=(id)=>document.getElementById(id);
            if(el('metric-storage-app')) el('metric-storage-app').textContent = fmtBytes(m.storage.app_used||0);
            if(el('metric-storage-progress')) el('metric-storage-progress').style.width = pct+'%';
            if(el('metric-storage-used')) el('metric-storage-used').textContent = '已用 '+fmtBytes(used)+' ('+pct+'%)';
            if(el('metric-storage-total')) el('metric-storage-total').textContent = '总计 '+fmtBytes(total);
            if(m.projects){
                // if(el('metric-projects-total')) el('metric-projects-total').textContent = (m.projects.total||0)+' 个项目';
                if(el('metric-projects-processing')) el('metric-projects-processing').textContent = m.projects.processing||0;
                if(el('metric-projects-completed')) el('metric-projects-completed').textContent = m.projects.completed||0;
            }
            const sys = (m.system&&m.system.status)||{};
            const engines = (m.system&&m.system.engines_loaded_count)||0;
            const ttsDefault = (m.system&&m.system.tts_default)||'';
            const vcEnabled = !!(m.system&&m.system.voice_clone_enabled);
            const apiCfg = (m.api&&m.api.configured_count)||0;
            if(el('metric-api-configured')) el('metric-api-configured').textContent = apiCfg;
            if(el('metric-engines')) el('metric-engines').textContent = engines;
            if(el('metric-llm')) el('metric-llm').textContent = sys.active_llm_model||'--';
            if(el('metric-vision')) el('metric-vision').textContent = sys.active_vision_model||'--';
            if(el('metric-tts')){
                let label = ttsDefault || '--';
                if(ttsDefault==='voice_clone'){
                    label = vcEnabled ? 'voice_clone (已启用)' : 'voice_clone (未启用)';
                }
                el('metric-tts').textContent = label;
            }
            const ok = (apiCfg>0 || engines>0);
            if(el('metric-system-text')) el('metric-system-text').textContent = ok ? '正常' : '待配置';
            if(el('metric-uptime')) el('metric-uptime').textContent = fmtDuration((m.system&&m.system.uptime_seconds)||0);
        }
        
        async function fetchSystemMetrics(){
            try{
                const res = await fetch('/api/system/metrics').then(r=>r.json());
                if(res && res.code===0) updateMetricsUI(res.data);
            }catch(e){/* 忽略短时失败 */}
        }

// 清空配置（置空常用字段并保存）
        async function clearAllConfig(){
            Notification.confirm('确定要清空所有API配置吗？', async ()=>{
                const fields=['custom_api_key','anthropic_api_key','gemini_api_key','kimi_api_key','qwen_api_key','ernie_api_key','ernie_secret_key','chatglm_api_key','deepseek_api_key','xfyun_appid','xfyun_api_key','xfyun_api_secret','claude_vision_api_key','gpt4v_api_key','azure_tts_key','azure_tts_region'];
                const payload={}; fields.forEach(k=>payload[k]='');
                const loading = layer.msg('正在清空配置...', {icon:16,time:0,shade:0.2});
                try{
                    const r1 = await fetch('/api/settings/api-config',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}).then(r=>r.json());
                    const r2 = await fetch('/api/config/save',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)}).then(r=>r.json()).catch(()=>({code:0}));
                    await fetch('/api/config/reload',{method:'POST'}).catch(()=>{});
                    layer.close(loading);
                    if((r1&&r1.code===0)||(r2&&r2.code===0)){ layer.msg('✅ 已清空',{icon:1}); loadAPIConfig(); }
                    else { layer.msg('❌ 清空失败',{icon:2}); }
                }catch(e){ layer.close(loading); layer.msg('❌ 清空失败',{icon:2}); }
            });
        }

        // 取消 - 恢复为后端当前配置
        function cancelChanges(){ loadAPIConfig(); layer.msg('已恢复当前配置',{icon:1}); }

        // 重置 - 清空输入并设置模型下拉为默认值
        function resetAll(){
            document.querySelectorAll('#settings-api input, #settings-api select').forEach(el=>{
                if(el.tagName==='INPUT') el.value='';
                if(el.tagName==='SELECT') el.selectedIndex=0;
            });
            layer.msg('已重置为默认值（未保存）',{icon:1});
        }

        // 重置设置
        function resetSettings() {
            confirmAction('重置设置', '确定要将当前页面设置恢复为默认值吗？', function() {
                var currentTab = element.tabGet('settings-tab');
                loadSettings();
                layer.msg('当前页面设置已重置', {icon: 1});
            });
        }

        // 检查更新
        function checkUpdate() {
            var loading = showLoading();
            apiRequest('/api/update/check', 'GET', {}, function(data) {
                hideLoading(loading);
                if (data.hasUpdate) {
                    layer.confirm(`发现新版本 v${data.version}，是否更新？`, function(index) {
                        layer.close(index);
                        downloadUpdate();
                    });
                } else {
                    layer.msg('当前已是最新版本', {icon: 1});
                }
            }, function(error) {
                hideLoading(loading);
                layer.msg('检查更新失败', {icon: 2});
            });
        }

        // 下载更新
        function downloadUpdate() {
            var loading = showLoading();
            apiRequest('/api/update/download', 'POST', {}, function(data) {
                hideLoading(loading);
                layer.msg('开始下载更新...', {icon: 1});
                // 这里可以打开下载链接
                window.open(data.downloadUrl, '_blank');
            }, function(error) {
                hideLoading(loading);
                layer.msg('下载更新失败', {icon: 2});
            });
        }

        // 打开帮助中心
        function openHelpCenter() {
            layer.open({
                type: 2,
                title: '帮助中心',
                area: ['800px', '600px'],
                content: 'https://docs.jjyb-ai.com'
            });
        }


        // 打开关于对话框
        function openAboutDialog() {
            layer.open({
                type: 1,
                title: '关于AIJian',
                area: ['600px', '400px'],
                content: `
                    <div class="layui-card">
                        <div class="layui-card-body">
                            <div class="text-center">
                                <h3 class="layui-card-title mt-5">AIJian v2.0.0</h3>
                                <div class="layui-elem-quote mt-5">
                                    <p>基于AI技术的智能视频剪辑工具，让视频创作更简单高效</p>
                                    <p class="mt-2">支持智能配音、自动字幕、智能剪辑等功能</p>
                                </div>
                            </div>
                        </div>
                    </div>
                `
            });
        }

        // 获取系统信息
        function getSystemInfo() {
            apiRequest('/system/info', 'GET', {}, function(data) {
                if (data.os) $('#os-info').text(data.os);
                if (data.cpu) $('#cpu-info').text(data.cpu);
                if (data.memory) $('#memory-info').text(data.memory);
                if (data.gpu) $('#gpu-info').text(data.gpu);
                if (data.disk) $('#disk-info').text(data.disk);
                if (data.python) $('#python-info').text(data.python);
                if (data.ffmpeg) $('#ffmpeg-info').text(data.ffmpeg);
            });
        }


