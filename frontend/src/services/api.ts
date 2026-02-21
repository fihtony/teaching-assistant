/**
 * API service for communicating with the backend
 */

import axios, { AxiosInstance } from "axios";
import type {
  Assignment,
  AssignmentListResponse,
  Template,
  AIConfig,
  AIConfigUpdate,
  TeacherProfile,
  Greeting,
  Group,
  GroupWithStudents,
  Student,
  ExportFormat,
  GradePhaseResponse,
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
  upload: async (data: { file: File; student_id?: number; student_name?: string }): Promise<Assignment> => {
    const formData = new FormData();
    formData.append("file", data.file);
    if (data.student_id != null) formData.append("student_id", String(data.student_id));
    if (data.student_name) formData.append("student_name", data.student_name);
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

  // List assignments (history: title, student, template, display_status, display_date; sort, search, status filter)
  list: async (params: {
    page?: number;
    limit?: number;
    page_size?: number;
    search?: string;
    status?: string;
    sort_by?: "date" | "student_name" | "title";
    sort_order?: "asc" | "desc";
  }): Promise<AssignmentListResponse> => {
    const { limit, page_size, ...rest } = params;
    const response = await api.get("/assignments", { params: { ...rest, page_size: page_size ?? limit ?? 10 } });
    return response.data;
  },

  // Delete assignment
  delete: async (id: string): Promise<{ message: string }> => {
    const response = await api.delete(`/assignments/${id}`);
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

  // 3-phase grading flow (optional signal for cancel)
  gradeUploadPhase: async (
    form: {
      file: File;
      student_id?: number;
      student_name?: string;
      background?: string;
      template_id?: number;
      instructions?: string;
    },
    signal?: AbortSignal,
  ): Promise<GradePhaseResponse> => {
    const formData = new FormData();
    formData.append("file", form.file);
    if (form.student_id != null) formData.append("student_id", String(form.student_id));
    if (form.student_name) formData.append("student_name", form.student_name);
    if (form.background) formData.append("background", form.background);
    if (form.template_id != null) formData.append("template_id", String(form.template_id));
    if (form.instructions) formData.append("instructions", form.instructions);
    const response = await api.post("/assignments/grade/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      signal,
    });
    return response.data;
  },

  gradeUploadTextPhase: async (
    form: {
      text_content: string;
      student_id?: number;
      student_name?: string;
      background?: string;
      template_id?: number;
      instructions?: string;
    },
    signal?: AbortSignal,
  ): Promise<GradePhaseResponse> => {
    const formData = new FormData();
    formData.append("text_content", form.text_content);
    if (form.student_id != null) formData.append("student_id", String(form.student_id));
    if (form.student_name) formData.append("student_name", form.student_name);
    if (form.background) formData.append("background", form.background);
    if (form.template_id != null) formData.append("template_id", String(form.template_id));
    if (form.instructions) formData.append("instructions", form.instructions);
    const response = await api.post("/assignments/grade/upload-text", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      signal,
    });
    return response.data;
  },

  analyzeContextPhase: async (assignmentId: number, signal?: AbortSignal): Promise<GradePhaseResponse> => {
    const response = await api.post(`/assignments/${assignmentId}/grade/analyze-context`, undefined, { signal });
    return response.data;
  },
  runGradingPhase: async (assignmentId: number, signal?: AbortSignal): Promise<GradePhaseResponse> => {
    const response = await api.post(`/assignments/${assignmentId}/grade/run`, undefined, { signal });
    return response.data;
  },

  // Get dashboard statistics
  getStats: async (): Promise<{
    total_graded: number;
    pending: number;
    this_week: number;
    needs_review: number;
  }> => {
    const response = await api.get("/assignments/stats/dashboard");
    return response.data;
  },

  // Update grading time (total time from all phases)
  updateGradingTime: async (assignmentId: number, totalTimeMs: number): Promise<void> => {
    await api.patch(`/assignments/${assignmentId}/grading-time`, {
      total_time_ms: totalTimeMs,
    });
  },

  // 3-phase preview grading flow (non-persistent, for instruction building)
  previewGradeUploadPhase: async (
    form: {
      file: File;
      student_id?: number;
      student_name?: string;
      background?: string;
      instructions?: string;
      ai_model?: string;
      ai_provider?: string;
    },
    signal?: AbortSignal,
  ): Promise<GradePhaseResponse> => {
    const formData = new FormData();
    formData.append("file", form.file);
    if (form.student_id != null) formData.append("student_id", String(form.student_id));
    if (form.student_name) formData.append("student_name", form.student_name);
    if (form.background) formData.append("background", form.background);
    if (form.instructions) formData.append("instructions", form.instructions);
    if (form.ai_model) formData.append("ai_model", form.ai_model);
    if (form.ai_provider) formData.append("ai_provider", form.ai_provider);
    const response = await api.post("/assignments/preview-grade/upload", formData, {
      headers: { "Content-Type": "multipart/form-data" },
      signal,
    });
    return response.data;
  },

  previewAnalyzeContextPhase: async (sessionId: string, signal?: AbortSignal): Promise<GradePhaseResponse> => {
    const response = await api.post(`/assignments/preview-grade/${sessionId}/analyze-context`, undefined, { signal });
    return response.data;
  },

  previewRunGradingPhase: async (sessionId: string, signal?: AbortSignal): Promise<GradePhaseResponse> => {
    const response = await api.post(`/assignments/preview-grade/${sessionId}/run`, undefined, { signal });
    return response.data;
  },

  getPreviewGradeResult: async (sessionId: string): Promise<{ html: string }> => {
    const response = await api.get(`/assignments/preview-grade/${sessionId}/result`);
    return response.data;
  },

  // Revise a graded output based on teacher's instruction (no DB change)
  reviseGrading: async (
    assignmentId: number,
    data: {
      ai_grading_id: number;
      teacher_instruction: string;
      current_html_content: string;
    },
    signal?: AbortSignal,
  ): Promise<{ html_content: string; elapsed_ms?: number; error?: string }> => {
    const response = await api.post(`/assignments/${assignmentId}/grade/revise`, data, { signal });
    return response.data;
  },

  // Save a revised version as the final graded output
  saveRevision: async (
    assignmentId: number,
    data: {
      ai_grading_id: number;
      html_content: string;
      revision_history?: Array<{ instruction: string; timestamp: string }>;
    },
  ): Promise<{ message: string; ai_grading_id: number; graded_at: string; updated_at: string }> => {
    const response = await api.put(`/assignments/${assignmentId}/grade/save-revision`, data);
    return response.data;
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
    apiKey?: string,
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
      models: (data.models || []) as (string | { name: string; vendor: string; id: string })[],
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

// Groups API
export const groupsApi = {
  list: async (): Promise<Group[]> => {
    const response = await api.get("/groups");
    return response.data;
  },
  get: async (id: number): Promise<GroupWithStudents> => {
    const response = await api.get(`/groups/${id}`);
    return response.data;
  },
  create: async (data: { name: string; description?: string; goal?: string }): Promise<Group> => {
    const response = await api.post("/groups", data);
    return response.data;
  },
  update: async (id: number, data: Partial<Group>): Promise<Group> => {
    const response = await api.patch(`/groups/${id}`, data);
    return response.data;
  },
  delete: async (id: number): Promise<void> => {
    await api.delete(`/groups/${id}`);
  },
};

// Students API
export const studentsApi = {
  list: async (group_id?: number): Promise<Student[]> => {
    const response = await api.get("/students", { params: group_id != null ? { group_id } : {} });
    return response.data;
  },
  get: async (id: number): Promise<Student> => {
    const response = await api.get(`/students/${id}`);
    return response.data;
  },
  create: async (data: Partial<Student> & { name: string }): Promise<Student> => {
    const response = await api.post("/students", data);
    return response.data;
  },
  update: async (id: number, data: Partial<Student>): Promise<Student> => {
    const response = await api.patch(`/students/${id}`, data);
    return response.data;
  },
  delete: async (id: number): Promise<void> => {
    await api.delete(`/students/${id}`);
  },
};

export default api;
