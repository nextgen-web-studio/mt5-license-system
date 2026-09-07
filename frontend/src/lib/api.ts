import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache, no-store, must-revalidate',
    'Pragma': 'no-cache',
    'Expires': '0',
  },
});

// Automatically attach the token if it exists in cookies
api.interceptors.request.use((config) => {
  if (typeof document !== 'undefined') {
    const token = document.cookie.split('; ').find(row => row.startsWith('admin_token='))?.split('=')[1];
    if (token) {
      config.headers.Authorization = 'Bearer ' + token;
    }
  }
  
  // Aggressive cache busting for GET requests
  if (config.method?.toLowerCase() === 'get') {
    config.params = config.params || {};
    config.params._t = Date.now();
  }
  
  return config;
});

export default api;
