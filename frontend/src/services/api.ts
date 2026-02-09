/**
 * API service for communicating with the backend
 */

import axios, { AxiosInstance } from "axios";
import type {
  Assignment,
  Template,
  AIConfig,
  AIConfigUpdate,
  TeacherProfile,
  Greeting,
  // CachedArticle,
  PaginatedResponse,
  // GradeRequest,
  BatchGradeRequest,
  ExportFormat,
} from "@/types";

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: "/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

// Assignments API
export const assignmentsApi = {
  // Upload a single assignment
  upload: async (data: { file: File; student_name?: string; background_info?: string; template_id?: string }): Promise<Assignment> => {
    const formData = new FormData();
    formData.append("file", data.file);
    if (data.student_name) formData.append("student_name", data.student_name);
    if (data.background_info) formData.append("background_info", data.background_info);
    if (data.template_id) formData.append("template_id", data.template_id);
    const response = await api.post("/assignments/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data;
  },

  // Batch upload assignments
  batchUpload: async (data: { files: File[]; background_info?: string; template_id?: string }): Promise<Assignment[]> => {
    const formData = new FormData();
    data.files.forEach((file) => formData.append("files", file));
    if (data.background_info) formData.append("background_info", data.background_info);
    if (data.template_id) formData.append("template_id", data.template_id);
    const response = await api.post("/assignments/batch-upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data;
  },

  // Get assignment by ID
  get: async (id: string): Promise<Assignment> => {
    const response = await api.get(`/assignments/${id}`);
    return response.data;
  },

  // List assignments
  list: async (params: { page?: number; limit?: number; search?: string; status?: string }): Promise<PaginatedResponse<Assignment>> => {
    const response = await api.get("/assignments", { params });
    return response.data;
  },

  // Grade an assignment
  grade: async (id: string): Promise<Assignment> => {
    const response = await api.post(`/assignments/${id}/grade`);
    return response.data;
  },

  // Batch grade assignments
  batchGrade: async (
    request: BatchGradeRequest,
  ): Promise<{
    completed: number;
    failed: number;
    results: Assignment[];
    errors: Array<{ assignment_id: string; error: string }>;
  }> => {
    const response = await api.post("/assignments/batch-grade", request);
    return response.data;
  },

  // Export assignment
  export: async (id: string, format: ExportFormat = "pdf"): Promise<Blob> => {
    const response = await api.get(`/assignments/${id}/export`, {
      params: { format },
      responseType: "blob",
    });
    return response.data;
  },

  // Delete assignment
  delete: async (id: string): Promise<void> => {
    await api.delete(`/assignments/${id}`);
  },
};

// Templates API
export const templatesApi = {
  // List all templates
  list: async (): Promise<Template[]> => {
    const response = await api.get("/templates");
    return response.data.items || [];
  },

  // Get template by ID
  getById: async (id: string): Promise<Template> => {
    const response = await api.get(`/templates/${id}`);
    return response.data;
  },

  // Create template
  create: async (template: Omit<Template, "id" | "created_at" | "updated_at" | "usage_count">): Promise<Template> => {
    const response = await api.post("/templates", template);
    return response.data;
  },

  // Update template
  update: async (id: string, template: Partial<Template>): Promise<Template> => {
    const response = await api.put(`/templates/${id}`, template);
    return response.data;
  },

  // Delete template
  delete: async (id: string): Promise<void> => {
    await api.delete(`/templates/${id}`);
  },
};

// Settings API
export const settingsApi = {
  // Get all settings (AI config + search_engine) in one call; backend never returns api_key
  getSettings: async (): Promise<AIConfig & { search_engine?: string }> => {
    const response = await api.get("/settings/settings");
    return response.data;
  },

  getAIConfig: async (): Promise<AIConfig> => {
    const response = await api.get("/settings/settings");
    return response.data;
  },

  // Update AI provider config only (clean body; no GET after save)
  updateAIProvider: async (update: {
    provider?: string;
    model?: string;
    base_url?: string;
    api_key?: string;
    temperature?: number;
    max_tokens?: number;
  }): Promise<{ ok: boolean }> => {
    const response = await api.post("/settings/ai-provider", update);
    return response.data;
  },

  updateAIConfig: async (update: AIConfigUpdate): Promise<AIConfig> => {
    const response = await api.post("/settings/settings", update);
    return response.data;
  },

  // Search engine: loaded from getSettings; save via separate endpoint
  getSearchEngine: async (): Promise<{ engine: string }> => {
    const response = await api.get("/settings/search-engine");
    return response.data;
  },

  // Update search engine configuration
  updateSearchEngine: async (engine: string): Promise<{ engine: string }> => {
    const response = await api.post("/settings/search-engine", { engine });
    return response.data;
  },

  // Get available models from a provider
  getModels: async (
    provider: string,
    baseUrl?: string,
    apiKey?: string
  ): Promise<{
    models: (string | { name: string; vendor: string; id: string })[];
    error?: string;
    message?: string;
  }> => {
    const response = await api.post("/settings/get-models", {
      provider,
      base_url: baseUrl,
      api_key: apiKey,
    });
    const data = response.data as { models?: unknown[]; error?: string; message?: string };
    return {
      models: data.models || [],
      error: data.error,
      message: data.message,
    };
  },

  // Test connection to a provider
  testConnection: async (provider: string, baseUrl?: string, apiKey?: string) => {
    const response = await api.post("/settings/test-connection", {
      provider,
      base_url: baseUrl,
      api_key: apiKey,
    });
    return response.data;
  },

  // Get teacher profile
  getTeacherProfile: async (): Promise<TeacherProfile> => {
    const response = await api.get("/settings/teacher-profile");
    return response.data;
  },

  // Update teacher profile
  updateTeacherProfile: async (profile: Partial<TeacherProfile>): Promise<TeacherProfile> => {
    const response = await api.post("/settings/teacher-profile", profile);
    return response.data;
  },
};

// Greeting API
export const greetingApi = {
  // Get greeting
  get: async (): Promise<Greeting> => {
    const response = await api.get("/greeting");
    return response.data;
  },
};

// Cache API
export const cacheApi = {
  // Get cache statistics
  getStats: async (): Promise<{ total_articles: number; cache_size: number }> => {
    const response = await api.get("/cache/stats");
    return response.data;
  },

  // Clear cache
  clear: async (): Promise<void> => {
    await api.delete("/cache");
  },
};

export default api;
