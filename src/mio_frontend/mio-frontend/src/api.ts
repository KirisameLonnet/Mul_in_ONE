import axios from 'axios';
import { reactive } from 'vue';

// --- Auth State ---
export const authState = reactive({
  username: localStorage.getItem('mio_username') || '',
  isLoggedIn: !!localStorage.getItem('mio_username'),
});

export const login = (username: string) => {
  authState.username = username;
  authState.isLoggedIn = true;
  localStorage.setItem('mio_username', username);
};

export const logout = () => {
  authState.username = '';
  authState.isLoggedIn = false;
  localStorage.removeItem('mio_username');
};

export const api = axios.create({
  baseURL: '/api',
});

// Interceptor to inject username
api.interceptors.request.use((config) => {
  if (authState.isLoggedIn) {
    config.params = config.params || {};
    if (!config.params.username) {
      config.params.username = authState.username;
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
  id: string;
  username: string;
  created_at: string;
  user_persona?: string;
  title?: string | null;
  user_display_name?: string | null;
  user_handle?: string | null;
  participants?: Array<{
    id: number;
    name: string;
    handle: string;
  }>;
}

// ...existing code...
export const createSession = async (
  user_persona?: string,
  title?: string,
  user_display_name?: string,
  user_handle?: string
): Promise<string> => {
  // Params injected by interceptor
  const params: any = {};
  if (user_persona) params.user_persona = user_persona;
  if (title) params.title = title;
  if (user_display_name) params.user_display_name = user_display_name;
  if (user_handle) params.user_handle = user_handle;
  
  const response = await api.post<{ session_id: string }>('/sessions', null, {
    params: Object.keys(params).length > 0 ? params : undefined
  });
  return response.data.session_id;
};

export const getSessions = async (): Promise<Session[]> => {
  const response = await api.get<Session[]>('/sessions');
  return response.data;
}

export const getSession = async (session_id: string): Promise<Session> => {
  const response = await api.get<Session>(`/sessions/${session_id}`);
  return response.data;
};

export const updateSessionParticipants = async (
  session_id: string,
  persona_ids: number[]
): Promise<Session> => {
  const response = await api.put<Session>(
    `/sessions/${session_id}/participants`,
    { persona_ids }
  );
  return response.data;
};

export const updateSessionMeta = async (
  session_id: string,
  payload: Partial<Pick<Session, 'title' | 'user_display_name' | 'user_handle' | 'user_persona'>>
): Promise<Session> => {
  const response = await api.patch<Session>(`/sessions/${session_id}`, payload);
  return response.data;
};

export const deleteSession = async (session_id: string): Promise<void> => {
  await api.delete(`/sessions/${session_id}`);
};

export const deleteSessions = async (session_ids: string[]): Promise<void> => {
  await api.post('/sessions/batch-delete', { session_ids });
};

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
  id: number;
  username: string;
  name: string;
  base_url: string;
  model: string;
  temperature?: number;
  created_at: string;
  api_key_preview?: string;
  is_embedding_model?: boolean;
  embedding_dim?: number | null;
}

export interface CreateAPIProfilePayload {
  username: string;
  name: string;
  base_url: string;
  model: string;
  api_key: string;
  temperature?: number;
  is_embedding_model?: boolean;
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
  username: string;
  name: string;
  handle: string;
  prompt: string;
  background?: string;
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
  username: string;
  name: string;
  prompt: string;
  background?: string;
  handle?: string;
  tone?: string;
  proactivity?: number;
  memory_window?: number;
  max_agents_per_turn?: number;
  api_profile_id?: number;
  is_default?: boolean;
}

export interface UpdatePersonaPayload {
  username: string;
  name?: string;
  prompt?: string;
  background?: string | null;
  handle?: string;
  tone?: string;
  proactivity?: number;
  memory_window?: number;
  max_agents_per_turn?: number;
  api_profile_id?: number | null;
  is_default?: boolean;
}

export const getAPIProfiles = async (username: string): Promise<APIProfile[]> => {
  const response = await api.get<APIProfile[]>('/personas/api-profiles', {
    params: { username },
  });
  return response.data;
};

export const getAPIProfile = async (username: string, profile_id: number): Promise<APIProfile> => {
  const response = await api.get<APIProfile>(`/personas/api-profiles/${profile_id}`, {
    params: { username }
  });
  return response.data;
};

export const createAPIProfile = async (payload: CreateAPIProfilePayload): Promise<APIProfile> => {
  const response = await api.post<APIProfile>('/personas/api-profiles', payload);
  return response.data;
};

export const updateAPIProfile = async (
  profile_id: number,
  payload: UpdateAPIProfilePayload
): Promise<APIProfile> => {
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
