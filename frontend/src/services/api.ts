/**
 * The only place the app talks to the backend. Screens call these functions and never use
 * fetch() directly, so changes to the API only need changes here.
 */
import Constants from 'expo-constants';
import { Platform } from 'react-native';

const API_PORT = 8000;

/**
 * Where the backend runs. In order of preference:
 * 1. EXPO_PUBLIC_API_URL from frontend/.env.local, e.g. http://192.168.0.214:8000
 * 2. During development: the computer running the Expo dev server, on port 8000
 *    (the phone already knows that computer's address, because it loaded the app from it)
 * 3. http://localhost:8000
 */
function apiBaseUrl(): string {
  if (process.env.EXPO_PUBLIC_API_URL) {
    return process.env.EXPO_PUBLIC_API_URL.replace(/\/$/, '');
  }
  if (Platform.OS === 'web' && typeof window !== 'undefined') {
    return `${window.location.protocol}//${window.location.hostname}:${API_PORT}`;
  }
  const devServerHost = Constants.expoConfig?.hostUri?.split(':')[0];
  return `http://${devServerHost ?? 'localhost'}:${API_PORT}`;
}

export const API_URL = apiBaseUrl();

export type Topic = {
  id: number;
  parent_id: number | null;
  name: string;
  card_count: number;
  due_count: number;
};

export type CardSummary = {
  id: number;
  note_id: number;
  preview: string;
  status: string;
  due_at: string | null;
};

export type Grade = 1 | 2 | 3 | 4;

export type CardToReview = {
  id: number;
  topic_id: number;
  topic_name: string;
  status: string;
  front_html: string;
  back_html: string;
  next_due_by_grade: Record<Grade, string>;
};

export type ReviewResult = {
  card_id: number;
  status: string;
  due_at: string;
};

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...init?.headers },
    });
  } catch {
    throw new ApiError(`Cannot reach the server at ${API_URL}. Is the backend running?`);
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = typeof body?.detail === 'string' ? body.detail : response.statusText;
    throw new ApiError(detail || `Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: 'POST', body: JSON.stringify(body) });
}

export const api = {
  topics: () => request<Topic[]>('/api/v1/topics'),
  createTopic: (name: string, parentId: number | null) =>
    post<Topic>('/api/v1/topics', { name, parent_id: parentId }),
  cardsInTopic: (topicId: number) => request<CardSummary[]>(`/api/v1/topics/${topicId}/cards`),
  createNote: (topicId: number, fields: string[]) =>
    post<{ id: number; card_ids: number[] }>('/api/v1/notes', { topic_id: topicId, fields }),
  reviewQueue: () => request<{ cards: CardToReview[] }>('/api/v1/review/queue'),
  submitReview: (cardId: number, grade: Grade, durationMs: number) =>
    post<ReviewResult>(`/api/v1/cards/${cardId}/reviews`, { grade, duration_ms: durationMs }),
};
