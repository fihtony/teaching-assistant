/**
 * Grading page - view and interact with graded assignments
 */

import { useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation } from "@tanstack/react-query";
import { assignmentsApi } from "@/services/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Download, FileText, CheckCircle, AlertTriangle, Star, Sparkles } from "lucide-react";

export function GradingPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [exportFormat, setExportFormat] = useState<"pdf" | "docx">("pdf");

  const { data: assignment, isLoading } = useQuery({
    queryKey: ["assignment", id],
    queryFn: () => assignmentsApi.get(id!),
    enabled: !!id,
  });

  const gradeMutation = useMutation({
    mutationFn: () => assignmentsApi.grade(id!),
  });

  const exportMutation = useMutation({
    mutationFn: () => assignmentsApi.export(id!, exportFormat),
    onSuccess: (blob) => {
      // Download the file
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `graded-${assignment?.student_name || "assignment"}.${exportFormat}`;
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
            <h1 className="text-2xl font-bold text-gray-900">{assignment.student_name || "Student Assignment"}</h1>
            <p className="text-sm text-gray-500">Uploaded: {new Date(assignment.created_at).toLocaleDateString()}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {assignment.status === "pending" && (
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

      {/* Main content */}
      <div className="grid gap-6 lg:grid-cols-3">
        {/* Original content */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Original Content
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg bg-gray-50 p-4">
              <pre className="whitespace-pre-wrap text-sm text-gray-700">
                {assignment.extracted_text || "Content extraction pending..."}
              </pre>
            </div>
          </CardContent>
        </Card>

        {/* Grading info */}
        <div className="space-y-4">
          {assignment.total_score !== null && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Star className="h-5 w-5 text-yellow-500" />
                  Score
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-4xl font-bold text-primary">{assignment.total_score}</p>
              </CardContent>
            </Card>
          )}

          {assignment.background_info && (
            <Card>
              <CardHeader>
                <CardTitle>Background Info</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-gray-600">{assignment.background_info}</p>
              </CardContent>
            </Card>
          )}

          {assignment.grading_context && (
            <Card>
              <CardHeader>
                <CardTitle>Referenced Materials</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {assignment.grading_context.articles?.map((article: any, i: number) => (
                    <div key={i} className="rounded-lg border bg-gray-50 p-3 text-sm">
                      <p className="font-medium">{article.title}</p>
                      {article.author && <p className="text-gray-500">by {article.author}</p>}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* Graded content */}
      {assignment.graded_content && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              Graded Content
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="prose max-w-none" dangerouslySetInnerHTML={{ __html: assignment.graded_content }} />
          </CardContent>
        </Card>
      )}

      {/* Feedback */}
      {assignment.feedback && (
        <Card className="mt-6">
          <CardHeader>
            <CardTitle>Overall Feedback</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-gray-700">{assignment.feedback}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    processing: "bg-blue-100 text-blue-800",
    completed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
  };

  return (
    <span className={`inline-flex rounded-full px-3 py-1 text-sm font-medium ${styles[status] || styles.pending}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
