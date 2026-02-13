/**
 * Dashboard page - main landing page with greeting and upload
 */

import React, { useCallback, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import type { FileRejection } from "react-dropzone";
import { GreetingBanner } from "@/components/common/GreetingBanner";
import { FileUpload } from "@/components/common/FileUpload";
import { GradingProgressDialog } from "@/components/common/GradingProgressDialog";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { assignmentsApi, templatesApi, studentsApi } from "@/services/api";
import { useNotification } from "@/contexts/NotificationContext";
import { useGradingProgress } from "@/hooks/useGradingProgress";
import { FileText, Upload, Clock, AlertCircle, CheckCircle, Sparkles } from "lucide-react";

export function Dashboard() {
  const navigate = useNavigate();
  const { show: showNotification } = useNotification();
  const {
    progressOpen,
    progressStep,
    progressError,
    phaseElapsedMs,
    totalElapsedMs,
    phaseTimes,
    startGradingProcess,
    handleCancelGrading,
    closeProgress,
  } = useGradingProgress();

  const [files, setFiles] = useState<File[]>([]);
  const [backgroundInfo, setBackgroundInfo] = useState("");
  const [studentName, setStudentName] = useState("");
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");

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
      // Batch upload for multiple files
      return assignmentsApi.batchUpload({
        files,
        background_info: backgroundInfo || undefined,
        template_id: selectedTemplate || undefined,
      });
    },
    onSuccess: () => {
      navigate("/history");
    },
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
      // Single file: use phased grading
      // Find student ID if student name is selected
      let studentId: number | undefined;
      if (studentName) {
        const selectedStudent = students.find((s) => s.name === studentName);
        if (selectedStudent) {
          studentId = selectedStudent.id;
        }
      }

      const assignmentId = await startGradingProcess({
        file: files[0],
        studentId,
        studentName: studentName || undefined,
        background: backgroundInfo || undefined,
        templateId: selectedTemplate || undefined,
      });

      if (assignmentId) {
        // Auto-redirect to result page
        navigate(`/grade/${assignmentId}`);
      } else if (progressError) {
        showNotification({ type: "error", message: progressError });
      }
      return;
    }

    // Multiple files: batch upload
    uploadMutation.mutate();
  };

  const isProcessing = uploadMutation.isPending || progressOpen;

  return (
    <div>
      {/* Progress dialog for single-file grading */}
      <GradingProgressDialog
        open={progressOpen}
        step={progressStep}
        error={progressError}
        phaseElapsedMs={phaseElapsedMs}
        totalElapsedMs={totalElapsedMs}
        phaseTimes={phaseTimes}
        onCancel={handleCancelGrading}
        onClose={closeProgress}
      />

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

const DASHBOARD_ACCEPT = {
  "text/plain": [".txt"],
  "application/pdf": [".pdf"],
  "application/msword": [".doc"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
};

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
