/**
 * API service for essay grading.
 */

export interface GradeEssayRequest {
  student_name?: string;
  student_level?: string;
  recent_activity?: string;
  essay_text?: string;
  file_id?: string;
  template_id?: string;
  additional_instructions?: string;
}

export interface GradingResult {
  grading_id: string;
  status: 'processing' | 'completed' | 'failed';
  html_result?: string;
  download_url?: string;
  student_name: string;
  student_level: string;
  created_at: string;
}

export interface GradingHistoryItem {
  id: string;
  student_name: string;
  student_level: string;
  template_id: string;
  created_at: string;
}

export interface GradingHistoryDetail {
  id: string;
  student_name: string;
  student_level?: string;
  recent_activity?: string;
  template_id?: string;
  additional_instructions?: string;
  essay_text?: string;
  html_result?: string;
  file_path?: string;
  created_at: string;
}

export interface GradingHistoryResponse {
  total: number;
  items: GradingHistoryItem[];
}

export interface AIProviderConfig {
  provider: string;
  api_key: string;
  model?: string;
  is_default?: boolean;
}

export interface AIProviderConfigResponse {
  id: string;
  provider: string;
  model?: string;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface AIProviderInfo {
  name: string;
  display_name: string;
  default_model: string;
  description: string;
}

const API_BASE = '/api/v1/grading';

/**
 * Grade a student essay.
 */
export async function gradeEssay(request: GradeEssayRequest): Promise<GradingResult> {
  const response = await fetch(`${API_BASE}/grade-essay`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Grading failed');
  }

  return response.json();
}

/**
 * Upload an essay file.
 */
export async function uploadEssayFile(file: File): Promise<{ file_id: string; file_path: string }> {
  const formData = new FormData();
  formData.append('file', file);

  const response = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Upload failed');
  }

  const data = await response.json();
  return { file_id: data.file_id, file_path: data.file_id };
}

/**
 * Get grading history.
 */
export async function getGradingHistory(page = 1, limit = 10): Promise<GradingHistoryResponse> {
  const offset = (page - 1) * limit;
  const response = await fetch(`${API_BASE}/history?limit=${limit}&offset=${offset}`);

  if (!response.ok) {
    throw new Error('Failed to fetch grading history');
  }

  return response.json();
}

/**
 * Get grading history by ID (includes HTML result).
 */
export async function getGradingHistoryById(gradingId: string): Promise<GradingHistoryDetail> {
  const response = await fetch(`${API_BASE}/${gradingId}`);

  if (!response.ok) {
    throw new Error('Failed to fetch grading result');
  }

  return response.json();
}

/**
 * Get a specific grading result.
 */
export async function getGradingResult(gradingId: string): Promise<GradingResult> {
  const response = await fetch(`${API_BASE}/${gradingId}`);

  if (!response.ok) {
    throw new Error('Failed to fetch grading result');
  }

  return response.json();
}

/**
 * Download HTML grading report.
 */
export async function downloadGrading(gradingId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/download/${gradingId}`);

  if (!response.ok) {
    throw new Error('Failed to download grading');
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `grading_${gradingId}.html`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  window.URL.revokeObjectURL(url);
}

/**
 * List available AI providers.
 */
export async function listAIProviders(): Promise<AIProviderInfo[]> {
  const response = await fetch(`${API_BASE}/providers`);

  if (!response.ok) {
    throw new Error('Failed to fetch AI providers');
  }

  return response.json();
}

/**
 * Save AI provider configuration.
 */
export async function saveAIConfig(config: AIProviderConfig): Promise<AIProviderConfigResponse> {
  const response = await fetch(`${API_BASE}/providers/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to save configuration');
  }

  return response.json();
}

/**
 * Get AI provider configurations.
 */
export async function getAIConfigs(): Promise<AIProviderConfigResponse[]> {
  const response = await fetch(`${API_BASE}/providers/config`);

  if (!response.ok) {
    throw new Error('Failed to fetch AI configurations');
  }

  return response.json();
}
