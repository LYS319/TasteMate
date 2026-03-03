// =============================================
// friend-chat.js
// 친구 패널 & 다중 채팅창 시스템 (공통 JS)
// =============================================

const chatWindows = new Map();
let globalSocket = null;
const MAX_CHAT_WINDOWS = 5;
const pendingMessages = new Map();

// ── 재연결 관련 상태 ──
let reconnectAttempts = 0;
let reconnectTimer = null;
let isConnecting = false;
let heartbeatTimer = null;

// =============================================
// Toast
// =============================================
function showToast(msg, type = '') {
    const t = document.getElementById('toast');
    if (!t) return;
    t.textContent = msg;
    t.className = `toast ${type}`;
    setTimeout(() => t.classList.add('show'), 10);
    setTimeout(() => t.classList.remove('show'), 2800);
}

// =============================================
// 패널 토글
// =============================================
let panelToggleLock = false;
function togglePanel() {
    if (panelToggleLock) return;
    const panel = document.getElementById('panelPanel');
    const overlay = document.getElementById('panelOverlay');
    const isActive = panel.classList.toggle('active');
    if (isActive) {
        overlay.style.display = 'block';
        setTimeout(() => overlay.classList.add('active'), 10);
        const currentUserId = localStorage.getItem('user_id');
        if (currentUserId) refreshPanelData();
    } else {
        panelToggleLock = true;
        overlay.classList.remove('active');
        setTimeout(() => {
            overlay.style.display = 'none';
            panelToggleLock = false;
        }, 300);
    }
}

function showTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach((b, i) => {
        b.classList.toggle('active', ['list', 'add', 'req'][i] === tabName);
    });
    document.querySelectorAll('.tab-content').forEach((c) => c.classList.remove('active'));
    document.getElementById('tab-' + tabName).classList.add('active');
    if (tabName === 'req') document.getElementById('req-dot').style.display = 'none';
}

// =============================================
// 패널 데이터 새로고침
// =============================================
async function refreshPanelData() {
    const currentUserId = localStorage.getItem('user_id');
    if (!currentUserId) return;
    try {
        const res = await fetch(`/api/friends/status/${currentUserId}`);
        const data = await res.json();
        const listContainer = document.getElementById('panel-list-container');
        if (data.friends && data.friends.length > 0) {
            listContainer.innerHTML = data.friends
                .map(
                    (f) => `
                <div class="friend-item" id="friend-item-${f.id}">
                    <div class="friend-name">
                        <div class="friend-avatar">${f.nickname.slice(0, 2)}</div>
                        ${f.nickname}
                    </div>
                    <div class="friend-actions">
                        <button class="action-btn btn-chat" onclick="openChat(${f.id}, '${f.nickname}')">💬</button>
                        <button class="action-btn btn-delete" onclick="confirmDeleteFriend(${f.id}, '${f.nickname}')" title="친구 삭제">🗑️</button>
                    </div>
                </div>
            `,
                )
                .join('');
        } else {
            listContainer.innerHTML = `<div class="empty-state"><div class="empty-icon">👥</div>아직 친구가 없어요.<br>친구를 추가해보세요!</div>`;
        }
        const reqContainer = document.getElementById('panel-req-container');
        if (data.requests && data.requests.length > 0) {
            document.getElementById('req-dot').style.display = 'inline-block';
            reqContainer.innerHTML = data.requests
                .map(
                    (r) => `
                <div class="friend-item" id="req-item-${r.id}">
                    <div class="friend-name">
                        <div class="friend-avatar">${r.nickname.slice(0, 2)}</div>
                        <div>
                            <div>${r.nickname}</div>
                            <div style="font-size:0.78rem; color:#888; font-weight:400">친구 요청을 보냈어요</div>
                        </div>
                    </div>
                    <div style="display:flex; gap:6px">
                        <button class="action-btn btn-accept" onclick="handleFriendAction(${r.id}, 'accept')">수락</button>
                        <button class="action-btn btn-reject" onclick="handleFriendAction(${r.id}, 'reject')">거절</button>
                    </div>
                </div>
            `,
                )
                .join('');
        } else {
            document.getElementById('req-dot').style.display = 'none';
            reqContainer.innerHTML = `<div class="empty-state"><div class="empty-icon">📭</div>받은 친구 요청이 없어요.</div>`;
        }
    } catch (e) {
        console.error('패널 데이터 로딩 오류:', e);
    }
}

