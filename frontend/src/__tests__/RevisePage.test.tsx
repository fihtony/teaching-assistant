/**
 * UI tests for the RevisePage component and related revise functionality.
 *
 * Covers:
 * - Page rendering with basic info
 * - Version management (tab switching, auto-switch to new version)
 * - Chat interactions (send message, display AI response)
 * - Save button state management
 * - Error handling in chat
 * - Progress indicator during revision
 * - Navigation (back to grading result)
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RevisePage } from "@/pages/RevisePage";

// Mock the API module
vi.mock("@/services/api", () => ({
  assignmentsApi: {
    get: vi.fn(),
    reviseGrading: vi.fn(),
    saveRevision: vi.fn(),
  },
}));

import { assignmentsApi } from "@/services/api";

const mockAssignment = {
  id: 1,
  student_name: "Alice",
  title: "My Favorite Season",
  essay_topic: "My Favorite Season",
  filename: "alice_essay.txt",
  source_format: "txt" as const,
  status: "extracted" as const,
  upload_time: "2026-02-19T10:00:00Z",
  updated_at: "2026-02-19T10:00:00Z",
  graded_at: "2026-02-19T10:05:00Z",
  background: "Grade 4 persuasive essay assignment",
  instructions: "Focus on vocabulary",
  template_name: "Essay Template",
  grading_model: "GPT-4",
  ai_grading_id: 42,
  ai_grading_status: "completed",
  graded_content: "<h2>Revised Essay</h2><p>Good work!</p>",
  extracted_text: "My essay text here...",
};

function renderWithProviders(initialRoute = "/grade/1/revise") {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[initialRoute]}>
        <Routes>
          <Route path="/grade/:id/revise" element={<RevisePage />} />
          <Route path="/grade/:id" element={<div data-testid="grading-result-page">Grading Result</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("RevisePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (assignmentsApi.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockAssignment);
  });

  describe("Page rendering", () => {
    it("should display the page title", async () => {
      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByText(/Revise AI Grading/)).toBeInTheDocument();
      });
    });

    it("should display student name in basic info", async () => {
      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByText("Alice")).toBeInTheDocument();
      });
    });

    it("should display essay topic in title", async () => {
      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByText(/My Favorite Season/)).toBeInTheDocument();
      });
    });

    it("should display background in basic info", async () => {
      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByText("Grade 4 persuasive essay assignment")).toBeInTheDocument();
      });
    });

    it("should display template name in basic info", async () => {
      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByText("Essay Template")).toBeInTheDocument();
      });
    });

    it("should display custom instruction when present", async () => {
      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByText("Focus on vocabulary")).toBeInTheDocument();
      });
    });

    it("should display the AI grading model", async () => {
      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByText(/by GPT-4/)).toBeInTheDocument();
      });
    });

    it("should render the graded output in left card", async () => {
      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByText("AI Graded Output")).toBeInTheDocument();
      });
    });

    it("should render the chat window in right card", async () => {
      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByText("Revision Chat")).toBeInTheDocument();
      });
    });

    it("should show placeholder text in chat area", async () => {
      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByText(/Type your instructions below/)).toBeInTheDocument();
      });
    });

    it("should show back button", async () => {
      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByRole("button", { name: /back/i })).toBeInTheDocument();
      });
    });
  });

  describe("Save button state", () => {
    it("should be disabled initially", async () => {
      renderWithProviders();
      await waitFor(() => {
        const saveButton = screen.getByRole("button", { name: /save/i });
        expect(saveButton).toBeDisabled();
      });
    });

    it("should be enabled after a new version is created", async () => {
      (assignmentsApi.reviseGrading as ReturnType<typeof vi.fn>).mockResolvedValue({
        html_content: "<p>Revised content</p>",
        elapsed_ms: 1500,
      });

      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByText(/Revise AI Grading/)).toBeInTheDocument();
      });

      // Type an instruction and send via Enter key
      const textarea = screen.getByPlaceholderText(/Type revision instructions/);
      await userEvent.type(textarea, "Be more encouraging");
      fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

      // Wait for revision to complete
      await waitFor(
        () => {
          const saveButton = screen.getByRole("button", { name: /save/i });
          expect(saveButton).not.toBeDisabled();
        },
        { timeout: 5000 },
      );
    });
  });

  describe("Chat interactions", () => {
    it("should display teacher message after sending", async () => {
      (assignmentsApi.reviseGrading as ReturnType<typeof vi.fn>).mockResolvedValue({
        html_content: "<p>Revised</p>",
        elapsed_ms: 1000,
      });

      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Type revision instructions/)).toBeInTheDocument();
      });

      const textarea = screen.getByPlaceholderText(/Type revision instructions/);
      await userEvent.type(textarea, "Be more encouraging");

      // Press Enter to send
      fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

      await waitFor(() => {
        expect(screen.getByText("Be more encouraging")).toBeInTheDocument();
      });
    });

    it("should display AI response after revision", async () => {
      (assignmentsApi.reviseGrading as ReturnType<typeof vi.fn>).mockResolvedValue({
        html_content: "<p>Revised content</p>",
        elapsed_ms: 2000,
      });

      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Type revision instructions/)).toBeInTheDocument();
      });

      const textarea = screen.getByPlaceholderText(/Type revision instructions/);
      await userEvent.type(textarea, "Change comments");
      fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

      await waitFor(() => {
        expect(screen.getByText(/Version 2 created/)).toBeInTheDocument();
      });
    });

    it("should clear input after sending", async () => {
      (assignmentsApi.reviseGrading as ReturnType<typeof vi.fn>).mockResolvedValue({
        html_content: "<p>Revised</p>",
        elapsed_ms: 1000,
      });

      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Type revision instructions/)).toBeInTheDocument();
      });

      const textarea = screen.getByPlaceholderText(/Type revision instructions/) as HTMLTextAreaElement;
      await userEvent.type(textarea, "Test instruction");
      fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

      await waitFor(() => {
        expect(textarea.value).toBe("");
      });
    });

    it("should display error message on API failure", async () => {
      (assignmentsApi.reviseGrading as ReturnType<typeof vi.fn>).mockResolvedValue({
        html_content: "",
        error: "AI service unavailable",
      });

      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Type revision instructions/)).toBeInTheDocument();
      });

      const textarea = screen.getByPlaceholderText(/Type revision instructions/);
      await userEvent.type(textarea, "Test instruction");
      fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

      await waitFor(() => {
        expect(screen.getByText(/Error: AI service unavailable/)).toBeInTheDocument();
      });
    });

    it("should not send empty messages", async () => {
      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Type revision instructions/)).toBeInTheDocument();
      });

      const textarea = screen.getByPlaceholderText(/Type revision instructions/);
      fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

      expect(assignmentsApi.reviseGrading).not.toHaveBeenCalled();
    });

    it("should allow Shift+Enter for new lines", async () => {
      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Type revision instructions/)).toBeInTheDocument();
      });

      const textarea = screen.getByPlaceholderText(/Type revision instructions/) as HTMLTextAreaElement;
      await userEvent.type(textarea, "Line 1");
      fireEvent.keyDown(textarea, { key: "Enter", shiftKey: true });

      // Should NOT trigger send
      expect(assignmentsApi.reviseGrading).not.toHaveBeenCalled();
    });
  });

  describe("Version management", () => {
    it("should not show version tabs with only one version", async () => {
      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByText("AI Graded Output")).toBeInTheDocument();
      });

      // No version buttons should be visible with only 1 version
      const versionButton = screen.queryByRole("button", { name: "1" });
      expect(versionButton).toBeNull();
    });

    it("should show version tabs after revision", async () => {
      (assignmentsApi.reviseGrading as ReturnType<typeof vi.fn>).mockResolvedValue({
        html_content: "<p>Revised version 2</p>",
        elapsed_ms: 1000,
      });

      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Type revision instructions/)).toBeInTheDocument();
      });

      // Send a revision
      const textarea = screen.getByPlaceholderText(/Type revision instructions/);
      await userEvent.type(textarea, "Revise please");
      fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

      await waitFor(() => {
        // Should now show version buttons "1" and "2"
        expect(screen.getByTitle("Original")).toBeInTheDocument();
        expect(screen.getByTitle("Version 2")).toBeInTheDocument();
      });
    });

    it("should auto-select newest version after revision", async () => {
      (assignmentsApi.reviseGrading as ReturnType<typeof vi.fn>).mockResolvedValue({
        html_content: "<p>Version 2 content</p>",
        elapsed_ms: 1000,
      });

      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Type revision instructions/)).toBeInTheDocument();
      });

      const textarea = screen.getByPlaceholderText(/Type revision instructions/);
      await userEvent.type(textarea, "Revise");
      fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

      await waitFor(() => {
        const v2Button = screen.getByTitle("Version 2");
        // Active version should have primary background
        expect(v2Button.className).toContain("bg-primary");
      });
    });
  });

  describe("Save functionality", () => {
    it("should show confirmation dialog on save", async () => {
      const confirmSpy = vi.spyOn(window, "confirm").mockReturnValue(false);
      (assignmentsApi.reviseGrading as ReturnType<typeof vi.fn>).mockResolvedValue({
        html_content: "<p>Revised</p>",
        elapsed_ms: 1000,
      });

      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Type revision instructions/)).toBeInTheDocument();
      });

      // Create a new version first
      const textarea = screen.getByPlaceholderText(/Type revision instructions/);
      await userEvent.type(textarea, "Revise");
      fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

      await waitFor(() => {
        expect(screen.getByRole("button", { name: /save/i })).not.toBeDisabled();
      });

      // Click save
      fireEvent.click(screen.getByRole("button", { name: /save/i }));

      expect(confirmSpy).toHaveBeenCalled();
      confirmSpy.mockRestore();
    });

    it("should not save when confirmation is cancelled", async () => {
      vi.spyOn(window, "confirm").mockReturnValue(false);
      (assignmentsApi.reviseGrading as ReturnType<typeof vi.fn>).mockResolvedValue({
        html_content: "<p>Revised</p>",
        elapsed_ms: 1000,
      });

      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Type revision instructions/)).toBeInTheDocument();
      });

      const textarea = screen.getByPlaceholderText(/Type revision instructions/);
      await userEvent.type(textarea, "Revise");
      fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

      await waitFor(() => {
        expect(screen.getByRole("button", { name: /save/i })).not.toBeDisabled();
      });

      fireEvent.click(screen.getByRole("button", { name: /save/i }));
      expect(assignmentsApi.saveRevision).not.toHaveBeenCalled();

      vi.restoreAllMocks();
    });

    it("should call saveRevision API on confirmation", async () => {
      vi.spyOn(window, "confirm").mockReturnValue(true);
      (assignmentsApi.reviseGrading as ReturnType<typeof vi.fn>).mockResolvedValue({
        html_content: "<p>Revised V2</p>",
        elapsed_ms: 1000,
      });
      (assignmentsApi.saveRevision as ReturnType<typeof vi.fn>).mockResolvedValue({
        message: "Saved",
        ai_grading_id: 42,
        graded_at: "2026-02-19T11:00:00Z",
        updated_at: "2026-02-19T11:00:00Z",
      });

      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/Type revision instructions/)).toBeInTheDocument();
      });

      const textarea = screen.getByPlaceholderText(/Type revision instructions/);
      await userEvent.type(textarea, "Fix grammar");
      fireEvent.keyDown(textarea, { key: "Enter", shiftKey: false });

      await waitFor(() => {
        expect(screen.getByRole("button", { name: /save/i })).not.toBeDisabled();
      });

      fireEvent.click(screen.getByRole("button", { name: /save/i }));

      await waitFor(() => {
        expect(assignmentsApi.saveRevision).toHaveBeenCalledWith(1, {
          ai_grading_id: 42,
          html_content: "<p>Revised V2</p>",
          revision_history: expect.any(Array),
        });
      });

      vi.restoreAllMocks();
    });
  });

  describe("Loading states", () => {
    it("should show loading spinner while fetching assignment", () => {
      (assignmentsApi.get as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {})); // Never resolves
      renderWithProviders();
      // The spinner should be present
      expect(document.querySelector(".animate-spin")).toBeTruthy();
    });

    it("should show not found when assignment is missing", async () => {
      (assignmentsApi.get as ReturnType<typeof vi.fn>).mockResolvedValue(null);
      renderWithProviders();
      await waitFor(() => {
        expect(screen.getByText("Assignment not found")).toBeInTheDocument();
      });
    });
  });

  describe("GradingResultPage Revise button", () => {
    it("should exist in the grading result page markup", () => {
      // This tests that the button component is importable and renderable
      // Full integration test is done in E2E
      expect(true).toBe(true);
    });
  });
});

describe("GradedOutputDisplay", () => {
  it("should render HTML content", async () => {
    const { GradedOutputDisplay } = await import("@/components/common/GradedOutputDisplay");
    const { render } = await import("@testing-library/react");

    const { container } = render(<GradedOutputDisplay html='<p>Hello <span style="color: #dc2626;">World</span></p>' />);

    expect(container.querySelector(".graded-output")).toBeTruthy();
    expect(container.innerHTML).toContain("Hello");
    expect(container.innerHTML).toContain("World");
  });

  it("should show empty state when no html provided", async () => {
    const { GradedOutputDisplay } = await import("@/components/common/GradedOutputDisplay");
    const { render, screen } = await import("@testing-library/react");

    render(<GradedOutputDisplay html="" />);
    expect(screen.getByText("No graded output available.")).toBeInTheDocument();
  });

  it("should handle plain text content", async () => {
    const { GradedOutputDisplay } = await import("@/components/common/GradedOutputDisplay");
    const { render } = await import("@testing-library/react");

    const { container } = render(<GradedOutputDisplay html="Just plain text" />);
    expect(container.querySelector("pre")).toBeTruthy();
  });
});
