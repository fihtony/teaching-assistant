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
import { ArrowLeft, Download, FileText, CheckCircle, AlertTriangle, Star, Sparkles } from "lucide-react";

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

export function GradingPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [exportFormat, setExportFormat] = useState<"pdf" | "docx">("pdf");

  const { data: assignment, isLoading } = useQuery({
    queryKey: ["assignment", id],
    queryFn: () => assignmentsApi.get(id!),
    enabled: !!id,
  });

  const gradeMutation = useMutation({
    mutationFn: () => assignmentsApi.grade(id!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["assignment", id] });
    },
  });

  const exportMutation = useMutation({
    mutationFn: () => assignmentsApi.export(id!, exportFormat),
    onSuccess: (blob) => {
      // Download the file
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `graded-${assignment?.title || assignment?.student_name || "assignment"}.${exportFormat}`;
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
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate(-1)}>
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{assignment.title || assignment.student_name || "Student Assignment"}</h1>
            <p className="text-sm text-gray-500">Uploaded: {new Date(assignment.created_at).toLocaleDateString()}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {assignment.status !== "completed" && (
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

          {assignment.status === "completed" && (
            <>
              <select
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value as "pdf" | "docx")}
                className="rounded-md border px-3 py-2"
              >
                <option value="pdf">PDF</option>
                <option value="docx">Word</option>
              </select>
              <Button onClick={() => exportMutation.mutate()} disabled={exportMutation.isPending}>
                <Download className="mr-2 h-4 w-4" />
                Export
              </Button>
            </>
          )}
        </div>
      </div>

      {/* Status badge */}
      <div className="mb-6">
        <StatusBadge status={assignment.status} />
      </div>

      {/* Side-by-side: Student homework (left) and AI-graded output (right) */}
      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Student Homework
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 min-h-0">
            <div className="rounded-lg bg-gray-50 p-4 h-full overflow-auto max-h-[70vh]">
              <pre className="whitespace-pre-wrap text-sm text-gray-700">
                {assignment.extracted_text || "Content extraction pending..."}
              </pre>
            </div>
          </CardContent>
        </Card>

        <Card className="flex flex-col">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              AI Graded Output
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 min-h-0">
            <div className="rounded-lg border bg-gray-50 p-4 h-full overflow-auto max-h-[70vh]">
              {assignment.graded_content ? (
                <div
                  className="graded-output prose prose-sm max-w-none"
                  dangerouslySetInnerHTML={{ __html: assignment.graded_content }}
                />
              ) : assignment.grading_results ? (
                <GradingResultsView results={assignment.grading_results as GradingResults} />
              ) : assignment.status === "completed" ? (
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
        {(assignment as { background?: string }).background && (
          <p className="text-sm text-gray-600">
            <span className="font-medium">Background:</span> {(assignment as { background?: string }).background}
          </p>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    uploaded: "bg-yellow-100 text-yellow-800",
    pending: "bg-yellow-100 text-yellow-800",
    processing: "bg-blue-100 text-blue-800",
    grading: "bg-blue-100 text-blue-800",
    completed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
  };

  return (
    <span className={`inline-flex rounded-full px-3 py-1 text-sm font-medium ${styles[status] || styles.pending}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
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
          <p className={item.is_correct ? "text-green-600" : "text-red-600"}>
            {item.is_correct ? "Correct" : "Incorrect"}
          </p>
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
