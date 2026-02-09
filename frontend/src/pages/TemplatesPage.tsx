/**
 * Templates page - manage grading templates
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { templatesApi } from "@/services/api";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Plus, Edit, Trash2, Save, X, BookTemplate } from "lucide-react";
import type { GradingTemplate } from "@/types";

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
  const queryClient = useQueryClient();
  const [isCreating, setIsCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formData, setFormData] = useState({
    name: "",
    description: "",
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
      resetForm();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<GradingTemplate> }) => templatesApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["templates"] });
      resetForm();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: templatesApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["templates"] });
    },
  });

  const resetForm = () => {
    setIsCreating(false);
    setEditingId(null);
    setFormData({
      name: "",
      description: "",
      question_types: defaultQuestionTypes,
      encouragement_words: ["Bravo!", "Excellent!", "Perfect!", "Well done!", "Outstanding!"],
    });
  };

  const handleEdit = (template: GradingTemplate) => {
    setEditingId(template.id);
    setIsCreating(false);
    setFormData({
      name: template.name,
      description: template.description || "",
      question_types: template.question_types,
      encouragement_words: template.encouragement_words,
    });
  };

  const handleSubmit = () => {
    if (editingId) {
      updateMutation.mutate({ id: editingId, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const handleQuestionTypeChange = (index: number, field: string, value: any) => {
    setFormData((prev) => ({
      ...prev,
      question_types: prev.question_types.map((qt, i) => (i === index ? { ...qt, [field]: value } : qt)),
    }));
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Grading Templates</h1>
        {!isCreating && !editingId && (
          <Button onClick={() => setIsCreating(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create Template
          </Button>
        )}
      </div>

      {/* Create/Edit form */}
      {(isCreating || editingId) && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>{editingId ? "Edit Template" : "Create Template"}</CardTitle>
            <CardDescription>Configure grading criteria and question type weights</CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <Label htmlFor="name">Template Name</Label>
                <Input
                  id="name"
                  value={formData.name}
                  onChange={(e) => setFormData((prev) => ({ ...prev, name: e.target.value }))}
                  placeholder="e.g., Standard English Test"
                  className="mt-1"
                />
              </div>
              <div>
                <Label htmlFor="description">Description</Label>
                <Input
                  id="description"
                  value={formData.description}
                  onChange={(e) => setFormData((prev) => ({ ...prev, description: e.target.value }))}
                  placeholder="Optional description"
                  className="mt-1"
                />
              </div>
            </div>

            <div>
              <Label>Question Types & Weights</Label>
              <div className="mt-2 space-y-2">
                {formData.question_types.map((qt, index) => (
                  <div key={qt.type} className="flex items-center gap-4 rounded-lg border p-3">
                    <input
                      type="checkbox"
                      checked={qt.enabled}
                      onChange={(e) => handleQuestionTypeChange(index, "enabled", e.target.checked)}
                      className="h-4 w-4 rounded"
                    />
                    <span className="flex-1 font-medium">{qt.name}</span>
                    <div className="flex items-center gap-2">
                      <Label className="text-sm text-gray-500">Weight:</Label>
                      <Input
                        type="number"
                        value={qt.weight}
                        onChange={(e) => handleQuestionTypeChange(index, "weight", parseInt(e.target.value))}
                        className="w-20"
                        min={0}
                        max={100}
                      />
                      <span className="text-sm text-gray-500">%</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div>
              <Label htmlFor="encouragement">Encouragement Words (comma-separated)</Label>
              <Textarea
                id="encouragement"
                value={formData.encouragement_words.join(", ")}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    encouragement_words: e.target.value
                      .split(",")
                      .map((s) => s.trim())
                      .filter(Boolean),
                  }))
                }
                placeholder="Bravo!, Excellent!, Perfect!, Well done!"
                className="mt-1"
                rows={2}
              />
              <p className="mt-1 text-xs text-gray-500">These words will be randomly selected for perfect sections</p>
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

      {/* Template list */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {isLoading ? (
          <p className="text-gray-500">Loading templates...</p>
        ) : templates?.length === 0 ? (
          <Card className="col-span-full">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <BookTemplate className="mb-4 h-12 w-12 text-gray-300" />
              <p className="text-gray-500">No templates yet. Create your first one!</p>
            </CardContent>
          </Card>
        ) : (
          templates?.map((template) => (
            <Card key={template.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-lg">{template.name}</CardTitle>
                    {template.description && <CardDescription>{template.description}</CardDescription>}
                  </div>
                  {template.is_default && (
                    <span className="rounded-full bg-primary/10 px-2 py-1 text-xs font-medium text-primary">Default</span>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                <div className="mb-4 space-y-1">
                  {template.question_types
                    .filter((qt) => qt.enabled)
                    .slice(0, 3)
                    .map((qt) => (
                      <div key={qt.type} className="flex items-center justify-between text-sm">
                        <span className="text-gray-600">{qt.name}</span>
                        <span className="font-medium">{qt.weight}%</span>
                      </div>
                    ))}
                  {template.question_types.filter((qt) => qt.enabled).length > 3 && (
                    <p className="text-xs text-gray-400">+{template.question_types.filter((qt) => qt.enabled).length - 3} more...</p>
                  )}
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="ghost" size="sm" onClick={() => handleEdit(template)}>
                    <Edit className="mr-1 h-4 w-4" />
                    Edit
                  </Button>
                  {!template.is_default && (
                    <Button variant="ghost" size="sm" onClick={() => deleteMutation.mutate(template.id)}>
                      <Trash2 className="mr-1 h-4 w-4 text-red-500" />
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>
    </div>
  );
}
