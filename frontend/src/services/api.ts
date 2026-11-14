import type {
  ChatMessage,
  Conversation,
  ConversationDetail,
  Dataset,
  Relationship,
  UploadResponse,
} from "../types/api";

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, init);
  } catch {
    throw new ApiError("Cannot reach the server. Is the backend running?");
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const detail = body?.detail;
    throw new ApiError(typeof detail === "string" ? detail : `Request failed (${response.status})`);
  }
  return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

const json = (body: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(body),
});

export const api = {
  listDatasets: () => request<Dataset[]>("/api/datasets"),

  uploadDatasets(files: File[]) {
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    return request<UploadResponse>("/api/datasets", { method: "POST", body: form });
  },

  listRelationships: () => request<Relationship[]>("/api/datasets/relationships"),

  deleteDataset: (id: string) => request<void>(`/api/datasets/${id}`, { method: "DELETE" }),

  listConversations: () => request<Conversation[]>("/api/conversations"),

  createConversation: () => request<Conversation>("/api/conversations", { method: "POST" }),

  getConversation: (id: string) => request<ConversationDetail>(`/api/conversations/${id}`),

  deleteConversation: (id: string) =>
    request<void>(`/api/conversations/${id}`, { method: "DELETE" }),

  sendMessage: (conversationId: string, question: string, datasetIds: string[]) =>
    request<ChatMessage>(
      `/api/conversations/${conversationId}/messages`,
      json({ question, dataset_ids: datasetIds }),
    ),
};
