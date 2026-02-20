/**
 * Grading page - view and interact with graded assignments.
 * Shows student homework and AI-graded output side by side (left and right).
 */

import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { assignmentsApi } from "@/services/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Download, FileText, CheckCircle, AlertTriangle, Star, Sparkles, Clock, XCircle, Pencil } from "lucide-react";
import { StatusBadge } from "@/components/StatusBadge";
import { GradedOutputDisplay } from "@/components/common/GradedOutputDisplay";

interface GradingItem {
  question_number: number;
  question_type: string;
  student_answer: string;
  correct_answer?: string;
  is_correct: boolean;
  comment: string;
}

interface GradingResults {
  items?: GradingItem[];
  section_scores?: Record<string, { correct: number; total: number; encouragement?: string }>;
  overall_comment?: string;
}

function formatDisplayDateTime(dateString: string | undefined): string {
  if (!dateString) return "—";
  try {
    const d = new Date(dateString);
    if (Number.isNaN(d.getTime())) return dateString;
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    const hours = String(d.getHours()).padStart(2, "0");
    const minutes = String(d.getMinutes()).padStart(2, "0");
    const seconds = String(d.getSeconds()).padStart(2, "0");
    return `${year}/${month}/${day} ${hours}:${minutes}:${seconds}`;
  } catch {
    return dateString;
  }
}

function calculateGradingTime(createdAt: string | undefined, gradedAt: string | undefined, gradingTimeSeconds?: number): string {
  if (gradingTimeSeconds !== undefined && gradingTimeSeconds !== null) {
    // Use grading_time from backend if available
    const minutes = Math.floor(gradingTimeSeconds / 60);
    const seconds = gradingTimeSeconds % 60;
    return `${minutes}m ${seconds}s`;
  }

  if (!createdAt || !gradedAt) return "—";
  try {
    const created = new Date(createdAt).getTime();
    const graded = new Date(gradedAt).getTime();
    if (Number.isNaN(created) || Number.isNaN(graded)) return "—";

    const diffMs = graded - created;
    if (diffMs < 0) return "—";

    const totalSeconds = Math.floor(diffMs / 1000);
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;

    return `${minutes}m ${seconds}s`;
  } catch {
    return "—";
  }
}

function getDisplayStatus(assignmentStatus: string, aiGradingStatus?: string): string {
  // Logic:
  // - If assignments.status = "extracted" and ai_grading.status = "not_started", show "Ready for grading"
  // - If assignment.status is failure or not "extracted", show assignment.status
  // - If assignments.status = "extracted" and ai_grading.status != "not_started", show ai_grading.status

  const aStatus = assignmentStatus?.toLowerCase() || "";

  // Check if status is extracted
  if (aStatus === "extracted") {
    // If no ai_grading_status or it's not_started, show "Ready for grading"
    if (!aiGradingStatus || aiGradingStatus.toLowerCase() === "not_started") {
      return "Ready for grading";
    }
    // Otherwise show ai_grading_status
    return aiGradingStatus;
  }

  // For any failure or non-extracted status, show assignment.status
  return assignmentStatus || "—";
}

function getGradingOutputIcon(aiGradingStatus?: string): { icon: React.ReactNode; label: string } {
  const status = aiGradingStatus?.toLowerCase() || "not_started";

  switch (status) {
    case "completed":
      return {
        icon: <CheckCircle className="h-5 w-5 text-green-500" />,
        label: "Completed",
      };
    case "failed":
      return {
        icon: <XCircle className="h-5 w-5 text-red-500" />,
        label: "Failed",
      };
    case "grading":
      return {
        icon: <Sparkles className="h-5 w-5 text-blue-500" />,
        label: "Grading",
      };
    case "not_started":
    default:
      return {
        icon: <Clock className="h-5 w-5 text-gray-400" />,
        label: "Not Started",
      };
  }
}