// =============================================
// 친구 신청
// =============================================
async function requestFriend() {
    const currentUserId = localStorage.getItem('user_id');
    if (!currentUserId) {
        showToast('로그인 후 이용해주세요!', 'error');
        return;
    }
    const nickname = document.getElementById('panelSearch').value.trim();
    const resultEl = document.getElementById('add-friend-result');
    if (!nickname) {
        resultEl.innerHTML = `<span style="color:#dc2626">닉네임을 입력해주세요.</span>`;
        return;
    }
    try {
        const formData = new FormData();
        formData.append('nickname', nickname);
        formData.append('from_user', currentUserId);
        const res = await fetch('/api/friends/request', { method: 'POST', body: formData });
        const data = await res.json();
        if (res.ok) {
            resultEl.innerHTML = `<span style="color:#16a34a">✅ ${data.message}</span>`;
            showToast(`${nickname}님에게 친구 신청을 보냈어요!`, 'success');
            document.getElementById('panelSearch').value = '';
        } else {
            resultEl.innerHTML = `<span style="color:#dc2626">❌ ${data.message || '닉네임을 다시 확인해주세요.'}</span>`;
            showToast('닉네임을 확인해주세요.', 'error');
        }
    } catch (e) {
        resultEl.innerHTML = `<span style="color:#dc2626">❌ 오류가 발생했습니다.</span>`;
    }
}

// =============================================
// 친구 요청 수락/거절
// =============================================
async function handleFriendAction(targetId, action) {
    const currentUserId = localStorage.getItem('user_id');
    if (!currentUserId) return;
    try {
        const formData = new FormData();
        formData.append('user_id', currentUserId);
        formData.append('target_id', targetId);
        formData.append('action', action);
        const res = await fetch('/api/friends/action', { method: 'POST', body: formData });
        if (res.ok) {
            showToast(
                action === 'accept' ? '친구가 되었어요! 🎉' : '요청을 거절했습니다.',
                action === 'accept' ? 'success' : '',
            );
            const item = document.getElementById(`req-item-${targetId}`);
            if (item) {
                item.style.opacity = '0';
                item.style.transition = 'opacity 0.3s';
                setTimeout(() => {
                    item.remove();
                    refreshPanelData();
                }, 300);
            }
        }
    } catch (e) {
        showToast('오류가 발생했습니다.', 'error');
    }
}

// =============================================
// 친구 삭제 모달
// =============================================
let pendingDeleteFriendId = null;
function confirmDeleteFriend(friendId, friendNickname) {
    pendingDeleteFriendId = friendId;
    document.getElementById('confirmModalTitle').textContent = `${friendNickname}님을 삭제할까요?`;
    document.getElementById('confirmModalDesc').textContent = '삭제하면 서로의 친구 목록에서\n사라집니다.';
    document.getElementById('confirmOkBtn').onclick = () => deleteFriend(friendId, friendNickname);
    const bg = document.getElementById('confirmModalBg');
    bg.style.display = 'flex';
    setTimeout(() => bg.classList.add('show'), 10);
}
function closeConfirmModal() {
    const bg = document.getElementById('confirmModalBg');
    bg.classList.remove('show');
    setTimeout(() => {
        bg.style.display = 'none';
        pendingDeleteFriendId = null;
    }, 250);
}
async function deleteFriend(friendId, friendNickname) {
    const currentUserId = localStorage.getItem('user_id');
    closeConfirmModal();
    try {
        const formData = new FormData();
        formData.append('user_id', currentUserId);
        formData.append('friend_id', friendId);
        const res = await fetch('/api/friends/delete', { method: 'POST', body: formData });
        const data = await res.json();
        if (res.ok) {
            showToast(`${friendNickname}님과 친구를 끊었습니다.`, '');
            const item = document.getElementById(`friend-item-${friendId}`);
            if (item) {
                item.style.transition = 'all 0.3s';
                item.style.opacity = '0';
                item.style.transform = 'translateX(20px)';
                setTimeout(() => item.remove(), 300);
            }
            closeChat(friendId);
        } else {
            showToast(data.message || '삭제 중 오류가 발생했습니다.', 'error');
        }
    } catch (e) {
        showToast('오류가 발생했습니다.', 'error');
    }
}

