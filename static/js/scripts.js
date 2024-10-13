document.addEventListener("DOMContentLoaded", function () {
  const institutionModal = document.getElementById("institutionModal");

  if (institutionModal) {
    institutionModal.addEventListener("show.bs.modal", function (event) {
      const button = event.relatedTarget;
      const uniId = button.getAttribute("data-uni-id");
      const searchCriteria = document.querySelector(".search-criteria");
      const selectedCourse = searchCriteria
        ? searchCriteria
            .querySelector(".badge:nth-child(2)")
            ?.textContent.split(": ")[1]
        : null;
      fetchInstitutionDetails(uniId, selectedCourse);
    });
  }

  function fetchInstitutionDetails(uniId, selectedCourse) {
    const searchType = selectedCourse ? "course" : "location";

    fetch(
      `/api/institution/${uniId}?search_type=${searchType}&course=${
        selectedCourse || ""
      }`
    )
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        return response.json();
      })
      .then((uni) => {
        populateModal(uni);
      })
      .catch((error) => {
        console.error("Error fetching institution details:", error);
        const modalBody = institutionModal.querySelector(".modal-body");
        modalBody.innerHTML = `<p class="text-danger">Error loading institution details. Please try again.</p>`;
      });
  }

  function populateModal(uni) {
    const modalTitle = institutionModal.querySelector(".modal-title");
    const institutionName = institutionModal.querySelector("#institutionName");
    const institutionState =
      institutionModal.querySelector("#institutionState");
    const institutionProgramType = institutionModal.querySelector(
      "#institutionProgramType"
    );
    const selectedCourseDetails = institutionModal.querySelector(
      "#selectedCourseDetails"
    );
    const institutionCoursesList = institutionModal.querySelector(
      "#institutionCoursesList"
    );
    const searchCriteriaElement =
      institutionModal.querySelector("#searchCriteria");

    modalTitle.textContent = "Institution Details";
    institutionName.textContent = uni.university_name;
    institutionState.textContent = uni.state;
    institutionProgramType.textContent = uni.program_type;
    searchCriteriaElement.textContent =
      uni.search_type === "course"
        ? `Course: ${uni.selected_course}`
        : `Location: ${uni.state}`;

    // Clear previous content
    selectedCourseDetails.innerHTML = "";
    institutionCoursesList.innerHTML = "";

    if (uni.search_type === "course" && uni.courses.length > 0) {
      const selectedCourse = uni.courses[0];
      selectedCourseDetails.innerHTML = generateCourseHTML(selectedCourse);
    }

    // Add all courses to the list
    uni.courses.forEach((course) => {
      const courseItem = document.createElement("div");
      courseItem.className =
        "d-flex justify-content-between align-items-center mb-2";
      courseItem.innerHTML = `
            <span>${course.course_name}</span>
            <button class="btn btn-sm btn-primary view-course" data-course-id="${course.id}">View Details</button>
        `;
      institutionCoursesList.appendChild(courseItem);
    });

    // Add event listeners to "View Details" buttons
    const viewCourseButtons = institutionModal.querySelectorAll(".view-course");
    viewCourseButtons.forEach((button) => {
      button.addEventListener("click", function () {
        const courseId = this.getAttribute("data-course-id");
        fetchCourseDetails(courseId);
      });
    });
  }

  function generateCourseHTML(course) {
    return `
        <div class="card mb-3">
            <div class="card-body">
                <h5 class="card-title">${course.course_name}</h5>
                <p><strong>UTME Requirements:</strong> ${
                  course.utme_requirements || "N/A"
                }</p>
                <p><strong>UTME Subjects:</strong> ${
                  course.subjects || "N/A"
                }</p>
                <p><strong>Direct Entry Requirements:</strong> ${
                  course.direct_entry_requirements || "N/A"
                }</p>
                <p><strong>Abbreviation:</strong> ${course.abbrv || "N/A"}</p>
            </div>
        </div>
    `;
  }

  function fetchCourseDetails(courseId) {
    fetch(`/course/${courseId}`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        return response.json();
      })
      .then((course) => {
        const selectedCourseDetails = institutionModal.querySelector(
          "#selectedCourseDetails"
        );
        selectedCourseDetails.innerHTML = generateCourseHTML(course);
      })
      .catch((error) => {
        console.error("Error fetching course details:", error);
        const selectedCourseDetails = institutionModal.querySelector(
          "#selectedCourseDetails"
        );
        selectedCourseDetails.innerHTML = `<p class="text-danger">Error loading course details. Please try again.</p>`;
      });
  }

  function populateCourseModal(course) {
    const modalTitle = courseModal.querySelector(".modal-title");
    const courseName = courseModal.querySelector("#courseName");
    const courseUniversity = courseModal.querySelector("#courseUniversity");
    const courseUtmeRequirements = courseModal.querySelector(
      "#courseUtmeRequirements"
    );
    const courseUtmeSubjects = courseModal.querySelector("#courseUtmeSubjects");
    const courseDirectEntryRequirements = courseModal.querySelector(
      "#courseDirectEntryRequirements"
    );
    const courseAbbreviation = courseModal.querySelector("#courseAbbreviation");

    modalTitle.textContent = "Course Details";
    courseName.textContent = course.course_name;
    courseUniversity.textContent = course.university_name;
    courseUtmeRequirements.textContent = course.utme_requirements || "N/A";
    courseUtmeSubjects.textContent = course.subjects || "N/A";
    courseDirectEntryRequirements.textContent =
      course.direct_entry_requirements || "N/A";
    courseAbbreviation.textContent = course.abbrv || "N/A";
  }

  function showCourseModal(courseId) {
    fetch(`/course/${courseId}`)
      .then((response) => {
        if (!response.ok) {
          throw new Error("Network response was not ok");
        }
        return response.json();
      })
      .then((course) => {
        const modalTitle = courseModal.querySelector(".modal-title");
        const courseName = courseModal.querySelector("#courseName");
        const courseUniversity = courseModal.querySelector("#courseUniversity");
        const courseUtmeRequirements = courseModal.querySelector(
          "#courseUtmeRequirements"
        );
        const courseUtmeSubjects = courseModal.querySelector(
          "#courseUtmeSubjects"
        );
        const courseDirectEntryRequirements = courseModal.querySelector(
          "#courseDirectEntryRequirements"
        );
        const courseAbbreviation = courseModal.querySelector(
          "#courseAbbreviation"
        );

        modalTitle.textContent = "Course Details";
        courseName.textContent = course.course_name;
        courseUniversity.textContent = course.university_name;
        courseUtmeRequirements.textContent = course.utme_requirements || "N/A";
        courseUtmeSubjects.textContent = course.subjects || "N/A";
        courseDirectEntryRequirements.textContent =
          course.direct_entry_requirements || "N/A";
        courseAbbreviation.textContent = course.abbrv || "N/A";

        const institutionModalInstance =
          bootstrap.Modal.getInstance(institutionModal);
        if (institutionModalInstance) {
          institutionModalInstance.hide();
        }

        const courseModalInstance = new bootstrap.Modal(courseModal);
        courseModalInstance.show();
      })
      .catch((error) => {
        console.error("Error fetching course details:", error);
        const modalBody = courseModal.querySelector(".modal-body");
        modalBody.innerHTML = `<p class="text-danger">Error loading course details. Please try again.</p>`;
      });
  }

  // Handle voting
  const voteButtons = document.querySelectorAll(".vote-btn");
  voteButtons.forEach((button) => {
    button.addEventListener("click", function () {
      const commentId = this.getAttribute("data-comment-id");
      const voteType = this.getAttribute("data-vote-type");

      fetch("/vote", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
        },
        body: `comment_id=${commentId}&vote_type=${voteType}`,
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.success) {
            const scoreElement = document.querySelector(`#score-${commentId}`);
            scoreElement.textContent = data.new_score;
          }
        })
        .catch((error) => {
          console.error("Error voting:", error);
        });
    });
  });

  // Handle comment deletion
  const deleteButtons = document.querySelectorAll(".delete-comment");
  deleteButtons.forEach((button) => {
    button.addEventListener("click", function (e) {
      e.preventDefault();
      if (confirm("Are you sure you want to delete this comment?")) {
        this.closest("form").submit();
      }
    });
  });

  // Handle password change form submission
  const changePasswordForm = document.getElementById("change-password-form");
  if (changePasswordForm) {
    changePasswordForm.addEventListener("submit", function (e) {
      const newPassword = document.getElementById("new_password").value;
      const confirmPassword = document.getElementById("confirm_password").value;

      if (newPassword !== confirmPassword) {
        e.preventDefault();
        alert("New passwords do not match");
      }
    });
  }
});
