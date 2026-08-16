// web/static/js/app.js
// Main JavaScript for AI Assistant Web Interface

let isStreaming = false;
let currentAbortController = null;
let messageCount = 0;
let currentMessageId = null;
let useRAG = true;

// ============================================
// SEND MESSAGE
// ============================================

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const question = input.value.trim();
    
    if (!question) return;
    if (isStreaming) return;
    
    // Hide welcome screen
    document.getElementById('welcomeScreen').classList.add('hidden');
    document.getElementById('messagesArea').classList.remove('hidden');
    
    // Add user message
    addUserMessage(question);
    
    // Clear input
    input.value = '';
    autoResize(input);
    
    // Show typing indicator
    showTypingIndicator();
    
    // Disable send button
    document.getElementById('sendBtn').disabled = true;
    document.getElementById('stopBtn').style.display = 'flex';
    
    isStreaming = true;
    
    try {
        // Prepare message for AI
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: question,
                use_rag: useRAG
            })
        });
        
        const data = await response.json();
        
        // Remove typing indicator
        removeTypingIndicator();
        
        if (data.success) {
            // Add AI message
            const msgId = addAIMessage(data.response, {
                tokens: data.tokens || 0,
                latency: data.latency || 0,
                tool_used: data.tool_used
            });
        } else {
            addErrorMessage(data.response || data.error || 'Unknown error');
        }
        
    } catch (error) {
        removeTypingIndicator();
        addErrorMessage('Network error: ' + error.message);
    }
    
    isStreaming = false;
    document.getElementById('sendBtn').disabled = false;
    document.getElementById('stopBtn').style.display = 'none';
}

// ============================================
// STREAMING (Server-Sent Events)
// ============================================

async function sendMessageStream() {
    const input = document.getElementById('chatInput');
    const question = input.value.trim();
    
    if (!question) return;
    if (isStreaming) return;
    
    // Hide welcome screen
    document.getElementById('welcomeScreen').classList.add('hidden');
    document.getElementById('messagesArea').classList.remove('hidden');
    
    // Add user message
    addUserMessage(question);
    
    // Clear input
    input.value = '';
    autoResize(input);
    
    // Show typing indicator
    showTypingIndicator();
    
    // Disable send button
    document.getElementById('sendBtn').disabled = true;
    document.getElementById('stopBtn').style.display = 'flex';
    
    isStreaming = true;
    
    try {
        const response = await fetch('/api/chat/stream', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: question,
                use_rag: useRAG
            })
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let fullText = '';
        let msgId = null;
        
        removeTypingIndicator();
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        
                        if (data.error) {
                            addErrorMessage(data.error);
                            break;
                        }
                        
                        if (data.is_last) {
                            // Finalize message
                            if (msgId) {
                                updateMessageStats(msgId, {
                                    tokens: data.tokens || 0,
                                    latency: data.latency || 0,
                                    tool_used: data.tool_used
                                });
                            }
                            break;
                        }
                        
                        if (data.text) {
                            fullText += data.text;
                            
                            if (!msgId) {
                                msgId = addAIMessage(fullText, {
                                    tokens: 0,
                                    latency: 0,
                                    tool_used: data.tool_used
                                });
                            } else {
                                updateAIMessage(msgId, fullText);
                            }
                        }
                        
                    } catch (e) {
                        console.error('Parse error:', e);
                    }
                }
            }
        }
        
        if (!msgId && fullText) {
            msgId = addAIMessage(fullText);
        }
        
    } catch (error) {
        removeTypingIndicator();
        addErrorMessage('Network error: ' + error.message);
    }
    
    isStreaming = false;
    document.getElementById('sendBtn').disabled = false;
    document.getElementById('stopBtn').style.display = 'none';
}

// ============================================
// DOM HELPERS
// ============================================

function addUserMessage(text) {
    const container = document.getElementById('messagesArea');
    const template = document.getElementById('userMessageTemplate');
    const clone = template.content.cloneNode(true);
    
    const content = clone.querySelector('.message-content');
    content.textContent = text;
    
    const time = clone.querySelector('.message-time');
    time.textContent = new Date().toLocaleTimeString();
    
    const message = clone.querySelector('.message');
    message.dataset.messageId = `msg_${++messageCount}`;
    message.dataset.content = text;
    
    container.appendChild(clone);
    container.scrollTop = container.scrollHeight;
    
    return message.dataset.messageId;
}

