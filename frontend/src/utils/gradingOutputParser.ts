/**
 * Parser for graded output HTML/Markdown
 * Extracts and structures the different sections of graded assignments
 * Handles both direct HTML from backend and markdown-style correction markup
 */

export interface GradingOutputSection {
  title: string;
  content: string;
  type: 'revised-essay' | 'detailed-corrections' | 'comments';
}

export interface ParsedGradingOutput {
  sections: GradingOutputSection[];
  rawHtml: string;
}

/**
 * Parse graded output HTML to extract main sections
 * Looks for common section patterns:
 * - "Revised Essay" or "essay" heading
 * - "Detailed Corrections" or "corrections" heading
 * - "Teacher's Comments" or "comments" heading
 */
export function parseGradingOutput(html: string): ParsedGradingOutput {
  const sections: GradingOutputSection[] = [];
  
  // Section definitions - try to find headers and extract content until next header
  const sectionConfigs = [
    {
      headerPattern: /revised\s+essay/i,
      type: 'revised-essay' as const,
      title: 'Revised Essay'
    },
    {
      headerPattern: /detailed\s+corrections/i,
      type: 'detailed-corrections' as const,
      title: 'Detailed Corrections'
    },
    {
      headerPattern: /teacher['']?s?\s+comments/i,
      type: 'comments' as const,
      title: "Teacher's Comments"
    }
  ];

  // First, find all headers with their positions
  const headerMatches: Array<{
    text: string;
    index: number;
    config: typeof sectionConfigs[0];
  }> = [];

  for (const config of sectionConfigs) {
    const match = html.match(config.headerPattern);
    if (match && match.index !== undefined) {
      headerMatches.push({
        text: match[0],
        index: match.index,
        config
      });
    }
  }

  // Sort by position
  headerMatches.sort((a, b) => a.index - b.index);

  // Extract content for each section
  for (let i = 0; i < headerMatches.length; i++) {
    const { index, config } = headerMatches[i];
    
    // Find the position right after the header
    const contentStart = index + headerMatches[i].text.length;
    
    // Find the end: either the next header or end of string
    let contentEnd = html.length;
    if (i < headerMatches.length - 1) {
      contentEnd = headerMatches[i + 1].index;
    }

    const content = html.substring(contentStart, contentEnd).trim();

    if (content) {  // Only add sections that have content
      sections.push({
        title: config.title,
        content,
        type: config.type
      });
    }
  }

  return {
    sections,
    rawHtml: html
  };
}

/**
 * Check if HTML contains grading correction markup
 * (red strikethrough, red text, underline)
 */
export function hasCorrectionsMarkup(html: string): boolean {
  return /style="[^"]*color:\s*red/.test(html) || 
         /class="correction-/.test(html);
}

/**
 * Extract text content from HTML (strip tags)
 */
export function stripHtmlTags(html: string): string {
  return html
    .replace(/<[^>]*>/g, '')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&')
    .trim();
}

/**
 * Format section content for display
 * Handle proper paragraph breaks and spacing
 */
export function formatSectionContent(content: string): string {
  // Ensure proper paragraph spacing
  return content
    .replace(/<\/p>\s*<p>/g, '</p><p>')
    .replace(/<\/li>\s*<li>/g, '</li><li>')
    .trim();
}
