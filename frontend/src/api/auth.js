const BASE_URL = process.env.REACT_APP_BACKEND_URL || 'http://localhost:8000';

export const authApi = {
  initiateGoogleAuth: () => {
    window.location.href = `${BASE_URL}/api/auth/google`;
  },
  getCurrentUser: () => localStorage.getItem('user_email'),
  setUserEmail: (email) => localStorage.setItem('user_email', email),
  logout: () => localStorage.removeItem('user_email'),
  isAuthenticated: () => !!localStorage.getItem('user_email'),
};
