function getQueryParams() {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.toString();
}

// Close dialog
document.body.addEventListener("htmx:afterRequest", function (evt) {
  const trigger = evt.detail.xhr.getResponseHeader("HX-Trigger");
  const status = evt.detail.xhr.status;
  const responseText = evt.detail.xhr.responseText;

  if (
    trigger === "form_invalid" ||
    status === 400 ||
    responseText.includes("text-danger")
  )
    return;

  const modalElement = evt.detail.target.closest(".modal");
  // Close the Bootstrap modal
  if (modalElement) {
    const modal = bootstrap.Modal.getInstance(modalElement);
    if (modal) modal.hide();
  }
});

// Function to generate a random RGB color
function getRandomColor() {
  var r = Math.floor(Math.random() * 256); // Random red value (0-255)
  var g = Math.floor(Math.random() * 256); // Random green value (0-255)
  var b = Math.floor(Math.random() * 256); // Random blue value (0-255)
  return `rgb(${r}, ${g}, ${b})`;
}

// Generate a random color palette with 25 colors
function generateRandomPalette() {
  var colors = [];
  for (var i = 0; i < 25; i++) {
    colors.push(getRandomColor());
  }
  return colors;
}

// Apply opacity to the generated random colors
function applyOpacityToPalette(palette, opacity) {
  return palette.map((color) => chroma(color).alpha(opacity).css());
}

// Animate numbers
function animateNumbers(element, value, prefix = "", suffix = "") {
  // Ensure the element starts with a counter property initialized to 0
  $(element)
    .prop("counter", 0)
    .animate(
      { counter: value },
      {
        duration: 1000, // Duration for the animation
        easing: "swing", // Easing effect
        step: function (now) {
          // Update the number displayed during the animation
          $(element).text(
            `${prefix}${Math.floor(now).toLocaleString()}${suffix}`,
          );
        },
        complete: function () {
          // Ensure the final value is set correctly after animation
          $(element).text(`${prefix}${value.toLocaleString()}${suffix}`);
        },
      },
    );
}
