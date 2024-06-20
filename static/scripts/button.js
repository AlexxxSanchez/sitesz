function toggleContextMenu(event) {
    event.preventDefault();
    var contextMenu = document.getElementById("contextMenu");
    if (contextMenu.style.display === "block") {
      contextMenu.style.display = "none";
    } else {
      contextMenu.style.display = "block";
    }
  }

  var button = document.getElementById("yourButtonId");
    button.addEventListener("click", function(event) {
    var contextMenu = document.getElementById("contextMenu");
    if (!contextMenu.contains(event.target)) {
      contextMenu.style.display = "block";
    }
  });