/**
 * Common progress dialog component for grading
 * Reusable by Dashboard and GradingPage
 */

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Sparkles, CheckCircle } from "lucide-react";
import { PROGRESS_LABELS, type ProgressStep } from "@/hooks/useGradingProgress";

interface GradingProgressDialogProps {
  open: boolean;
  step: ProgressStep;
  error: string | null;
  phaseElapsedMs: number | null;
  totalElapsedMs: number;
  phaseTimes: Record<string, number>;
  onCancel: () => void;
  onClose: () => void;
}

function formatElapsedMs(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

function formatPhaseTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  if (totalSeconds < 60) {
    return `${totalSeconds}s`;
  }
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}m ${s}s`;
}

export function GradingProgressDialog({
  open,
  step,
  error,
  phaseElapsedMs,
  totalElapsedMs,
  phaseTimes,
  onCancel,
  onClose,
}: GradingProgressDialogProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <Card className="w-full max-w-md mx-4 shadow-xl">
        <CardHeader>
          <CardTitle>Grading in progress</CardTitle>
          <CardDescription>{error ? "An error occurred." : "Please wait while we process the assignment."}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {error ? (
            <div className="space-y-3">
              <p className="text-sm text-red-600">{error}</p>
              {phaseElapsedMs != null && <p className="text-xs text-gray-500">Elapsed: {(phaseElapsedMs / 1000).toFixed(1)}s</p>}
              <Button variant="outline" onClick={onClose}>
                Close
              </Button>
            </div>
          ) : step === "completed" ? (
            <div className="space-y-3">
              <ul className="space-y-2">
                {(["uploading", "extracting", "grading", "completed"] as const).map((s) => {
                  const phaseTime = phaseTimes[s];

                  return (
                    <li key={s} className="flex items-center gap-2 text-sm text-gray-500">
                      <CheckCircle className="h-4 w-4 shrink-0 text-green-500" />
                      <span>
                        {PROGRESS_LABELS[s]}
                        {phaseTime && <span className="ml-2 italic text-xs">- {formatPhaseTime(phaseTime)}</span>}
                      </span>
                    </li>
                  );
                })}
              </ul>
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs text-gray-500">Total: {formatElapsedMs(totalElapsedMs)}</p>
                <Button variant="default" size="sm" onClick={onClose}>
                  Close
                </Button>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <ul className="space-y-2">
                {(["uploading", "extracting", "grading", "completed"] as const).map((s) => {
                  const isActive = step === s;
                  const order = ["uploading", "extracting", "grading", "completed"] as const;
                  const stepIndex = order.indexOf(s);
                  const currentIndex = step ? order.indexOf(step) : -1;
                  const isDoneStep = currentIndex > stepIndex;
                  const phaseTime = phaseTimes[s];

                  return (
                    <li
                      key={s}
                      className={`flex items-center gap-2 text-sm ${
                        isActive ? "font-medium text-primary" : isDoneStep ? "text-gray-500" : "text-gray-400"
                      }`}
                    >
                      {isDoneStep ? (
                        <CheckCircle className="h-4 w-4 shrink-0 text-green-500" />
                      ) : isActive ? (
                        <Sparkles className="h-4 w-4 shrink-0 animate-spin text-primary" />
                      ) : (
                        <span className="h-4 w-4 shrink-0 rounded-full border-2 border-gray-300" />
                      )}
                      <span>
                        {PROGRESS_LABELS[s]}
                        {isDoneStep && phaseTime && <span className="ml-2 italic text-xs">- {formatPhaseTime(phaseTime)}</span>}
                      </span>
                    </li>
                  );
                })}
              </ul>
              <div className="flex items-center justify-between gap-2">
                <p className="text-xs text-gray-500">Total: {formatElapsedMs(totalElapsedMs)}</p>
                <Button variant="outline" size="sm" onClick={onCancel}>
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
