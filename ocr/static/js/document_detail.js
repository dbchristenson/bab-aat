// static/js/documents_detail.js
document.addEventListener('DOMContentLoaded', () => {
    const docInput = document.getElementById('docNumberInput');
    const clearBtn = document.getElementById('clearFilters');
    const vesselChecks = document.querySelectorAll('.vessel-checkbox');
    const rows = document.querySelectorAll('table tbody tr');
    const dropdownLabel = document.getElementById('vesselDropdownLabel');

    function applyFilters() {
        // 1) gather checked vessel IDs
        const selectedV = Array.from(vesselChecks)
            .filter(cb => cb.checked)
            .map(cb => cb.value);

        // 2) substring to match
        const term = docInput.value.trim().toLowerCase();

        // 3) show/hide rows
        rows.forEach(row => {
            const vId = row.dataset.vesselId;
            const doc = row.dataset.documentNumber;
            const okV = !selectedV.length || selectedV.includes(vId);
            const okD = !term || doc.includes(term);
            row.style.display = (okV && okD) ? '' : 'none';
        });

        // 4) update dropdown button text
        if (!selectedV.length) {
            dropdownLabel.textContent = 'All Vessels';
        } else {
            const names = Array.from(vesselChecks)
                .filter(cb => cb.checked)
                .map(cb => cb.nextElementSibling.textContent);
            dropdownLabel.textContent = names.join(', ');
        }
    }

    vesselChecks.forEach(cb => cb.addEventListener('change', applyFilters));
    docInput.addEventListener('input', applyFilters);

    clearBtn.addEventListener('click', () => {
        // uncheck all
        vesselChecks.forEach(cb => cb.checked = false);
        // clear search
        docInput.value = '';
        applyFilters();
    });
});
