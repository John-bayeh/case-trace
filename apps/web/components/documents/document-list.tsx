"use client";

import React, { useState, useMemo } from "react";
import {
  FileText,
  Search,
  Filter,
  Calendar,
  Clock,
  User,
  Eye,
  ExternalLink,
} from "lucide-react";
import { ClinicalDocument } from "@/types/patient";
import { formatDate, formatDateTime } from "@/lib/utils";
import { DocumentViewer } from "./document-viewer";

interface DocumentListProps {
  documents: ClinicalDocument[];
}

export function DocumentList({ documents }: DocumentListProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedType, setSelectedType] = useState<string>("all");
  const [selectedDoc, setSelectedDoc] = useState<ClinicalDocument | null>(null);

  // Extract distinct document types for filter
  const documentTypes = useMemo(() => {
    const types = new Set<string>();
    documents.forEach((d) => {
      if (d.document_type) types.add(d.document_type);
    });
    return Array.from(types).sort();
  }, [documents]);

  const filteredDocs = useMemo(() => {
    let list = [...documents];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(
        (d) =>
          d.title.toLowerCase().includes(q) ||
          d.id.toLowerCase().includes(q) ||
          d.author.toLowerCase().includes(q) ||
          (d.encounter_id && d.encounter_id.toLowerCase().includes(q)) ||
          (d.text_content && d.text_content.toLowerCase().includes(q))
      );
    }

    if (selectedType !== "all") {
      list = list.filter((d) => d.document_type === selectedType);
    }

    // Default sort descending by event_at
    return list.sort(
      (a, b) => new Date(b.event_at).getTime() - new Date(a.event_at).getTime()
    );
  }, [documents, searchQuery, selectedType]);

  const getTypeBadgeClass = (type: string) => {
    switch (type.toLowerCase()) {
      case "progress_note":
      case "clinical_note":
        return "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/20";
      case "radiology_report":
        return "bg-purple-500/10 text-purple-700 dark:text-purple-400 border-purple-500/20";
      case "discharge_summary":
        return "bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/20";
      case "consultation":
      case "specialist_note":
        return "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/20";
      case "laboratory_report":
      case "lab_report":
        return "bg-cyan-500/10 text-cyan-700 dark:text-cyan-400 border-cyan-500/20";
      default:
        return "bg-secondary text-secondary-foreground border-border";
    }
  };

  return (
    <>
      <div className="space-y-4">
        {/* Search & Filter Header */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-card p-4 rounded-xl border border-border shadow-sm">
          <div className="relative flex-1 max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search reports by title, author, ID, or clinical text..."
              className="w-full pl-9 pr-4 py-2 text-xs sm:text-sm bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary placeholder:text-muted-foreground transition-all"
              aria-label="Search clinical documents"
            />
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Filter className="h-3.5 w-3.5" />
              <span>Type:</span>
              <select
                value={selectedType}
                onChange={(e) => setSelectedType(e.target.value)}
                className="bg-background border border-input rounded-lg px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary capitalize"
              >
                <option value="all">All Document Types ({documents.length})</option>
                {documentTypes.map((t) => (
                  <option key={t} value={t}>
                    {t.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </div>

            <div className="text-xs text-muted-foreground px-2 py-1 rounded bg-secondary font-medium">
              {filteredDocs.length} of {documents.length} records
            </div>
          </div>
        </div>

        {/* Documents Table */}
        <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs sm:text-sm border-collapse">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-muted-foreground font-semibold text-xs uppercase tracking-wider">
                  <th className="py-3 px-4">Document Identifier</th>
                  <th className="py-3 px-4">Title & Type</th>
                  <th className="py-3 px-4">Author / Dept</th>
                  <th className="py-3 px-4">Event Date (event_at)</th>
                  <th className="py-3 px-4">Documentation (authored_at)</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {filteredDocs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-12 text-center text-muted-foreground">
                      <FileText className="h-8 w-8 mx-auto mb-2 text-muted-foreground/40" />
                      <p className="font-medium text-sm">No clinical documents found</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Try modifying search or clearing the document type filter.
                      </p>
                    </td>
                  </tr>
                ) : (
                  filteredDocs.map((doc) => (
                    <tr
                      key={doc.id}
                      onClick={() => setSelectedDoc(doc)}
                      className="hover:bg-muted/40 cursor-pointer transition-colors group"
                    >
                      {/* ID & Encounter */}
                      <td className="py-3.5 px-4">
                        <div className="font-mono font-bold text-foreground text-xs sm:text-sm">
                          {doc.id}
                        </div>
                        {doc.encounter_id && (
                          <div className="text-[11px] font-mono text-muted-foreground mt-0.5">
                            {doc.encounter_id}
                          </div>
                        )}
                      </td>

                      {/* Title & Type */}
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-foreground group-hover:text-primary transition-colors">
                          {doc.title}
                        </div>
                        <div className="mt-1">
                          <span
                            className={`inline-block px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider rounded border ${getTypeBadgeClass(
                              doc.document_type
                            )}`}
                          >
                            {doc.document_type.replace(/_/g, " ")}
                          </span>
                        </div>
                      </td>

                      {/* Author */}
                      <td className="py-3.5 px-4 text-muted-foreground">
                        <div className="flex items-center gap-1.5 text-foreground font-medium">
                          <User className="h-3.5 w-3.5 text-muted-foreground" />
                          <span>{doc.author}</span>
                        </div>
                        {doc.metadata?.department && (
                          <div className="text-[11px] text-muted-foreground mt-0.5">
                            {doc.metadata.department}
                          </div>
                        )}
                      </td>

                      {/* Event Date */}
                      <td className="py-3.5 px-4 font-mono text-xs text-muted-foreground">
                        {formatDateTime(doc.event_at)}
                      </td>

                      {/* Authored Date */}
                      <td className="py-3.5 px-4 font-mono text-xs text-muted-foreground">
                        {formatDateTime(doc.authored_at)}
                      </td>

                      {/* Action */}
                      <td className="py-3.5 px-4 text-right">
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedDoc(doc);
                          }}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-secondary hover:bg-primary hover:text-primary-foreground text-secondary-foreground transition-all shadow-sm"
                        >
                          <Eye className="h-3.5 w-3.5" />
                          <span>Inspect</span>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Inspector Modal */}
      <DocumentViewer
        document={selectedDoc}
        onClose={() => setSelectedDoc(null)}
      />
    </>
  );
}
