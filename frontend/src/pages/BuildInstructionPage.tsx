/**
 * Build Instruction with AI - create grading instruction templates using AI assistance
 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import type { FileRejection } from "react-dropzone";
import { assignmentsApi, studentsApi, settingsApi, templatesApi } from "@/services/api";
import { useNotification } from "@/contexts/NotificationContext";
import { useGradingProgress } from "@/hooks/useGradingProgress";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { FileUpload } from "@/components/common/FileUpload";
import { GradingProgressDialog } from "@/components/common/GradingProgressDialog";
import { GradedOutputDisplay } from "@/components/common/GradedOutputDisplay";
import { ArrowLeft, Sparkles, Loader2, Copy, Send } from "lucide-react";

const CONTENT_ACCEPT = {
  "text/plain": [".txt"],
  "application/pdf": [".pdf"],
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
};

export function BuildInstructionPage() {
  const navigate = useNavigate();
  const { show: showNotification } = useNotification();

  // State for student info
  const [studentName, setStudentName] = useState("");
  const [useCustomStudentName, setUseCustomStudentName] = useState(false);
  const [customStudentName, setCustomStudentName] = useState("");
  const [background, setBackground] = useState("");

  // State for grading instruction
  const [instruction, setInstruction] = useState("");

  // State for content
  const [contentText, setContentText] = useState("");
  const [files, setFiles] = useState<File[]>([]);

  // State for AI output
  const [aiOutput, setAiOutput] = useState<string>("");

  // State for chat
  const [chatMessages, setChatMessages] = useState<Array<{ role: "user" | "assistant"; content: string }>>([]);
  const [chatInput, setChatInput] = useState("");
  const [isRegeneratingInstruction, setIsRegeneratingInstruction] = useState(false);

  // State for template selection dialog
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);

  // State for AI config - read from settings
  const [aiProvider, setAiProvider] = useState<string | null>(null);
  const [aiModel, setAiModel] = useState<string | null>(null);
  const [defaultModel, setDefaultModel] = useState<string | null>(null);
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [loadingModels, setLoadingModels] = useState(false);

  // Grading progress
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

  // Fetch data
  const { data: students = [] } = useQuery({
    queryKey: ["students"],
    queryFn: () => studentsApi.list(),
  });

  const { data: templates } = useQuery({
    queryKey: ["templates"],
    queryFn: templatesApi.list,
  });

  const { data: aiConfig } = useQuery({
    queryKey: ["ai-config"],
    queryFn: () => settingsApi.getAIConfig(),
  });

  useEffect(() => {
    if (aiConfig) {
      const provider = aiConfig.default_provider || "copilot";
      const model = aiConfig.default_model || "gpt-4o";
      setAiProvider(provider);
      setDefaultModel(model); // Store the default model from settings
      setAiModel(model); // Initialize to default model as well
    }
  }, [aiConfig]);

  // Fetch available models when provider changes
  useEffect(() => {
    const fetchModels = async () => {
      if (!aiProvider) return;
      setLoadingModels(true);
      try {
        const result = await settingsApi.getModels(aiProvider);
        if (result.models) {
          // Extract model IDs (not names) since settings stores model IDs
          const modelStrings = result.models.map((m) => (typeof m === "string" ? m : m.id)).filter((m) => m);
          // Remove duplicates by using Set
          const uniqueModels = Array.from(new Set(modelStrings));
          setAvailableModels(uniqueModels);

          // Set the model to the default one from settings if available, otherwise use the first model
          if (defaultModel && uniqueModels.includes(defaultModel)) {
            setAiModel(defaultModel);
          } else if (uniqueModels.length > 0) {
            setAiModel(uniqueModels[0]);
          }
        }
      } catch (error) {
        console.warn("Failed to fetch available models:", error);
        setAvailableModels([]);
      } finally {
        setLoadingModels(false);
      }
    };
    fetchModels();
  }, [aiProvider, defaultModel]);

  // Auto-close progress dialog when grading completes
  useEffect(() => {
    if (progressStep === "completed" && progressOpen) {
      // Close the dialog after a short delay to show completion state
      const timer = setTimeout(() => {
        closeProgress();
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [progressStep, progressOpen, closeProgress]);

  const handleFilesSelected = (newFiles: File[]) => {
    setFiles(newFiles.slice(0, 1)); // Only allow one file
  };

  const handleRemoveFile = () => {
    setFiles([]);
  };

  const handleCancelClick = () => {
    handleCancelGrading();
    // Close the dialog after a short delay to allow the cancel to be processed
    setTimeout(() => {
      closeProgress();
    }, 500);
  };

  const handleUnsupportedFiles = (rejected: FileRejection[], acceptedFormatsLabel: string) => {
    const names = rejected.map((r) => r.file.name).join(", ");
    showNotification({
      type: "warning",
      message: `${names} ${rejected.length > 1 ? "are" : "is"} not supported. Only ${acceptedFormatsLabel} ${rejected.length > 1 ? "are" : "is"} supported.`,
    });
  };

  const handleGradeWithAI = async () => {
    if (!contentText && files.length === 0) {
      showNotification({
        type: "warning",
        message: "Please provide content - either paste text or upload a file",
      });
      return;
    }

    if (!instruction.trim()) {
      showNotification({
        type: "warning",
        message: "Please provide grading instruction",
      });
      return;
    }

    const finalStudentName = useCustomStudentName ? customStudentName : studentName;
    let studentId: number | undefined;
    if (!useCustomStudentName && studentName) {
      const selectedStudent = students.find((s) => s.name === studentName);
      if (selectedStudent) {
        studentId = selectedStudent.id;
      }
    }

    const sessionId = await startGradingProcess({
      file: files.length > 0 ? files[0] : undefined,
      studentId,
      studentName: finalStudentName || undefined,
      background: background || undefined,
      templateId: undefined,
      contentText: contentText || undefined,
      instructions: instruction.trim(),
      aiModel: aiModel || undefined,
      isPreview: true,
    });

    if (sessionId) {
      // Fetch the grading result from the preview endpoint
      try {
        const result = await assignmentsApi.getPreviewGradeResult(sessionId);
        console.log("[BuildInstructionPage] Preview result received:", {
          htmlLength: result.html?.length,
          htmlFirst500: result.html?.substring(0, 500),
          containsHtmlTags: result.html ? /<[a-z]/i.test(result.html) : false,
          containsMarkdownMarkup: result.html ? /~~|{{/.test(result.html) : false,
          containsRevisedEssay: result.html ? /revised\s+essay/i.test(result.html) : false,
          containsDetailedCorrections: result.html ? /detailed\s+corrections/i.test(result.html) : false,
          containsTeachersComments: result.html ? /teacher.*comments/i.test(result.html) : false,
        });

        if (result.html) {
          setAiOutput(result.html);
          showNotification({
            type: "success",
            message: "AI grading completed! See the result in the 'AI Graded Result' section.",
          });
        } else {
          setAiOutput("Grading completed but no output was generated.");
          showNotification({
            type: "warning",
            message: "Grading completed but no output was generated.",
          });
        }
      } catch (error) {
        console.error("[BuildInstructionPage] Failed to fetch preview grading result:", error);
        setAiOutput("Unable to retrieve grading result. Please check the logs.");
        showNotification({
          type: "error",
          message: "Failed to fetch grading result. Please try again.",
        });
      }
    } else if (progressError) {
      showNotification({
        type: "error",
        message: progressError,
      });
    }
  };

  const handleLoadTemplate = (templateId: string) => {
    const selectedTemplate = templates?.find((t) => t.id === templateId);
    if (selectedTemplate) {
      setInstruction(selectedTemplate.instructions || "");
      setShowTemplateDialog(false);
      showNotification({
        type: "success",
        message: `Loaded template: ${selectedTemplate.name}`,
      });
    }
  };

  const handleSendChatMessage = async () => {
    if (!chatInput.trim()) return;

    // Add user message to chat
    const userMessage = chatInput;
    setChatMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setChatInput("");
    setIsRegeneratingInstruction(true);

    // TODO: Call AI API to regenerate instruction based on chat input
    // For now, show placeholder response
    setTimeout(() => {
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "I'll regenerate the instruction based on your requirements. This feature will be connected to the AI API soon.",
        },
      ]);
      setIsRegeneratingInstruction(false);
    }, 1000);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate("/templates")} title="Back">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <h1 className="text-2xl font-bold text-gray-900">Build Instruction with AI</h1>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Label className="text-sm font-medium text-gray-700">Provider:</Label>
            <span className="px-3 py-2 text-sm bg-gray-100 rounded-md border border-gray-200">{aiProvider}</span>
          </div>
          <div className="flex items-center gap-2">
            <Label htmlFor="ai-model" className="text-sm font-medium text-gray-700">
              Model:
            </Label>
            <select
              id="ai-model"
              value={aiModel || ""}
              onChange={(e) => setAiModel(e.target.value)}
              disabled={loadingModels || availableModels.length === 0 || progressOpen}
              className="px-3 py-2 text-sm rounded-md border border-gray-300 bg-white focus:outline-none focus:ring-1 focus:ring-primary disabled:bg-gray-100 disabled:text-gray-400"
            >
              {availableModels.length === 0 ? (
                <option value="">{loadingModels ? "Loading models..." : "No models available"}</option>
              ) : (
                <>
                  {!aiModel && <option value="">Select a model...</option>}
                  {availableModels.map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </>
              )}
            </select>
          </div>
        </div>
      </div>

      {/* Main Content - Two column layout */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Left Column: Student Info + Instruction + Content */}
        <div className="space-y-4">
          {/* Student Information Card */}
          <Card>
            <CardHeader>
              <CardTitle>Student Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="space-y-2">
                <Label>Student Name</Label>
                <select
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

              <div className="space-y-2 flex-1">
                <Label htmlFor="background">Background (Optional)</Label>
                <Textarea
                  id="background"
                  value={background}
                  onChange={(e) => setBackground(e.target.value)}
                  placeholder="e.g., 'Reading Alice in Wonderland, learning about descriptive writing'"
                  className="mt-1 flex-1"
                  rows={3}
                />
              </div>
            </CardContent>
          </Card>

          {/* Instruction Card */}
          <Card>
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Grading Instruction</CardTitle>
              <Button variant="ghost" size="sm" onClick={() => setShowTemplateDialog(true)} title="Load existing template">
                <Copy className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent>
              <Textarea
                id="instruction"
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                placeholder="Enter grading instruction..."
                rows={10}
                className="resize-y"
              />
            </CardContent>
          </Card>

          {/* Content Card */}
          <Card>
            <CardHeader>
              <CardTitle>Sample Content</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {files.length === 0 ? (
                <div>
                  <Textarea
                    id="contentText"
                    value={contentText}
                    onChange={(e) => setContentText(e.target.value)}
                    placeholder="Paste the content here..."
                    className="mt-2 min-h-[200px] font-mono text-sm"
                    rows={10}
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
        </div>

        {/* Right Column: Chat + AI Output */}
        <div className="space-y-4 flex flex-col">
          {/* Grade Button */}
          <Button onClick={handleGradeWithAI} disabled={progressOpen} className="w-full" size="lg">
            {progressOpen ? (
              <>
                <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                Grading...
              </>
            ) : (
              <>
                <Sparkles className="mr-2 h-5 w-5" />
                Grade with AI & Review Result
              </>
            )}
          </Button>

          {/* Chat Window */}
          <Card className="flex flex-col flex-1">
            <CardContent className="mt-6 flex-1 flex flex-col space-y-3">
              {/* Chat Messages */}
              <div className="flex-1 border rounded-lg p-3 h-[250px] bg-gray-50 overflow-y-auto">
                <div className="space-y-3">
                  {chatMessages.length === 0 ? (
                    <p className="text-xs text-gray-500 text-center py-4">Start a conversation to refine your grading instruction</p>
                  ) : (
                    chatMessages.map((msg, idx) => (
                      <div key={idx} className={`text-sm ${msg.role === "user" ? "text-right" : "text-left"}`}>
                        <div
                          className={`inline-block rounded-lg px-3 py-2 max-w-xs ${
                            msg.role === "user" ? "bg-primary text-white" : "bg-gray-200 text-gray-900"
                          }`}
                        >
                          {msg.content}
                        </div>
                      </div>
                    ))
                  )}
                  {isRegeneratingInstruction && (
                    <div className="text-left">
                      <div className="inline-block bg-gray-200 text-gray-900 rounded-lg px-3 py-2">
                        <Loader2 className="h-4 w-4 animate-spin inline" />
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Chat Input */}
              <div className="flex gap-2">
                <Input
                  placeholder="Ask AI to improve the instruction..."
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      handleSendChatMessage();
                    }
                  }}
                  disabled={isRegeneratingInstruction}
                  className="text-sm flex-1"
                />
                <Button
                  onClick={handleSendChatMessage}
                  disabled={isRegeneratingInstruction || !chatInput.trim()}
                  size="sm"
                  variant="default"
                >
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* AI Output Card */}
          <Card className="flex flex-col flex-1 bg-white border border-gray-200 shadow-sm">
            <CardHeader className="border-b border-gray-200">
              <CardTitle className="text-base font-semibold text-gray-900">📋 AI Graded Result</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col overflow-hidden p-0">
              {aiOutput ? (
                <div className="flex-1 overflow-y-auto p-4 bg-gray-50">
                  <GradedOutputDisplay html={aiOutput} className="text-sm" />
                </div>
              ) : (
                <div className="flex-1 flex items-center justify-center p-4">
                  <p className="text-sm text-gray-500 text-center">Click "Grade with AI & Review Result" to see AI feedback here.</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Grading Progress Dialog */}
      <GradingProgressDialog
        open={progressOpen}
        step={progressStep}
        error={progressError}
        phaseElapsedMs={phaseElapsedMs}
        totalElapsedMs={totalElapsedMs}
        phaseTimes={phaseTimes}
        onCancel={handleCancelClick}
        onClose={closeProgress}
      />

      {/* Template Selection Modal */}
      {showTemplateDialog && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <Card className="w-full max-w-md max-h-[600px] overflow-hidden flex flex-col">
            <CardHeader className="border-b">
              <CardTitle>Load Instruction Template</CardTitle>
              <p className="text-sm text-gray-600 mt-2">Select an existing template to use as starting point</p>
            </CardHeader>
            <CardContent className="flex-1 overflow-y-auto p-4 space-y-2">
              {templates && templates.length > 0 ? (
                templates.map((template) => (
                  <button
                    key={template.id}
                    onClick={() => handleLoadTemplate(template.id)}
                    className="w-full text-left p-3 rounded-lg border border-gray-200 hover:bg-gray-50 hover:border-primary transition-colors"
                  >
                    <div className="font-medium text-sm">{template.name}</div>
                    {template.description && <div className="text-xs text-gray-600 mt-1">{template.description}</div>}
                  </button>
                ))
              ) : (
                <p className="text-sm text-gray-500 text-center py-4">No templates available</p>
              )}
            </CardContent>
            <div className="border-t p-4 flex gap-2">
              <Button variant="outline" className="flex-1" onClick={() => setShowTemplateDialog(false)}>
                Cancel
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
