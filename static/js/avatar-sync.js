/**
 * TasteMate — 아바타 색상 동기화 (외부 파일용 전역 공통)
 */
(function () {
    // [핵심] 색상을 입히는 함수
    function applyAvatarColor() {
        const avatarColor = localStorage.getItem('avatarColor');
        if (!avatarColor) return;

        const avatars = document.querySelectorAll('.nickname-avatar');
        avatars.forEach(el => {
            // CSS 우선순위를 이기기 위해 !important 사용
            el.style.setProperty('background', avatarColor, 'important');
            el.style.setProperty('background-image', 'none', 'important');
            el.style.color = '#fff';
        });
    }

    // 전역 함수로 등록 (어디서든 호출 가능하게)
    window.applyAvatarColor = applyAvatarColor;
    window.setAvatarColor = function (color) {
        localStorage.setItem('avatarColor', color);
        applyAvatarColor();
    };

    // 실행 로직
    const init = () => {
        applyAvatarColor();

        // MutationObserver: renderHeader() 등으로 HTML이 교체되어도 즉시 감지
        const observer = new MutationObserver((mutations) => {
            let shouldApply = false;
            mutations.forEach(mutation => {
                if (mutation.addedNodes.length > 0) shouldApply = true;
            });
            if (shouldApply) applyAvatarColor();
        });

        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    };

    // DOM이 이미 로드되었는지 확인 후 실행
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();