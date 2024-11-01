// app/static/js/utils.js

// Don't redefine debounce if it exists in window
if (!window.debounce) {
  function debounce(func, wait) {
      let timeout;
      return function executedFunction(...args) {
          const later = () => {
              clearTimeout(timeout);
              func(...args);
          };
          clearTimeout(timeout);
          timeout = setTimeout(later, wait);
      };
  }
  window.debounce = debounce;
}

// Icon utilities as a separate namespace to avoid conflicts
window.IconUtils = {
  getInstitutionIcon(type) {
      const typeUpper = type.toUpperCase();
      const iconMap = {
          'UNIVERSITIES': 'fa-university',
          'POLYTECHNIC': 'fa-industry',
          'COLLEGES': 'fa-school',
          'EDUCATION_TECHNICAL': 'fa-cog',
          'EDUCATION': 'fa-chalkboard-teacher',
          'HEALTH': 'fa-hospital',
          'MEDICAL': 'fa-hospital',
          'TECHNOLOGY': 'fa-microchip',
          'AGRICULTURE': 'fa-leaf',
          'DISTANCE': 'fa-laptop',
          'E_LEARNING': 'fa-laptop'
      };

      for (const [key, value] of Object.entries(iconMap)) {
          if (typeUpper.includes(key)) {
              return value;
          }
      }

      return 'fa-graduation-cap';
  },

  createIcon(iconClass, options = {}) {
      const {
          size = 'normal',
          color = null,
          spin = false,
          pulse = false,
          fixedWidth = false
      } = options;

      const icon = document.createElement('i');
      icon.className = `fas ${iconClass}`;

      if (size !== 'normal') icon.classList.add(`fa-${size}`);
      if (spin) icon.classList.add('fa-spin');
      if (pulse) icon.classList.add('fa-pulse');
      if (fixedWidth) icon.classList.add('fa-fw');
      if (color) icon.style.color = color;

      if (window.iconFallbacks && window.iconFallbacks[iconClass]) {
          icon.setAttribute('data-fallback', window.iconFallbacks[iconClass]);
      }

      return icon;
  },

  setButtonLoading(button, loading) {
      const originalContent = button.dataset.originalContent || button.innerHTML;
      
      if (loading) {
          button.dataset.originalContent = originalContent;
          button.innerHTML = `<i class="fas fa-spinner fa-spin"></i> Loading...`;
          button.disabled = true;
      } else {
          button.innerHTML = originalContent;
          button.disabled = false;
      }
  }
};

// Add this to your existing utils.js
$(document).ready(function() {
    // Handle search form submission
    $('.nav-search').on('submit', function(e) {
        const searchInput = $(this).find('.search-input');
        
        // If search input is empty, prevent submission and focus the input
        if (!searchInput.val().trim()) {
            e.preventDefault();
            searchInput.focus();
        }
    });
});