export function GradingResultPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [exportFormat, setExportFormat] = useState<"pdf" | "docx" | "html">("pdf");

  const { data: assignment, isLoading } = useQuery({
    queryKey: ["assignment", id],
    queryFn: () => assignmentsApi.get(id!),
    enabled: !!id,
  });

  const gradeMutation = useMutation({
    mutationFn: () => assignmentsApi.gradeUploadPhase({ file: new File([], "dummy") }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assignment", id] });
    },
  });

  const exportMutation = useMutation({
    mutationFn: () => {
      if (exportFormat === "html") {
        // For HTML, we'll return the graded_content as-is
        return Promise.resolve(new Blob([assignment?.graded_content || ""], { type: "text/html" }));
      }
      return assignmentsApi.export(id!, exportFormat);
    },
    onSuccess: (blob) => {
      // Download the file
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `graded-${assignment?.student_name || "assignment"}.${exportFormat === "html" ? "html" : exportFormat}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    },
  });

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Sparkles className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!assignment) {
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-4">
        <AlertTriangle className="h-12 w-12 text-yellow-500" />
        <p className="text-gray-600">Assignment not found</p>
        <Button variant="outline" onClick={() => navigate("/")}>
          Go back to Dashboard
        </Button>
      </div>
    );
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate("/history")} aria-label="Back">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="text-2xl font-bold text-gray-900 flex-1 truncate" title={assignment.title || "Assignment"}>
          {assignment.title || "Assignment"}
        </h1>
        <StatusBadge status={getDisplayStatus(assignment.status, assignment.ai_grading_status)} />
        <div className="flex items-center gap-2 flex-shrink-0">
          {!assignment.graded_at && (
            <Button onClick={() => gradeMutation.mutate()} disabled={gradeMutation.isPending}>
              {gradeMutation.isPending ? (
                <>
                  <Sparkles className="mr-2 h-4 w-4 animate-spin" />
                  Grading...
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-4 w-4" />
                  Start Grading
                </>
              )}
            </Button>
          )}

          {assignment.graded_at && (
            <>
              <select
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value as "pdf" | "docx" | "html")}
                className="rounded-md border px-3 py-2"
                aria-label="Export format"
              >
                <option value="pdf">PDF</option>
                <option value="docx">Word (DOCX)</option>
                <option value="html">HTML</option>
              </select>
              <Button onClick={() => exportMutation.mutate()} disabled={exportMutation.isPending}>
                <Download className="mr-2 h-4 w-4" />
                Export
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Information Card - Single Row */}
      <div className="mb-6">
        <Card>
          <CardContent className="pt-6">
            <div className="flex gap-4">
              {/* Student Name - 1 unit */}
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-gray-500 uppercase">Student Name</p>
                <p className="mt-1 text-sm font-medium text-gray-900 truncate" title={assignment.student_name || "—"}>
                  {assignment.student_name || "—"}
                </p>
              </div>
              {/* Template Name - 2 units */}
              <div className="flex-[2] min-w-0">
                <p className="text-xs font-medium text-gray-500 uppercase">Template</p>
                <p className="mt-1 text-sm font-medium text-gray-900 truncate" title={assignment.template_name || "—"}>
                  {assignment.template_name || "—"}
                </p>
              </div>
              {/* Uploaded Time - 1 unit */}
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-gray-500 uppercase">Uploaded Time</p>
                <p className="mt-1 text-sm text-gray-900">{formatDisplayDateTime(assignment.updated_at)}</p>
              </div>
              {/* Graded Time - 1 unit */}
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-gray-500 uppercase">Graded Time</p>
                <p className="mt-1 text-sm text-gray-900">{assignment.graded_at ? formatDisplayDateTime(assignment.graded_at) : "—"}</p>
              </div>
              {/* Grading Time - 1 unit */}
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-gray-500 uppercase">Grading Time</p>
                <p className="mt-1 text-sm text-gray-900">
                  {calculateGradingTime(assignment.created_at, assignment.graded_at, assignment.grading_time)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Background only - Show after information card */}
      {assignment.background && !assignment.instructions && (
        <div className="mb-6">
          <Card>
            <CardContent className="pt-4 pb-4">
              <label className="text-xs font-medium text-gray-500 uppercase">Background</label>
              <div className="mt-2 w-full text-sm text-gray-700 max-h-[5lh] overflow-y-auto whitespace-pre-wrap">
                {assignment.background}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Custom Instruction only - Show after information card */}
      {assignment.instructions && !assignment.background && (
        <div className="mb-6">
          <Card>
            <CardContent className="pt-4 pb-4">
              <label className="text-xs font-medium text-gray-500 uppercase">Custom Instruction</label>
              <div className="mt-2 w-full text-sm text-gray-700 max-h-[5lh] overflow-y-auto whitespace-pre-wrap">
                {assignment.instructions}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Both Background and Instructions - Show side by side below information card */}
      {assignment.background && assignment.instructions && (
        <div className="mb-6 grid gap-6 lg:grid-cols-2">
          <Card>
            <CardContent className="pt-4 pb-4">
              <label className="text-xs font-medium text-gray-500 uppercase">Background</label>
              <div className="mt-2 w-full text-sm text-gray-700 max-h-[5lh] overflow-y-auto whitespace-pre-wrap">
                {assignment.background}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-4 pb-4">
              <label className="text-xs font-medium text-gray-500 uppercase">Custom Instruction</label>
              <div className="mt-2 w-full text-sm text-gray-700 max-h-[5lh] overflow-y-auto whitespace-pre-wrap">
                {assignment.instructions}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Side-by-side: Student homework (left) and AI-graded output (right) - Now after background/instructions */}

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Student Homework
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 min-h-0">
            <div className="rounded-lg bg-gray-50 p-4 h-full overflow-auto max-h-[87.5vh]">
              <pre className="whitespace-pre-wrap text-sm text-gray-700">
                {assignment.extracted_text || "Content extraction pending..."}
              </pre>
            </div>
          </CardContent>
        </Card>

        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                {getGradingOutputIcon(assignment.ai_grading_status).icon}
                AI Graded Output
                {assignment.grading_model && (
                  <span className="text-xs italic text-gray-500 font-normal ml-2">by {assignment.grading_model}</span>
                )}
              </span>
              {assignment.graded_content && (
                <Button variant="outline" size="sm" onClick={() => navigate(`/grade/${id}/revise`)}>
                  <Pencil className="mr-1 h-4 w-4" />
                  Revise
                </Button>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 min-h-0">
            <div className="rounded-lg border bg-gray-50 p-4 h-full overflow-auto max-h-[87.5vh]">
              {assignment.graded_content ? (
                <GradedOutputDisplay html={assignment.graded_content} />
              ) : assignment.grading_results ? (
                <GradingResultsView results={assignment.grading_results as GradingResults} />
              ) : assignment.graded_at ? (
                <p className="text-gray-500">Grading results are available for export (PDF/Word).</p>
              ) : (
                <p className="text-gray-500">Complete grading to see AI feedback here.</p>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-4">
        {assignment.total_score != null && (
          <Card>
            <CardContent className="flex items-center gap-2 pt-4">
              <Star className="h-5 w-5 text-yellow-500" />
              <span className="text-2xl font-bold text-primary">{assignment.total_score}</span>
              <span className="text-sm text-gray-500">Score</span>
            </CardContent>
          </Card>
        )}
      </div>

      {/* Score and other metadata */}
      <div className="mt-6 flex flex-wrap items-center gap-4">
        {assignment.total_score != null && (
          <Card>
            <CardContent className="flex items-center gap-2 pt-4">
              <Star className="h-5 w-5 text-yellow-500" />
              <span className="text-2xl font-bold text-primary">{assignment.total_score}</span>
              <span className="text-sm text-gray-500">Score</span>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

function GradingResultsView({ results }: { results: GradingResults }) {
  const items = results.items ?? [];
  const sectionScores = results.section_scores ?? {};
  const overall = results.overall_comment;

  return (
    <div className="space-y-4 text-sm">
      {Object.keys(sectionScores).length > 0 && (
        <div className="flex flex-wrap gap-2">
          {Object.entries(sectionScores).map(([key, s]) => (
            <span key={key} className="rounded bg-gray-200 px-2 py-1">
              {key}: {s.correct}/{s.total}
              {s.encouragement ? ` — ${s.encouragement}` : ""}
            </span>
          ))}
        </div>
      )}
      {items.map((item, i) => (
        <div key={i} className="rounded border border-gray-200 p-3">
          <p className="font-medium">
            Q{item.question_number} ({item.question_type})
          </p>
          <p className="text-gray-700">Student: {item.student_answer}</p>
          {item.correct_answer != null && <p className="text-gray-600">Correct: {item.correct_answer}</p>}
          <p className={item.is_correct ? "text-green-600" : "text-red-600"}>{item.is_correct ? "Correct" : "Incorrect"}</p>
          {item.comment && <p className="mt-1 text-gray-600">{item.comment}</p>}
        </div>
      ))}
      {overall && (
        <div className="rounded border border-primary/20 bg-primary/5 p-3">
          <p className="font-medium text-primary">Overall comment</p>
          <p className="text-gray-700">{overall}</p>
        </div>
      )}
    </div>
  );
}
