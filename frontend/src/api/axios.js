import axios from 'axios';

const BASE_URL = process.env.REACT_APP_BACKEND_URL || '';

const apiClient = axios.create({
  baseURL: `${BASE_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to attach user_email from localStorage
apiClient.interceptors.request.use(
  (config) => {
    const userEmail = localStorage.getItem('user_email');
    if (userEmail) {
      config.headers['X-User-Email'] = userEmail;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message = error.response?.data?.detail || error.message || 'An error occurred';
    console.error('API Error:', message);
    return Promise.reject(error);
  }
);

export default apiClient;
