// app/static/js/search_results.js

document.addEventListener("DOMContentLoaded", function () {
  const loadingOverlay = document.getElementById("loadingOverlay");
  const filterForm = document.getElementById("filterForm");
  const mainSearchForm = document.getElementById("mainSearchForm");
  const resultTabs = document.getElementById('resultTabs');
  let currentRequest = null;

  // Initialize tooltips
  initializeTooltips();

  // Handle main search form submission
  if (mainSearchForm) {
      mainSearchForm.addEventListener("submit", function (e) {
          e.preventDefault();
          performSearch();
      });
  }

  // Handle filter form submission if it exists
  if (filterForm) {
      filterForm.addEventListener("submit", function (e) {
          e.preventDefault();
          performSearch();
      });
  }

  async function performSearch() {
      try {
          showLoadingOverlay(true);

          // Cancel any pending requests
          if (currentRequest) {
              currentRequest.abort();
          }

          // Build search parameters with better error handling
          const searchParams = new URLSearchParams();
          
          // Get query from either the main search form or filter form
          let queryInput = mainSearchForm?.querySelector('input[name="q"]') || 
                          filterForm?.querySelector('input[name="q"]');
                          
          if (!queryInput) {
              console.error('Search input not found');
              throw new Error('Search configuration error');
          }

          const queryValue = queryInput.value.trim();
          if (!queryValue) {
              throw new Error('Please enter a search term');
          }

          searchParams.set('q', queryValue);
          
          // Safely add filter parameters if filter form exists
          if (filterForm) {
              const filterData = new FormData(filterForm);
              filterData.forEach((value, key) => {
                  if (value && key !== 'q') { // Avoid duplicating query parameter
                      searchParams.append(key, value);
                  }
              });
          }

          // Create AbortController for this request
          const controller = new AbortController();
          currentRequest = controller;

          // Log the request parameters for debugging
          console.debug('Search parameters:', searchParams.toString());

          // Perform API call with improved error handling
          const response = await fetch(`/api/search?${searchParams.toString()}`, {
              signal: controller.signal,
              headers: {
                  'Accept': 'application/json',
                  'X-Requested-With': 'XMLHttpRequest'
              }
          });

          console.debug('Response status:', response.status);

          // Handle non-OK responses
          if (!response.ok) {
              const errorData = await response.json();
              throw new Error(errorData.error || 'Search failed');
          }

          const data = await response.json();
          console.debug('Search response:', data);

          // Validate response data
          if (!data.universities || !data.courses) {
              throw new Error('Invalid response format');
          }

          // Update URL without reload
          window.history.pushState({}, '', `${window.location.pathname}?${searchParams.toString()}`);

          // Update results
          updateResults(data);

      } catch (error) {
          if (error.name === 'AbortError') {
              console.debug('Request was cancelled');
              return;
          }
          handleSearchError(error);
      } finally {
          showLoadingOverlay(false);
          currentRequest = null;
      }
  }

  function updateResults(data) {
      try {
          const { universities, courses } = data;

          // Clear existing error messages
          clearErrors();

          // Update counts
          updateResultCounts(data);

          // Update universities tab
          const universitiesContainer = document.getElementById('institutions');
          if (universitiesContainer) {
              universitiesContainer.innerHTML = renderUniversities(universities.items);
          }

          // Update courses tab
          const coursesContainer = document.getElementById('courses');
          if (coursesContainer) {
              coursesContainer.innerHTML = renderCourses(courses.items);
          }

          // Initialize course modals
          initializeCourseModals();

      } catch (error) {
          console.error('Error updating results:', error);
          showError('Error displaying results. Please try again.');
      }
  }

  function renderUniversities(universities) {
      if (!Array.isArray(universities) || universities.length === 0) {
          return renderNoResults('universities');
      }

      return `
          <div class="row g-4">
              ${universities.map(uni => `
                  <div class="col-md-6">
                      <div class="result-card">
                          <div class="card-body">
                              <div class="d-flex justify-content-between align-items-start mb-3">
                                  <h5 class="card-title mb-0">${escapeHtml(uni.university_name)}</h5>
                                  <span class="institution-type type-${(uni.program_type || '').toLowerCase()}">${escapeHtml(uni.program_type || '')}</span>
                              </div>
                              <p class="card-text">
                                  <i class="fas fa-map-marker-alt me-2 text-primary"></i>${escapeHtml(uni.location || 'Location not available')}
                              </p>
                              <div class="mt-3">
                                  <a href="/university/institution/${uni.id}" class="btn btn-primary w-100">
                                      <i class="fas fa-info-circle me-2"></i>View Details
                                  </a>
                              </div>
                          </div>
                      </div>
                  </div>
              `).join('')}
          </div>`;
  }

  function renderCourses(courses) {
      if (!Array.isArray(courses) || courses.length === 0) {
          return renderNoResults('courses');
      }

      return `
          <div class="row g-4">
              ${courses.map(course => `
                  <div class="col-md-6">
                      <div class="result-card">
                          <div class="card-body">
                              <h5 class="card-title mb-3">${escapeHtml(course.course_name)}</h5>
                              <p class="card-text mb-2">
                                  <i class="fas fa-university me-2 text-primary"></i>${escapeHtml(course.state || '')}
                              </p>
                              <p class="card-text mb-3">
                                  <i class="fas fa-graduation-cap me-2 text-success"></i>${escapeHtml(course.program_type || '')}
                              </p>
                              <button class="btn btn-primary w-100" data-bs-toggle="modal" data-bs-target="#courseModal${course.id}">
                                  <i class="fas fa-info-circle me-2"></i>View Requirements
                              </button>
                          </div>
                      </div>
                  </div>

                  <!-- Course Modal -->
                  <div class="modal fade course-modal" id="courseModal${course.id}" tabindex="-1" data-course-id="${course.id}">
                      <div class="modal-dialog modal-lg">
                          <div class="modal-content">
                              <div class="modal-header">
                                  <h5 class="modal-title">${escapeHtml(course.course_name)}</h5>
                                  <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                              </div>
                              <div class="modal-body">
                                  <div class="requirement-section">
                                      ${course.utme_requirements ? `
                                          <div class="mb-3">
                                              <h6 class="text-primary">UTME Requirements:</h6>
                                              <p>${escapeHtml(course.utme_requirements)}</p>
                                          </div>
                                      ` : ''}
                                      ${course.direct_entry_requirements ? `
                                          <div class="mb-3">
                                              <h6 class="text-primary">Direct Entry Requirements:</h6>
                                              <p>${escapeHtml(course.direct_entry_requirements)}</p>
                                          </div>
                                      ` : ''}
                                      ${course.subjects ? `
                                          <div class="mb-3">
                                              <h6 class="text-primary">Required Subjects:</h6>
                                              <p>${escapeHtml(course.subjects)}</p>
                                          </div>
                                      ` : ''}
                                  </div>
                              </div>
                          </div>
                      </div>
                  </div>
              `).join('')}
          </div>`;
  }

  function renderNoResults(type) {
      return `
          <div class="no-results">
              <i class="fas fa-${type === 'universities' ? 'university' : 'book'} mb-3"></i>
              <h3>No ${type === 'universities' ? 'Institutions' : 'Courses'} Found</h3>
              <p class="text-muted">Try adjusting your search criteria or filters</p>
          </div>`;
  }

  function updateResultCounts(data) {
      try {
          const { universities, courses, metadata } = data;
          const query = searchForm.querySelector('input[name="q"]').value.trim();

          // Update total results count
          const resultsCount = document.querySelector('.results-count');
          if (resultsCount) {
              const total = metadata ? metadata.total_universities + metadata.total_courses :
                  universities.total + courses.total;
              resultsCount.textContent = `Found ${total} results for "${escapeHtml(query)}"`;
          }

          // Update tab counts
          const universitiesTab = document.querySelector('#institutions-tab');
          if (universitiesTab) {
              const uniTotal = metadata ? metadata.total_universities : universities.total;
              universitiesTab.innerHTML = `<i class="fas fa-university me-2"></i>Institutions (${uniTotal})`;
          }

          const coursesTab = document.querySelector('#courses-tab');
          if (coursesTab) {
              const courseTotal = metadata ? metadata.total_courses : courses.total;
              coursesTab.innerHTML = `<i class="fas fa-book me-2"></i>Courses (${courseTotal})`;
          }
      } catch (error) {
          console.error('Error updating result counts:', error);
      }
  }

  function showLoadingOverlay(show) {
      if (loadingOverlay) {
          loadingOverlay.style.display = show ? "flex" : "none";
          loadingOverlay.setAttribute('aria-busy', show ? 'true' : 'false');
      }
  }

  function showError(message) {
      // Remove any existing error alerts
      clearErrors();

      const alert = document.createElement('div');
      alert.className = 'alert alert-danger alert-dismissible fade show';
      alert.setAttribute('role', 'alert');
      alert.innerHTML = `
          <div class="d-flex align-items-center">
              <i class="fas fa-exclamation-circle me-2"></i>
              <div>${escapeHtml(message)}</div>
              <button type="button" class="btn-close ms-auto" data-bs-dismiss="alert" aria-label="Close"></button>
          </div>`;
      
      // Find the best place to show the error
      const container = document.querySelector('.tab-content') || 
                       document.querySelector('.container') ||
                       document.body;
      
      if (container) {
          container.insertBefore(alert, container.firstChild);
          
          // Scroll to error message
          alert.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
  }

  function clearErrors() {
      const existingAlerts = document.querySelectorAll('.alert-danger');
      existingAlerts.forEach(alert => alert.remove());
  }

  function handleSearchError(error) {
      console.error('Search error:', error);
      showError(error.message || 'An unexpected error occurred. Please try again.');
  }

  // Utility function to escape HTML and prevent XSS
  function escapeHtml(unsafe) {
      if (unsafe == null) return '';
      return unsafe
          .toString()
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#039;");
  }

  // Initialize tooltips function
  function initializeTooltips() {
      const tooltipTriggerList = [].slice.call(
          document.querySelectorAll('[data-bs-toggle="tooltip"]')
      );
      tooltipTriggerList.forEach(function (tooltipTriggerEl) {
          new bootstrap.Tooltip(tooltipTriggerEl);
      });
  }

  // Restore filter state from URL parameters
  restoreFilterState();

  // Course tab functionality
  function initializeCourseTab() {
      const courseSearchInput = document.getElementById('courseSearchInput');
      const courseCards = document.querySelectorAll('.course-result-card');
      const compareBtn = document.getElementById('compareCoursesBtn');
      const shareButtons = document.querySelectorAll('.share-course');

      // Course search
      if (courseSearchInput) {
          courseSearchInput.addEventListener('input', debounce(function(e) {
              const searchTerm = e.target.value.toLowerCase();
              filterCourses(searchTerm);
          }, 300));
      }

      // Course comparison
      if (compareBtn) {
          compareBtn.addEventListener('click', function() {
              const selectedCourses = document.querySelectorAll('.course-compare:checked');
              if (selectedCourses.length < 2) {
                  showNotification('Please select at least 2 courses to compare', 'warning');
                  return;
              }
              // Implement comparison logic
              compareCourses(Array.from(selectedCourses).map(cb => cb.value));
          });
      }

      // Share functionality
      shareButtons.forEach(btn => {
          btn.addEventListener('click', async function() {
              const courseId = this.dataset.courseId;
              const courseTitle = this.closest('.card').querySelector('.card-title').textContent;
              try {
                  await shareCourse(courseId, courseTitle);
              } catch (error) {
                  showNotification('Failed to share course', 'error');
              }
          });
      });
  }

  function filterCourses(searchTerm) {
      const courseCards = document.querySelectorAll('.course-result-card');
      courseCards.forEach(card => {
          const courseName = card.querySelector('.card-title').textContent.toLowerCase();
          const universities = Array.from(card.querySelectorAll('.university-item'))
              .map(item => item.textContent.toLowerCase());
          
          const matches = courseName.includes(searchTerm) || 
                         universities.some(uni => uni.includes(searchTerm));
          
          card.closest('.col-md-6').style.display = matches ? 'block' : 'none';
      });
  }

  async function shareCourse(courseId, courseTitle) {
      const shareData = {
          title: courseTitle,
          text: `Check out this course: ${courseTitle}`,
          url: `${window.location.origin}/course/${courseId}`
      };

      try {
          if (navigator.share) {
              await navigator.share(shareData);
          } else {
              await navigator.clipboard.writeText(shareData.url);
              showNotification('Link copied to clipboard!', 'success');
          }
      } catch (error) {
          throw error;
      }
  }

  // Initialize when DOM is loaded
  document.addEventListener('DOMContentLoaded', function() {
      initializeCourseTab();
  });
});

function restoreFilterState() {
  if (!filterForm) return;

  const urlParams = new URLSearchParams(window.location.search);
  
  // Restore state filter
  const stateSelect = filterForm.querySelector('select[name="state"]');
  const state = urlParams.get('state');
  if (stateSelect && state) {
      stateSelect.value = state;
  }

  // Restore program type filter
  const programTypes = urlParams.getAll('program_type');
  programTypes.forEach(type => {
      const checkbox = filterForm.querySelector(`input[name="program_type"][value="${type}"]`);
      if (checkbox) {
          checkbox.checked = true;
      }
  });
}