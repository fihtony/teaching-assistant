/**
 * Dashboard page - main landing page with greeting and upload
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import type { FileRejection } from "react-dropzone";
import { GreetingBanner } from "@/components/common/GreetingBanner";
import { FileUpload } from "@/components/common/FileUpload";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { assignmentsApi, templatesApi, studentsApi } from "@/services/api";
import { useNotification } from "@/contexts/NotificationContext";
import { FileText, Clock, CheckCircle, AlertCircle, Upload, Sparkles } from "lucide-react";

function formatElapsedMs(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

function formatPhaseTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  if (totalSeconds < 60) {
    return `${totalSeconds}s`;
  }
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}m ${s}s`;
}

const DASHBOARD_ACCEPT = {
  "text/plain": [".txt"],
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "application/msword": [".doc"],
};

type ProgressStep = "uploading" | "extracting" | "preparing" | "grading" | "completed" | null;

const PROGRESS_LABELS: Record<NonNullable<ProgressStep>, string> = {
  uploading: "Uploading file",
  extracting: "Analysing context",
  preparing: "Analysing context",
  grading: "AI grading",
  completed: "Prepare report",
};

export function Dashboard() {
  const navigate = useNavigate();
  const { show: showNotification } = useNotification();
  const [files, setFiles] = useState<File[]>([]);
  const [backgroundInfo, setBackgroundInfo] = useState("");
  const [studentName, setStudentName] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const [phaseTimes, setPhaseTimes] = useState<Record<string, number>>({});
  const [progressOpen, setProgressOpen] = useState(false);
  const [progressStep, setProgressStep] = useState<ProgressStep>(null);
  const [progressError, setProgressError] = useState<string | null>(null);
  const [phaseElapsedMs, setPhaseElapsedMs] = useState<number | null>(null);
  const [totalElapsedMs, setTotalElapsedMs] = useState(0);
  const startTimeRef = useRef<number | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const cancelledRef = useRef(false);

  const handleUnsupportedFiles = useCallback(
    (rejected: FileRejection[], acceptedFormatsLabel: string) => {
      const names = rejected.map((r) => r.file.name).join(", ");
      showNotification({
        type: "warning",
        message: `${names} ${rejected.length > 1 ? "are" : "is"} not supported. Only ${acceptedFormatsLabel} ${rejected.length > 1 ? "are" : "is"} supported.`,
      });
    },
    [showNotification],
  );

  const { data: templates } = useQuery({
    queryKey: ["templates"],
    queryFn: templatesApi.list,
  });

  const { data: students = [] } = useQuery({
    queryKey: ["students"],
    queryFn: () => studentsApi.list(),
  });

  const { data: dashboardStats = { total_graded: 0, pending: 0, this_week: 0, needs_review: 0 } } = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: assignmentsApi.getStats,
  });

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (files.length === 1) {
        return assignmentsApi.upload({
          file: files[0],
          student_name: studentName || undefined,
          background_info: backgroundInfo || undefined,
          template_id: selectedTemplate || undefined,
        });
      } else {
        return assignmentsApi.batchUpload({
          files,
          background_info: backgroundInfo || undefined,
          template_id: selectedTemplate || undefined,
        });
      }
    },
    onSuccess: (data) => {
      if (files.length !== 1) {
        navigate("/history");
      }
      // When single file, progress dialog flow handles navigation
    },
  });

  const gradeMutation = useMutation({
    mutationFn: ({ id, background, templateId }: { id: string; background?: string; templateId?: string }) =>
      assignmentsApi.grade(id, {
        background: background || undefined,
        template_id: templateId || undefined,
      }),
  });

  const handleFilesSelected = (newFiles: File[]) => {
    setFiles((prev) => [...prev, ...newFiles]);
  };

  const handleRemoveFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  // Update total elapsed every 500ms while progress dialog is open
  useEffect(() => {
    if (!progressOpen || progressError) return;
    const start = startTimeRef.current;
    if (start == null) return;
    const interval = setInterval(() => {
      setTotalElapsedMs(Date.now() - start);
    }, 500);
    return () => clearInterval(interval);
  }, [progressOpen, progressError]);

  const handleCancelGrading = useCallback(() => {
    cancelledRef.current = true;
    abortControllerRef.current?.abort();
  }, []);

  const handleSubmit = async () => {
    if (files.length === 0) return;
    if (files.length === 1) {
      setProgressError(null);
      setPhaseElapsedMs(null);
      setTotalElapsedMs(0);
      setPhaseTimes({});
      setProgressOpen(true);
      setProgressStep("uploading");
      startTimeRef.current = Date.now();
      cancelledRef.current = false;
      abortControllerRef.current = new AbortController();
      const signal = abortControllerRef.current.signal;
      try {
        const uploadRes = await assignmentsApi.gradeUploadPhase(
          {
            file: files[0],
            student_name: studentName || undefined,
            background: backgroundInfo || undefined,
            template_id: selectedTemplate ? Number(selectedTemplate) : undefined,
          },
          signal,
        );
        if (cancelledRef.current) return;
        if (uploadRes.error) {
          setProgressError(uploadRes.error);
          setPhaseElapsedMs(uploadRes.elapsed_ms ?? null);
          return;
        }
        setPhaseElapsedMs(uploadRes.elapsed_ms ?? null);
        if (uploadRes.elapsed_ms != null) {
          setPhaseTimes((prev) => ({ ...prev, uploading: uploadRes.elapsed_ms as number }));
        }
        const assignmentId = uploadRes.assignment_id!;
        setProgressStep("extracting");
        const analyzeRes = await assignmentsApi.analyzeContextPhase(assignmentId, signal);
        if (cancelledRef.current) return;
        if (analyzeRes.error) {
          setProgressError(analyzeRes.error);
          setPhaseElapsedMs(analyzeRes.elapsed_ms ?? null);
          return;
        }
        setPhaseElapsedMs(analyzeRes.elapsed_ms ?? null);
        if (analyzeRes.elapsed_ms != null) {
          setPhaseTimes((prev) => ({ ...prev, extracting: analyzeRes.elapsed_ms as number }));
        }
        setProgressStep("grading");
        const runRes = await assignmentsApi.runGradingPhase(assignmentId, signal);
        if (cancelledRef.current) return;
        if (runRes.error) {
          setProgressError(runRes.error);
          setPhaseElapsedMs(runRes.elapsed_ms ?? null);
          return;
        }
        setPhaseElapsedMs(runRes.elapsed_ms ?? null);
        if (runRes.elapsed_ms != null) {
          setPhaseTimes((prev) => ({ ...prev, grading: runRes.elapsed_ms as number }));
        }
        setProgressStep("completed");
        await new Promise((r) => setTimeout(r, 1500));
        if (cancelledRef.current) return;
        navigate(`/grade/${assignmentId}`);
      } catch (err: unknown) {
        if (cancelledRef.current) return;
        const isAbort =
          err instanceof Error &&
          (err.name === "CanceledError" || err.name === "AbortError" || (err as { code?: string }).code === "ERR_CANCELED");
        if (isAbort) return;
        const message = err instanceof Error ? err.message : "Something went wrong";
        setProgressError(message);
        showNotification({ type: "error", message });
      } finally {
        setProgressOpen(false);
        setProgressStep(null);
        setPhaseElapsedMs(null);
        setTotalElapsedMs(0);
        setPhaseTimes({});
        startTimeRef.current = null;
        abortControllerRef.current = null;
      }
      return;
    }
    uploadMutation.mutate();
  };

  const isProcessing = uploadMutation.isPending || progressOpen;

  return (
    <div>
      {/* Progress dialog for single-file grading */}
      {progressOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <Card className="w-full max-w-md mx-4 shadow-xl">
            <CardHeader>
              <CardTitle>Grading in progress</CardTitle>
              <CardDescription>{progressError ? "An error occurred." : "Please wait while we process the assignment."}</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {progressError ? (
                <div className="space-y-3">
                  <p className="text-sm text-red-600">{progressError}</p>
                  {phaseElapsedMs != null && <p className="text-xs text-gray-500">Elapsed: {(phaseElapsedMs / 1000).toFixed(1)}s</p>}
                  <Button
                    variant="outline"
                    onClick={() => {
                      setProgressOpen(false);
                      setProgressError(null);
                      setProgressStep(null);
                    }}
                  >
                    Close
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  <ul className="space-y-2">
                    {(["uploading", "extracting", "grading", "completed"] as const).map((step) => {
                      const isActive = progressStep === step;
                      const order = ["uploading", "extracting", "grading", "completed"] as const;
                      const stepIndex = order.indexOf(step);
                      const currentIndex = progressStep ? order.indexOf(progressStep) : -1;
                      const isDoneStep = currentIndex > stepIndex || (step === "completed" && progressStep === "completed");
                      const phaseTime = phaseTimes[step];
                      return (
                        <li
                          key={step}
                          className={`flex items-center gap-2 text-sm ${isActive ? "font-medium text-primary" : isDoneStep ? "text-gray-500" : "text-gray-400"}`}
                        >
                          {isDoneStep ? (
                            <CheckCircle className="h-4 w-4 shrink-0 text-green-500" />
                          ) : isActive ? (
                            <Sparkles className="h-4 w-4 shrink-0 animate-spin text-primary" />
                          ) : (
                            <span className="h-4 w-4 shrink-0 rounded-full border-2 border-gray-300" />
                          )}
                          <span>
                            {PROGRESS_LABELS[step]}
                            {isDoneStep && phaseTime && <span className="ml-2 italic text-xs">- {formatPhaseTime(phaseTime)}</span>}
                          </span>
                        </li>
                      );
                    })}
                  </ul>
                  <div className="flex items-center justify-between gap-2">
                    <p className="text-xs text-gray-500">Total: {formatElapsedMs(totalElapsedMs)}</p>
                    <Button variant="outline" size="sm" onClick={handleCancelGrading}>
                      Cancel
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      <GreetingBanner />

      {/* Stats overview */}
      <div className="mb-8 grid gap-4 md:grid-cols-4">
        <StatCard icon={<FileText className="h-5 w-5" />} label="Total Graded" value={String(dashboardStats.total_graded)} color="blue" />
        <StatCard icon={<Clock className="h-5 w-5" />} label="Pending" value={String(dashboardStats.pending)} color="yellow" />
        <StatCard icon={<CheckCircle className="h-5 w-5" />} label="This Week" value={String(dashboardStats.this_week)} color="green" />
        <StatCard icon={<AlertCircle className="h-5 w-5" />} label="Needs Review" value={String(dashboardStats.needs_review)} color="red" />
      </div>

      {/* Upload section */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Upload className="h-5 w-5" />
                Upload Assignment
              </CardTitle>
              <CardDescription>Upload student assignments for AI-powered grading</CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <FileUpload
                onFilesSelected={handleFilesSelected}
                selectedFiles={files}
                onRemoveFile={handleRemoveFile}
                disabled={isProcessing}
                accept={DASHBOARD_ACCEPT}
                acceptedFormatsLabel="TXT, PDF, Word (.DOCX, .DOC)"
                onUnsupportedFiles={handleUnsupportedFiles}
              />

              <div>
                <Label>Student Name</Label>
                <select
                  aria-label="Select student name"
                  value={studentName}
                  onChange={(e) => {
                    setStudentName(e.target.value);
                  }}
                  disabled={isProcessing}
                  className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm disabled:bg-gray-100 disabled:text-gray-400 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="">-- Select a student --</option>
                  {students.map((student) => (
                    <option key={student.id} value={student.name}>
                      {student.name}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <Label htmlFor="backgroundInfo">Background Information</Label>
                <Textarea
                  id="backgroundInfo"
                  value={backgroundInfo}
                  onChange={(e) => setBackgroundInfo(e.target.value)}
                  placeholder="e.g., 'Alice in Wonderland book report, Chapter 1-5 analysis'"
                  className="mt-1"
                  rows={3}
                />
                <p className="mt-1 text-xs text-gray-500">AI will search for referenced books/articles to provide better context</p>
              </div>

              <div>
                <Label htmlFor="template">Instruction template</Label>
                <select
                  id="template"
                  title="Instruction template"
                  value={selectedTemplate}
                  onChange={(e) => setSelectedTemplate(e.target.value)}
                  disabled={isProcessing}
                  className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm disabled:bg-gray-100 disabled:text-gray-400 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="">-- Select a template --</option>
                  {templates?.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </div>

              <Button
                onClick={handleSubmit}
                disabled={files.length === 0 || !studentName || !selectedTemplate || isProcessing}
                className="w-full"
                size="lg"
              >
                {isProcessing ? (
                  <>
                    <Sparkles className="mr-2 h-5 w-5 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Sparkles className="mr-2 h-5 w-5" />
                    Start AI Grading
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Quick actions */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button variant="outline" className="w-full justify-start" onClick={() => navigate("/history")}>
                <FileText className="mr-2 h-4 w-4" />
                View History
              </Button>
              <Button variant="outline" className="w-full justify-start" onClick={() => navigate("/grading")}>
                <FileText className="mr-2 h-4 w-4" />
                Assignment Grading
              </Button>
              <Button variant="outline" className="w-full justify-start" onClick={() => navigate("/templates")}>
                <FileText className="mr-2 h-4 w-4" />
                Manage Instructions
              </Button>
              <Button variant="outline" className="w-full justify-start" onClick={() => navigate("/settings")}>
                <FileText className="mr-2 h-4 w-4" />
                Settings
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Tips</CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-gray-600">
                <li className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  Add background info for better grading context
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  Batch upload multiple files for efficient grading
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-primary">•</span>
                  Create custom instructions for different assignment types
                </li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: "blue" | "yellow" | "green" | "red";
}

function StatCard({ icon, label, value, color }: StatCardProps) {
  const colors = {
    blue: "bg-blue-50 text-blue-600",
    yellow: "bg-yellow-50 text-yellow-600",
    green: "bg-green-50 text-green-600",
    red: "bg-red-50 text-red-600",
  };

  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-4">
        <div className={`rounded-lg p-3 ${colors[color]}`}>{icon}</div>
        <div>
          <p className="text-2xl font-bold text-gray-900">{value}</p>
          <p className="text-sm text-gray-500">{label}</p>
        </div>
      </CardContent>
    </Card>
  );
}
