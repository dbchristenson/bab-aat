// static/js/documents.js
document.addEventListener('DOMContentLoaded', () => {
    const checkboxes = document.querySelectorAll('.vessel-checkbox');
    const docInput = document.getElementById('docNumberInput');
    const clearBtn = document.getElementById('clearFilters');
    const rows = document.querySelectorAll('table tbody tr');
    const countEl = document.getElementById('docCount');

    // update the “Showing X” count
    function updateCount() {
        const visible = Array.from(rows).filter(r => r.style.display !== 'none').length;
        countEl.textContent = visible;
    }

    // show/hide rows by checked vessels & substring match
    function applyFilters() {
        const selectedV = Array.from(checkboxes)
            .filter(cb => cb.checked)
            .map(cb => cb.value);
        const term = docInput.value.trim().toLowerCase();

        rows.forEach(row => {
            const okV = !selectedV.length || selectedV.includes(row.dataset.vesselId);
            const okD = !term || row.dataset.documentNumber.includes(term);
            row.style.display = (okV && okD) ? '' : 'none';
        });

        updateCount();
    }

    // events
    checkboxes.forEach(cb => cb.addEventListener('change', applyFilters));
    docInput.addEventListener('input', applyFilters);
    clearBtn.addEventListener('click', () => {
        checkboxes.forEach(cb => cb.checked = false);
        docInput.value = '';
        applyFilters();
    });

    // init
    updateCount();
});
