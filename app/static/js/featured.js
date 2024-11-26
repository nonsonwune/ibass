// Featured institutions functionality
function initFeaturedInstitutions() {
    const container = document.getElementById('featuredInstitutions');
    const loadingPlaceholder = document.getElementById('loadingPlaceholder');

    function createInstitutionCard(institution) {
        return `
            <div class="col-md-6 col-lg-4" data-aos="fade-up" data-aos-delay="100">
                <div class="institution-card h-100 bg-white rounded-4 shadow-sm p-4">
                    <div class="d-flex align-items-center mb-3">
                        <div class="institution-icon me-3">
                            <i class="fas fa-university text-primary fa-2x"></i>
                        </div>
                        <h3 class="h5 mb-0">${institution.name}</h3>
                    </div>
                    <div class="institution-details">
                        <p class="mb-2">
                            <i class="fas fa-map-marker-alt text-muted me-2"></i>
                            ${institution.state}
                        </p>
                        <p class="mb-2">
                            <i class="fas fa-graduation-cap text-muted me-2"></i>
                            ${institution.type}
                        </p>
                        <p class="mb-0">
                            <i class="fas fa-book text-muted me-2"></i>
                            ${institution.courses_count} Courses
                        </p>
                    </div>
                    <a href="/institution/${institution.id}" 
                       class="btn btn-outline-primary mt-3">
                        Learn More
                    </a>
                </div>
            </div>
        `;
    }

    // Fetch and render featured institutions
    fetch('/api/featured-institutions')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                loadingPlaceholder.style.display = 'none';
                const institutionsHtml = data.institutions
                    .map(createInstitutionCard)
                    .join('');
                container.innerHTML = institutionsHtml;
                // Reinitialize AOS for new elements
                AOS.refresh();
            } else {
                throw new Error(data.message);
            }
        })
        .catch(error => {
            loadingPlaceholder.innerHTML = `
                <div class="alert alert-danger" role="alert">
                    Failed to load featured institutions. Please try again later.
                </div>
            `;
            console.error('Error:', error);
        });
}

// Initialize when document is ready
document.addEventListener('DOMContentLoaded', initFeaturedInstitutions);
