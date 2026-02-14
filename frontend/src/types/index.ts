/**
 * TypeScript types for the Teaching Grading System
 */

// Question types
export type QuestionType = "mcq" | "true_false" | "fill_blank" | "qa" | "reading" | "picture" | "essay";

// Assignment status
export type AssignmentStatus = "uploaded" | "extracted" | "upload_failed" | "extract_failed";

// Source format
export type SourceFormat = "pdf" | "docx" | "doc" | "image";

// Export format
export type ExportFormat = "pdf" | "docx";

// Group
export interface Group {
  id: number;
  name: string;
  description?: string;
  goal?: string;
  created_at?: string;
  updated_at?: string;
}

export interface GroupWithStudents extends Group {
  students: Student[];
}

// Student
export type Gender = "boy" | "girl";

export interface Student {
  id: number;
  name: string;
  age?: number;
  gender?: Gender;
  vocabulary?: string;
  grade?: string;
  group_id?: number;
  additional_info?: string;
  created_at?: string;
  updated_at?: string;
  group_name?: string;
}

// Grade phase response (3-phase grading flow)
export interface GradePhaseResponse {
  phase: string;
  assignment_id?: number;
  context_id?: number;
  ai_grading_id?: number;
  status?: string;
  elapsed_ms?: number;
  error?: string;
}

// Assignment (list/detail from API)
export interface Assignment {
  id: number | string;
  title?: string;
  student_name?: string;
  template_display?: string;
  display_status?: string;
  display_date?: string;
  filename: string;
  source_format: SourceFormat;
  status: AssignmentStatus;
  created_at?: string;
  updated_at?: string;
  upload_time?: string;
  graded_at?: string;
  essay_topic?: string;
  grading_model?: string;
  latest_grading_status?: "grading" | "completed" | "failed";
  background?: string;
  instructions?: string;
  template_name?: string;
  grading_time?: number;
  ai_grading_status?: string;
  extracted_text?: string;
  graded_content?: string;
  grading_results?: unknown;
  total_score?: number;
}

// Question type config
export interface QuestionTypeConfig {
  type: string;
  name: string;
  weight: number;
  enabled: boolean;
}

// Instruction format for template instructions field
export type InstructionFormat = "markdown" | "html" | "text" | "json";

// Template/Grading Template
export interface Template {
  id: string;
  name: string;
  description?: string;
  instructions?: string;
  instruction_format?: InstructionFormat;
  question_types: QuestionTypeConfig[];
  encouragement_words: string[];
  is_default?: boolean;
  created_at?: string;
  updated_at?: string;
  usage_count?: number;
}

// GradingTemplate alias for backward compatibility
export type GradingTemplate = Template;

// AI Config
export interface AIConfig {
  default_provider: string;
  default_model: string;
  api_key: string;
  api_base_url?: string;
  temperature: number;
  max_tokens: number;
  search_engine: string;
  copilot_base_url?: string;
  copilot_available_models?: string[];
}

export interface AIConfigUpdate {
  provider?: string;
  model?: string;
  api_key?: string;
  base_url?: string;
  temperature?: number;
  max_tokens?: number;
  search_engine?: string;
  copilot_base_url?: string;
}

export interface TestConnectionRequest {
  provider: string;
  base_url?: string;
  api_key?: string;
}

export interface TestConnectionResponse {
  success: boolean;
  message: string;
  models?: string[];
  error?: string;
}

// Teacher profile
export interface TeacherProfile {
  id?: string;
  name: string;
  email?: string;
  avatar_url?: string;
  bio?: string;
  created_at?: string;
}

// Greeting
export interface GreetingSource {
  title: string;
  author?: string;
}

export interface Greeting {
  greeting: string;
  source?: GreetingSource;
}

// Cached article
export interface CachedArticle {
  id: string;
  title: string;
  author?: string;
  source_url?: string;
  source_type?: string;
  cached_at: string;
  expires_at?: string;
  access_count: number;
}

// API Response types
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit?: number;
  page_size?: number;
  status_options?: string[];
}

export interface AssignmentListResponse extends PaginatedResponse<Assignment> {
  status_options: string[];
}

export interface GradeRequest {
  assignment_id: string;
  background_info?: string;
  template_id?: string;
}

export interface BatchGradeRequest {
  assignment_ids: string[];
  background_info?: string;
  template_id?: string;
}
