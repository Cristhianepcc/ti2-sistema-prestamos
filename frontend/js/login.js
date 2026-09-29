document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const errorAlert = document.getElementById('error-alert');

    // Limpiar errores previos
    errorAlert.classList.add('d-none');

    try {
        const response = await fetch('http://localhost:8000/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (!response.ok) {
            // Manejo del ESTADO DE ERROR DE CREDENCIALES
            throw new Error(data.detail || 'Credenciales incorrectas');
        }

        // Obtener el token (sea access_token o token)
        const token = data.access_token || data.token;
        if (token) {
            localStorage.setItem('token', token);
        }

        // Redirigir al catálogo/inicio
        window.location.href = 'index.html';

    } catch (err) {
        // Mostrar mensaje de error en la interfaz
        errorAlert.textContent = err.message;
        errorAlert.classList.remove('d-none');
    }
});