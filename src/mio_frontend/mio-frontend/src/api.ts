import axios from 'axios';
import { reactive } from 'vue';

// --- Auth State ---
export const authState = reactive({
  username: localStorage.getItem('mio_username') || '',
  isLoggedIn: !!localStorage.getItem('access_token'),
  token: localStorage.getItem('access_token') || '',
});

export const login = (username: string, token: string) => {
  authState.username = username;
  authState.token = token;
  authState.isLoggedIn = true;
  localStorage.setItem('mio_username', username);
  localStorage.setItem('access_token', token);
};

export const logout = () => {
  authState.username = '';
  authState.token = '';
  authState.isLoggedIn = false;
  localStorage.removeItem('mio_username');
  localStorage.removeItem('access_token');
};

export const api = axios.create({
  baseURL: '/api',
});

// Interceptor to inject JWT token and username
api.interceptors.request.use((config) => {
  if (authState.isLoggedIn && authState.token) {
    // 添加 JWT Bearer token
    config.headers.Authorization = `Bearer ${authState.token}`;
    
    // 保留原有的 username 参数注入（向后兼容）
    config.params = config.params || {};
    if (!config.params.username) {
      config.params.username = authState.username;
    }
  }
  return config;
});

// 401 拦截器：token 过期时自动跳转登录
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      logout();
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export interface Message {
  id: string;
  sender: string;
  content: string;
  timestamp: string;
}

export interface Session {
  id: string;
  username: string;
  created_at: string;
  user_persona?: string;
  title?: string | null;
  user_display_name?: string | null;
  user_handle?: string | null;
}

export interface APIProfile {
  id: number;
  user_id: number;
  name: string;
  base_url: string;
  model: string;
  temperature: number;
  created_at: string;
  is_embedding_model: boolean;
  embedding_dim?: number | null;
}

export interface CreateAPIProfilePayload {
  username: string;
  name: string;
  base_url: string;
  model: string;
  api_key: string;
  temperature?: number;
  is_embedding_model: boolean;
  embedding_dim?: number | null;
}

export interface UpdateAPIProfilePayload {
  username: string;
  name?: string;
  base_url?: string;
  model?: string;
  api_key?: string;
  temperature?: number;
  is_embedding_model?: boolean;
  embedding_dim?: number | null;
}

export interface Persona {
  id: number;
  user_id: number;
  name: string;
  handle: string;
  prompt: string;
  background?: string | null;
  tone: string;
  proactivity: number;
  memory_window: number;
  max_agents_per_turn: number;
  api_profile_id?: number | null;
  is_default: boolean;
}

export interface CreatePersonaPayload {
  username: string;
  name: string;
  handle: string;
  prompt: string;
  background?: string | null;
  tone?: string;
  proactivity?: number;
  memory_window?: number;
  max_agents_per_turn?: number;
  api_profile_id?: number | null;
  is_default?: boolean;
}

export interface UpdatePersonaPayload {
  username: string;
  name?: string;
  handle?: string;
  prompt?: string;
  background?: string | null;
  tone?: string;
  proactivity?: number;
  memory_window?: number;
  max_agents_per_turn?: number;
  api_profile_id?: number | null;
  is_default?: boolean;
}

export interface CreateSessionPayload {
  username: string;
  persona_ids: number[];
  user_persona?: string;
  title?: string;
  user_display_name?: string;
  user_handle?: string;
}

export interface UpdateSessionPayload {
  title?: string;
  user_display_name?: string;
  user_handle?: string;
  user_persona?: string;
}

export interface UserMessage {
  content: string;
  sender_name?: string;
  target_personas?: string[];
}

export const getSessions = async (username: string): Promise<Session[]> => {
  const response = await api.get<Session[]>('/sessions', {
    params: { username },
  });
  return response.data;
};

export const getSession = async (sessionId: string, username: string): Promise<Session> => {
  const response = await api.get<Session>(`/sessions/${sessionId}`, {
    params: { username },
  });
  return response.data;
};

export const getSessionMessages = async (sessionId: string, username: string): Promise<Message[]> => {
  const response = await api.get<Message[]>(`/sessions/${sessionId}/messages`, {
    params: { username },
  });
  return response.data;
};

// Alias for getSessionMessages (for backward compatibility)
export const getMessages = getSessionMessages;

