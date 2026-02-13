/**
 * Instructions page - manage grading instructions (templates)
 */

import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import { templatesApi } from "@/services/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Plus, Edit, Trash2, Save, X, BookOpen, ArrowLeft, FileText, Code, Braces, Sparkles } from "lucide-react";
import { useNotification } from "@/contexts";
import type { GradingTemplate } from "@/types";
import type { QuestionTypeConfig } from "@/types";

const LEFT_QUESTION_TYPES_COUNT = 4;

function FormatIcon({ format }: { format: string }) {
  const f = (format || "text").toLowerCase();
  const title = f.charAt(0).toUpperCase() + f.slice(1);
  const wrap = (icon: React.ReactNode) => <span title={title}>{icon}</span>;
  const base = "h-4 w-4 ";
  if (f === "markdown") return wrap(<BookOpen className={base + "text-blue-600"} />);
  if (f === "html") return wrap(<Code className={base + "text-orange-600"} />);
  if (f === "json") return wrap(<Braces className={base + "text-green-600"} />);
  return wrap(<FileText className={base + "text-muted-foreground"} />);
}

function tryBeautifyJson(text: string): string {
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return text;
  }
}

const defaultQuestionTypes = [
  { type: "mcq", name: "Multiple Choice", weight: 15, enabled: true },
  { type: "true_false", name: "True/False", weight: 10, enabled: true },
  { type: "fill_blank", name: "Fill in the Blank", weight: 15, enabled: true },
  { type: "short_answer", name: "Short Answer", weight: 20, enabled: true },
  { type: "reading_comprehension", name: "Reading Comprehension", weight: 20, enabled: true },
  { type: "picture_description", name: "Picture Description", weight: 10, enabled: true },
  { type: "essay", name: "Essay", weight: 10, enabled: true },
];

