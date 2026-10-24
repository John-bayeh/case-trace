"use client";

import React, { useState, useMemo } from "react";
import {
  FlaskConical,
  Search,
  Filter,
  AlertCircle,
  Clock,
  FileText,
  ArrowUpDown,
  CheckCircle2,
} from "lucide-react";
import { Observation } from "@/types/patient";
import { formatDate, formatDateTime } from "@/lib/utils";

interface LabsTableProps {
  observations: Observation[];
  onSelectDocument?: (documentId: string) => void;
}

export function LabsTable({ observations, onSelectDocument }: LabsTableProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [onlyAbnormal, setOnlyAbnormal] = useState(false);
  const [sortBy, setSortBy] = useState<"date" | "test" | "status">("date");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("desc");

  // Determine abnormal state strictly from source reference ranges
  const checkAbnormal = (obs: Observation): "high" | "low" | "normal" | null => {
    if (obs.value_numeric === null || obs.value_numeric === undefined) return null;
    const low = obs.reference_range_low ?? obs.reference_low;
    const high = obs.reference_range_high ?? obs.reference_high;

    if (low !== null && low !== undefined && obs.value_numeric < low) {
      return "low";
    }
    if (high !== null && high !== undefined && obs.value_numeric > high) {
      return "high";
    }
    if (low !== null || high !== null) {
      return "normal";
    }
    return null;
  };

  const filtered = useMemo(() => {
    let list = [...observations];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(
        (o) =>
          o.test_name.toLowerCase().includes(q) ||
          (o.test_code && o.test_code.toLowerCase().includes(q)) ||
          o.id.toLowerCase().includes(q) ||
          (o.encounter_id && o.encounter_id.toLowerCase().includes(q))
      );
    }

    if (onlyAbnormal) {
      list = list.filter((o) => {
        const flag = checkAbnormal(o);
        return flag === "high" || flag === "low";
      });
    }

    list.sort((a, b) => {
      let comparison = 0;
      if (sortBy === "date") {
        const timeA = new Date(a.specimen_collected_at || a.reported_at || 0).getTime();
        const timeB = new Date(b.specimen_collected_at || b.reported_at || 0).getTime();
        comparison = timeA - timeB;
      } else if (sortBy === "test") {
        comparison = a.test_name.localeCompare(b.test_name);
      } else if (sortBy === "status") {
        comparison = a.status.localeCompare(b.status);
      }
      return sortDirection === "asc" ? comparison : -comparison;
    });

    return list;
  }, [observations, searchQuery, onlyAbnormal, sortBy, sortDirection]);

  const handleSort = (field: "date" | "test" | "status") => {
    if (sortBy === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortBy(field);
      setSortDirection("desc");
    }
  };

  return (
    <div className="space-y-4">
      {/* Search and Filters Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-card p-4 rounded-xl border border-border shadow-sm">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by test name, code (e.g. CRP, HGB), or ID..."
            className="w-full pl-9 pr-4 py-2 text-xs sm:text-sm bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary placeholder:text-muted-foreground transition-all"
            aria-label="Search laboratory observations"
          />
        </div>

        <div className="flex items-center gap-3">
          <label className="flex items-center gap-2 text-xs text-foreground cursor-pointer select-none">
            <input
              type="checkbox"
              checked={onlyAbnormal}
              onChange={(e) => setOnlyAbnormal(e.target.checked)}
              className="h-4 w-4 rounded border-input text-primary focus:ring-primary/40"
            />
            <span className="font-semibold text-rose-600 dark:text-rose-400">
              Show Abnormal Only
            </span>
          </label>

          <div className="text-xs text-muted-foreground px-2.5 py-1 rounded bg-secondary font-medium">
            {filtered.length} of {observations.length} results
          </div>
        </div>
      </div>

      {/* Observations Table */}
      <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs sm:text-sm border-collapse">
            <thead>
              <tr className="border-b border-border bg-muted/40 text-muted-foreground font-semibold text-xs uppercase tracking-wider">
                <th
                  onClick={() => handleSort("test")}
                  className="py-3 px-4 cursor-pointer hover:text-foreground transition-colors"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Test Name / Code</span>
                    <ArrowUpDown className="h-3 w-3" />
                  </div>
                </th>
                <th className="py-3 px-4">Result Value</th>
                <th className="py-3 px-4">Reference Range</th>
                <th className="py-3 px-4 text-center">Flag</th>
                <th
                  onClick={() => handleSort("date")}
                  className="py-3 px-4 cursor-pointer hover:text-foreground transition-colors"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Specimen / Reported At</span>
                    <ArrowUpDown className="h-3 w-3" />
                  </div>
                </th>
                <th className="py-3 px-4">Encounter / Source</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-12 text-center text-muted-foreground">
                    <FlaskConical className="h-8 w-8 mx-auto mb-2 text-muted-foreground/40" />
                    <p className="font-medium text-sm">No laboratory observations found</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      {onlyAbnormal
                        ? "No abnormal values detected for this patient in the filtered subset."
                        : "Try adjusting your search criteria."}
                    </p>
                  </td>
                </tr>
              ) : (
                filtered.map((obs) => {
                  const flag = checkAbnormal(obs);
                  const low = obs.reference_range_low ?? obs.reference_low;
                  const high = obs.reference_range_high ?? obs.reference_high;

                  return (
                    <tr key={obs.id} className="hover:bg-muted/40 transition-colors">
                      {/* Test Name & Code */}
                      <td className="py-3.5 px-4">
                        <div className="font-semibold text-foreground">
                          {obs.test_name}
                        </div>
                        <div className="flex items-center gap-2 mt-0.5">
                          {obs.test_code && (
                            <span className="font-mono text-xs font-semibold px-1.5 py-0.5 rounded bg-secondary text-secondary-foreground">
                              {obs.test_code}
                            </span>
                          )}
                          <span className="font-mono text-[11px] text-muted-foreground">
                            {obs.id}
                          </span>
                        </div>
                      </td>

                      {/* Result Value */}
                      <td className="py-3.5 px-4 font-mono">
                        <span
                          className={`text-sm font-bold ${
                            flag === "high" || flag === "low"
                              ? "text-rose-600 dark:text-rose-400"
                              : "text-foreground"
                          }`}
                        >
                          {obs.value_numeric !== null && obs.value_numeric !== undefined
                            ? obs.value_numeric
                            : obs.value_text || "—"}
                        </span>
                        {obs.unit && (
                          <span className="text-xs text-muted-foreground ml-1.5">
                            {obs.unit}
                          </span>
                        )}
                      </td>

                      {/* Reference Range */}
                      <td className="py-3.5 px-4 text-xs font-mono text-muted-foreground">
                        {low !== null && high !== null && low !== undefined && high !== undefined ? (
                          <span>
                            {low} – {high} {obs.unit || ""}
                          </span>
                        ) : low !== null && low !== undefined ? (
                          <span>&gt; {low}</span>
                        ) : high !== null && high !== undefined ? (
                          <span>&lt; {high}</span>
                        ) : (
                          <span>Not specified</span>
                        )}
                      </td>

                      {/* Flag */}
                      <td className="py-3.5 px-4 text-center">
                        {flag === "high" ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/30">
                            HIGH
                          </span>
                        ) : flag === "low" ? (
                          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/10 text-amber-600 dark:text-amber-400 border border-amber-500/30">
                            LOW
                          </span>
                        ) : flag === "normal" ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                            Normal
                          </span>
                        ) : (
                          <span className="text-muted-foreground text-xs">—</span>
                        )}
                      </td>

                      {/* Dates */}
                      <td className="py-3.5 px-4 text-xs text-muted-foreground font-mono">
                        <div>
                          Collected:{" "}
                          <span className="text-foreground">
                            {formatDateTime(obs.specimen_collected_at)}
                          </span>
                        </div>
                        {obs.reported_at && (
                          <div className="text-[11px] text-muted-foreground mt-0.5">
                            Reported: {formatDateTime(obs.reported_at)}
                          </div>
                        )}
                      </td>

                      {/* Encounter & Source */}
                      <td className="py-3.5 px-4 text-xs">
                        {obs.encounter_id && (
                          <div className="font-mono text-muted-foreground">
                            Enc: {obs.encounter_id}
                          </div>
                        )}
                        {obs.source_document_id && (
                          <div className="mt-1">
                            {onSelectDocument ? (
                              <button
                                onClick={() => onSelectDocument(obs.source_document_id!)}
                                className="inline-flex items-center gap-1 font-mono text-[11px] text-primary hover:underline"
                              >
                                <FileText className="h-3 w-3" />
                                <span>{obs.source_document_id}</span>
                              </button>
                            ) : (
                              <span className="font-mono text-[11px] text-muted-foreground">
                                Ref: {obs.source_document_id}
                              </span>
                            )}
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