export const createSession = async (payload: CreateSessionPayload): Promise<Session> => {
  const response = await api.post<Session>('/sessions', payload);
  return response.data;
};

export const updateSession = async (sessionId: string, username: string, payload: UpdateSessionPayload): Promise<Session> => {
  const response = await api.patch<Session>(`/sessions/${sessionId}`, payload, {
    params: { username }
  });
  return response.data;
};

// Alias for updateSession with simpler signature
export const updateSessionMeta = async (sessionId: string, payload: UpdateSessionPayload): Promise<Session> => {
  const response = await api.patch<Session>(`/sessions/${sessionId}`, payload);
  return response.data;
};

export const updateSessionParticipants = async (sessionId: string, personaIds: number[]): Promise<void> => {
  await api.patch(`/sessions/${sessionId}/participants`, { persona_ids: personaIds });
};

export const deleteSession = async (sessionId: string, username: string): Promise<void> => {
  await api.delete(`/sessions/${sessionId}`, {
    params: { username },
  });
};

export const deleteSessions = async (sessionIds: string[]): Promise<void> => {
  await Promise.all(sessionIds.map(id => api.delete(`/sessions/${id}`)));
};

export const sendMessage = async (sessionId: string, username: string, userMessage: UserMessage): Promise<void> => {
  await api.post(`/sessions/${sessionId}/messages`, userMessage, {
    params: { username },
  });
};

export const stopSession = async (sessionId: string, username: string): Promise<void> => {
  await api.post(`/sessions/${sessionId}/stop`, null, {
    params: { username }
  });
};

export const getAPIProfiles = async (username: string): Promise<APIProfile[]> => {
  const response = await api.get<APIProfile[]>('/personas/api-profiles', {
    params: { username },
  });
  return response.data;
};

export const createAPIProfile = async (payload: CreateAPIProfilePayload): Promise<APIProfile> => {
  const response = await api.post<APIProfile>('/personas/api-profiles', payload);
  return response.data;
};

export const updateAPIProfile = async (profile_id: number, payload: UpdateAPIProfilePayload): Promise<APIProfile> => {
  const { username, ...body } = payload;
  const response = await api.patch<APIProfile>(`/personas/api-profiles/${profile_id}`, body, {
    params: { username }
  });
  return response.data;
};

export const deleteAPIProfile = async (username: string, profile_id: number): Promise<void> => {
  await api.delete(`/personas/api-profiles/${profile_id}`, {
    params: { username }
  });
};

export const getPersonas = async (username: string): Promise<Persona[]> => {
  const response = await api.get<Persona[]>('/personas/personas', {
    params: { username },
  });
  return response.data;
};

export const createPersona = async (payload: CreatePersonaPayload): Promise<Persona> => {
  const response = await api.post<Persona>('/personas/personas', payload);
  return response.data;
};

export const updatePersona = async (persona_id: number, payload: UpdatePersonaPayload): Promise<Persona> => {
  const { username, ...body } = payload;
  const response = await api.patch<Persona>(`/personas/personas/${persona_id}`, body, {
    params: { username }
  });
  return response.data;
};

export const deletePersona = async (username: string, persona_id: number): Promise<void> => {
  await api.delete(`/personas/personas/${persona_id}`, {
    params: { username }
  });
};

// ==================== Auth APIs (FastAPI-Users) ====================

export interface LoginCredentials {
  username: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  username: string;
  display_name?: string;
}

export interface UserInfo {
  id: number;
  email: string;
  username: string;
  display_name?: string;
  is_active: boolean;
  is_superuser: boolean;
  is_verified: boolean;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export const authLogin = async (credentials: LoginCredentials): Promise<AuthResponse> => {
  const formData = new FormData();
  formData.append('username', credentials.username);
  formData.append('password', credentials.password);
  
  const response = await api.post<AuthResponse>('/auth/login', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
  });
  return response.data;
};

export const authRegister = async (payload: RegisterPayload): Promise<UserInfo> => {
  const response = await api.post<UserInfo>('/auth/register', payload);
  return response.data;
};

export const getCurrentUser = async (): Promise<UserInfo> => {
  const response = await api.get<UserInfo>('/users/me');
  return response.data;
};

export const authLogout = async (): Promise<void> => {
  await api.post('/auth/logout');
  logout();
};

export const deleteAccount = async (): Promise<void> => {
  await api.delete('/auth/account');
};
