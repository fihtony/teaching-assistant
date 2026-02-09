/**
 * History page - view all graded assignments and essay grading history
 */

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { assignmentsApi } from "@/services/api";
import * as gradingApi from "@/services/gradingApi";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FileText, Search, ChevronLeft, ChevronRight, Eye, Download, Trash2, Filter, Sparkles } from "lucide-react";

export function HistoryPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [essayPage, setEssayPage] = useState(1);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [activeTab, setActiveTab] = useState<"assignments" | "essays">("assignments");

  const { data, isLoading } = useQuery({
    queryKey: ["assignments", page, search, statusFilter],
    queryFn: () =>
      assignmentsApi.list({
        page,
        limit: 10,
        search: search || undefined,
        status: statusFilter !== "all" ? statusFilter : undefined,
      }),
    enabled: activeTab === "assignments",
  });

  const { data: essayData, isLoading: isLoadingEssays } = useQuery({
    queryKey: ["essay-grading-history", essayPage],
    queryFn: () => gradingApi.getGradingHistory(essayPage, 10),
    enabled: activeTab === "essays",
  });

  const assignments = data?.items || [];
  const totalPages = data ? Math.ceil(data.total / 10) : 1;
  const essays = essayData?.items || [];
  const totalEssayPages = essayData ? Math.ceil(essayData.total / 10) : 1;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Grading History</h1>
      </div>

      {/* Tabs */}
      <div className="mb-6 flex gap-2 border-b">
        <button
          onClick={() => setActiveTab("assignments")}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === "assignments"
              ? "border-b-2 border-primary text-primary"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          <FileText className="mr-2 inline h-4 w-4" />
          Assignments
        </button>
        <button
          onClick={() => setActiveTab("essays")}
          className={`px-4 py-2 font-medium transition-colors ${
            activeTab === "essays"
              ? "border-b-2 border-primary text-primary"
              : "text-gray-500 hover:text-gray-700"
          }`}
        >
          <Sparkles className="mr-2 inline h-4 w-4" />
          Essay Grading
        </button>
      </div>

      {activeTab === "assignments" ? (
        <>
          {/* Filters */}
          <Card className="mb-6">
            <CardContent className="flex items-center gap-4 py-4">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <Input
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search by student name..."
                  className="pl-10"
                />
              </div>
              <div className="flex items-center gap-2">
                <Filter className="h-4 w-4 text-gray-400" />
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="rounded-md border px-3 py-2 text-sm"
                >
                  <option value="all">All Status</option>
                  <option value="pending">Pending</option>
                  <option value="processing">Processing</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
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
                <div className="divide-y">
                  {assignments.map((assignment: any) => (
                    <div key={assignment.id} className="flex items-center justify-between py-4">
                      <div className="flex items-center gap-4">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100">
                          <FileText className="h-5 w-5 text-gray-600" />
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">{assignment.student_name || "Unknown Student"}</p>
                          <p className="text-sm text-gray-500">
                            {new Date(assignment.created_at).toLocaleDateString()} • {assignment.source_format?.toUpperCase()}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center gap-4">
                        <StatusBadge status={assignment.status} />
                        {assignment.total_score !== null && (
                          <span className="text-lg font-semibold text-primary">{assignment.total_score}</span>
                        )}
                        <div className="flex items-center gap-1">
                          <Button variant="ghost" size="icon" onClick={() => navigate(`/grade/${assignment.id}`)}>
                            <Eye className="h-4 w-4" />
                          </Button>
                          {assignment.status === "completed" && (
                            <Button variant="ghost" size="icon">
                              <Download className="h-4 w-4" />
                            </Button>
                          )}
                          <Button variant="ghost" size="icon">
                            <Trash2 className="h-4 w-4 text-red-500" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
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
        </>
      ) : (
        <>
          {/* Essay Grading History */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5" />
                Essay Grading History
              </CardTitle>
            </CardHeader>
            <CardContent>
              {isLoadingEssays ? (
                <div className="flex h-32 items-center justify-center">
                  <p className="text-gray-500">Loading...</p>
                </div>
              ) : essays.length === 0 ? (
                <div className="flex h-32 flex-col items-center justify-center gap-2">
                  <Sparkles className="h-12 w-12 text-gray-300" />
                  <p className="text-gray-500">No essay grading history found</p>
                  <Button variant="outline" onClick={() => navigate("/essay-grading")}>
                    Start New Essay Grading
                  </Button>
                </div>
              ) : (
                <>
                  <div className="divide-y">
                    {essays.map((essay: any) => (
                      <div key={essay.id} className="flex items-center justify-between py-4">
                        <div className="flex items-center gap-4">
                          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100">
                            <Sparkles className="h-5 w-5 text-purple-600" />
                          </div>
                          <div>
                            <p className="font-medium text-gray-900">{essay.student_name || "Unknown Student"}</p>
                            <p className="text-sm text-gray-500">
                              {new Date(essay.created_at).toLocaleDateString()} • {essay.student_level || "No level"}
                            </p>
                            {essay.recent_activity && (
                              <p className="text-xs text-gray-400">{essay.recent_activity}</p>
                            )}
                          </div>
                        </div>

                        <div className="flex items-center gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => navigate(`/essay-grading?result=${essay.id}`)}
                            title="View Result"
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => gradingApi.downloadGrading(essay.id)}
                            title="Download Report"
                          >
                            <Download className="h-4 w-4" />
                          </Button>
                          <Button variant="ghost" size="icon" title="Delete">
                            <Trash2 className="h-4 w-4 text-red-500" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Pagination */}
                  {totalEssayPages > 1 && (
                    <div className="mt-4 flex items-center justify-center gap-2">
                      <Button variant="outline" size="icon" disabled={essayPage === 1} onClick={() => setEssayPage((p) => p - 1)}>
                        <ChevronLeft className="h-4 w-4" />
                      </Button>
                      <span className="text-sm text-gray-600">
                        Page {essayPage} of {totalEssayPages}
                      </span>
                      <Button
                        variant="outline"
                        size="icon"
                        disabled={essayPage === totalEssayPages}
                        onClick={() => setEssayPage((p) => p + 1)}
                      >
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    pending: "bg-yellow-100 text-yellow-800",
    processing: "bg-blue-100 text-blue-800",
    completed: "bg-green-100 text-green-800",
    failed: "bg-red-100 text-red-800",
  };

  return (
    <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${styles[status] || styles.pending}`}>
      {status.charAt(0).toUpperCase() + status.slice(1)}
    </span>
  );
}