function addAIMessage(text, stats = {}) {
    const container = document.getElementById('messagesArea');
    const template = document.getElementById('aiMessageTemplate');
    const clone = template.content.cloneNode(true);
    
    const content = clone.querySelector('.message-content');
    content.innerHTML = marked.parse(text);
    
    // Highlight code blocks
    content.querySelectorAll('pre code').forEach(block => {
        hljs.highlightElement(block);
    });
    
    const time = clone.querySelector('.message-time span');
    if (time) {
        time.textContent = new Date().toLocaleTimeString();
    }
    
    // Stats
    if (stats.tokens) {
        const tokenEl = clone.querySelector('.info-tokens');
        if (tokenEl) tokenEl.textContent = stats.tokens;
    }
    
    if (stats.latency) {
        const timeEl = clone.querySelector('.info-time');
        if (timeEl) timeEl.textContent = stats.latency.toFixed(1) + 's';
    }
    
    if (stats.tool_used) {
        const modelName = clone.querySelector('.info-model-name');
        if (modelName) modelName.textContent = 'Tool: ' + stats.tool_used;
    }
    
    const message = clone.querySelector('.message');
    const msgId = `msg_${++messageCount}`;
    message.dataset.messageId = msgId;
    message.dataset.content = text;
    
    container.appendChild(clone);
    container.scrollTop = container.scrollHeight;
    
    return msgId;
}

function updateAIMessage(msgId, text) {
    const container = document.getElementById('messagesArea');
    const messages = container.querySelectorAll('.message.assistant');
    
    for (const msg of messages) {
        if (msg.dataset.messageId === msgId) {
            const content = msg.querySelector('.message-content');
            content.innerHTML = marked.parse(text);
            
            // Re-highlight code
            content.querySelectorAll('pre code').forEach(block => {
                hljs.highlightElement(block);
            });
            
            container.scrollTop = container.scrollHeight;
            break;
        }
    }
}

function updateMessageStats(msgId, stats) {
    const container = document.getElementById('messagesArea');
    const messages = container.querySelectorAll('.message.assistant');
    
    for (const msg of messages) {
        if (msg.dataset.messageId === msgId) {
            if (stats.tokens) {
                const tokenEl = msg.querySelector('.info-tokens');
                if (tokenEl) tokenEl.textContent = stats.tokens;
            }
            if (stats.latency) {
                const timeEl = msg.querySelector('.info-time');
                if (timeEl) timeEl.textContent = stats.latency.toFixed(1) + 's';
            }
            if (stats.tool_used) {
                const modelName = msg.querySelector('.info-model-name');
                if (modelName) modelName.textContent = 'Tool: ' + stats.tool_used;
            }
            break;
        }
    }
}

