"use client";

import React from "react";
import {
  X,
  FileText,
  Calendar,
  Clock,
  User,
  Building,
  Tag,
  Copy,
  Check,
  ExternalLink,
} from "lucide-react";
import { ClinicalDocument } from "@/types/patient";
import { formatDate, formatDateTime } from "@/lib/utils";

interface DocumentViewerProps {
  document: ClinicalDocument | null;
  onClose: () => void;
}

export function DocumentViewer({ document, onClose }: DocumentViewerProps) {
  const [copied, setCopied] = React.useState(false);

  if (!document) return null;

  const handleCopy = () => {
    if (document.text_content) {
      navigator.clipboard.writeText(document.text_content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // Format clinical text paragraphs and sections cleanly
  const renderFormattedContent = (content: string) => {
    const lines = content.split("\n");
    return lines.map((line, idx) => {
      const trimmed = line.trim();
      if (!trimmed) {
        return <div key={idx} className="h-3" />;
      }

      // Check if line looks like a clinical section heading (e.g., "Chief concern:", "Assessment:", etc.)
      const isHeading =
        /^(Chief concern|History|Examination|Assessment|Plan|Impression|Findings|Technique|Indication|Procedure|Clinical History|Discussion|Recommendation|Diagnoses):/i.test(
          trimmed
        ) ||
        (trimmed.endsWith(":") && trimmed.length < 40);

      if (isHeading) {
        const colonIndex = trimmed.indexOf(":");
        if (colonIndex !== -1) {
          const header = trimmed.substring(0, colonIndex + 1);
          const rest = trimmed.substring(colonIndex + 1);
          return (
            <p key={idx} className="mb-2 leading-relaxed text-foreground">
              <span className="font-bold text-primary inline-block min-w-[120px]">{header}</span>
              <span>{rest}</span>
            </p>
          );
        }
        return (
          <h4
            key={idx}
            className="font-bold text-primary text-xs uppercase tracking-wider mt-4 mb-1.5"
          >
            {trimmed}
          </h4>
        );
      }

      return (
        <p key={idx} className="mb-2 leading-relaxed text-foreground">
          {line}
        </p>
      );
    });
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-black/60 backdrop-blur-sm animate-in fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby="doc-viewer-title"
    >
      <div className="bg-card border border-border rounded-xl shadow-2xl max-w-4xl w-full h-[90vh] flex flex-col overflow-hidden text-card-foreground">
        {/* Top Header */}
        <div className="px-6 py-3.5 border-b border-border bg-muted/40 flex items-center justify-between shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <div className="h-9 w-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
              <FileText className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h2
                  id="doc-viewer-title"
                  className="text-base font-bold text-foreground truncate"
                >
                  {document.title}
                </h2>
                <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-secondary text-secondary-foreground border border-border">
                  {document.id}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] uppercase font-semibold tracking-wider bg-primary/10 text-primary">
                  {document.document_type.replace(/_/g, " ")}
                </span>
              </div>
              <p className="text-xs text-muted-foreground mt-0.5">
                Authored by {document.author} • Patient ID: {document.patient_id}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopy}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border bg-background hover:bg-secondary text-xs font-medium text-foreground transition-colors"
              title="Copy clinical text"
            >
              {copied ? (
                <>
                  <Check className="h-3.5 w-3.5 text-emerald-600" />
                  <span className="text-emerald-600 font-semibold">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="h-3.5 w-3.5" />
                  <span>Copy Text</span>
                </>
              )}
            </button>
            <button
              onClick={onClose}
              className="text-muted-foreground hover:text-foreground p-1.5 rounded-md hover:bg-secondary transition-colors"
              aria-label="Close document inspection"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Content Body & Metadata Split */}
        <div className="flex-1 flex flex-col md:flex-row min-h-0 overflow-hidden">
          {/* Main Document Content */}
          <div className="flex-1 p-6 overflow-y-auto bg-background/50 border-b md:border-b-0 md:border-r border-border font-sans text-xs sm:text-sm">
            {document.text_content ? (
              <div className="max-w-prose">
                <div className="p-3 mb-4 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-700 dark:text-amber-400 text-xs font-medium">
                  SYNTHETIC CLINICAL RECORD — NOT FOR CLINICAL USE
                </div>
                <div className="space-y-1">
                  {renderFormattedContent(document.text_content)}
                </div>
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center p-8 text-muted-foreground">
                <FileText className="h-10 w-10 text-muted-foreground/30 mb-2" />
                <p className="font-semibold text-sm">Structured Text Unavailable</p>
                <p className="text-xs text-muted-foreground mt-1 max-w-sm">
                  This record is registered as an external or binary asset (MIME:{" "}
                  <code>{document.mime_type}</code>).
                </p>
              </div>
            )}
          </div>

          {/* Right Provenance & Metadata Panel */}
          <div className="w-full md:w-80 p-5 overflow-y-auto bg-muted/20 shrink-0 space-y-5 text-xs">
            <div>
              <h3 className="font-bold text-foreground uppercase tracking-wider text-[11px] mb-3 flex items-center gap-1.5">
                <Tag className="h-3.5 w-3.5 text-primary" />
                <span>Provenance & Metadata</span>
              </h3>

              <div className="space-y-3 bg-card p-3.5 rounded-lg border border-border">
                <div>
                  <span className="text-muted-foreground block text-[10px] uppercase font-semibold">
                    Document Identifier
                  </span>
                  <span className="font-mono font-medium text-foreground">
                    {document.id}
                  </span>
                </div>

                <div>
                  <span className="text-muted-foreground block text-[10px] uppercase font-semibold">
                    Associated Encounter
                  </span>
                  <span className="font-mono font-medium text-foreground">
                    {document.encounter_id || "Unassociated"}
                  </span>
                </div>

                <div>
                  <span className="text-muted-foreground block text-[10px] uppercase font-semibold">
                    Document Type
                  </span>
                  <span className="font-medium capitalize text-foreground">
                    {document.document_type.replace(/_/g, " ")}
                  </span>
                </div>

                <div>
                  <span className="text-muted-foreground block text-[10px] uppercase font-semibold">
                    Author / Department
                  </span>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <User className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="font-medium text-foreground">{document.author}</span>
                  </div>
                  {document.metadata?.department && (
                    <div className="flex items-center gap-1.5 mt-1 text-muted-foreground text-[11px]">
                      <Building className="h-3.5 w-3.5" />
                      <span>{document.metadata.department}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>

            {/* Preserving Timestamp Semantics */}
            <div>
              <h3 className="font-bold text-foreground uppercase tracking-wider text-[11px] mb-3 flex items-center gap-1.5">
                <Clock className="h-3.5 w-3.5 text-primary" />
                <span>Chronology & Timestamps</span>
              </h3>

              <div className="space-y-3 bg-card p-3.5 rounded-lg border border-border">
                <div>
                  <span className="text-muted-foreground block text-[10px] uppercase font-semibold">
                    Clinical Event Date (event_at)
                  </span>
                  <span className="font-mono text-foreground font-medium">
                    {formatDateTime(document.event_at)}
                  </span>
                </div>

                <div>
                  <span className="text-muted-foreground block text-[10px] uppercase font-semibold">
                    Documentation Date (authored_at)
                  </span>
                  <span className="font-mono text-foreground font-medium">
                    {formatDateTime(document.authored_at)}
                  </span>
                </div>

                <div className="pt-2 border-t border-border/60 text-[11px] text-muted-foreground">
                  <span className="italic">
                    Note: CASETRACE timeline analysis preserves distinct event vs documentation
                    timestamps to detect documentation delays.
                  </span>
                </div>
              </div>
            </div>

            {/* Source Reference & MIME */}
            <div>
              <h3 className="font-bold text-foreground uppercase tracking-wider text-[11px] mb-2">
                Storage & Asset
              </h3>
              <div className="bg-card p-3 rounded-lg border border-border space-y-1.5 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">MIME:</span>
                  <span className="font-mono text-foreground">{document.mime_type}</span>
                </div>
                {document.storage_path && (
                  <div>
                    <span className="text-muted-foreground block">Reference Path:</span>
                    <span className="font-mono text-[10px] text-muted-foreground break-all">
                      {document.storage_path}
                    </span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-border bg-muted/30 flex items-center justify-between shrink-0">
          <span className="text-xs text-muted-foreground">
            Preserving clinical provenance • Source Ref: <code>{document.id}</code>
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 text-xs font-semibold rounded-lg bg-secondary hover:bg-muted text-foreground transition-colors"
          >
            Close Viewer
          </button>
        </div>
      </div>
    </div>
  );
}
