// API URL
const API_URL = '/api';

// Load and display users
async function loadUsers() {
    try {
        const response = await fetch(`${API_URL}/users`);
        const users = await response.json();
        
        const usersList = document.getElementById('usersList');
        if (usersList) {
            usersList.innerHTML = users.map(user => `
                <div class="user-card">
                    <h4>${user.username}</h4>
                    <p>${user.email}</p>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading users:', error);
    }
}

// Logout function
function logout() {
    fetch(`${API_URL}/logout`, {
        method: 'POST'
    })
    .then(response => {
        if (response.ok) {
            window.location.href = '/';
        }
    })
    .catch(error => {
        console.error('Error logging out:', error);
    });
}

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    // Load users if the users list element exists
    const usersList = document.getElementById('usersList');
    if (usersList) {
        loadUsers();
    }
}); 