// =============================================
// ── 다중 채팅창 시스템 ──
// =============================================
async function openChat(targetId, targetName) {
    targetId = String(targetId);
    const currentUserId = localStorage.getItem('user_id');

    if (chatWindows.has(targetId)) {
        const win = chatWindows.get(targetId);
        win.minimized = false;
        win.el.classList.remove('minimized');
        win.el.querySelector('.chat-input').focus();
        _clearUnread(targetId);
        return;
    }

    if (chatWindows.size >= MAX_CHAT_WINDOWS) {
        const oldestKey = chatWindows.keys().next().value;
        closeChat(oldestKey);
    }

    const winEl = _createChatWindowEl(targetId, targetName);
    document.getElementById('chat-windows-container').appendChild(winEl);
    chatWindows.set(targetId, { el: winEl, minimized: false, unread: 0, targetName });

    // 이미 연결돼 있으면 상태 즉시 반영
    if (globalSocket && globalSocket.readyState === WebSocket.OPEN) {
        const statusEl = winEl.querySelector('.chat-ws-status');
        if (statusEl) statusEl.textContent = '온라인 ✓';
    }

    await _loadHistory(targetId, winEl);

    if (pendingMessages.has(targetId)) {
        pendingMessages.get(targetId).forEach((m) => _appendMessage(targetId, m.text, m.type));
        pendingMessages.delete(targetId);
    }
    winEl.querySelector('.chat-input').focus();
    _clearUnread(targetId);
}

function _createChatWindowEl(targetId, targetName) {
    const div = document.createElement('div');
    div.className = 'chat-window';
    div.dataset.targetId = targetId;
    div.innerHTML = `
        <div class="chat-header" onclick="_toggleMinimize('${targetId}')">
            <div class="chat-header-info">
                <div class="chat-target-avatar">${targetName.slice(0, 2)}</div>
                <span class="chat-target-name">${targetName}</span>
                <span class="chat-ws-status">연결 중...</span>
            </div>
            <div class="chat-header-actions">
                <span class="unread-badge" style="display:none">0</span>
                <button class="chat-ctrl-btn" title="최소화" onclick="event.stopPropagation(); _toggleMinimize('${targetId}')">—</button>
                <button class="chat-ctrl-btn" title="닫기" onclick="event.stopPropagation(); closeChat('${targetId}')">✕</button>
            </div>
        </div>
        <div class="chat-messages" id="chat-msgs-${targetId}">
            <div style="text-align:center;color:#ccc;font-size:0.8rem;padding:20px 0">대화 기록 불러오는 중...</div>
        </div>
        <div class="chat-input-area">
            <input class="chat-input" placeholder="메시지 입력..."
                onkeyup="if(event.keyCode===13) _sendMessage('${targetId}')" />
            <button class="chat-send-btn" onclick="_sendMessage('${targetId}')">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="22" y1="2" x2="11" y2="13"></line>
                    <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
                </svg>
            </button>
        </div>
    `;
    return div;
}

async function _loadHistory(targetId, winEl) {
    const currentUserId = localStorage.getItem('user_id');
    const msgBox = winEl.querySelector('.chat-messages');
    try {
        const res = await fetch(`/api/chat/history?user1=${currentUserId}&user2=${targetId}`);
        const history = await res.json();
        msgBox.innerHTML = '';
        if (history.length === 0) {
            msgBox.innerHTML =
                '<div style="text-align:center;color:#ccc;font-size:0.82rem;padding:30px 0">아직 대화가 없어요.<br>먼저 인사를 건네보세요! 👋</div>';
        } else {
            history.forEach((m) => _appendMessage(targetId, m.message, m.sender_id == currentUserId ? 'me' : 'other'));
        }
    } catch (e) {
        msgBox.innerHTML =
            '<div style="text-align:center;color:#dc2626;font-size:0.82rem;padding:20px 0">대화 기록을 불러오지 못했습니다.</div>';
    }
    msgBox.scrollTop = msgBox.scrollHeight;
}

function closeChat(targetId) {
    targetId = String(targetId);
    if (!chatWindows.has(targetId)) return;
    const win = chatWindows.get(targetId);
    win.el.style.transition = 'opacity 0.2s, transform 0.2s';
    win.el.style.opacity = '0';
    win.el.style.transform = 'translateY(20px) scale(0.95)';
    setTimeout(() => win.el.remove(), 220);
    chatWindows.delete(targetId);
}

function _toggleMinimize(targetId) {
    targetId = String(targetId);
    if (!chatWindows.has(targetId)) return;
    const win = chatWindows.get(targetId);
    win.minimized = !win.minimized;
    win.el.classList.toggle('minimized', win.minimized);
    if (!win.minimized) _clearUnread(targetId);
}

function _appendMessage(targetId, text, type) {
    const msgBox = document.getElementById(`chat-msgs-${targetId}`);
    if (!msgBox) return;
    const empty = msgBox.querySelector('div[style*="text-align:center"]');
    if (empty) empty.remove();

    const wrapper = document.createElement('div');
    wrapper.style.cssText = `display:flex; flex-direction:column; align-items:${type === 'me' ? 'flex-end' : 'flex-start'}`;

    const bubble = document.createElement('div');
    bubble.className = `msg ${type}`;
    bubble.textContent = text;

    const time = document.createElement('div');
    const now = new Date();
    time.textContent = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
    time.style.cssText = 'font-size:0.65rem; color:#bbb; margin-top:3px; padding:0 4px';

    wrapper.appendChild(bubble);
    wrapper.appendChild(time);
    msgBox.appendChild(wrapper);
    msgBox.scrollTop = msgBox.scrollHeight;
}

