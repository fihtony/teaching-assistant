/**
 * History page - view assignments and grading history (from ai_grading + assignments)
 */

import { useState, useMemo } from "react";
import { useQuery, useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { assignmentsApi } from "@/services/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/StatusBadge";
import { FileText, Search, ChevronLeft, ChevronRight, Trash2, Filter, ArrowUp, ArrowDown, ArrowUpDown, Minus } from "lucide-react";
import type { Assignment, AssignmentListResponse } from "@/types";

type SortField = "date" | "student_name" | "title" | "display_status";
type SortOrder = "asc" | "desc" | null;

function formatDisplayDate(value: string | undefined): string {
  if (!value) return "—";
  try {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return value;
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${year}/${month}/${day}`;
  } catch {
    return value;
  }
}

export function HistoryPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<SortField | null>(null);
  const [sortOrder, setSortOrder] = useState<SortOrder>(null);

  const deleteMutation = useMutation({
    mutationFn: (id: string) => assignmentsApi.delete(id),
    onSuccess: () => {
      // Invalidate and refetch
      window.location.reload();
    },
  });

  // Determine actual sort order for API
  const actualSortOrder = sortOrder === null ? "desc" : sortOrder;

  const { data, isLoading } = useQuery({
    queryKey: ["assignments", page, search, statusFilter, sortBy, actualSortOrder],
    queryFn: () =>
      assignmentsApi.list({
        page,
        page_size: 10,
        search: search || undefined,
        status: statusFilter !== "all" ? statusFilter : undefined,
        sort_by: sortBy ?? "date",
        sort_order: actualSortOrder ?? "desc",
      }),
  });

  const assignments = data?.items || [];
  const totalPages = data ? Math.ceil((data.total ?? 0) / 10) : 1;
  const statusOptions = data?.status_options || [];

  const handleSort = (field: SortField) => {
    if (sortBy === field) {
      // Same field clicked
      if (sortOrder === null) {
        // Was unsorted, now ascending
        setSortOrder("asc");
      } else if (sortOrder === "asc") {
        // Was ascending, now descending
        setSortOrder("desc");
      } else {
        // Was descending, now unsorted (null)
        setSortOrder(null);
        setSortBy(null);
      }
    } else {
      // Different field clicked
      setSortBy(field);
      setSortOrder("asc");
    }
  };

  const getSortIcon = (field: SortField) => {
    if (sortBy !== field) return <ArrowUpDown className="h-3 w-3" />;
    if (sortOrder === "asc") return <ArrowUp className="h-3 w-3" />;
    if (sortOrder === "desc") return <ArrowDown className="h-3 w-3" />;
    return <Minus className="h-3 w-3" />;
  };

  const handleDelete = (assignment: Assignment) => {
    const message = `Are you sure you want to delete this assignment?\n\nTitle: ${assignment.title || "Assignment"}\nStudent: ${assignment.student_name || "—"}\nStatus: ${assignment.display_status || "—"}\nTemplate: ${assignment.template_display || "—"}`;
    if (window.confirm(message)) {
      deleteMutation.mutate(String(assignment.id));
    }
  };

  const handleRowClick = (assignmentId: number | string, event: React.MouseEvent) => {
    // Check if clicked element is delete button
    const target = event.target as HTMLElement;
    const deleteButton = target.closest('button[title="Delete"]');
    if (!deleteButton) {
      navigate(`/grade/${assignmentId}`);
    }
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Grading History</h1>
      </div>

      {/* Filters */}
      <Card className="mb-6">
        <CardContent className="flex items-center gap-4 py-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by title or student name..."
              className="pl-10"
            />
          </div>
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-gray-400" />
            <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="rounded-md border px-3 py-2 text-sm">
              <option value="all">All Status</option>
              {statusOptions.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
          </div>
        </CardContent>
      </Card>

      {/* Assignment list */}
      <Card>
        <CardHeader>
          <CardTitle>Assignments</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex h-32 items-center justify-center">
              <p className="text-gray-500">Loading...</p>
            </div>
          ) : assignments.length === 0 ? (
            <div className="flex h-32 flex-col items-center justify-center gap-2">
              <FileText className="h-12 w-12 text-gray-300" />
              <p className="text-gray-500">No assignments found</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-gray-600">
                    <th className="pb-2 pr-4 font-medium cursor-pointer hover:bg-gray-100 select-none" onClick={() => handleSort("title")}>
                      <div className="flex items-center gap-1">
                        Title
                        {getSortIcon("title")}
                      </div>
                    </th>
                    <th
                      className="pb-2 pr-4 font-medium cursor-pointer hover:bg-gray-100 select-none"
                      onClick={() => handleSort("student_name")}
                    >
                      <div className="flex items-center gap-1">
                        Student Name
                        {getSortIcon("student_name")}
                      </div>
                    </th>
                    <th className="pb-2 pr-4 font-medium">Template</th>
                    <th
                      className="pb-2 pr-4 font-medium cursor-pointer hover:bg-gray-100 select-none"
                      onClick={() => handleSort("display_status")}
                    >
                      <div className="flex items-center gap-1">
                        Status
                        {getSortIcon("display_status")}
                      </div>
                    </th>
                    <th className="pb-2 pr-4 font-medium cursor-pointer hover:bg-gray-100 select-none" onClick={() => handleSort("date")}>
                      <div className="flex items-center gap-1">
                        Date
                        {getSortIcon("date")}
                      </div>
                    </th>
                    <th className="pb-2 w-16">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {assignments.map((assignment: Assignment) => (
                    <tr key={assignment.id} className="cursor-pointer hover:bg-gray-50" onClick={(e) => handleRowClick(assignment.id, e)}>
                      <td className="py-3 pr-4 font-medium text-gray-900 max-w-[200px] truncate" title={assignment.title ?? ""}>
                        {assignment.title || "Assignment"}
                      </td>
                      <td className="py-3 pr-4 text-gray-700">{assignment.student_name || "—"}</td>
                      <td className="py-3 pr-4 text-gray-700 max-w-[150px] truncate" title={assignment.template_display ?? ""}>
                        {assignment.template_display || "—"}
                      </td>
                      <td className="py-3 pr-4">
                        <StatusBadge status={assignment.display_status || assignment.status} />
                      </td>
                      <td className="py-3 pr-4 text-gray-600">{formatDisplayDate(assignment.display_date)}</td>
                      <td className="py-3">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(assignment);
                          }}
                          title="Delete"
                          disabled={deleteMutation.isPending}
                        >
                          <Trash2 className="h-4 w-4 text-red-500" />
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="mt-4 flex items-center justify-center gap-2">
              <Button variant="outline" size="icon" disabled={page === 1} onClick={() => setPage((p) => p - 1)}>
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="text-sm text-gray-600">
                Page {page} of {totalPages}
              </span>
              <Button variant="outline" size="icon" disabled={page === totalPages} onClick={() => setPage((p) => p + 1)}>
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
