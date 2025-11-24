import axios from 'axios';
import { reactive } from 'vue';

// --- Auth State ---
export const authState = reactive({
  username: localStorage.getItem('mio_username') || '',
  tenantId: localStorage.getItem('mio_tenant_id') || 'default_tenant',
  isLoggedIn: !!localStorage.getItem('mio_username'),
});

export const login = (username: string, tenantId: string = 'default_tenant') => {
  authState.username = username;
  authState.tenantId = tenantId;
  authState.isLoggedIn = true;
  localStorage.setItem('mio_username', username);
  localStorage.setItem('mio_tenant_id', tenantId);
};

export const logout = () => {
  authState.username = '';
  authState.isLoggedIn = false;
  localStorage.removeItem('mio_username');
  // We might want to keep tenant_id or clear it. Let's keep it for convenience.
};

const api = axios.create({
  baseURL: '/api',
});

// Interceptor to inject tenant_id and user_id
api.interceptors.request.use((config) => {
  if (authState.isLoggedIn) {
    config.params = config.params || {};
    if (!config.params.tenant_id) {
      config.params.tenant_id = authState.tenantId;
    }
    if (!config.params.user_id) {
      config.params.user_id = authState.username; // Mapping username to user_id (email)
    }
  }
  return config;
});

export interface Message {
  id: string;
  sender: string;
  content: string;
  timestamp: string;
}

export interface Session {
  id: string; // Changed from session_id to match backend model usually, but let's check usage
  tenant_id: string;
  user_id: string;
  created_at: string;
}

// ...existing code...
export const createSession = async (): Promise<string> => {
  // Params injected by interceptor
  const response = await api.post<Session>('/sessions');
  return response.data.id;
};

export const getSessions = async (): Promise<Session[]> => {
  const response = await api.get<Session[]>('/sessions');
  return response.data;
}

export const getMessages = async (session_id: string, limit: number = 50): Promise<Message[]> => {
  const response = await api.get<Message[]>(`/sessions/${session_id}/messages`, {
    params: { limit },
  });
  return response.data;
};

export const sendMessage = async (session_id: string, content: string, target_personas: string[] = []): Promise<void> => {
  await api.post(
    `/sessions/${session_id}/messages`,
    { 
      content,
      target_personas 
    }
  );
};

export interface APIProfile {
// ...existing code...
  id: number;
  tenant_id: string;
  name: string;
  base_url: string;
  model: string;
  temperature?: number;
  created_at: string;
  api_key_preview?: string;
}

export interface CreateAPIProfilePayload {
  tenant_id: string;
  name: string;
  base_url: string;
  model: string;
  api_key: string;
  temperature?: number;
}

export interface UpdateAPIProfilePayload {
  tenant_id: string;
  name?: string;
  base_url?: string;
  model?: string;
  api_key?: string;
  temperature?: number;
}

export interface Persona {
  id: number;
  tenant_id: string;
  name: string;
  handle: string;
  prompt: string;
  tone: string;
  proactivity: number;
  memory_window: number;
  max_agents_per_turn: number;
  is_default: boolean;
  api_profile_id?: number;
  api_profile_name?: string;
  api_model?: string;
  api_base_url?: string;
  temperature?: number;
}

export interface CreatePersonaPayload {
  tenant_id: string;
  name: string;
  prompt: string;
  handle?: string;
  tone?: string;
  proactivity?: number;
  memory_window?: number;
  max_agents_per_turn?: number;
  api_profile_id?: number;
  is_default?: boolean;
}

export interface UpdatePersonaPayload {
  tenant_id: string;
  name?: string;
  prompt?: string;
  handle?: string;
  tone?: string;
  proactivity?: number;
  memory_window?: number;
  max_agents_per_turn?: number;
  api_profile_id?: number | null;
  is_default?: boolean;
}

export const getAPIProfiles = async (tenant_id: string): Promise<APIProfile[]> => {
  const response = await api.get<APIProfile[]>('/api-profiles', {
    params: { tenant_id },
  });
  return response.data;
};

export const getAPIProfile = async (tenant_id: string, profile_id: number): Promise<APIProfile> => {
  const response = await api.get<APIProfile>(`/api-profiles/${profile_id}`, {
    params: { tenant_id }
  });
  return response.data;
};

export const createAPIProfile = async (payload: CreateAPIProfilePayload): Promise<APIProfile> => {
  const response = await api.post<APIProfile>('/api-profiles', payload);
  return response.data;
};

export const updateAPIProfile = async (
  profile_id: number,
  payload: UpdateAPIProfilePayload
): Promise<APIProfile> => {
  const { tenant_id, ...body } = payload;
  const response = await api.patch<APIProfile>(`/api-profiles/${profile_id}`, body, {
    params: { tenant_id }
  });
  return response.data;
};

export const deleteAPIProfile = async (tenant_id: string, profile_id: number): Promise<void> => {
  await api.delete(`/api-profiles/${profile_id}`, {
    params: { tenant_id }
  });
};

export const getPersonas = async (tenant_id: string): Promise<Persona[]> => {
  const response = await api.get<Persona[]>('/personas', {
    params: { tenant_id },
  });
  return response.data;
};

export const createPersona = async (payload: CreatePersonaPayload): Promise<Persona> => {
  const response = await api.post<Persona>('/personas', payload);
  return response.data;
};

export const updatePersona = async (persona_id: number, payload: UpdatePersonaPayload): Promise<Persona> => {
  const { tenant_id, ...body } = payload;
  const response = await api.patch<Persona>(`/personas/${persona_id}`, body, {
    params: { tenant_id }
  });
  return response.data;
};

export const deletePersona = async (tenant_id: string, persona_id: number): Promise<void> => {
  await api.delete(`/personas/${persona_id}`, {
    params: { tenant_id }
  });
};