function _sendMessage(targetId) {
    targetId = String(targetId);
    const win = chatWindows.get(targetId);
    if (!win) return;

    const input = win.el.querySelector('.chat-input');
    const msg = input.value.trim();
    if (!msg) return;

    if (!globalSocket || globalSocket.readyState !== WebSocket.OPEN) {
        showToast('연결 중입니다. 잠시 후 다시 시도해주세요.');
        connectWebSocket();
        return;
    }

    globalSocket.send(JSON.stringify({ receiver_id: targetId, message: msg }));
    _appendMessage(targetId, msg, 'me');
    input.value = '';
}

function _incrementUnread(targetId) {
    targetId = String(targetId);
    const win = chatWindows.get(targetId);
    if (!win) return;
    win.unread++;
    const badge = win.el.querySelector('.unread-badge');
    badge.textContent = win.unread;
    badge.style.display = 'flex';
}

function _clearUnread(targetId) {
    targetId = String(targetId);
    const win = chatWindows.get(targetId);
    if (!win) return;
    win.unread = 0;
    const badge = win.el.querySelector('.unread-badge');
    if (badge) badge.style.display = 'none';
}

// =============================================
// 모든 채팅창 상태 텍스트 업데이트
// =============================================
function _updateAllWindowStatus(text) {
    chatWindows.forEach((win) => {
        const statusEl = win.el.querySelector('.chat-ws-status');
        if (statusEl) statusEl.textContent = text;
    });
}

// =============================================
// 하트비트 (연결 유지용 ping)
// =============================================
function _startHeartbeat() {
    _stopHeartbeat();
    heartbeatTimer = setInterval(() => {
        if (globalSocket && globalSocket.readyState === WebSocket.OPEN) {
            // 서버가 ping 메시지를 무시해도 소켓이 살아있는지 확인하는 역할
            try {
                globalSocket.send(JSON.stringify({ type: 'ping' }));
            } catch (e) {}
        }
    }, 25000); // 25초마다 ping
}

function _stopHeartbeat() {
    if (heartbeatTimer) {
        clearInterval(heartbeatTimer);
        heartbeatTimer = null;
    }
}

// =============================================
// WebSocket 연결 (지수 백오프 재연결)
// =============================================
function connectWebSocket() {
    const currentUserId = localStorage.getItem('user_id');
    if (!currentUserId) {
        console.warn('[WS] 로그인 상태가 아닙니다.');
        return;
    }

    // 이미 연결됐거나 연결 중이면 중복 연결 방지
    if (isConnecting) {
        console.log('[WS] 이미 연결 시도 중입니다.');
        return;
    }
    if (globalSocket && globalSocket.readyState === WebSocket.OPEN) {
        console.log('[WS] 이미 연결되어 있습니다.');
        return;
    }

    // 이전 소켓 명시적 정리
    if (globalSocket) {
        globalSocket.onclose = null; // 재귀 재연결 방지
        globalSocket.close();
        globalSocket = null;
    }

    isConnecting = true;
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${protocol}://${location.host}/ws/chat/${currentUserId}`;
    console.log(`[WS] 연결 시도 (${reconnectAttempts + 1}회): ${wsUrl}`);

    try {
        globalSocket = new WebSocket(wsUrl);

        globalSocket.onopen = () => {
            console.log('[WS] 연결 성공!');
            isConnecting = false;
            reconnectAttempts = 0; // 성공하면 횟수 초기화

            _updateAllWindowStatus('온라인 ✓');
            _startHeartbeat();

            // 재연결 성공 시 토스트는 재시도가 1회 이상이었을 때만 표시
            if (reconnectAttempts > 0) {
                showToast('채팅 서버에 재연결됐습니다.', 'success');
            }
        };

        globalSocket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);

                // ping 응답(pong)은 무시
                if (data.type === 'pong' || data.type === 'ping') return;

                const senderId = String(data.sender_id);

                if (chatWindows.has(senderId)) {
                    const win = chatWindows.get(senderId);
                    _appendMessage(senderId, data.message, 'other');
                    if (win.minimized) _incrementUnread(senderId);
                } else {
                    if (!pendingMessages.has(senderId)) pendingMessages.set(senderId, []);
                    pendingMessages.get(senderId).push({ text: data.message, type: 'other' });
                    showToast('💬 새 메시지가 도착했어요!', '');
                }
            } catch (e) {
                console.error('[WS] 메시지 파싱 오류:', e);
            }
        };

        globalSocket.onclose = (event) => {
            console.warn('[WS] 연결 종료:', event.code, event.reason);
            isConnecting = false;
            _stopHeartbeat();
            _updateAllWindowStatus('재연결 중...');

            // 1000(정상 종료) 또는 1001(페이지 이탈)은 재연결 안 함
            if (event.code === 1000 || event.code === 1001) {
                console.log('[WS] 정상 종료. 재연결하지 않습니다.');
                _updateAllWindowStatus('오프라인');
                return;
            }

            // 지수 백오프: 3s → 6s → 12s → 24s → 30s (최대)
            const delay = Math.min(3000 * Math.pow(2, reconnectAttempts), 30000);
            reconnectAttempts++;
            console.log(`[WS] ${delay / 1000}초 후 재연결 시도... (${reconnectAttempts}회)`);

            if (reconnectAttempts === 1) {
                showToast('채팅 서버와 연결이 끊겼습니다. 재연결 중...', 'error');
            }

            reconnectTimer = setTimeout(() => {
                const uid = localStorage.getItem('user_id');
                if (uid) connectWebSocket();
            }, delay);
        };

        globalSocket.onerror = (e) => {
            console.error('[WS] 소켓 오류:', e);
            isConnecting = false;
            // onerror 다음엔 항상 onclose가 호출되므로 재연결은 onclose에서 처리
        };
    } catch (e) {
        console.error('[WS] 연결 예외:', e);
        isConnecting = false;
        showToast('채팅 서버 연결 중 오류가 발생했습니다.', 'error');
    }
}

