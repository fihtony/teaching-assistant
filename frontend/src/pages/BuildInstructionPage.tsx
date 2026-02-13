/**
 * Build Instruction with AI - create grading instruction templates using AI assistance
 */

import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import type { FileRejection } from "react-dropzone";
import { studentsApi, settingsApi, templatesApi } from "@/services/api";
import { useNotification } from "@/contexts/NotificationContext";
import { useGradingProgress } from "@/hooks/useGradingProgress";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { FileUpload } from "@/components/common/FileUpload";
import { GradingProgressDialog } from "@/components/common/GradingProgressDialog";
import { ArrowLeft, Sparkles, Loader2, Save, Copy, Send } from "lucide-react";

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
  const [hasGradedOnce, setHasGradedOnce] = useState(false);

  // State for chat
  const [chatMessages, setChatMessages] = useState<Array<{ role: "user" | "assistant"; content: string }>>([]);
  const [chatInput, setChatInput] = useState("");
  const [isRegeneratingInstruction, setIsRegeneratingInstruction] = useState(false);

  // State for template selection dialog
  const [showTemplateDialog, setShowTemplateDialog] = useState(false);

  // State for saving template
  const [isSavingTemplate, setIsSavingTemplate] = useState(false);
  const [templateName, setTemplateName] = useState("");
  const [templateDesc, setTemplateDesc] = useState("");

  // State for AI config - read from settings
  const [aiProvider, setAiProvider] = useState("copilot");
  const [aiModel, setAiModel] = useState("gpt-4o");

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
      setAiProvider(aiConfig.provider || "copilot");
      setAiModel(aiConfig.model || "gpt-4o");
    }
  }, [aiConfig]);

  const handleFilesSelected = (newFiles: File[]) => {
    setFiles(newFiles.slice(0, 1)); // Only allow one file
  };

  const handleRemoveFile = () => {
    setFiles([]);
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

    const assignmentId = await startGradingProcess({
      file: files.length > 0 ? files[0] : undefined,
      studentId,
      studentName: finalStudentName || undefined,
      background: background || undefined,
      templateId: undefined,
      contentText: contentText || undefined,
    });

    if (assignmentId) {
      setHasGradedOnce(true);
      // TODO: Fetch grading result and display in aiOutput
      // For now, show a placeholder
      setAiOutput("AI output will be displayed here after grading completes...");
    } else if (progressError) {
      showNotification({
        type: "error",
        message: progressError,
      });
    }
  };

  const handleSaveTemplate = async () => {
    if (!templateName.trim()) {
      showNotification({
        type: "warning",
        message: "Please enter a template name",
      });
      return;
    }

    if (!instruction.trim()) {
      showNotification({
        type: "warning",
        message: "Please provide grading instruction to save",
      });
      return;
    }

    setIsSavingTemplate(true);
    try {
      await templatesApi.create({
        name: templateName,
        description: templateDesc,
        instructions: instruction,
        instruction_format: "text",
        question_types: [],
        encouragement_words: [],
      });

      showNotification({
        type: "success",
        message: "Instruction template saved successfully!",
      });

      // Reset form
      setTemplateName("");
      setTemplateDesc("");
      navigate("/templates");
    } catch (error) {
      showNotification({
        type: "error",
        message: error instanceof Error ? error.message : "Failed to save template",
      });
    } finally {
      setIsSavingTemplate(false);
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
    <div className="min-h-screen bg-gray-50 p-6">
      {/* Header */}
      <div className="mb-6 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={() => navigate("/templates")} title="Back">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Build Instruction with AI</h1>
            <p className="mt-1 text-sm text-gray-600">
              Create grading instructions using AI assistance • Provider: {aiProvider} • Model: {aiModel}
            </p>
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
          <Card className="flex flex-col flex-1 bg-white">
            <CardHeader>
              <CardTitle className="text-base">AI Graded Result</CardTitle>
            </CardHeader>
            <CardContent className="flex-1 flex flex-col space-y-3">
              {aiOutput ? (
                <div className="prose prose-sm max-w-none overflow-y-auto flex-1">
                  <div className="text-sm text-gray-700 space-y-2" dangerouslySetInnerHTML={{ __html: aiOutput }} />
                </div>
              ) : (
                <p className="text-sm text-gray-500">Complete grading to see AI feedback here.</p>
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
        onCancel={handleCancelGrading}
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
