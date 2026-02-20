/**
 * RevisePage — allows teachers to revise AI graded output through a chat interface.
 *
 * Layout:
 *  - Title row: "Revise AI grading" + Save button (right-aligned, disabled until revision created)
 *  - Basic info card (full width, read-only): student name, essay topic, background, template, custom instruction
 *  - Two side-by-side cards: AI graded output (left) / Chat window (right), same height
 *
 * Features:
 *  - Version management: "1", "2", "3"... tabs for each version
 *  - Chat interface: teacher types instructions → AI revises output
 *  - Save: confirms with native dialog, saves selected version as final, navigates back
 */

import { useState, useRef, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { assignmentsApi } from "@/services/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Save, Send, Sparkles, Loader2 } from "lucide-react";
import { GradedOutputDisplay } from "@/components/common/GradedOutputDisplay";
import { ConfirmDialog } from "@/components/common/ConfirmDialog";

interface ChatMessage {
  role: "teacher" | "ai";
  content: string;
  timestamp: string;
}

interface GradedVersion {
  id: number; // 1-based version number
  html_content: string;
  instruction?: string; // The teacher instruction that generated this version
}

export function RevisePage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // State
  const [versions, setVersions] = useState<GradedVersion[]>([]);
  const [currentVersionId, setCurrentVersionId] = useState(1);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isRevising, setIsRevising] = useState(false);
  const [hasNewVersions, setHasNewVersions] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [showSaveConfirm, setShowSaveConfirm] = useState(false);

  const chatEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Fetch assignment data
  const { data: assignment, isLoading } = useQuery({
    queryKey: ["assignment", id],
    queryFn: () => assignmentsApi.get(id!),
    enabled: !!id,
  });

  // Initialize versions with original graded output
  useEffect(() => {
    if (assignment?.graded_content && versions.length === 0) {
      setVersions([{ id: 1, html_content: assignment.graded_content }]);
      setCurrentVersionId(1);
    }
  }, [assignment, versions.length]);

  // Scroll chat to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages]);

  // Auto-resize textarea
  const handleTextareaChange = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInputValue(e.target.value);
    const textarea = e.target;
    textarea.style.height = "auto";
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + "px";
  }, []);

  // Get current version's HTML
  const currentVersion = versions.find((v) => v.id === currentVersionId);
  const currentHtml = currentVersion?.html_content || "";

  // Handle sending a revision instruction
  const handleSendRevision = useCallback(async () => {
    if (!inputValue.trim() || isRevising || !assignment) return;

    const instruction = inputValue.trim();
    setInputValue("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }

    // Add teacher message to chat
    const teacherMsg: ChatMessage = {
      role: "teacher",
      content: instruction,
      timestamp: new Date().toISOString(),
    };
    setChatMessages((prev) => [...prev, teacherMsg]);

    setIsRevising(true);
    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const result = await assignmentsApi.reviseGrading(
        Number(assignment.id),
        {
          ai_grading_id: assignment.ai_grading_id!,
          teacher_instruction: instruction,
          current_html_content: currentHtml,
        },
        controller.signal,
      );

      if (result.error) {
        const aiMsg: ChatMessage = {
          role: "ai",
          content: `Error: ${result.error}`,
          timestamp: new Date().toISOString(),
        };
        setChatMessages((prev) => [...prev, aiMsg]);
      } else {
        // Create new version
        const newVersionId = versions.length + 1;
        const newVersion: GradedVersion = {
          id: newVersionId,
          html_content: result.html_content,
          instruction,
        };
        setVersions((prev) => [...prev, newVersion]);
        setCurrentVersionId(newVersionId);
        setHasNewVersions(true);

        const aiMsg: ChatMessage = {
          role: "ai",
          content: `Revision complete — Version ${newVersionId} created.${result.elapsed_ms ? ` (${(result.elapsed_ms / 1000).toFixed(1)}s)` : ""}`,
          timestamp: new Date().toISOString(),
        };
        setChatMessages((prev) => [...prev, aiMsg]);
      }
    } catch (err: unknown) {
      if (err instanceof Error && err.name === "AbortError") return;
      const aiMsg: ChatMessage = {
        role: "ai",
        content: `Error: ${err instanceof Error ? err.message : "Unknown error"}`,
        timestamp: new Date().toISOString(),
      };
      setChatMessages((prev) => [...prev, aiMsg]);
    } finally {
      setIsRevising(false);
      abortRef.current = null;
    }
  }, [inputValue, isRevising, assignment, currentHtml, versions.length]);

  // Handle save - show confirmation dialog
  const handleSaveClick = useCallback(() => {
    if (!assignment || !currentVersion) return;
    setShowSaveConfirm(true);
  }, [assignment, currentVersion]);

  // Handle confirmed save
  const handleConfirmSave = useCallback(async () => {
    if (!assignment || !currentVersion) return;

    setIsSaving(true);
    setShowSaveConfirm(false);
    try {
      // Build revision history from chat messages
      const revisionHistory = chatMessages
        .filter((m) => m.role === "teacher")
        .map((m) => ({
          instruction: m.content,
          timestamp: m.timestamp,
        }));

      await assignmentsApi.saveRevision(Number(assignment.id), {
        ai_grading_id: assignment.ai_grading_id!,
        html_content: currentVersion.html_content,
        revision_history: revisionHistory,
      });

      // Invalidate cache so grading result page shows updated content
      await queryClient.invalidateQueries({ queryKey: ["assignment", id] });

      // Navigate back to grading result page
      navigate(`/grade/${id}`);
    } catch (err) {
      alert(`Failed to save: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setIsSaving(false);
    }
  }, [assignment, currentVersion, chatMessages, id, navigate, queryClient]);

  // Handle Enter key in textarea
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSendRevision();
      }
    },
    [handleSendRevision],
  );

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
        <p className="text-gray-600">Assignment not found</p>
        <Button variant="outline" onClick={() => navigate("/")}>
          Go back
        </Button>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Title row */}
      <div className="mb-4 flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => navigate(`/grade/${id}`)} aria-label="Back">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <h1 className="text-2xl font-bold text-gray-900 flex-1 truncate">
          Revise AI Grading{assignment.title || assignment.essay_topic ? `: ${assignment.title || assignment.essay_topic}` : ""}
        </h1>
        <Button onClick={handleSaveClick} disabled={!hasNewVersions || isSaving}>
          {isSaving ? (
            <>
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Save className="mr-2 h-4 w-4" />
              Save
            </>
          )}
        </Button>
      </div>

      {/* Basic info card */}
      <div className="mb-4">
        <Card>
          <CardContent className="pt-4 pb-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase">Student Name</p>
                <p className="mt-1 text-sm font-medium text-gray-900 truncate">{assignment.student_name || "—"}</p>
              </div>
              <div>
                <p className="text-xs font-medium text-gray-500 uppercase">Template</p>
                <p className="mt-1 text-sm font-medium text-gray-900 truncate">{assignment.template_name || "—"}</p>
              </div>
              {assignment.background && (
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase">Background</p>
                  <div className="mt-1 text-sm text-gray-700 bg-white rounded border border-gray-200 p-2 max-h-20 overflow-y-auto whitespace-pre-wrap">
                    {assignment.background}
                  </div>
                </div>
              )}
              {assignment.instructions && (
                <div>
                  <p className="text-xs font-medium text-gray-500 uppercase">Custom Instruction</p>
                  <div className="mt-1 text-sm text-gray-700 bg-white rounded border border-gray-200 p-2 max-h-20 overflow-y-auto whitespace-pre-wrap">
                    {assignment.instructions}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Two main cards side by side */}
      <div className="grid grid-cols-2 gap-4" style={{ height: "calc(100vh)", maxHeight: "800px" }}>
        {/* Left: AI Graded Output */}
        <Card className="flex flex-col overflow-hidden">
          <CardHeader className="flex-shrink-0 pb-2">
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2 text-base">
                <Sparkles className="h-5 w-5 text-green-500" />
                AI Graded Output
                {assignment.grading_model && (
                  <span className="text-xs italic text-gray-500 font-normal ml-2">by {assignment.grading_model}</span>
                )}
              </span>
              {/* Version tabs */}
              {versions.length > 1 && (
                <div className="flex items-center gap-1">
                  {versions.map((v) => (
                    <button
                      key={v.id}
                      onClick={() => setCurrentVersionId(v.id)}
                      className={`w-7 h-7 rounded text-sm font-medium transition-colors ${
                        v.id === currentVersionId ? "bg-primary text-white" : "bg-gray-100 text-gray-600 hover:bg-gray-200"
                      }`}
                      title={v.id === 1 ? "Original" : `Version ${v.id}`}
                    >
                      {v.id}
                    </button>
                  ))}
                </div>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 min-h-0 overflow-hidden">
            <div className="rounded-lg border bg-gray-50 p-4 h-full overflow-y-auto">
              {currentHtml ? <GradedOutputDisplay html={currentHtml} /> : <p className="text-gray-500">No graded output available.</p>}
            </div>
          </CardContent>
        </Card>

        {/* Right: Chat Window */}
        <Card className="flex flex-col overflow-hidden">
          <CardHeader className="flex-shrink-0 pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <Send className="h-5 w-5 text-blue-500" />
              Revision Chat
            </CardTitle>
          </CardHeader>
          <CardContent className="flex-1 min-h-0 flex flex-col">
            {/* Chat messages */}
            <div className="flex-1 min-h-0 overflow-auto rounded-lg border bg-gray-50 p-4 mb-3">
              {chatMessages.length === 0 && (
                <div className="flex h-full items-center justify-center">
                  <p className="text-sm text-gray-400 text-center">
                    Type your instructions below to revise the AI grading output.
                    <br />
                    <span className="text-xs">E.g., "Be more encouraging in the comments" or "Re-grade with focus on grammar"</span>
                  </p>
                </div>
              )}
              {chatMessages.map((msg, idx) => (
                <div key={idx} className={`mb-3 flex ${msg.role === "teacher" ? "justify-end" : "justify-start"}`}>
                  <div
                    className={`max-w-[85%] rounded-lg px-3 py-2 text-sm ${
                      msg.role === "teacher" ? "bg-primary text-white" : "bg-white border text-gray-700"
                    }`}
                  >
                    {msg.content}
                  </div>
                </div>
              ))}
              {isRevising && (
                <div className="mb-3 flex justify-start">
                  <div className="max-w-[85%] rounded-lg px-3 py-2 text-sm bg-white border text-gray-500 flex items-center gap-2">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    AI is revising...
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Input area */}
            <div className="flex gap-2 items-end flex-shrink-0">
              <textarea
                ref={textareaRef}
                value={inputValue}
                onChange={handleTextareaChange}
                onKeyDown={handleKeyDown}
                placeholder="Type revision instructions... (Enter to send, Shift+Enter for new line)"
                className="flex-1 resize-none rounded-lg border bg-white px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
                rows={1}
                disabled={isRevising}
              />
              <Button size="sm" onClick={handleSendRevision} disabled={!inputValue.trim() || isRevising} className="h-9 px-3">
                {isRevising ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Save confirmation dialog */}
      <ConfirmDialog
        open={showSaveConfirm}
        title="Save Revised Version"
        description={`Save Version ${currentVersionId} as the final graded output?\n\nThis will replace the original grading result. All other versions will be discarded.`}
        confirmLabel="Save"
        cancelLabel="Cancel"
        isDangerous={false}
        isLoading={isSaving}
        onConfirm={handleConfirmSave}
        onCancel={() => setShowSaveConfirm(false)}
      />

      {/* Progress dialog overlay */}
      {isRevising && (
        <div className="fixed inset-0 bg-black/20 flex items-center justify-center z-50 pointer-events-none">
          <div className="bg-white rounded-lg shadow-xl p-6 flex items-center gap-4 pointer-events-auto">
            <Loader2 className="h-6 w-6 animate-spin text-primary" />
            <div>
              <p className="font-medium text-gray-900">Revising graded output...</p>
              <p className="text-sm text-gray-500">AI is processing your revision instruction</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
