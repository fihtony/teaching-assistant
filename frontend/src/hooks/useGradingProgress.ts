/**
 * Common hook for managing grading progress with phases
 * Reusable by Dashboard and GradingPage
 */

import { useCallback, useRef, useState } from "react";
import { assignmentsApi } from "@/services/api";

export type ProgressStep = "uploading" | "extracting" | "grading" | "completed" | null;

export const PROGRESS_LABELS: Record<NonNullable<ProgressStep>, string> = {
  uploading: "Uploading file",
  extracting: "Analysing context",
  grading: "AI grading",
  completed: "Prepare report",
};

export interface GradingProgressConfig {
  file?: File;
  studentId?: number;
  studentName?: string;
  background?: string;
  templateId?: string | number;
  contentText?: string;
  assignmentId?: string | number;
  instructions?: string; // Custom grading instructions (for preview mode like BuildInstructionPage)
  aiModel?: string; // AI model to use for grading (overrides default from settings)
  isPreview?: boolean; // Use preview endpoints (non-persistent grading)
}

export interface UseGradingProgressReturn {
  progressOpen: boolean;
  progressStep: ProgressStep;
  progressError: string | null;
  phaseElapsedMs: number | null;
  totalElapsedMs: number;
  phaseTimes: Record<string, number>;
  startGradingProcess: (config: GradingProgressConfig) => Promise<string | null>; // Returns assignment ID or null on error
  handleCancelGrading: () => void;
  closeProgress: () => void;
}

