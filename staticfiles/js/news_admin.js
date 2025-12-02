document.addEventListener('DOMContentLoaded', function () {
    const sectionSelect = document.querySelector('#id_section');
    const subSectionSelect = document.querySelector('#id_sub_section');

    if (sectionSelect) {
        sectionSelect.addEventListener('change', function () {
            const sectionId = this.value;

            fetch(`/ajax/get-subsections/?section_id=${sectionId}`)
                .then(response => response.json())
                .then(data => {
                    subSectionSelect.innerHTML = '<option value="">---------</option>';
                    data.forEach(sub => {
                        const option = document.createElement('option');
                        option.value = sub.id;
                        option.textContent = sub.title;
                        subSectionSelect.appendChild(option);
                    });
                });
        });
    }
});
