const loginForm = document.getElementById('login-form');
const errorAlert = document.getElementById('error-alert');
const btnEntrar = loginForm.querySelector('button[type="submit"]');

// Contraseña compartida por todos los usuarios de prueba (ver backend/app/seeds.py).
const PASSWORD_DEMO = 'prestamos123';

const quickChips = document.getElementById('quick-login-chips');
if (quickChips) {
    quickChips.addEventListener('click', (e) => {
        const btn = e.target.closest('.chip-opt');
        if (!btn) return;
        document.getElementById('email').value = btn.dataset.email;
        document.getElementById('password').value = PASSWORD_DEMO;
        showFormError(errorAlert, null);
    });
}

loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    showFormError(errorAlert, null);
    setBusy(btnEntrar, true, 'Entrando…');

    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    try {
        await api.login(email, password);
        window.location.href = 'inicio.html';
    } catch (err) {
        showFormError(errorAlert, err.message);
    } finally {
        setBusy(btnEntrar, false);
    }
});