export function useGradingProgress(): UseGradingProgressReturn {
  const [progressOpen, setProgressOpen] = useState(false);
  const [progressStep, setProgressStep] = useState<ProgressStep>(null);
  const [progressError, setProgressError] = useState<string | null>(null);
  const [phaseElapsedMs, setPhaseElapsedMs] = useState<number | null>(null);
  const [totalElapsedMs, setTotalElapsedMs] = useState(0);
  const [phaseTimes, setPhaseTimes] = useState<Record<string, number>>({});

  const startTimeRef = useRef<number | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const cancelledRef = useRef(false);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const handleCancelGrading = useCallback(() => {
    cancelledRef.current = true;
    abortControllerRef.current?.abort();
  }, []);

  const closeProgress = useCallback(() => {
    setProgressOpen(false);
    setProgressStep(null);
    setProgressError(null);
    setPhaseElapsedMs(null);
    setTotalElapsedMs(0);
    setPhaseTimes({});
    startTimeRef.current = null;
    abortControllerRef.current = null;
    if (timerRef.current) clearInterval(timerRef.current);
  }, []);

  const startGradingProcess = useCallback(async (config: GradingProgressConfig): Promise<string | null> => {
    // Reset state
    setProgressError(null);
    setPhaseElapsedMs(null);
    setTotalElapsedMs(0);
    setPhaseTimes({});
    setProgressOpen(true);
    setProgressStep("uploading");
    startTimeRef.current = Date.now();
    cancelledRef.current = false;
    abortControllerRef.current = new AbortController();
    const signal = abortControllerRef.current.signal;

    // Start timer to update total elapsed
    if (timerRef.current) clearInterval(timerRef.current);
    timerRef.current = setInterval(() => {
      if (startTimeRef.current) {
        setTotalElapsedMs(Date.now() - startTimeRef.current);
      }
    }, 500);

    try {
      let assignmentId: string | number;

      // Step 1: Upload (if file provided) or use existing assignment
      if (config.file) {
        setProgressStep("uploading");
        const uploadRes = config.isPreview
          ? await assignmentsApi.previewGradeUploadPhase(
              {
                file: config.file,
                student_id: config.studentId || undefined,
                student_name: config.studentName || undefined,
                background: config.background || undefined,
                instructions: config.instructions || undefined,
                ai_model: config.aiModel || undefined,
              },
              signal,
            )
          : await assignmentsApi.gradeUploadPhase(
              {
                file: config.file,
                student_id: config.studentId || undefined,
                student_name: config.studentName || undefined,
                background: config.background || undefined,
                template_id: config.templateId ? Number(config.templateId) : undefined,
              },
              signal,
            );

        if (cancelledRef.current) return null;

        if (uploadRes.error) {
          setProgressError(uploadRes.error);
          setPhaseElapsedMs(uploadRes.elapsed_ms ?? null);
          return null;
        }

        setPhaseElapsedMs(uploadRes.elapsed_ms ?? null);
        if (uploadRes.elapsed_ms != null) {
          setPhaseTimes((prev) => ({ ...prev, uploading: uploadRes.elapsed_ms as number }));
        }

        assignmentId = uploadRes.assignment_id!;
      } else {
        // Using existing assignment, skip upload phase
        assignmentId = config.assignmentId!;
      }

      // Ensure assignmentId is a string for preview API calls (session ID), or number for regular API
      const assignmentIdForNextPhase = config.isPreview
        ? String(assignmentId)
        : typeof assignmentId === "string"
          ? parseInt(assignmentId, 10)
          : assignmentId;

      // Step 2: Analyze context
      setProgressStep("extracting");
      const analyzeRes = config.isPreview
        ? await assignmentsApi.previewAnalyzeContextPhase(String(assignmentIdForNextPhase), signal)
        : await assignmentsApi.analyzeContextPhase(assignmentIdForNextPhase as number, signal);

      if (cancelledRef.current) return null;

      if (analyzeRes.error) {
        setProgressError(analyzeRes.error);
        setPhaseElapsedMs(analyzeRes.elapsed_ms ?? null);
        return null;
      }

      setPhaseElapsedMs(analyzeRes.elapsed_ms ?? null);
      if (analyzeRes.elapsed_ms != null) {
        setPhaseTimes((prev) => ({ ...prev, extracting: analyzeRes.elapsed_ms as number }));
      }

      // Step 3: Run grading
      setProgressStep("grading");
      const runRes = config.isPreview
        ? await assignmentsApi.previewRunGradingPhase(String(assignmentIdForNextPhase), signal)
        : await assignmentsApi.runGradingPhase(assignmentIdForNextPhase as number, signal);

      if (cancelledRef.current) return null;

      if (runRes.error) {
        setProgressError(runRes.error);
        setPhaseElapsedMs(runRes.elapsed_ms ?? null);
        return null;
      }

      setPhaseElapsedMs(runRes.elapsed_ms ?? null);
      if (runRes.elapsed_ms != null) {
        setPhaseTimes((prev) => ({ ...prev, grading: runRes.elapsed_ms as number }));
      }

      // Step 4: Show completion
      setProgressStep("completed");
      await new Promise((r) => setTimeout(r, 1500));

      if (cancelledRef.current) return null;

      // Save the total elapsed time to backend (only for persistent grading)
      if (!config.isPreview && startTimeRef.current) {
        const finalTotalMs = Date.now() - startTimeRef.current;
        try {
          await assignmentsApi.updateGradingTime(assignmentIdForNextPhase as number, finalTotalMs);
        } catch (err) {
          // Log but don't fail if we can't save the time
          console.warn("Failed to save grading time:", err);
        }
      }

      return String(assignmentId);
    } catch (err: unknown) {
      if (cancelledRef.current) return null;

      const isAbort =
        err instanceof Error &&
        (err.name === "CanceledError" || err.name === "AbortError" || (err as { code?: string }).code === "ERR_CANCELED");

      if (isAbort) return null;

      const message = err instanceof Error ? err.message : "Something went wrong";
      setProgressError(message);
      return null;
    } finally {
      if (timerRef.current) clearInterval(timerRef.current);
    }
  }, []);

  return {
    progressOpen,
    progressStep,
    progressError,
    phaseElapsedMs,
    totalElapsedMs,
    phaseTimes,
    startGradingProcess,
    handleCancelGrading,
    closeProgress,
  };
}
