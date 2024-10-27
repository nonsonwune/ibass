// app/static/js/bookmarks.js

function initializeBookmarkSystem() {
  console.log("Initializing bookmark system");
  const bookmarkButtons = document.querySelectorAll(".bookmark-btn");
  bookmarkButtons.forEach((button) => {
    button.addEventListener("click", handleBookmarkClick);
  });
}

async function handleBookmarkClick(event) {
  event.preventDefault();

  if (!window.isAuthenticated) {
    window.location.href = "/auth/login";
    return;
  }

  const button = this;
  const uniId = button.getAttribute("data-uni-id");
  const isBookmarked = button.classList.contains("btn-secondary");

  try {
    const url = isBookmarked
      ? `/api/remove_bookmark/${uniId}`
      : "/api/bookmark";
    const method = "POST";
    const body = isBookmarked ? null : JSON.stringify({ university_id: uniId });

    const response = await fetch(url, {
      method,
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": window.csrfToken,
      },
      body,
    });

    if (response.redirected || response.status === 401) {
      throw new Error("Please sign in to bookmark institutions.");
    }

    if (!response.ok) {
      throw new Error("An unexpected error occurred.");
    }

    const data = await response.json();

    if (data.success) {
      updateBookmarkButtonUI(button, !isBookmarked);
      showToast(
        isBookmarked ? "Bookmark removed" : "Institution bookmarked",
        "success"
      );
    } else {
      throw new Error(data.message || "Bookmarking failed");
    }
  } catch (error) {
    console.error("Bookmark error:", error);
    showToast(error.message || "Error managing bookmark", "danger");
  }
}

function fetchUserBookmarks() {
  fetch("/api/user_bookmarks", {
    credentials: "same-origin",
    headers: {
      "X-CSRFToken": window.csrfToken,
      Accept: "application/json",
    },
  })
    .then((response) => {
      if (response.redirected || response.status === 401) {
        console.log("User not authenticated");
        return null;
      }
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      return response.json();
    })
    .then((data) => {
      if (data) {
        applyUserBookmarks(data);
      }
    })
    .catch((error) => {
      console.error("Error fetching user bookmarks:", error);
    });
}

function applyUserBookmarks(bookmarks) {
  document.querySelectorAll(".bookmark-btn").forEach((button) => {
    const uniId = button.getAttribute("data-uni-id");
    updateBookmarkButtonUI(button, bookmarks.includes(parseInt(uniId)));
  });
}

function updateBookmarkButtonUI(button, isBookmarked) {
  const bookmarkText = button.querySelector(".bookmark-text");
  const icon = button.querySelector("i");

  if (isBookmarked) {
    button.classList.add("btn-secondary");
    button.classList.remove("btn-outline-secondary");
    bookmarkText.textContent = "Bookmarked";
    icon.classList.remove("fa-bookmark");
    icon.classList.add("fa-check");
  } else {
    button.classList.remove("btn-secondary");
    button.classList.add("btn-outline-secondary");
    bookmarkText.textContent = "Bookmark";
    icon.classList.add("fa-bookmark");
    icon.classList.remove("fa-check");
  }
}

// Expose functions globally
window.initializeBookmarkSystem = initializeBookmarkSystem;
window.handleBookmarkClick = handleBookmarkClick;
window.fetchUserBookmarks = fetchUserBookmarks;
window.applyUserBookmarks = applyUserBookmarks;
window.updateBookmarkButtonUI = updateBookmarkButtonUI;
