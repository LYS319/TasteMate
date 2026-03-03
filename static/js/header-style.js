// header-style.js
// 테이스트메이트.html의 상단 메뉴바 스타일을 모든 페이지에 적용

document.addEventListener('DOMContentLoaded', function () {
    // 아바타 색상 동기화 스크립트 (모든 페이지 공통)
    const avatarColor = localStorage.getItem('avatarColor');
    if (avatarColor) {
        document.querySelectorAll('.nickname-avatar').forEach(function (el) {
            el.style.backgroundColor = avatarColor;
            el.style.color = '#fff';
        });
    }
    // about.html 스타일 기준으로 상단바 스타일 통일 적용
    const header = document.querySelector('.header');
    if (header) {
        header.style.display = 'flex';
        header.style.justifyContent = 'space-between';
        header.style.alignItems = 'center';
        header.style.padding = '16px 32px';
        header.style.background = 'rgba(255, 255, 255, 0.9)';
        header.style.boxShadow = '0 4px 20px rgba(220, 38, 38, 0.08)';
        header.style.backdropFilter = 'blur(15px)';
        header.style.position = 'fixed';
        header.style.top = '0';
        header.style.left = '0';
        header.style.right = '0';
        header.style.zIndex = '1000';
    }
    // 메뉴바 내부 스타일 통일 (about.html 기준)
    document.querySelectorAll('.menu-item').forEach(function (el) {
        el.style.fontSize = '1.15rem';
        el.style.fontWeight = '700';
        el.style.color = '#222';
        el.style.textDecoration = 'none';
        el.style.padding = '8px 18px';
        el.style.borderRadius = '8px';
        el.style.transition = 'background 0.18s, color 0.18s';
    });
    // 메뉴바 hover 효과 (about.html 기준)
    document.querySelectorAll('.menu-item').forEach(function (el) {
        el.addEventListener('mouseenter', function () {
            el.style.background = '#f1f1f1';
            el.style.color = '#dc2626';
        });
        el.addEventListener('mouseleave', function () {
            el.style.background = '';
            el.style.color = '#222';
        });
    });
    // 드롭다운 메뉴 스타일 (about.html 기준)
    document.querySelectorAll('.dropdown-content a').forEach(function (el) {
        el.style.color = '#222';
        el.style.padding = '10px 24px';
        el.style.textDecoration = 'none';
        el.style.display = 'block';
        el.style.fontWeight = '600';
        el.style.borderRadius = '8px';
        el.style.fontSize = '1.08rem';
        el.style.transition = 'background 0.2s, color 0.2s';
        el.addEventListener('mouseenter', function () {
            el.style.background = '#ffe5e5';
        });
        el.addEventListener('mouseleave', function () {
            el.style.background = '';
        });
    });
    // 드롭다운 메뉴 hover 동작 (모든 페이지 공통)
    document.querySelectorAll('.game-dropdown').forEach(function (dropdown) {
        const dropdownContent = dropdown.querySelector('.dropdown-content');
        if (!dropdownContent) return;
        let dropdownTimer = null;
        dropdown.addEventListener('mouseenter', function () {
            clearTimeout(dropdownTimer);
            dropdownContent.style.display = 'block';
        });
        dropdown.addEventListener('mouseleave', function () {
            dropdownTimer = setTimeout(function () {
                dropdownContent.style.display = '';
            }, 120);
        });
        dropdownContent.addEventListener('mouseenter', function () {
            clearTimeout(dropdownTimer);
            dropdownContent.style.display = 'block';
        });
        dropdownContent.addEventListener('mouseleave', function () {
            dropdownTimer = setTimeout(function () {
                dropdownContent.style.display = '';
            }, 120);
        });
    });
});
