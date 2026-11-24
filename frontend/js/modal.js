// Modal genérico y reutilizable: reemplaza los formularios que se abrían
// expandidos dentro de la tarjeta (Reservar/Solicitar en el catálogo) por un
// diálogo centrado. No depende de otro script; se puede usar en cualquier
// página con `openModal(titulo, bodyHTML)` / `closeModal()` / `modalBody()`.

(function () {
  let overlay;

  function crearOverlay() {
    const el = document.createElement("div");
    el.className = "modal-overlay";
    el.hidden = true;
    el.innerHTML = `
      <div class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-titulo">
        <div class="modal-head">
          <h3 id="modal-titulo"></h3>
          <button type="button" class="modal-cerrar" aria-label="Cerrar">&times;</button>
        </div>
        <div class="modal-body"></div>
      </div>`;
    document.body.appendChild(el);

    el.addEventListener("click", (evento) => {
      if (evento.target === el) closeModal();
    });
    el.querySelector(".modal-cerrar").addEventListener("click", closeModal);
    document.addEventListener("keydown", (evento) => {
      if (evento.key === "Escape" && !el.hidden) closeModal();
    });

    return el;
  }

  function asegurarOverlay() {
    if (!overlay) overlay = crearOverlay();
    return overlay;
  }

  window.openModal = function (titulo, bodyHTML, opciones = {}) {
    const el = asegurarOverlay();
    // `opciones.ancho`: para contenido que no es un formulario (ej. una tabla
    // de varias columnas), que no entra en el max-width pensado para forms.
    // Se resetea la clase en cada apertura: si no, un modal ancho dejaba
    // "pegada" esa clase en la siguiente apertura normal (el overlay es un
    // singleton que se reusa entre llamadas).
    el.querySelector(".modal").className = opciones.ancho ? "modal modal-ancho" : "modal";
    el.querySelector("#modal-titulo").textContent = titulo;
    el.querySelector(".modal-body").innerHTML = bodyHTML;
    el.hidden = false;
    const primerCampo = el.querySelector(".modal-body input, .modal-body textarea, .modal-body select");
    if (primerCampo) primerCampo.focus();
  };

  window.closeModal = function () {
    if (!overlay) return;
    overlay.hidden = true;
    overlay.querySelector(".modal-body").innerHTML = "";
  };

  window.modalBody = function () {
    return asegurarOverlay().querySelector(".modal-body");
  };
})();
