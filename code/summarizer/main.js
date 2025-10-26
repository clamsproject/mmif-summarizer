
// https://www.w3schools.com/howto/howto_js_toggle_hide_show.asp

function toggle(id) {
  var x = document.getElementById(id);
  if (x.style.display === "none") {
    x.style.display = "block";
  } else {
    x.style.display = "none";
  }
}
