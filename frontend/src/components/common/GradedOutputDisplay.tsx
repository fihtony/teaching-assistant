/**
 * Shared component for displaying AI-graded output with proper styling
 * Used by both GradingResultPage and BuildInstructionPage
 *
 * Features:
 * - Displays HTML-formatted grading output with correction markup
 * - Red strikethrough for deletions/errors
 * - Red text for corrections and additions
 * - Proper heading and list styling
 * - Responsive layout with proper spacing
 * - CSS: graded-output prose prose-sm max-w-none
 * - Auto-detects HTML vs plain text and handles gracefully
 */

import { memo, useMemo } from "react";

interface GradedOutputDisplayProps {
  html: string;
  className?: string;
}

/**
 * Check if content looks like HTML
 * Simple heuristic: contains HTML tags
 */
function isHtmlContent(content: string): boolean {
  const isHtml = /<[a-z][\s\S]*>/i.test(content);
  if (content.length < 500) {
    console.log("[GradedOutputDisplay] HTML detection:", {
      contentLength: content.length,
      isHtml,
      first100: content.substring(0, 100),
      regexPattern: /<[a-z][\s\S]*>/i.toString(),
    });
  }
  return isHtml;
}

export const GradedOutputDisplay = memo(function GradedOutputDisplay({ html, className = "" }: GradedOutputDisplayProps) {
  const { safeHtml } = useMemo(() => {
    if (!html) return { isHtml: false, safeHtml: "" };

    const htmlChecked = isHtmlContent(html);
    console.log("[GradedOutputDisplay] Content analysis:", {
      contentLength: html.length,
      isHtmlContent: htmlChecked,
      containsSpanTags: html.includes("<span"),
      containsPTags: html.includes("<p"),
      containsHTags: html.includes("<h"),
      containsMarkdownSyntax: html.includes("~~") || html.includes("{{"),
    });

    const processed = htmlChecked ? html : escapeHtml(html);

    if (!htmlChecked) {
      // If it's plain text, wrap it in <p> tags for better display
      return {
        isHtml: false,
        safeHtml: `<pre style="white-space: pre-wrap; word-wrap: break-word; font-family: inherit;">${processed}</pre>`,
      };
    }

    // It's HTML, display directly with proper styling
    return {
      isHtml: true,
      safeHtml: html,
    };
  }, [html]);

  if (!html) {
    return <p className="text-gray-500">No graded output available.</p>;
  }

  // Display HTML with graded-output styling for proper formatting of corrections
  return <div className={`graded-output prose prose-sm max-w-none ${className}`} dangerouslySetInnerHTML={{ __html: safeHtml }} />;
});

// Helper to escape HTML to prevent XSS when displaying plain text as text
function escapeHtml(text: string): string {
  const map: Record<string, string> = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  };
  return text.replace(/[&<>"']/g, (char) => map[char]);
}

GradedOutputDisplay.displayName = "GradedOutputDisplay";
