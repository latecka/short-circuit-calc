import axios from 'axios';

// Use relative URL when running with vite proxy, absolute URL otherwise
const API_URL = import.meta.env.VITE_API_URL || '';

const client = axios.create({
  baseURL: `${API_URL}/api/v1`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 responses
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: async (email, password) => {
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);
    const response = await client.post('/auth/login', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  },
  register: async (email, password, fullName) => {
    const response = await client.post('/auth/register', {
      email,
      password,
      full_name: fullName,
    });
    return response.data;
  },
  me: async () => {
    const response = await client.get('/auth/me');
    return response.data;
  },
};

// Projects API
export const projectsApi = {
  list: async (page = 1, pageSize = 20) => {
    const response = await client.get('/projects', {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },
  get: async (id) => {
    const response = await client.get(`/projects/${id}`);
    return response.data;
  },
  create: async (name, description) => {
    const response = await client.post('/projects', { name, description });
    return response.data;
  },
  update: async (id, data) => {
    const response = await client.patch(`/projects/${id}`, data);
    return response.data;
  },
  delete: async (id) => {
    await client.delete(`/projects/${id}`);
  },
  // Versions
  listVersions: async (projectId) => {
    const response = await client.get(`/projects/${projectId}/versions`);
    return response.data;
  },
  getVersion: async (projectId, versionId) => {
    const response = await client.get(`/projects/${projectId}/versions/${versionId}`);
    return response.data;
  },
  createVersion: async (projectId, elements, comment) => {
    const response = await client.post(`/projects/${projectId}/versions`, {
      elements,
      comment,
    });
    return response.data;
  },
};

// Calculations API
export const calculationsApi = {
  run: async (networkVersionId, mode, faultTypes, faultBuses) => {
    const response = await client.post('/calculations', {
      network_version_id: networkVersionId,
      calculation_mode: mode,
      fault_types: faultTypes,
      fault_buses: faultBuses,
    });
    return response.data;
  },
  list: async (projectId, page = 1, pageSize = 20) => {
    const response = await client.get('/calculations', {
      params: { project_id: projectId, page, page_size: pageSize },
    });
    return response.data;
  },
  get: async (id) => {
    const response = await client.get(`/calculations/${id}`);
    return response.data;
  },
  delete: async (id) => {
    await client.delete(`/calculations/${id}`);
  },
};

export default client;
