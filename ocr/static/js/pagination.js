document.addEventListener('DOMContentLoaded', () => {
    const jumpForm = document.getElementById('jumpForm');
    const jumpTo = document.getElementById('jumpTo');
    const maxPage = Number(jumpTo.max);

    jumpForm.addEventListener('submit', () => {
        let p = Number(jumpTo.value);
        if (!p || p < 1 || p > maxPage) {
            // optionally, flash an error style:
            jumpTo.classList.add('is-invalid');
            return;
        }
        // rebuild URL, preserving other query params
        const params = new URLSearchParams(window.location.search);
        params.set('page', p);
        window.location.search = params.toString();
    });

    // clear invalid state on input
    jumpTo.addEventListener('input', () => {
        jumpTo.classList.remove('is-invalid');
    });
});
