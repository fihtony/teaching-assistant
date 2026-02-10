/**
 * Essay Grading page - AI-powered essay grading with HTML output
 */

import { useState, useEffect } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useMutation, useQuery } from "@tanstack/react-query";
import * as gradingApi from "@/services/gradingApi";
import { templatesApi } from "@/services/api";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { FileUpload } from "@/components/common/FileUpload";
import { FileText, Sparkles, Download, Eye, ArrowLeft, Loader2 } from "lucide-react";

export function EssayGradingPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const resultId = searchParams.get("result");

  const [studentName, setStudentName] = useState("");
  const [studentLevel, setStudentLevel] = useState("");
  const [recentActivity, setRecentActivity] = useState("");
  const [essayText, setEssayText] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [selectedTemplate, setSelectedTemplate] = useState<string>("");
  const [additionalInstructions, setAdditionalInstructions] = useState("");
  const [htmlResult, setHtmlResult] = useState<string | null>(null);

  // Fetch templates
  const { data: templates } = useQuery({
    queryKey: ["templates"],
    queryFn: templatesApi.list,
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
      setStudentLevel(historyResult.student_level || "");
      setRecentActivity(historyResult.recent_activity || "");
      setEssayText(historyResult.essay_text || "");
      setHtmlResult(historyResult.html_result || null);
    }
  }, [historyResult]);

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (files.length > 0) {
        const fileResult = await gradingApi.uploadEssayFile(files[0]);
        return gradingApi.gradeEssay({
          student_name: studentName || undefined,
          student_level: studentLevel || undefined,
          recent_activity: recentActivity || undefined,
          file_id: fileResult.file_id,
          template_id: selectedTemplate || undefined,
          additional_instructions: additionalInstructions || undefined,
        });
      } else {
        return gradingApi.gradeEssay({
          student_name: studentName || undefined,
          student_level: studentLevel || undefined,
          recent_activity: recentActivity || undefined,
          essay_text: essayText || undefined,
          template_id: selectedTemplate || undefined,
          additional_instructions: additionalInstructions || undefined,
        });
      }
    },
    onSuccess: (data) => {
      setHtmlResult(data.html_result || null);
    },
  });

  const handleFilesSelected = (newFiles: File[]) => {
    setFiles(newFiles.slice(0, 1)); // Only allow one file
  };

  const handleRemoveFile = () => {
    setFiles([]);
  };

  const handleDownload = () => {
    if (!htmlResult) return;
    gradingApi.downloadGrading(resultId || "current");
  };

  const handleReset = () => {
    setStudentName("");
    setStudentLevel("");
    setRecentActivity("");
    setEssayText("");
    setFiles([]);
    setAdditionalInstructions("");
    setHtmlResult(null);
    navigate("/essay-grading");
  };

  if (isLoadingHistory) {
    return (
      <div className="flex h-96 items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-gray-500">Loading essay grading result...</p>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={() => navigate("/history")}>
            <ArrowLeft className="h-4 w-4" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Essay Grading</h1>
            <p className="text-sm text-gray-500">AI-powered essay grading with detailed feedback</p>
          </div>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* Input section */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Student Information
              </CardTitle>
              <CardDescription>Provide student context for better grading</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <Label htmlFor="studentName">Student Name</Label>
                <Input
                  id="studentName"
                  value={studentName}
                  onChange={(e) => setStudentName(e.target.value)}
                  placeholder="Enter student name"
                  className="mt-1"
                />
              </div>

              <div>
                <Label htmlFor="studentLevel">Student Level</Label>
                <Input
                  id="studentLevel"
                  value={studentLevel}
                  onChange={(e) => setStudentLevel(e.target.value)}
                  placeholder="e.g., Grade 5, High School, College"
                  className="mt-1"
                />
              </div>

              <div>
                <Label htmlFor="recentActivity">Recent Activity / Context</Label>
                <Textarea
                  id="recentActivity"
                  value={recentActivity}
                  onChange={(e) => setRecentActivity(e.target.value)}
                  placeholder="e.g., 'Reading Alice in Wonderland, learning about descriptive writing'"
                  className="mt-1"
                  rows={2}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Essay Content
              </CardTitle>
              <CardDescription>Paste essay text or upload a file</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {files.length === 0 ? (
                <div>
                  <Label htmlFor="essayText">Essay Text</Label>
                  <Textarea
                    id="essayText"
                    value={essayText}
                    onChange={(e) => setEssayText(e.target.value)}
                    placeholder="Paste the essay text here..."
                    className="mt-1 min-h-[200px] font-mono text-sm"
                    rows={10}
                  />
                </div>
              ) : (
                <FileUpload
                  onFilesSelected={handleFilesSelected}
                  selectedFiles={files}
                  onRemoveFile={handleRemoveFile}
                  disabled={uploadMutation.isPending}
                  accept={{ "text/*": [".txt"], "application/pdf": [".pdf"], "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"] }}
                />
              )}

              <div className="text-center text-sm text-gray-500">or</div>

              {files.length === 0 && (
                <FileUpload
                  onFilesSelected={handleFilesSelected}
                  selectedFiles={[]}
                  onRemoveFile={() => {}}
                  disabled={uploadMutation.isPending}
                  accept={{ "text/*": [".txt"], "application/pdf": [".pdf"], "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"] }}
                />
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Grading Options</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
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

              <div>
                <Label htmlFor="additionalInstructions">Additional Instructions</Label>
                <Textarea
                  id="additionalInstructions"
                  value={additionalInstructions}
                  onChange={(e) => setAdditionalInstructions(e.target.value)}
                  placeholder="e.g., 'Focus on grammar and spelling, provide detailed feedback'"
                  className="mt-1"
                  rows={3}
                />
              </div>
            </CardContent>
          </Card>

          <div className="flex gap-2">
            <Button
              onClick={() => uploadMutation.mutate()}
              disabled={uploadMutation.isPending || (!essayText && files.length === 0)}
              className="flex-1"
              size="lg"
            >
              {uploadMutation.isPending ? (
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
            {htmlResult && (
              <Button onClick={handleReset} variant="outline" size="lg">
                <Eye className="mr-2 h-5 w-5" />
                New Essay
              </Button>
            )}
          </div>
        </div>

        {/* Result section */}
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Sparkles className="h-5 w-5" />
                  Grading Result
                </span>
                {htmlResult && (
                  <div className="flex items-center gap-2">
                    <Button onClick={handleDownload} variant="outline" size="sm">
                      <Download className="mr-2 h-4 w-4" />
                      Download
                    </Button>
                  </div>
                )}
              </CardTitle>
              <CardDescription>
                {htmlResult ? "AI-graded essay with red-ink corrections" : "Result will appear here after grading"}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {uploadMutation.isPending ? (
                <div className="flex h-96 items-center justify-center">
                  <div className="flex flex-col items-center gap-4">
                    <Loader2 className="h-12 w-12 animate-spin text-primary" />
                    <p className="text-gray-500">AI is grading the essay...</p>
                    <p className="text-sm text-gray-400">This may take a moment</p>
                  </div>
                </div>
              ) : htmlResult ? (
                <div className="h-[600px] overflow-y-auto rounded-md border p-4">
                  {/* Warning: HTML content from AI - ensure sanitization in production */}
                  <div
                    dangerouslySetInnerHTML={{ __html: htmlResult }}
                    className="prose prose-sm max-w-none"
                  />
                </div>
              ) : (
                <div className="flex h-96 flex-col items-center justify-center gap-4 text-gray-400">
                  <Sparkles className="h-16 w-16" />
                  <p>Submit an essay to see the grading result</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
