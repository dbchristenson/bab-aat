document.addEventListener('DOMContentLoaded', function () {
    // Ensure you are selecting the correct file input and file-name-display element
    const fileInput = document.getElementById('id_file');
    const fileNameDisplay = document.querySelector('.file-name-display');

    if (fileInput) {
        fileInput.addEventListener('change', function () {
            if (this.files.length > 0) {
                const fileName = this.files.length === 1
                    ? this.files[0].name
                    : `${this.files.length} files selected`;
                // Update only the dedicated span element
                fileNameDisplay.textContent = fileName;
            }
        });
    }

    // Form validation remains unchanged
    const form = document.querySelector('.needs-validation');
    if (form) {
        form.addEventListener('submit', function (event) {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    }
});
