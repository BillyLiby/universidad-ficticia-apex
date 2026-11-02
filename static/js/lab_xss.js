// VULNERABLE (XSS basado en DOM): el fragmento de la URL se inserta como HTML.
(function () {
  var salida = document.getElementById("dom-out");
  var valor = decodeURIComponent(window.location.hash.slice(1));
  if (valor) {
    salida.innerHTML = "Hola, " + valor;
  }
})();
