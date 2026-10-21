const loginForm = document.getElementById('login-form');
const errorAlert = document.getElementById('error-alert');
const btnEntrar = loginForm.querySelector('button[type="submit"]');

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