import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
  },
});

// Automatically attach the token if it exists in cookies
api.interceptors.request.use((config) => {
  if (typeof document !== 'undefined') {
    const token = document.cookie.split('; ').find(row => row.startsWith('admin_token='))?.split('=')[1];
    if (token) {
      config.headers.Authorization = \Bearer \ + token;
    }
  }
  return config;
});

export default api;
