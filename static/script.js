/* 통합 JS: TasteMate에서 병합 */

// 1. 햄버거 메뉴 토글
function toggleMenu() {
    const menu = document.getElementById('mainNavMenu');
    if (menu) {
        const isHidden = menu.style.display === 'none' || menu.style.display === '';
        menu.style.display = isHidden ? 'flex' : 'none';
    }
}

document.addEventListener('click', (e) => {
    const menu = document.getElementById('mainNavMenu');
    const toggleBtn = document.querySelector('.menu-toggle-btn');
    if (menu && menu.style.display === 'flex') {
        if (!menu.contains(e.target) && !toggleBtn.contains(e.target)) {
            menu.style.display = 'none';
        }
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const nickname = localStorage.getItem('nickname');
    const isAdmin = localStorage.getItem('is_admin');
    const headerRightArea = document.getElementById('headerRightArea');

    if (nickname && headerRightArea) {
        const shortNickname = nickname.length > 5 ? nickname.substring(0, 4) + '..' : nickname;
        let adminButton =
            isAdmin === '1'
                ? `<button class="login-btn" onclick="location.href='/admin'" style="background: #34495e;">관리자</button>`
                : '';

        headerRightArea.innerHTML = `
            <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap; justify-content:flex-end;">
                <span style="font-weight:700; color:#dc2626; font-size:0.85rem; margin-right:4px;">👤 ${shortNickname}</span>
                ${adminButton}
                <button class="login-btn" onclick="location.href='/mypage'" style="background: #f39c12;">정보</button>
                <button class="login-btn" onclick="logout()" style="background: #7f8c8d;">로그아웃</button>
                <div class="current-location" id="gps-location" onclick="getGPSLocation()">📍 위치 탐색</div>
            </div>
        `;
        getGPSLocation();
    }

    if (document.querySelector('.community-preview')) {
        fetchRecentPosts();
    }
});

async function fetchRecentPosts() {
    const container = document.querySelector('.community-preview');
    if (!container) return;

    try {
        const response = await fetch('/api/admin/posts');
        const posts = await response.json();

        if (!posts || posts.length === 0) {
            container.innerHTML = `<p style="text-align:center; width:100%; color:#999; padding:20px 0;">작성된 게시글이 없습니다.</p>`;
            return;
        }

        container.innerHTML = posts
            .slice(0, 5)
            .map((post) => {
                const isNotice = post.is_notice === 1;
                const cardClass = isNotice ? 'community-card notice-item' : 'community-card';
                const noticeBadge = isNotice ? '<span class="notice-badge">📢 [공지]</span>' : '';

                return `
                <div class="${cardClass}" onclick="location.href='/post/${post.id}'" style="cursor:pointer;">
                    <div class="card-category" style="font-size:0.8rem; color:#dc2626; font-weight:700; margin-bottom:6px;"># ${post.category}</div>
                    <div class="card-title" style="font-size:1.15rem; font-weight:700; margin-bottom:10px; color:#222;">
                        ${noticeBadge} ${post.title}
                    </div>
                    <div class="card-info" style="display:flex; justify-content:space-between; font-size:0.85rem; color:#666;">
                        <span>👤 ${post.author}</span>
                        <span>📅 ${post.date.split(' ')[0]}</span>
                    </div>
                </div>
            `;
            })
            .join('');
    } catch (e) {
        container.innerHTML = `<p style="text-align:center; width:100%; color:#dc2626;">데이터 로드 실패</p>`;
    }
}

function getGPSLocation() {
    const locSpan = document.getElementById('gps-location');
    if (!locSpan || !navigator.geolocation) return;
    navigator.geolocation.getCurrentPosition(async (pos) => {
        try {
            const res = await fetch(
                `https://nominatim.openstreetmap.org/reverse?format=json&lat=${pos.coords.latitude}&lon=${pos.coords.longitude}`,
            );
            // ...이하 생략...
        } catch (e) {}
    });
}
