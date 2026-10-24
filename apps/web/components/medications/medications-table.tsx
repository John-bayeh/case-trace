"use client";

import React, { useState, useMemo } from "react";
import { Pill, Filter, Calendar, User, FileText, CheckCircle2 } from "lucide-react";
import { Medication } from "@/types/patient";
import { formatDate, formatDateTime } from "@/lib/utils";

interface MedicationsTableProps {
  medications: Medication[];
  onSelectDocument?: (documentId: string) => void;
}

export function MedicationsTable({
  medications,
  onSelectDocument,
}: MedicationsTableProps) {
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const filtered = useMemo(() => {
    if (statusFilter === "all") return medications;
    return medications.filter(
      (m) => m.status.toLowerCase() === statusFilter.toLowerCase()
    );
  }, [medications, statusFilter]);

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "active":
        return "bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/30";
      case "completed":
        return "bg-blue-500/10 text-blue-700 dark:text-blue-400 border-blue-500/30";
      case "discontinued":
      case "cancelled":
        return "bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/30";
      default:
        return "bg-secondary text-secondary-foreground border-border";
    }
  };

  return (
    <div className="space-y-4">
      {/* Filters Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-card p-4 rounded-xl border border-border shadow-sm">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Filter className="h-3.5 w-3.5" />
          <span>Status:</span>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-background border border-input rounded-lg px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary capitalize"
          >
            <option value="all">All Medications ({medications.length})</option>
            <option value="active">Active Only</option>
            <option value="completed">Completed Only</option>
            <option value="discontinued">Discontinued Only</option>
          </select>
        </div>

        <div className="text-xs text-muted-foreground px-2 py-1 rounded bg-secondary font-medium">
          {filtered.length} of {medications.length} prescriptions
        </div>
      </div>

      {/* Table */}
      <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs sm:text-sm border-collapse">
            <thead>
              <tr className="border-b border-border bg-muted/40 text-muted-foreground font-semibold text-xs uppercase tracking-wider">
                <th className="py-3 px-4">Medication & Generic</th>
                <th className="py-3 px-4">Dose & Route</th>
                <th className="py-3 px-4">Frequency</th>
                <th className="py-3 px-4 text-center">Status</th>
                <th className="py-3 px-4">Dates (Start – End)</th>
                <th className="py-3 px-4">Prescriber / Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-muted-foreground">
                    <Pill className="h-8 w-8 mx-auto mb-2 text-muted-foreground/40" />
                    <p className="font-medium text-sm">No medication records found</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      No prescriptions matching the selected filter.
                    </p>
                  </td>
                </tr>
              ) : (
                filtered.map((med) => (
                  <tr key={med.id} className="hover:bg-muted/40 transition-colors">
                    {/* Name */}
                    <td className="py-3.5 px-4">
                      <div className="font-semibold text-foreground">
                        {med.medication_name}
                      </div>
                      <div className="text-[11px] font-mono text-muted-foreground">
                        {med.generic_name} • {med.id}
                      </div>
                    </td>

                    {/* Dose & Route */}
                    <td className="py-3.5 px-4 font-medium text-foreground">
                      <div>
                        {med.dose} {med.dose_unit || ""}
                      </div>
                      <div className="text-[11px] text-muted-foreground capitalize">
                        Route: {med.route || "oral"}
                      </div>
                    </td>

                    {/* Frequency */}
                    <td className="py-3.5 px-4 text-muted-foreground capitalize">
                      {med.frequency ? med.frequency.replace(/_/g, " ") : "As directed"}
                    </td>

                    {/* Status */}
                    <td className="py-3.5 px-4 text-center">
                      <span
                        className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-semibold capitalize border ${getStatusBadge(
                          med.status
                        )}`}
                      >
                        {med.status}
                      </span>
                    </td>

                    {/* Dates */}
                    <td className="py-3.5 px-4 text-xs font-mono text-muted-foreground">
                      <div>Start: {med.start_at || "—"}</div>
                      <div>End: {med.end_at || "Ongoing"}</div>
                    </td>

                    {/* Prescriber & Source */}
                    <td className="py-3.5 px-4 text-xs">
                      {med.prescriber && (
                        <div className="text-foreground font-medium flex items-center gap-1">
                          <User className="h-3 w-3 text-muted-foreground" />
                          <span>{med.prescriber}</span>
                        </div>
                      )}
                      {med.source_document_id && (
                        <div className="mt-1">
                          {onSelectDocument ? (
                            <button
                              onClick={() => onSelectDocument(med.source_document_id!)}
                              className="inline-flex items-center gap-1 font-mono text-[11px] text-primary hover:underline"
                            >
                              <FileText className="h-3 w-3" />
                              <span>{med.source_document_id}</span>
                            </button>
                          ) : (
                            <span className="font-mono text-[11px] text-muted-foreground">
                              Ref: {med.source_document_id}
                            </span>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
