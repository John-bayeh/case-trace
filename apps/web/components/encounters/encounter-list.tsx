"use client";

import React, { useState, useMemo } from "react";
import {
  Clock,
  Building,
  User,
  Calendar,
  Filter,
  ChevronDown,
  ChevronRight,
  FileText,
  FlaskConical,
  Activity,
} from "lucide-react";
import { Encounter } from "@/types/patient";
import { formatDate, formatDateTime } from "@/lib/utils";

interface EncounterListProps {
  encounters: Encounter[];
  onSelectDocument?: (documentId: string) => void;
}

export function EncounterList({ encounters, onSelectDocument }: EncounterListProps) {
  const [selectedDept, setSelectedDept] = useState<string>("all");
  const [selectedType, setSelectedType] = useState<string>("all");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const departments = useMemo(() => {
    const set = new Set<string>();
    encounters.forEach((e) => {
      if (e.department) set.add(e.department);
    });
    return Array.from(set).sort();
  }, [encounters]);

  const encounterTypes = useMemo(() => {
    const set = new Set<string>();
    encounters.forEach((e) => {
      if (e.encounter_type) set.add(e.encounter_type);
    });
    return Array.from(set).sort();
  }, [encounters]);

  const filtered = useMemo(() => {
    let list = [...encounters];

    if (selectedDept !== "all") {
      list = list.filter((e) => e.department === selectedDept);
    }

    if (selectedType !== "all") {
      list = list.filter((e) => e.encounter_type === selectedType);
    }

    // Chronological order descending by started_at
    return list.sort(
      (a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime()
    );
  }, [encounters, selectedDept, selectedType]);

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div className="space-y-4">
      {/* Filters Bar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-card p-4 rounded-xl border border-border shadow-sm">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Filter className="h-3.5 w-3.5" />
            <span>Department:</span>
            <select
              value={selectedDept}
              onChange={(e) => setSelectedDept(e.target.value)}
              className="bg-background border border-input rounded-lg px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="all">All Departments ({departments.length})</option>
              {departments.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <span>Type:</span>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="bg-background border border-input rounded-lg px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary capitalize"
            >
              <option value="all">All Encounter Types</option>
              {encounterTypes.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="text-xs text-muted-foreground px-2 py-1 rounded bg-secondary font-medium self-end sm:self-auto">
          {filtered.length} of {encounters.length} encounters
        </div>
      </div>

      {/* Encounters List */}
      <div className="space-y-3">
        {filtered.length === 0 ? (
          <div className="bg-card border border-border rounded-xl p-12 text-center text-muted-foreground">
            <Clock className="h-8 w-8 mx-auto mb-2 text-muted-foreground/40" />
            <p className="font-semibold text-sm">No encounters match filters</p>
            <p className="text-xs text-muted-foreground mt-1">
              Reset department or encounter type filter to display records.
            </p>
          </div>
        ) : (
          filtered.map((enc) => {
            const isExpanded = expandedId === enc.id;

            return (
              <div
                key={enc.id}
                className="bg-card border border-border rounded-xl shadow-sm overflow-hidden transition-all"
              >
                {/* Header row */}
                <div
                  onClick={() => toggleExpand(enc.id)}
                  className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4 cursor-pointer hover:bg-muted/30 transition-colors"
                >
                  <div className="flex items-start sm:items-center gap-3">
                    <button
                      type="button"
                      className="p-1 rounded text-muted-foreground hover:text-foreground shrink-0 mt-0.5 sm:mt-0"
                      aria-label="Toggle details"
                    >
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                    </button>

                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="font-mono font-bold text-foreground text-sm">
                          {enc.id}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[11px] font-semibold uppercase tracking-wider bg-primary/10 text-primary">
                          {enc.encounter_type}
                        </span>
                        <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-secondary text-secondary-foreground">
                          {enc.status}
                        </span>
                      </div>

                      <div className="flex items-center gap-4 mt-1.5 text-xs text-muted-foreground flex-wrap">
                        <div className="flex items-center gap-1 text-foreground font-medium">
                          <Building className="h-3.5 w-3.5 text-muted-foreground" />
                          <span>{enc.department}</span>
                        </div>
                        <span className="text-border">•</span>
                        <div className="flex items-center gap-1">
                          <User className="h-3.5 w-3.5 text-muted-foreground" />
                          <span>{enc.provider_name}</span>
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="sm:text-right shrink-0 pl-7 sm:pl-0">
                    <div className="text-xs font-mono font-medium text-foreground">
                      Started: {formatDateTime(enc.started_at)}
                    </div>
                    {enc.ended_at && (
                      <div className="text-[11px] font-mono text-muted-foreground mt-0.5">
                        Ended: {formatDateTime(enc.ended_at)}
                      </div>
                    )}
                  </div>
                </div>

                {/* Expanded Details Section */}
                {isExpanded && (
                  <div className="px-6 pb-5 pt-2 border-t border-border/80 bg-muted/20 text-xs space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {/* Clinical Events in this encounter */}
                      <div className="bg-card p-3.5 rounded-lg border border-border">
                        <h4 className="font-bold uppercase tracking-wider text-[11px] text-foreground mb-2 flex items-center gap-1.5">
                          <Activity className="h-3.5 w-3.5 text-primary" />
                          <span>Clinical Events</span>
                        </h4>
                        {enc.clinical_events && enc.clinical_events.length > 0 ? (
                          <div className="space-y-2">
                            {enc.clinical_events.map((ev) => (
                              <div
                                key={ev.id}
                                className="p-2 rounded bg-muted/40 border border-border/60 text-xs"
                              >
                                <div className="flex justify-between items-center text-[11px] mb-1">
                                  <span className="font-mono font-semibold text-primary">
                                    {ev.id}
                                  </span>
                                  <span className="text-muted-foreground font-mono">
                                    {formatDateTime(ev.occurred_at || ev.documented_at)}
                                  </span>
                                </div>
                                <p className="text-foreground">{ev.description}</p>
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-muted-foreground italic text-xs">
                            No discrete clinical events recorded for this encounter.
                          </p>
                        )}
                      </div>

                      {/* Associated Documents */}
                      <div className="bg-card p-3.5 rounded-lg border border-border">
                        <h4 className="font-bold uppercase tracking-wider text-[11px] text-foreground mb-2 flex items-center gap-1.5">
                          <FileText className="h-3.5 w-3.5 text-primary" />
                          <span>Generated Reports & Notes</span>
                        </h4>
                        {enc.documents && enc.documents.length > 0 ? (
                          <div className="space-y-2">
                            {enc.documents.map((d) => (
                              <div
                                key={d.id}
                                className="p-2 rounded bg-muted/40 border border-border/60 flex items-center justify-between gap-2"
                              >
                                <div>
                                  <div className="font-semibold text-foreground">
                                    {d.title}
                                  </div>
                                  <div className="text-[11px] font-mono text-muted-foreground">
                                    {d.id} • {d.author}
                                  </div>
                                </div>
                                {onSelectDocument && (
                                  <button
                                    onClick={() => onSelectDocument(d.id)}
                                    className="px-2.5 py-1 rounded bg-secondary hover:bg-primary hover:text-primary-foreground text-[11px] font-medium transition-colors shrink-0"
                                  >
                                    View
                                  </button>
                                )}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <p className="text-muted-foreground italic text-xs">
                            Documents can be accessed in the Documents & Reports tab.
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
