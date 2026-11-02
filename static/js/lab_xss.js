(function () {
  var salida = document.getElementById("dom-out");
  var valor = "";
  try {
    valor = decodeURIComponent(window.location.hash.slice(1));
  } catch (e) {
    valor = "";
  }
  if (valor) {
    salida.textContent = "Hola, " + valor;
  }
})();
