// app/static/js/scripts.js
$(function() {
  // 1) Toggle de colapso/expansión del sidebar
  $('#menu-toggle').on('click', function() {
    $('body').toggleClass('mini-navbar');
  });

  // 2) Toggle manual de submenús
  $('#side-menu li > a').on('click', function(e) {
    var $submenu = $(this).next('ul.nav-second-level');
    if ($submenu.length) {
      e.preventDefault();
      // Desplegar / ocultar
      $submenu.slideToggle(200);
      // Marca la sección abierta (puedes usarla para rotar la flecha si quieres)
      $(this).parent().toggleClass('open');
    }
  });
});