function addErrorMessage(text) {
    const container = document.getElementById('messagesArea');
    const div = document.createElement('div');
    div.className = 'error-message';
    div.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${text}`;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function showTypingIndicator() {
    const container = document.getElementById('messagesArea');
    const div = document.createElement('div');
    div.className = 'typing-indicator';
    div.id = 'typingIndicator';
    div.innerHTML = '<span></span><span></span><span></span>';
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
}

function removeTypingIndicator() {
    const el = document.getElementById('typingIndicator');
    if (el) el.remove();
}

// ============================================
// INPUT HANDLERS
// ============================================

function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

function stopGeneration() {
    isStreaming = false;
    document.getElementById('sendBtn').disabled = false;
    document.getElementById('stopBtn').style.display = 'none';
    removeTypingIndicator();
}

// ============================================
// SUGGESTIONS
// ============================================

function sendSuggestion(text) {
    document.getElementById('chatInput').value = text;
    sendMessage();
}

// ============================================
// NEW CHAT
// ============================================

function startNewChat() {
    const container = document.getElementById('messagesArea');
    container.innerHTML = '';
    container.classList.add('hidden');
    document.getElementById('welcomeScreen').classList.remove('hidden');
    messageCount = 0;
    
    fetch('/api/clear', { method: 'POST' });
}

// ============================================
// FILE UPLOAD
// ============================================

function handleFileUpload(input) {
    const file = input.files[0];
    if (!file) return;
    
    const fileInfo = document.getElementById('fileInfo');
    const fileName = document.getElementById('fileName');
    fileName.textContent = file.name;
    fileInfo.classList.add('show');
}

function clearFile() {
    document.getElementById('fileInfo').classList.remove('show');
    document.getElementById('fileInput').value = '';
}

// ============================================
// THEME TOGGLE
// ============================================

function toggleTheme() {
    document.documentElement.classList.toggle('light-mode');
    const icon = document.getElementById('themeIcon');
    if (document.documentElement.classList.contains('light-mode')) {
        icon.className = 'fas fa-sun';
    } else {
        icon.className = 'fas fa-moon';
    }
}

// ============================================
// SIDEBAR TOGGLE (Mobile)
// ============================================

function toggleSidebar() {
    const container = document.getElementById('appContainer');
    const overlay = document.getElementById('sidebarOverlay');
    container.classList.toggle('sidebar-closed');
    overlay.classList.toggle('show');
}

// ============================================
// MCP / AGENT / SKILL TOGGLES
// ============================================

function toggleMCP() {
    const skills = document.getElementById('agentSkills');
    skills.classList.toggle('show');
}

function toggleAgentSkills() {
    const skills = document.getElementById('agentSkills');
    skills.classList.toggle('show');
}

function toggleProjects() {
    const projects = document.getElementById('projectsList');
    projects.classList.toggle('show');
}

function toggleSettings() {
    const panel = document.getElementById('settingsPanel');
    panel.classList.toggle('show');
}

function toggleSwitch(el) {
    el.classList.toggle('active');
}

function selectMCP(el) {
    document.querySelectorAll('.skill-tag').forEach(t => t.classList.remove('selected'));
    el.classList.add('selected');
}

function selectAgents(el) {
    document.querySelectorAll('.skill-tag').forEach(t => t.classList.remove('selected'));
    el.classList.add('selected');
}

function selectSkill(el) {
    document.querySelectorAll('.skill-tag').forEach(t => t.classList.remove('selected'));
    el.classList.add('selected');
}

function toggleModelDropdown() {
    document.getElementById('modelDropdown').classList.toggle('show');
}

function selectModel(name, el) {
    document.querySelectorAll('.model-option').forEach(o => o.classList.remove('selected'));
    el.classList.add('selected');
    document.getElementById('selectedModel').textContent = name;
    document.getElementById('modelDropdown').classList.remove('show');
}

function toggleTempChat() {
    const btn = document.getElementById('tempChatBtn');
    btn.classList.toggle('active');
    // Temp chat logic
}

// ============================================
// IP ADDRESS DISPLAY
// ============================================

async function getIP() {
    try {
        const response = await fetch('https://api.ipify.org?format=json');
        const data = await response.json();
        const display = document.querySelector('.ip-display span');
        if (display) display.textContent = data.ip;
    } catch {
        const display = document.querySelector('.ip-display span');
        if (display) display.textContent = '127.0.0.1';
    }
}

// ============================================
// SEARCH (Ctrl+K)
// ============================================

document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        document.getElementById('searchInput').focus();
    }
});

// ============================================
// INIT
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    getIP();
    
    // Close dropdown on click outside
    document.addEventListener('click', (e) => {
        const dropdown = document.getElementById('modelDropdown');
        const btn = document.getElementById('modelSelectBtn');
        if (!dropdown.contains(e.target) && !btn.contains(e.target)) {
            dropdown.classList.remove('show');
        }
    });
});

// ============================================
// EXPOSE TO GLOBAL
// ============================================

window.sendMessage = sendMessage;
window.sendMessageStream = sendMessageStream;
window.sendSuggestion = sendSuggestion;
window.startNewChat = startNewChat;
window.handleKeyDown = handleKeyDown;
window.autoResize = autoResize;
window.stopGeneration = stopGeneration;
window.toggleSidebar = toggleSidebar;
window.toggleTheme = toggleTheme;
window.toggleMCP = toggleMCP;
window.toggleAgentSkills = toggleAgentSkills;
window.toggleProjects = toggleProjects;
window.toggleSettings = toggleSettings;
window.toggleSwitch = toggleSwitch;
window.selectMCP = selectMCP;
window.selectAgents = selectAgents;
window.selectSkill = selectSkill;
window.toggleModelDropdown = toggleModelDropdown;
window.selectModel = selectModel;
window.toggleTempChat = toggleTempChat;
window.handleFileUpload = handleFileUpload;
window.clearFile = clearFile;