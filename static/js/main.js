// Flash auto-dismiss
document.addEventListener("DOMContentLoaded", () => {
  const flash = document.getElementById("flashMessage");
  if (flash) {
    setTimeout(() => {
      flash.style.transition = "opacity 0.4s";
      flash.style.opacity = "0";
      setTimeout(() => flash.remove(), 400);
    }, 4000);
  }

  // Sidebar mobile toggle
  const toggle = document.getElementById("sidebarToggle");
  const sidebar = document.querySelector(".sidebar");
  if (toggle && sidebar) {
    toggle.addEventListener("click", () => sidebar.classList.toggle("open"));
    document.addEventListener("click", (e) => {
      if (!sidebar.contains(e.target) && !toggle.contains(e.target)) {
        sidebar.classList.remove("open");
      }
    });
  }

  // Confirm destructive actions
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (e) => {
      if (!confirm(form.dataset.confirm)) e.preventDefault();
    });
  });
});