// =============================================
// 페이지 숨김/복귀 감지 (탭 전환, 화면 잠금 등)
// =============================================
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        const uid = localStorage.getItem('user_id');
        if (uid && (!globalSocket || globalSocket.readyState !== WebSocket.OPEN)) {
            console.log('[WS] 페이지 복귀 감지 → 재연결 시도');
            reconnectAttempts = 0; // 복귀 시 횟수 리셋
            connectWebSocket();
        }
    }
});

// =============================================
// 친구 요청 폴링 (30초)
// =============================================
async function pollFriendRequests() {
    const currentUserId = localStorage.getItem('user_id');
    if (!currentUserId) return;
    try {
        const res = await fetch(`/api/friends/status/${currentUserId}`);
        const data = await res.json();
        const dot = document.getElementById('req-dot');
        if (dot) dot.style.display = data.requests && data.requests.length > 0 ? 'inline-block' : 'none';
    } catch (e) {}
}

// =============================================
// 패널 공통 초기화
// =============================================
function initFriendChatPanel() {
    const currentUserId = localStorage.getItem('user_id');
    const currentNickname = localStorage.getItem('nickname');

    const hint = document.getElementById('panel-login-hint');
    if (hint) hint.textContent = currentNickname ? `${currentNickname}님의 친구 목록` : '로그인 후 이용하세요';

    const overlay = document.getElementById('panelOverlay');
    if (overlay) overlay.addEventListener('click', togglePanel);

    // 패널 외부 클릭 시 패널 닫기
    document.addEventListener('mousedown', function (e) {
        const panel = document.getElementById('panelPanel');
        const fab = document.getElementById('panelFab');
        if (!panel || !panel.classList.contains('active')) return;
        // 패널, 오버레이, FAB 버튼이 아닌 곳 클릭 시 닫기
        if (!panel.contains(e.target) && !overlay.contains(e.target) && !(fab && fab.contains(e.target))) {
            togglePanel();
        }
    });

    // ESC 키로 패널 닫기
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape' || e.key === 'Esc' || e.keyCode === 27) {
            const panel = document.getElementById('panelPanel');
            if (panel && panel.classList.contains('active')) {
                togglePanel();
            }
        }
    });

    if (!currentUserId) {
        const listContainer = document.getElementById('panel-list-container');
        if (listContainer)
            listContainer.innerHTML = `<div class="empty-state"><div class="empty-icon">🔐</div>로그인 후 친구 기능을<br>이용할 수 있어요.</div>`;
        const reqContainer = document.getElementById('panel-req-container');
        if (reqContainer)
            reqContainer.innerHTML = `<div class="empty-state"><div class="empty-icon">🔐</div>로그인 후 이용해주세요.</div>`;
        return;
    }

    connectWebSocket();
    pollFriendRequests();
    setInterval(pollFriendRequests, 30000);
}
