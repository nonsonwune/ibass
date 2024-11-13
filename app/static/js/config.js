const AppConfig = {
    // Animation durations
    ANIMATION_DURATION: 300,
    DEBOUNCE_DELAY: 300,
    
    // Search settings
    MAX_SUGGESTIONS: 10,
    MIN_SEARCH_LENGTH: 2,
    
    // API endpoints
    ENDPOINTS: {
        LOCATIONS: '/api/locations',
        PROGRAMME_TYPES: '/api/programme_types',
        PROGRAMME_TYPES_BY_STATE: (state) => `/api/programme-types/${encodeURIComponent(state)}`,
        COURSES: '/api/courses',
        INSTITUTION: (id) => `/api/institution/${id}`,
        BOOKMARKS: '/api/user_bookmarks'
    },
    
    // CSS classes
    CLASSES: {
        ACTIVE: 'active',
        SELECTED: 'selected',
        SHOW: 'show',
        LOADING: 'loading'
    }
};

// Export for use in other files
window.AppConfig = AppConfig; 