// static/js/configSelect.js
document.addEventListener('DOMContentLoaded', () => {
    const radios = document.querySelectorAll('.config-select');
    const label = document.getElementById('configDropdownLabel');

    radios.forEach(radio => {
        radio.addEventListener('change', e => {
            const val = e.target.value;
            // 1) update button text
            label.textContent = val;
            // 2) reload with ?config=val (preserving other params)
            const url = new URL(window.location);
            url.searchParams.set('config', val);
            window.location = url.toString();
        });
    });
});
