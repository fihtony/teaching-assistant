/**
 * Dashboard page - main landing page with greeting and upload
 */

import React, { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import type { FileRejection } from "react-dropzone";
import { GreetingBanner } from "@/components/common/GreetingBanner";
import { FileUpload } from "@/components/common/FileUpload";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { assignmentsApi, templatesApi } from "@/services/api";
import { useNotification } from "@/contexts/NotificationContext";
import { FileText, Clock, CheckCircle, AlertCircle, Upload, Sparkles } from "lucide-react";

const DASHBOARD_ACCEPT = {
  "text/plain": [".txt"],
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
  "application/msword": [".doc"],
};

type ProgressStep =
  | "uploading"
  | "extracting"
  | "preparing"
  | "grading"
  | "completed"
  | null;

const PROGRESS_LABELS: Record<NonNullable<ProgressStep>, string> = {
  uploading: "Uploading file...",
  extracting: "Extracting text...",
  preparing: "Preparing grading instructions...",
  grading: "AI grading...",
  completed: "Completed",
};

export function Dashboard() {
  const navigate = useNavigate();
  const { show: showNotification } = useNotification();
  const [files, setFiles] = useState<File[]>([]);
  const [backgroundInfo, setBackgroundInfo] = useState("");
  const [studentName, setStudentName] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const [progressOpen, setProgressOpen] = useState(false);
  const [progressStep, setProgressStep] = useState<ProgressStep>(null);
  const [progressError, setProgressError] = useState<string | null>(null);

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

  const handleSubmit = async () => {
    if (files.length === 0) return;
    if (files.length === 1) {
      setProgressError(null);
      setProgressOpen(true);
      setProgressStep("uploading");
      try {
        const assignment = await uploadMutation.mutateAsync();
        const id = String((assignment as { id: number }).id);
        setProgressStep("extracting");
        await new Promise((r) => setTimeout(r, 400));
        setProgressStep("preparing");
        await new Promise((r) => setTimeout(r, 300));
        setProgressStep("grading");
        await gradeMutation.mutateAsync({
          id,
          background: backgroundInfo || undefined,
          templateId: selectedTemplate ? Number(selectedTemplate) : undefined,
        });
        setProgressStep("completed");
        await new Promise((r) => setTimeout(r, 600));
        navigate(`/grade/${id}`);
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : "Something went wrong";
        setProgressError(message);
        showNotification({ type: "error", message });
      } finally {
        setProgressOpen(false);
        setProgressStep(null);
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
              <CardDescription>
                {progressError ? "An error occurred." : "Please wait while we process the assignment."}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {progressError ? (
                <p className="text-sm text-red-600">{progressError}</p>
              ) : (
                <ul className="space-y-2">
                  {(["uploading", "extracting", "preparing", "grading", "completed"] as const).map((step) => {
                    const isActive = progressStep === step;
                    const order = ["uploading", "extracting", "preparing", "grading", "completed"] as const;
                    const stepIndex = order.indexOf(step);
                    const currentIndex = progressStep ? order.indexOf(progressStep) : -1;
                    const isDoneStep = currentIndex > stepIndex || (step === "completed" && progressStep === "completed");
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
                        {PROGRESS_LABELS[step]}
                      </li>
                    );
                  })}
                </ul>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      <GreetingBanner />

      {/* Stats overview */}
      <div className="mb-8 grid gap-4 md:grid-cols-4">
        <StatCard icon={<FileText className="h-5 w-5" />} label="Total Graded" value="128" color="blue" />
        <StatCard icon={<Clock className="h-5 w-5" />} label="Pending" value="5" color="yellow" />
        <StatCard icon={<CheckCircle className="h-5 w-5" />} label="This Week" value="23" color="green" />
        <StatCard icon={<AlertCircle className="h-5 w-5" />} label="Needs Review" value="2" color="red" />
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

              {files.length === 1 && (
                <div>
                  <Label htmlFor="studentName">Student Name (optional)</Label>
                  <Input
                    id="studentName"
                    value={studentName}
                    onChange={(e) => setStudentName(e.target.value)}
                    placeholder="Enter student name"
                    className="mt-1"
                  />
                </div>
              )}

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
                <Label htmlFor="template">Grading Instruction</Label>
                <select
                  id="template"
                  value={selectedTemplate}
                  onChange={(e) => setSelectedTemplate(e.target.value)}
                  className="mt-1 w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                >
                  <option value="">Default Template</option>
                  {templates?.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.name}
                    </option>
                  ))}
                </select>
              </div>

              <Button onClick={handleSubmit} disabled={files.length === 0 || isProcessing} className="w-full" size="lg">
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
              <Button variant="outline" className="w-full justify-start" onClick={() => navigate("/essay-grading")}>
                <FileText className="mr-2 h-4 w-4" />
                New Essay Grading
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
