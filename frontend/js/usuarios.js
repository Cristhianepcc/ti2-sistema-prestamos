// Usuarios y Roles (RF7, próxima entrega). Solo navegación: la pantalla
// todavía no tiene datos propios, ver nota en usuarios.html.

if (!requireAuth()) throw new Error("sin sesión");

renderSidebar("usuarios");
