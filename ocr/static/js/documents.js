// static/js/documents.js
document.addEventListener('DOMContentLoaded', () => {
    const checkboxes = document.querySelectorAll('.vessel-checkbox');
    const docInput = document.getElementById('docNumberInput');
    const clearBtn = document.getElementById('clearFilters');
    const rows = Array.from(document.querySelectorAll('table tbody tr'));
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

    // sorting
    let currentKey = null;
    let currentOrder = "asc"; //asc or desc
    const headers = document.querySelectorAll('th.sortable')

    function clearAllArrows() {
        headers.forEach(h => {
            const icon = h.querySelector('i');
            icon.className = 'fas fa-sort';
        });
    }

    function sortRows(key) {
        // flip sort order if same key, otherwise default to asc
        if (currentKey === key) {
            currentOrder = (currentOrder === 'asc') ? 'desc' : 'asc';
        } else {
            currentKey = key;
            currentOrder = 'asc';
        }

        // clear & set arrow
        clearAllArrows();
        const header = document.querySelector(`th[data-key="${key}"]`);
        const arrow = header.querySelector('i');
        arrow.className = `fas fa-sort-${currentOrder === 'asc' ? 'up' : 'down'}`;

        // do the actual sort
        rows.sort((a, b) => {
            let va = a.dataset[key],
                vb = b.dataset[key];

            // numeric sort for these two fields
            va = Number(va);
            vb = Number(vb);

            return (currentOrder === 'asc') ? (va - vb) : (vb - va);
        });

        // re-append in sorted order
        const tbody = document.querySelector('table tbody');
        rows.forEach(r => tbody.appendChild(r));
    }

    headers.forEach(h => {
        h.addEventListener('click', () => {
            const key = h.dataset.key;  // 'documentId' or 'fileSize'
            sortRows(key);
        });
    });

    // init
    applyFilters();
    updateCount();
});
