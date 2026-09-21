// Helpers de render (issue #5) — para pintar estados y listas sin repetir código.

function showLoading(el) {
  el.innerHTML = `<div class="text-center text-muted py-4">
    <div class="spinner-border" role="status"></div>
    <div class="mt-2">Cargando…</div></div>`;
}

function showError(el, msg) {
  el.innerHTML = `<div class="alert alert-danger" role="alert">${msg}</div>`;
}

function showEmpty(el, msg = "No hay datos.") {
  el.innerHTML = `<div class="text-center text-muted py-4">${msg}</div>`;
}

// Renderiza una lista usando una función que devuelve el HTML de cada item.
function renderList(el, items, itemHtml, emptyMsg) {
  if (!items || items.length === 0) return showEmpty(el, emptyMsg);
  el.innerHTML = items.map(itemHtml).join("");
}
