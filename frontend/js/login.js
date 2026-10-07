document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const errorAlert = document.getElementById('error-alert');

    // Ocultar alerta de errores previas
    errorAlert.classList.add('d-none');

    try {
        // 1. POST /auth/login (o /api/auth/login según la API de FastAPI)
        const response = await fetch('http://localhost:8000/api/auth/login', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json' 
            },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Credenciales inválidas');
        }

        // 2. Guardar token JWT en localStorage
        const token = data.access_token || data.token;
        localStorage.setItem('token', token);

        // 3. Redirección al catálogo (index.html)
        window.location.href = 'index.html';

    } catch (err) {
        // Mostrar error en pantalla
        errorAlert.textContent = err.message;
        errorAlert.classList.remove('d-none');
    }
});