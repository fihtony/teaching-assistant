/**
 * Assignment Grading page - AI-powered assignment grading with full page layout
 */

import { useCallback, useState, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import type { FileRejection } from "react-dropzone";
import * as gradingApi from "@/services/gradingApi";
import { templatesApi, studentsApi } from "@/services/api";
import { useNotification } from "@/contexts/NotificationContext";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { FileUpload } from "@/components/common/FileUpload";
import { GradingProgressDialog } from "@/components/common/GradingProgressDialog";
import { useGradingProgress } from "@/hooks/useGradingProgress";
import { FileText, Sparkles, Loader2 } from "lucide-react";

const CONTENT_ACCEPT = {
  "text/plain": [".txt"],
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
};

export function GradingPage() {
  const navigate = useNavigate();
  const { show: showNotification } = useNotification();
  const [searchParams] = useSearchParams();
  const resultId = searchParams.get("result");

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

  const [studentName, setStudentName] = useState("");
  const [useCustomStudentName, setUseCustomStudentName] = useState(false);
  const [customStudentName, setCustomStudentName] = useState("");
  const [background, setBackground] = useState("");
  const [contentText, setContentText] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const [additionalInstructions, setAdditionalInstructions] = useState("");

  // Fetch templates
  const { data: templates } = useQuery({
    queryKey: ["templates"],
    queryFn: templatesApi.list,
  });

  // Fetch students list
  const { data: students = [] } = useQuery({
    queryKey: ["students"],
    queryFn: () => studentsApi.list(),
  });

  // Fetch result from history if resultId is provided
  const { data: historyResult, isLoading: isLoadingHistory } = useQuery({
    queryKey: ["essay-grading-result", resultId],
    queryFn: () => gradingApi.getGradingHistoryById(resultId!),
    enabled: !!resultId,
  });

  useEffect(() => {
    if (historyResult) {
      setStudentName(historyResult.student_name || "");
      setBackground(historyResult.recent_activity || "");
      setContentText(historyResult.essay_text || "");
    }
  }, [historyResult]);

  const handleFilesSelected = (newFiles: File[]) => {
    setFiles(newFiles.slice(0, 1)); // Only allow one file
  };

  const handleRemoveFile = () => {
    setFiles([]);
  };

  const handleStartGrading = async () => {
    if (!contentText && files.length === 0) {
      showNotification({
        type: "warning",
        message: "Please provide content - either paste text or upload a file",
      });
      return;
    }

    const finalStudentName = useCustomStudentName ? customStudentName : studentName;
    // Find student ID if student name is selected from list
    let studentId: number | undefined;
    if (!useCustomStudentName && studentName) {
      const selectedStudent = students.find((s) => s.name === studentName);
      if (selectedStudent) {
        studentId = selectedStudent.id;
      }
    }

    const assignmentId = await startGradingProcess({
      file: files.length > 0 ? files[0] : undefined,
      studentId,
      studentName: finalStudentName || undefined,
      background: background || undefined,
      templateId: selectedTemplate || undefined,
      contentText: contentText || undefined,
      instructions: additionalInstructions || undefined,
    });

    if (assignmentId) {
      // Auto-redirect to result page
      navigate(`/grade/${assignmentId}`);
    } else if (progressError) {
      showNotification({
        type: "error",
        message: progressError,
      });
    }
  };

  if (isLoadingHistory) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-gray-500">Loading assessment...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      {/* Header with title and button */}
      <div className="mb-5 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Assignment Grading</h1>
          <p className="mt-1 text-sm text-gray-500">AI-powered assessment with detailed feedback</p>
        </div>
        <Button
          onClick={handleStartGrading}
          disabled={progressOpen || (!contentText && files.length === 0)}
          size="lg"
          className="h-12 px-8"
        >
          {progressOpen ? (
            <>
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              Grading...
            </>
          ) : (
            <>
              <Sparkles className="mr-2 h-5 w-5" />
              Start AI Grading
            </>
          )}
        </Button>
      </div>

      {/* Main content - two columns for student info and grading options */}
      <div className="mb-2 grid gap-3 lg:grid-cols-2">
        {/* Left: Student Information */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Student Information
            </CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col space-y-2">
            {/* Student Name Selection */}
            <div className="space-y-2">
              <Label>Student Name</Label>
              {/* Select list */}
              <select
                aria-label="Select student name"
                value={useCustomStudentName ? "" : studentName}
                onChange={(e) => {
                  setStudentName(e.target.value);
                }}
                disabled={useCustomStudentName}
                className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm disabled:bg-gray-100 disabled:text-gray-400 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="">-- Select a student --</option>
                {students.map((student) => (
                  <option key={student.id} value={student.name}>
                    {student.name}
                  </option>
                ))}
              </select>

              {/* Checkbox + Custom input - separate row with fixed height */}
              <div className="flex items-center gap-2 h-10">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={useCustomStudentName}
                    onChange={(e) => {
                      setUseCustomStudentName(e.target.checked);
                      if (e.target.checked) {
                        setStudentName("");
                      } else {
                        setCustomStudentName("");
                      }
                    }}
                    className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-1"
                  />
                  <span className="text-sm font-medium text-gray-700">Enter Student Name</span>
                </label>
                {useCustomStudentName && (
                  <Input
                    type="text"
                    value={customStudentName}
                    onChange={(e) => setCustomStudentName(e.target.value)}
                    placeholder="Student name"
                    className="flex-1 h-8"
                  />
                )}
              </div>
            </div>

            {/* Background */}
            <div className="space-y-2 mt-auto flex flex-col flex-1">
              <Label htmlFor="background">Background</Label>
              <Textarea
                id="background"
                value={background}
                onChange={(e) => setBackground(e.target.value)}
                placeholder="e.g., 'Reading Alice in Wonderland, learning about descriptive writing'"
                className="mt-1 flex-1"
                rows={4}
              />
            </div>
          </CardContent>
        </Card>

        {/* Right: Grading Options */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">Grading Options</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col space-y-4">
            <div className="space-y-2">
              <Label htmlFor="template">Grading Instruction</Label>
              <select
                id="template"
                value={selectedTemplate}
                onChange={(e) => setSelectedTemplate(e.target.value)}
                className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
              >
                <option value="">-- Select a template --</option>
                {templates?.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2 mt-auto flex flex-col flex-1">
              <Label htmlFor="additionalInstructions">Additional Instructions</Label>
              <Textarea
                id="additionalInstructions"
                value={additionalInstructions}
                onChange={(e) => setAdditionalInstructions(e.target.value)}
                placeholder="e.g., 'Focus on grammar and spelling, provide detailed feedback'"
                className="mt-1 flex-1"
                rows={6}
              />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Full width content section */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Content
          </CardTitle>
          <CardDescription>Paste content text or upload a file</CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 pt-0">
          {files.length === 0 ? (
            <div>
              <Textarea
                id="contentText"
                value={contentText}
                onChange={(e) => setContentText(e.target.value)}
                placeholder="Paste the content here..."
                className="mt-2 min-h-[300px] font-mono text-sm"
                rows={15}
              />
            </div>
          ) : (
            <FileUpload
              onFilesSelected={handleFilesSelected}
              selectedFiles={files}
              onRemoveFile={handleRemoveFile}
              disabled={progressOpen}
              accept={CONTENT_ACCEPT}
              acceptedFormatsLabel="TXT, PDF, Word (.DOCX)"
              onUnsupportedFiles={handleUnsupportedFiles}
            />
          )}

          {files.length === 0 && (
            <>
              <div className="text-center text-sm text-gray-500">or</div>
              <FileUpload
                onFilesSelected={handleFilesSelected}
                selectedFiles={[]}
                onRemoveFile={() => {}}
                disabled={progressOpen}
                accept={CONTENT_ACCEPT}
                acceptedFormatsLabel="TXT, PDF, Word (.DOCX)"
                onUnsupportedFiles={handleUnsupportedFiles}
              />
            </>
          )}
        </CardContent>
      </Card>

      {/* Grading progress dialog */}
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
    </div>
  );
}
