/**
 * StatusBadge component - displays status with color coding
 * Used in both history list and grading page
 */

interface StatusBadgeProps {
  status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const getStatusStyle = (status: string): string => {
    const s = status.toLowerCase();
    if (s === "ready for grading") {
      return "bg-blue-100 text-blue-800";
    }
    if (s === "uploaded") {
      return "bg-gray-100 text-gray-800";
    }
    if (s === "extracted") {
      return "bg-green-100 text-green-800";
    }
    if (s === "uploading") {
      return "bg-yellow-100 text-yellow-800";
    }
    if (s === "grading") {
      return "bg-blue-100 text-blue-800";
    }
    if (s === "completed") {
      return "bg-green-100 text-green-800";
    }
    if (s === "not_started") {
      return "bg-gray-100 text-gray-800";
    }
    if (s.includes("failed")) {
      return "bg-red-100 text-red-800";
    }
    return "bg-gray-100 text-gray-800";
  };

  const style = getStatusStyle(status);
  // Capitalize first letter of each word
  const label = status
    .split(" ")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
    .join(" ");

  return <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${style}`}>{label}</span>;
}