export function TemplatesPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { show: showNotification } = useNotification();
  const [isCreating, setIsCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const defaultEncouragementWords = ["Bravo!", "Excellent!", "Perfect!", "Well done!", "Outstanding!"];
  const [encouragementWordsText, setEncouragementWordsText] = useState(defaultEncouragementWords.join(", "));
  const [formData, setFormData] = useState({
    name: "",
    description: "",
    instructions: "",
    instruction_format: "markdown" as "markdown" | "html" | "text" | "json",
    question_types: defaultQuestionTypes,
    encouragement_words: ["Bravo!", "Excellent!", "Perfect!", "Well done!", "Outstanding!"],
  });

  const { data: templates, isLoading } = useQuery({
    queryKey: ["templates"],
    queryFn: templatesApi.list,
  });

  const createMutation = useMutation({
    mutationFn: templatesApi.create,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["templates"] });
      showNotification({ type: "success", message: "Instruction saved successfully." });
      resetForm();
    },
    onError: (err: Error) => {
      showNotification({ type: "error", message: err.message || "Failed to save instruction." });
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<GradingTemplate> }) => templatesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["templates"] });
      showNotification({ type: "success", message: "Instruction saved successfully." });
      resetForm();
    },
    onError: (err: Error) => {
      showNotification({ type: "error", message: err.message || "Failed to save instruction." });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: templatesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["templates"] });
      showNotification({ type: "success", message: "Instruction deleted." });
    },
    onError: (err: Error) => {
      showNotification({ type: "error", message: err.message || "Failed to delete instruction." });
    },
  });

  const [templateToDelete, setTemplateToDelete] = useState<GradingTemplate | null>(null);
  const deleteDialogRef = useRef<HTMLDialogElement>(null);

  const handleDeleteClick = (template: GradingTemplate) => {
    setTemplateToDelete(template);
    deleteDialogRef.current?.showModal();
  };

  const closeDeleteDialog = () => {
    setTemplateToDelete(null);
    deleteDialogRef.current?.close();
  };

  const confirmDelete = () => {
    if (templateToDelete) {
      deleteMutation.mutate(templateToDelete.id);
      closeDeleteDialog();
    }
  };

  const resetForm = () => {
    setIsCreating(false);
    setEditingId(null);
    setEncouragementWordsText(defaultEncouragementWords.join(", "));
    setFormData({
      name: "",
      description: "",
      instructions: "",
      instruction_format: "markdown",
      question_types: defaultQuestionTypes,
      encouragement_words: defaultEncouragementWords,
    });
  };

  function normalizeQuestionTypes(raw: GradingTemplate["question_types"] | undefined): typeof defaultQuestionTypes {
    const fromDb = Array.isArray(raw) ? raw : [];
    const dbByType: Record<string, { weight: number; enabled: boolean; name?: string }> = {};
    fromDb.forEach((qt) => {
      const obj = typeof qt === "string" ? { type: qt, name: qt, weight: 10, enabled: true } : (qt as QuestionTypeConfig);
      dbByType[obj.type] = {
        weight: typeof obj.weight === "number" ? obj.weight : 10,
        enabled: typeof obj.enabled === "boolean" ? obj.enabled : true,
        name: obj.name,
      };
    });
    return defaultQuestionTypes.map((preset) => {
      const fromRecord = dbByType[preset.type];
      if (!fromRecord) return { ...preset };
      return {
        type: preset.type,
        name: fromRecord.name ?? preset.name,
        weight: fromRecord.weight,
        enabled: fromRecord.enabled,
      };
    });
  }

  const handleEdit = (template: GradingTemplate) => {
    setEditingId(template.id);
    setIsCreating(false);
    const words = Array.isArray(template.encouragement_words) ? template.encouragement_words : defaultEncouragementWords;
    setEncouragementWordsText(words.join(", "));
    setFormData({
      name: template.name,
      description: template.description || "",
      instructions: template.instructions ?? "",
      instruction_format: (template.instruction_format as "markdown" | "html" | "text" | "json") ?? "text",
      question_types: normalizeQuestionTypes(template.question_types),
      encouragement_words: words,
    });
  };

  const buildApiPayload = () => {
    const questionTypes = formData.question_types.map((qt) => ({
      type: qt.type,
      name: qt.name,
      weight: qt.enabled ? qt.weight : 0,
      enabled: qt.enabled,
    }));
    return {
      name: formData.name,
      description: formData.description || undefined,
      instructions: formData.instructions.trim() || "No instructions provided.",
      instruction_format: formData.instruction_format,
      encouragement_words: (() => {
        const arr = encouragementWordsText
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean);
        return arr.length ? arr : defaultEncouragementWords;
      })(),
      question_types: questionTypes,
    };
  };

  const handleSubmit = () => {
    const payload = buildApiPayload();
    if (editingId) {
      updateMutation.mutate({ id: editingId, data: payload });
    } else {
      createMutation.mutate(payload);
    }
  };

  const handleQuestionTypeChange = (index: number, field: keyof QuestionTypeConfig, value: unknown) => {
    setFormData((prev) => ({
      ...prev,
      question_types: prev.question_types.map((qt, i) =>
        i === index ? { ...qt, [field]: value, ...(field === "enabled" && value === false ? { weight: 0 } : {}) } : qt,
      ),
    }));
  };

  const handleInstructionsBlur = () => {
    if (formData.instruction_format === "json") {
      const beautified = tryBeautifyJson(formData.instructions);
      if (beautified !== formData.instructions) setFormData((prev) => ({ ...prev, instructions: beautified }));
    }
  };

  const isFormVisible = isCreating || editingId;
  const leftTypes = formData.question_types.slice(0, LEFT_QUESTION_TYPES_COUNT);
  const rightTypes = formData.question_types.slice(LEFT_QUESTION_TYPES_COUNT);
  const isSplitInstructions = formData.instruction_format === "markdown" || formData.instruction_format === "html";

  const sourceTextareaRef = useRef<HTMLTextAreaElement>(null);
  const INSTRUCTIONS_MIN_HEIGHT = 300; /* 50% bigger than previous 200 */
  const INSTRUCTIONS_MAX_HEIGHT = 720;
  const [sourceHeight, setSourceHeight] = useState(INSTRUCTIONS_MIN_HEIGHT);

  useEffect(() => {
    if (!isSplitInstructions || !sourceTextareaRef.current) return;
    const ta = sourceTextareaRef.current;
    ta.style.height = "auto";
    const h = Math.max(INSTRUCTIONS_MIN_HEIGHT, Math.min(ta.scrollHeight, INSTRUCTIONS_MAX_HEIGHT));
    ta.style.height = `${h}px`;
    setSourceHeight(h);
  }, [isSplitInstructions, formData.instructions]);

  return (
    <div>
      <div className="mb-6 flex items-center justify-between gap-4">
        <div className="flex min-w-0 flex-1 items-start gap-3">
          {isFormVisible && (
            <Button variant="ghost" size="icon" onClick={resetForm} title="Back to list">
              <ArrowLeft className="h-5 w-5" />
            </Button>
          )}
          <div className="flex min-w-0 flex-1 flex-col gap-0.5">
            <h1 className="text-2xl font-bold text-gray-900">
              {isFormVisible ? (editingId ? "Edit Instruction" : "New Instruction") : "Instructions"}
            </h1>
            {isFormVisible && <p className="text-[0.9rem] text-gray-600">Configure grading criteria and question type weights</p>}
          </div>
        </div>
        {!isFormVisible && (
          <div className="flex gap-2">
            <Button onClick={() => setIsCreating(true)}>
              <Plus className="mr-2 h-4 w-4" />
              New Instruction
            </Button>
            <Button variant="outline" onClick={() => navigate("/build-instruction")}>
              <Sparkles className="mr-2 h-4 w-4" />
              Build with AI
            </Button>
          </div>
        )}
      </div>

      {/* Create/Edit form - only when creating or editing; list hidden */}
      {isFormVisible && (
        <Card className="mb-6">
          <CardContent className="space-y-6 pt-6">
            {/* a. Instruction name - full width */}
            <div>
              <Label htmlFor="name" className="text-[1.3em] font-bold">
                Instruction name
              </Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                placeholder="e.g., Standard English Test"
                className="mt-1 w-full"
              />
            </div>

            {/* b. Description - 1 row to start, expandable */}
            <div>
              <Label htmlFor="description" className="text-[1.3em] font-bold">
                Description
              </Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
                placeholder="Optional description"
                className="mt-1 w-full resize-y"
                rows={1}
              />
            </div>

            {/* c. Encouragement Words - free input; converted to array only on save */}
            <div>
              <Label htmlFor="encouragement">
                <span className="text-[1.3em] font-bold">Encouragement Words</span>
                <span className="text-[0.975em] font-normal"> (comma-separated)</span>
              </Label>
              <Textarea
                id="encouragement"
                value={encouragementWordsText}
                onChange={(e) => setEncouragementWordsText(e.target.value)}
                placeholder="Bravo!, Excellent!, Perfect!, Well done!"
                className="mt-1 w-full resize-y"
                rows={1}
              />
              <p className="mt-1 text-xs text-gray-500">Randomly selected for perfect sections</p>
            </div>

            {/* d. Question Types & Weights - two columns: left 4, right 3 */}
            <div>
              <Label className="text-[1.3em] font-bold">Question Types & Weights</Label>
              <div className="mt-2 grid grid-cols-1 gap-4 md:grid-cols-2">
                <div className="space-y-2">
                  {leftTypes.map((qt, idx) => (
                    <div key={qt.type} className="flex items-center gap-4 rounded-lg border p-3">
                      <input
                        type="checkbox"
                        checked={qt.enabled}
                        onChange={(e) => handleQuestionTypeChange(idx, "enabled", e.target.checked)}
                        className="h-4 w-4 rounded"
                      />
                      <span className="flex-1 font-medium">{qt.name}</span>
                      <div className="flex items-center gap-2">
                        <Label className="text-sm text-gray-500">Weight:</Label>
                        <Input
                          type="number"
                          value={qt.enabled ? (qt.weight === 0 ? "" : qt.weight) : ""}
                          onChange={(e) => {
                            const v = e.target.value;
                            handleQuestionTypeChange(idx, "weight", v === "" ? 0 : parseInt(v, 10) || 0);
                          }}
                          className="w-20"
                          min={0}
                          max={100}
                          disabled={!qt.enabled}
                        />
                        <span className="text-sm text-gray-500">%</span>
                      </div>
                    </div>
                  ))}
                </div>
                <div className="space-y-2">
                  {rightTypes.map((qt, idx) => (
                    <div key={qt.type} className="flex items-center gap-4 rounded-lg border p-3">
                      <input
                        type="checkbox"
                        checked={qt.enabled}
                        onChange={(e) => handleQuestionTypeChange(idx + LEFT_QUESTION_TYPES_COUNT, "enabled", e.target.checked)}
                        className="h-4 w-4 rounded"
                      />
                      <span className="flex-1 font-medium">{qt.name}</span>
                      <div className="flex items-center gap-2">
                        <Label className="text-sm text-gray-500">Weight:</Label>
                        <Input
                          type="number"
                          value={qt.enabled ? (qt.weight === 0 ? "" : qt.weight) : ""}
                          onChange={(e) => {
                            const v = e.target.value;
                            handleQuestionTypeChange(idx + LEFT_QUESTION_TYPES_COUNT, "weight", v === "" ? 0 : parseInt(v, 10) || 0);
                          }}
                          className="w-20"
                          min={0}
                          max={100}
                          disabled={!qt.enabled}
                        />
                        <span className="text-sm text-gray-500">%</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* e. Grading Instructions - split for markdown/html, single for text/json with json beautify */}
            <div>
              <div className="flex items-center justify-between gap-4">
                <Label className="text-[1.3em] font-bold">Grading Instructions</Label>
                <div className="flex items-center gap-2">
                  <Label htmlFor="instruction_format" className="text-sm font-normal text-gray-600">
                    Format
                  </Label>
                  <select
                    id="instruction_format"
                    value={formData.instruction_format}
                    onChange={(e) =>
                      setFormData((prev) => ({
                        ...prev,
                        instruction_format: e.target.value as "markdown" | "html" | "text" | "json",
                      }))
                    }
                    className="rounded border border-gray-300 px-3 py-1.5 text-sm"
                  >
                    <option value="text">Plain text</option>
                    <option value="markdown">Markdown</option>
                    <option value="html">HTML</option>
                    <option value="json">JSON</option>
                  </select>
                </div>
              </div>
              {isSplitInstructions ? (
                <div className="mt-2 grid grid-cols-1 gap-4 md:grid-cols-2">
                  <div>
                    <Label className="text-xs text-gray-500">Source</Label>
                    <Textarea
                      ref={sourceTextareaRef}
                      value={formData.instructions}
                      onChange={(e) => setFormData((prev) => ({ ...prev, instructions: e.target.value }))}
                      placeholder="Enter content..."
                      className="mt-1 w-full resize-none overflow-auto font-mono text-sm"
                      rows={3}
                      style={{ minHeight: INSTRUCTIONS_MIN_HEIGHT, maxHeight: INSTRUCTIONS_MAX_HEIGHT }}
                    />
                  </div>
                  <div>
                    <Label className="text-xs text-gray-500">Preview</Label>
                    <div
                      className="mt-1 w-full overflow-auto rounded border border-gray-200 bg-gray-50 p-4"
                      style={{ minHeight: sourceHeight, maxHeight: INSTRUCTIONS_MAX_HEIGHT, height: sourceHeight }}
                    >
                      {formData.instruction_format === "markdown" && (
                        <div className="markdown-preview break-words">
                          <ReactMarkdown remarkPlugins={[remarkBreaks]}>{formData.instructions || "*No content*"}</ReactMarkdown>
                        </div>
                      )}
                      {formData.instruction_format === "html" && (
                        <iframe
                          title="HTML preview"
                          srcDoc={formData.instructions || "<p><em>No content</em></p>"}
                          className="w-full rounded border-0 bg-white"
                          style={{ minHeight: sourceHeight - 32, maxHeight: INSTRUCTIONS_MAX_HEIGHT - 32 }}
                          sandbox="allow-same-origin"
                        />
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="mt-2">
                  <Textarea
                    value={formData.instructions}
                    onChange={(e) => setFormData((prev) => ({ ...prev, instructions: e.target.value }))}
                    onBlur={handleInstructionsBlur}
                    placeholder={
                      formData.instruction_format === "json" ? "Valid JSON (auto-formatted on blur)" : "Enter grading instructions..."
                    }
                    className="min-h-[120px] w-full resize-y font-mono text-sm"
                    rows={6}
                  />
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={resetForm}>
                <X className="mr-2 h-4 w-4" />
                Cancel
              </Button>
              <Button onClick={handleSubmit} disabled={!formData.name || createMutation.isPending || updateMutation.isPending}>
                <Save className="mr-2 h-4 w-4" />
                {editingId ? "Update" : "Create"}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Instruction list - only when not creating/editing */}
      {!isFormVisible && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {isLoading ? (
            <p className="text-gray-500">Loading instructions...</p>
          ) : templates?.length === 0 ? (
            <Card className="col-span-full">
              <CardContent className="flex flex-col items-center justify-center py-12">
                <BookOpen className="mb-4 h-12 w-12 text-gray-300" />
                <p className="text-gray-500">No instructions yet. Create your first one!</p>
              </CardContent>
            </Card>
          ) : (
            templates?.map((template) => (
              <Card key={template.id}>
                <CardHeader>
                  <div className="min-w-0">
                    <CardTitle className="line-clamp-2 text-lg" title={template.name}>
                      {template.name || "—"}
                    </CardTitle>
                    {template.description != null && template.description !== "" && (
                      <CardDescription className="mt-1 line-clamp-2" title={template.description}>
                        {template.description}
                      </CardDescription>
                    )}
                  </div>
                  {template.is_default && (
                    <span className="mt-2 inline-block rounded-full bg-primary/10 px-2 py-1 text-xs font-medium text-primary">Default</span>
                  )}
                </CardHeader>
                <CardContent>
                  <div className="mb-4 space-y-1">
                    {(() => {
                      const types = (Array.isArray(template.question_types) ? template.question_types : []).map((qt) =>
                        typeof qt === "string" ? { type: qt, name: qt, weight: 0, enabled: true } : qt,
                      );
                      const enabled = types.filter((qt) => qt.enabled !== false);
                      return (
                        <>
                          {enabled.slice(0, 3).map((qt) => (
                            <div key={qt.type} className="flex items-center justify-between text-sm">
                              <span className="text-gray-600">{qt.name}</span>
                              <span className="font-medium">{qt.weight}%</span>
                            </div>
                          ))}
                          {enabled.length > 3 && <p className="text-xs text-gray-400">+{enabled.length - 3} more...</p>}
                        </>
                      );
                    })()}
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="flex items-center text-muted-foreground" title={`Format: ${template.instruction_format || "text"}`}>
                      <FormatIcon format={template.instruction_format || "text"} />
                    </span>
                    <div className="flex gap-2">
                      <Button variant="ghost" size="sm" onClick={() => handleEdit(template)}>
                        <Edit className="mr-1 h-4 w-4" />
                        Edit
                      </Button>
                      {!template.is_default && (
                        <Button variant="ghost" size="sm" onClick={() => handleDeleteClick(template)}>
                          <Trash2 className="mr-1 h-4 w-4 text-red-500" />
                        </Button>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      )}

      <dialog
        ref={deleteDialogRef}
        className="w-full max-w-md rounded-lg border border-gray-200 bg-white p-6 shadow-lg backdrop:bg-black/20"
        onCancel={closeDeleteDialog}
      >
        {templateToDelete && (
          <>
            <h3 className="text-lg font-semibold text-gray-900">Delete instruction?</h3>
            <div className="mt-4 space-y-2 text-sm text-gray-600">
              <p>
                <span className="font-medium">Name:</span> {templateToDelete.name || "—"}
              </p>
              <p>
                <span className="font-medium">Description:</span> {templateToDelete.description || "—"}
              </p>
              <p>
                <span className="font-medium">Question types:</span>{" "}
                {(Array.isArray(templateToDelete.question_types) ? templateToDelete.question_types : [])
                  .map((qt) => (typeof qt === "string" ? qt : (qt as { name?: string }).name || (qt as { type?: string }).type))
                  .join(", ") || "—"}
              </p>
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <Button variant="outline" onClick={closeDeleteDialog}>
                Cancel
              </Button>
              <Button variant="destructive" onClick={confirmDelete}>
                Delete
              </Button>
            </div>
          </>
        )}
      </dialog>
    </div>
  );
}
