function isElementInViewport(el) {
    const rect = el.getBoundingClientRect();
    return (
        rect.left + 32 >= 0 &&
        rect.right - 32 <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

function checkVisibility() {
    const container = document.getElementById('scrollContainer');
    const items = container.querySelectorAll('div');
    items.forEach(item => {
        if (isElementInViewport(item)) {
            item.classList.remove('dimmed');
        } else {
            item.classList.add('dimmed');
        }
    });
}

document.getElementById('scrollContainer').addEventListener('scroll', checkVisibility);

// Initial check
checkVisibility();