/**
 * Students page - manage groups and students, view students by group
 */

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useNotification } from "@/contexts";
import { groupsApi, studentsApi } from "@/services/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Users,
  UserPlus,
  FolderPlus,
  Pencil,
  Trash2,
  X,
} from "lucide-react";
import type { Group, Student, Gender } from "@/types";

type DeleteTarget = { type: "group"; id: number; name: string } | { type: "student"; id: number; name: string } | null;

export function StudentsPage() {
  const queryClient = useQueryClient();
  const { show: showNotification } = useNotification();
  const [selectedGroupId, setSelectedGroupId] = useState<number | null>(null);
  const [showGroupModal, setShowGroupModal] = useState(false);
  const [showStudentModal, setShowStudentModal] = useState(false);
  const [editingGroup, setEditingGroup] = useState<Group | null>(null);
  const [editingStudent, setEditingStudent] = useState<Student | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget>(null);
  const [groupForm, setGroupForm] = useState({ name: "", description: "", goal: "" });
  const [studentForm, setStudentForm] = useState<Partial<Student> & { name: string }>({
    name: "",
    age: undefined,
    gender: undefined,
    vocabulary: "",
    grade: "",
    group_id: undefined,
    additional_info: "",
  });

  const { data: groups = [], isLoading: groupsLoading } = useQuery({
    queryKey: ["groups"],
    queryFn: () => groupsApi.list(),
  });

  const { data: students = [], isLoading: studentsLoading } = useQuery({
    queryKey: ["students", selectedGroupId],
    queryFn: () => studentsApi.list(selectedGroupId ?? undefined),
  });

  const createGroupMutation = useMutation({
    mutationFn: (data: { name: string; description?: string; goal?: string }) =>
      groupsApi.create(data),
    onSuccess: (data) => {
      queryClient.setQueryData<Group[]>(["groups"], (prev) => [...(prev ?? []), data]);
      setShowGroupModal(false);
      setEditingGroup(null);
      setGroupForm({ name: "", description: "", goal: "" });
      showNotification({ type: "success", message: "Group created successfully." });
    },
    onError: (err: Error) => {
      showNotification({ type: "error", message: err.message || "Failed to create group." });
    },
  });

  const updateGroupMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Group> }) =>
      groupsApi.update(id, data),
    onSuccess: (data) => {
      queryClient.setQueryData<Group[]>(["groups"], (prev) =>
        (prev ?? []).map((g) => (g.id === data.id ? data : g))
      );
      setShowGroupModal(false);
      setEditingGroup(null);
      setGroupForm({ name: "", description: "", goal: "" });
      showNotification({ type: "success", message: "Group updated successfully." });
    },
    onError: (err: Error) => {
      showNotification({ type: "error", message: err.message || "Failed to update group." });
    },
  });

  const deleteGroupMutation = useMutation({
    mutationFn: (id: number) => groupsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["groups"] });
      queryClient.invalidateQueries({ queryKey: ["students"] });
      if (selectedGroupId) setSelectedGroupId(null);
      setDeleteTarget(null);
      showNotification({ type: "success", message: "Group deleted." });
    },
    onError: (err: Error) => {
      showNotification({ type: "error", message: err.message || "Failed to delete group." });
      setDeleteTarget(null);
    },
  });

  const createStudentMutation = useMutation({
    mutationFn: (data: Partial<Student> & { name: string }) => studentsApi.create(data),
    onSuccess: (data) => {
      queryClient.setQueryData<Student[]>(["students", selectedGroupId], (prev) => {
        const list = prev ?? [];
        if (selectedGroupId == null) return [...list, data];
        if (data.group_id === selectedGroupId) return [...list, data];
        return list;
      });
      setShowStudentModal(false);
      resetStudentForm();
      showNotification({ type: "success", message: "Student added successfully." });
    },
    onError: (err: Error) => {
      showNotification({ type: "error", message: err.message || "Failed to add student." });
    },
  });

  const updateStudentMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Student> }) =>
      studentsApi.update(id, data),
    onSuccess: (data) => {
      queryClient.setQueryData<Student[]>(["students", selectedGroupId], (prev) => {
        const list = (prev ?? []).map((s) => (s.id === data.id ? data : s));
        if (selectedGroupId != null && data.group_id !== selectedGroupId) return list.filter((s) => s.id !== data.id);
        return list;
      });
      setShowStudentModal(false);
      setEditingStudent(null);
      resetStudentForm();
      showNotification({ type: "success", message: "Student updated successfully." });
    },
    onError: (err: Error) => {
      showNotification({ type: "error", message: err.message || "Failed to update student." });
    },
  });

  const deleteStudentMutation = useMutation({
    mutationFn: (id: number) => studentsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["students"] });
      setDeleteTarget(null);
      showNotification({ type: "success", message: "Student deleted." });
    },
    onError: (err: Error) => {
      showNotification({ type: "error", message: err.message || "Failed to delete student." });
      setDeleteTarget(null);
    },
  });

  function resetStudentForm() {
    setStudentForm({
      name: "",
      age: undefined,
      gender: undefined,
      vocabulary: "",
      grade: "",
      group_id: selectedGroupId ?? undefined,
      additional_info: "",
    });
  }

  function openAddStudent() {
    setEditingStudent(null);
    setStudentForm({
      name: "",
      age: undefined,
      gender: undefined,
      vocabulary: "",
      grade: "",
      group_id: selectedGroupId ?? undefined,
      additional_info: "",
    });
    setShowStudentModal(true);
  }

  function openEditStudent(s: Student) {
    setEditingStudent(s);
    setStudentForm({
      name: s.name,
      age: s.age,
      gender: s.gender,
      vocabulary: s.vocabulary ?? "",
      grade: s.grade ?? "",
      group_id: s.group_id,
      additional_info: s.additional_info ?? "",
    });
    setShowStudentModal(true);
  }

  function openAddGroup() {
    setEditingGroup(null);
    setGroupForm({ name: "", description: "", goal: "" });
    setShowGroupModal(true);
  }

  function openEditGroup(g: Group) {
    setEditingGroup(g);
    setGroupForm({
      name: g.name,
      description: g.description ?? "",
      goal: g.goal ?? "",
    });
    setShowGroupModal(true);
  }

  function submitStudent(e: React.FormEvent) {
    e.preventDefault();
    const payload = {
      name: studentForm.name,
      age: studentForm.age,
      gender: studentForm.gender,
      vocabulary: studentForm.vocabulary || undefined,
      grade: studentForm.grade || undefined,
      group_id: studentForm.group_id && studentForm.group_id > 0 ? studentForm.group_id : undefined,
      additional_info: studentForm.additional_info || undefined,
    };
    if (editingStudent) {
      updateStudentMutation.mutate({ id: editingStudent.id, data: payload });
    } else {
      createStudentMutation.mutate(payload);
    }
  }

  return (
    <div>
      <h1 className="mb-6 text-2xl font-bold text-gray-900">Students & Groups</h1>

      {/* Delete confirmation dialog - do not close on backdrop click */}
      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" role="dialog" aria-modal="true" aria-labelledby="delete-dialog-title">
          <Card className="mx-4 w-full max-w-sm" onClick={(e) => e.stopPropagation()}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle id="delete-dialog-title">
                {deleteTarget.type === "group" ? "Delete group?" : "Delete student?"}
              </CardTitle>
              <Button variant="ghost" size="icon" onClick={() => setDeleteTarget(null)} aria-label="Close">
                <X className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-gray-600">
                {deleteTarget.type === "group"
                  ? `Delete "${deleteTarget.name}"? Students in this group will be unassigned.`
                  : `Delete student "${deleteTarget.name}"? This cannot be undone.`}
              </p>
              <div className="mt-4 flex justify-end gap-2">
                <Button variant="outline" onClick={() => setDeleteTarget(null)}>
                  Cancel
                </Button>
                <Button
                  variant="destructive"
                  onClick={() => {
                    if (deleteTarget.type === "group") {
                      deleteGroupMutation.mutate(deleteTarget.id);
                    } else {
                      deleteStudentMutation.mutate(deleteTarget.id);
                    }
                  }}
                  disabled={deleteGroupMutation.isPending || deleteStudentMutation.isPending}
                >
                  Delete
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Group add/edit modal - do not close on backdrop click */}
      {showGroupModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" role="dialog" aria-modal="true" aria-labelledby="group-dialog-title">
          <Card className="mx-4 w-full max-w-md" onClick={(e) => e.stopPropagation()}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle id="group-dialog-title">{editingGroup ? "Edit group" : "New group"}</CardTitle>
              <Button variant="ghost" size="icon" onClick={() => { setShowGroupModal(false); setEditingGroup(null); setGroupForm({ name: "", description: "", goal: "" }); }} aria-label="Close">
                <X className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent>
              <form
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.target as HTMLElement).tagName !== "TEXTAREA") e.preventDefault();
                }}
                onSubmit={(e) => {
                  e.preventDefault();
                  if (!groupForm.name.trim()) return;
                  if (editingGroup) {
                    updateGroupMutation.mutate({
                      id: editingGroup.id,
                      data: {
                        name: groupForm.name.trim(),
                        description: groupForm.description.trim() || undefined,
                        goal: groupForm.goal.trim() || undefined,
                      },
                    });
                  } else {
                    createGroupMutation.mutate({
                      name: groupForm.name.trim(),
                      description: groupForm.description.trim() || undefined,
                      goal: groupForm.goal.trim() || undefined,
                    });
                  }
                }}
              >
                <Label>Name *</Label>
                <Input
                  value={groupForm.name}
                  onChange={(e) => setGroupForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="Group name"
                  className="mb-2"
                />
                <Label>Description</Label>
                <Textarea
                  value={groupForm.description}
                  onChange={(e) => setGroupForm((f) => ({ ...f, description: e.target.value }))}
                  placeholder="Optional, supports line breaks"
                  rows={3}
                  className="mb-2 min-h-[4rem] resize-y"
                />
                <Label>Goal</Label>
                <Textarea
                  value={groupForm.goal}
                  onChange={(e) => setGroupForm((f) => ({ ...f, goal: e.target.value }))}
                  placeholder="Optional, supports line breaks"
                  rows={3}
                  className="mb-2 min-h-[4rem] resize-y"
                />
                <div className="mt-4 flex justify-end gap-2">
                  <Button type="button" variant="outline" onClick={() => { setShowGroupModal(false); setEditingGroup(null); setGroupForm({ name: "", description: "", goal: "" }); }}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={!groupForm.name.trim() || createGroupMutation.isPending || updateGroupMutation.isPending}>
                    {editingGroup ? "Update" : "Create"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Student add/edit modal - do not close on backdrop click */}
      {showStudentModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 overflow-y-auto py-8" role="dialog" aria-modal="true" aria-labelledby="student-dialog-title">
          <Card className="mx-4 w-full max-w-lg my-auto" onClick={(e) => e.stopPropagation()}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle id="student-dialog-title">{editingStudent ? "Edit student" : "Add student"}</CardTitle>
              <Button variant="ghost" size="icon" onClick={() => { setShowStudentModal(false); setEditingStudent(null); resetStudentForm(); }} aria-label="Close">
                <X className="h-4 w-4" />
              </Button>
            </CardHeader>
            <CardContent>
              <form
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.target as HTMLElement).tagName !== "TEXTAREA") e.preventDefault();
                }}
                onSubmit={submitStudent}
              >
                <div className="grid gap-2 sm:grid-cols-2">
                  <div>
                    <Label>Name *</Label>
                    <Input
                      value={studentForm.name}
                      onChange={(e) => setStudentForm((f) => ({ ...f, name: e.target.value }))}
                      placeholder="Student name"
                      required
                    />
                  </div>
                  <div>
                    <Label>Age</Label>
                    <Input
                      type="number"
                      min={0}
                      value={studentForm.age ?? ""}
                      onChange={(e) =>
                        setStudentForm((f) => ({ ...f, age: e.target.value ? Number(e.target.value) : undefined }))
                      }
                      placeholder="Optional"
                    />
                  </div>
                  <div>
                    <Label>Gender</Label>
                    <select
                      className="w-full rounded-md border px-3 py-2 text-sm"
                      value={studentForm.gender ?? ""}
                      onChange={(e) =>
                        setStudentForm((f) => ({ ...f, gender: (e.target.value || undefined) as Gender | undefined }))
                      }
                    >
                      <option value="">—</option>
                      <option value="boy">Boy</option>
                      <option value="girl">Girl</option>
                    </select>
                  </div>
                  <div>
                    <Label>Grade</Label>
                    <Input
                      value={studentForm.grade ?? ""}
                      onChange={(e) => setStudentForm((f) => ({ ...f, grade: e.target.value }))}
                      placeholder="e.g. Grade 4"
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <Label>Group</Label>
                    <select
                      className="w-full rounded-md border px-3 py-2 text-sm"
                      value={studentForm.group_id ?? ""}
                      onChange={(e) =>
                        setStudentForm((f) => ({
                          ...f,
                          group_id: e.target.value ? Number(e.target.value) : undefined,
                        }))
                      }
                    >
                      <option value="">No group</option>
                      {groups.map((g) => (
                        <option key={g.id} value={g.id}>
                          {g.name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="sm:col-span-2">
                    <Label>Vocabulary</Label>
                    <Input
                      value={studentForm.vocabulary ?? ""}
                      onChange={(e) => setStudentForm((f) => ({ ...f, vocabulary: e.target.value }))}
                      placeholder="Optional"
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <Label>Additional info</Label>
                    <Textarea
                      value={studentForm.additional_info ?? ""}
                      onChange={(e) => setStudentForm((f) => ({ ...f, additional_info: e.target.value }))}
                      placeholder="Optional notes, press Enter for new line"
                      rows={3}
                      className="min-h-[4rem] resize-y"
                    />
                  </div>
                </div>
                <div className="mt-4 flex justify-end gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => { setShowStudentModal(false); setEditingStudent(null); resetStudentForm(); }}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    disabled={
                      !studentForm.name.trim() ||
                      createStudentMutation.isPending ||
                      updateStudentMutation.isPending
                    }
                  >
                    {editingStudent ? "Update" : "Add"}
                  </Button>
                </div>
              </form>
            </CardContent>
          </Card>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Groups sidebar */}
        <Card className="lg:col-span-1">
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Groups
            </CardTitle>
            <Button size="sm" onClick={openAddGroup}>
              <FolderPlus className="mr-1 h-4 w-4" />
              New group
            </Button>
          </CardHeader>
          <CardContent>
            {groupsLoading ? (
              <p className="text-sm text-gray-500">Loading groups...</p>
            ) : groups.length === 0 ? (
              <p className="text-sm text-gray-500">No groups yet. Create one above.</p>
            ) : (
              <ul className="space-y-1">
                <li>
                  <button
                    type="button"
                    onClick={() => setSelectedGroupId(null)}
                    className={`w-full rounded-lg px-3 py-2 text-left text-sm ${
                      selectedGroupId === null ? "bg-primary/10 font-medium text-primary" : "hover:bg-gray-100"
                    }`}
                  >
                    All students
                  </button>
                </li>
                {groups.map((g) => (
                  <li key={g.id} className="flex items-center justify-between gap-1">
                    <button
                      type="button"
                      onClick={() => setSelectedGroupId(g.id)}
                      className={`min-w-0 flex-1 rounded-lg px-3 py-2 text-left text-sm ${
                        selectedGroupId === g.id ? "bg-primary/10 font-medium text-primary" : "hover:bg-gray-100"
                      }`}
                    >
                      {g.name}
                    </button>
                    <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0" onClick={() => openEditGroup(g)} title="Edit group">
                      <Pencil className="h-4 w-4 text-gray-500" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 shrink-0"
                      onClick={() => setDeleteTarget({ type: "group", id: g.id, name: g.name })}
                    >
                      <Trash2 className="h-4 w-4 text-red-500" />
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* Students list */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between space-y-0">
            <CardTitle>
              {selectedGroupId === null
                ? "All students"
                : groups.find((g) => g.id === selectedGroupId)?.name ?? "Students"}
            </CardTitle>
            <Button size="sm" onClick={openAddStudent}>
              <UserPlus className="mr-1 h-4 w-4" />
              Add student
            </Button>
          </CardHeader>
          <CardContent>
            {studentsLoading ? (
              <p className="text-sm text-gray-500">Loading students...</p>
            ) : students.length === 0 ? (
              <p className="text-sm text-gray-500">
                {selectedGroupId === null ? "No students yet. Add one above." : "No students in this group."}
              </p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-gray-600">
                      <th className="pb-2 pr-2 text-center font-medium">Name</th>
                      <th className="pb-2 pr-2 text-center font-medium">Age</th>
                      <th className="pb-2 pr-2 text-center font-medium">Gender</th>
                      <th className="pb-2 pr-2 text-center font-medium">Grade</th>
                      <th className="pb-2 pr-2 text-center font-medium">Group</th>
                      <th className="pb-2 text-center font-medium w-20">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {students.map((s) => (
                      <tr key={s.id}>
                        <td className="py-2 pr-2 text-center font-medium">{s.name}</td>
                        <td className="py-2 pr-2 text-center">{s.age ?? "—"}</td>
                        <td className="py-2 pr-2 text-center capitalize">{s.gender ?? "—"}</td>
                        <td className="py-2 pr-2 text-center">{s.grade ?? "—"}</td>
                        <td className="py-2 pr-2 text-center">{s.group_name ?? "—"}</td>
                        <td className="py-2 text-center">
                          <div className="flex justify-center gap-1">
                            <Button variant="ghost" size="icon" onClick={() => openEditStudent(s)}>
                              <Pencil className="h-4 w-4" />
                            </Button>
                            <Button
                              variant="ghost"
                              size="icon"
                              onClick={() => setDeleteTarget({ type: "student", id: s.id, name: s.name })}
                            >
                              <Trash2 className="h-4 w-4 text-red-500" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
