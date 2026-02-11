/**
 * File upload component with drag and drop support
 */

import { useCallback, useMemo } from "react";
import { useDropzone, type FileRejection } from "react-dropzone";
import { Upload, File, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface FileUploadProps {
  onFilesSelected: (files: File[]) => void;
  selectedFiles: File[];
  onRemoveFile: (index: number) => void;
  accept?: Record<string, string[]>;
  maxFiles?: number;
  disabled?: boolean;
  /** Human-readable list of allowed formats, e.g. "TXT, PDF, Word (.docx, .doc)". Used in rejection notification. */
  acceptedFormatsLabel?: string;
  /** Called when user drops or selects unsupported files. If not provided, no notification is shown. */
  onUnsupportedFiles?: (rejected: FileRejection[], acceptedFormatsLabel: string) => void;
}

/** Build a short label from accept map, e.g. "TXT, PDF, DOCX" */
export function getAcceptedFormatsLabel(accept: Record<string, string[]>): string {
  const exts = new Set<string>();
  Object.values(accept).forEach((arr) => arr.forEach((e) => exts.add(e)));
  return (
    Array.from(exts)
      .sort()
      .map((e) => (e.startsWith(".") ? e.slice(1).toUpperCase() : e.toUpperCase()))
      .join(", ") || "supported formats"
  );
}

export function FileUpload({
  onFilesSelected,
  selectedFiles,
  onRemoveFile,
  accept = {
    "application/pdf": [".pdf"],
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": [".docx"],
    "application/msword": [".doc"],
    "image/png": [".png"],
    "image/jpeg": [".jpg", ".jpeg"],
  },
  maxFiles = 10,
  disabled = false,
  acceptedFormatsLabel,
  onUnsupportedFiles,
}: FileUploadProps) {
  const formatsLabel = useMemo(
    () => acceptedFormatsLabel ?? getAcceptedFormatsLabel(accept),
    [accept, acceptedFormatsLabel],
  );

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      onFilesSelected(acceptedFiles);
    },
    [onFilesSelected],
  );

  const onDropRejected = useCallback(
    (rejected: FileRejection[]) => {
      if (rejected.length > 0 && onUnsupportedFiles) {
        onUnsupportedFiles(rejected, formatsLabel);
      }
    },
    [onUnsupportedFiles, formatsLabel],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    onDropRejected,
    accept,
    maxFiles,
    disabled,
  });

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  return (
    <div className="space-y-4">
      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 transition-colors",
          isDragActive ? "border-primary bg-primary/5" : "border-gray-300 hover:border-primary/50 hover:bg-gray-50",
          disabled && "cursor-not-allowed opacity-50",
        )}
      >
        <input {...getInputProps()} />
        <Upload className={cn("mb-4 h-12 w-12", isDragActive ? "text-primary" : "text-gray-400")} />
        <p className="mb-2 text-lg font-medium text-gray-700">{isDragActive ? "Drop files here" : "Drag & drop files here"}</p>
        <p className="text-sm text-gray-500">or click to browse (PDF, Word, Images)</p>
      </div>

      {/* Selected files */}
      {selectedFiles.length > 0 && (
        <div className="space-y-2">
          <p className="text-sm font-medium text-gray-700">Selected files ({selectedFiles.length})</p>
          {selectedFiles.map((file, index) => (
            <div key={`${file.name}-${index}`} className="flex items-center justify-between rounded-lg border bg-white p-3">
              <div className="flex items-center gap-3">
                <File className="h-5 w-5 text-gray-400" />
                <div>
                  <p className="text-sm font-medium text-gray-700">{file.name}</p>
                  <p className="text-xs text-gray-500">{formatFileSize(file.size)}</p>
                </div>
              </div>
              <Button variant="ghost" size="icon" onClick={() => onRemoveFile(index)} disabled={disabled}>
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
