"use client";

import React from "react";
import { Camera, Calendar, Clock, FileText, CheckCircle2, Image as ImageIcon } from "lucide-react";
import { ImagingStudy } from "@/types/patient";
import { formatDate, formatDateTime } from "@/lib/utils";

interface ImagingListProps {
  imaging: ImagingStudy[];
  onSelectDocument?: (documentId: string) => void;
}

export function ImagingList({ imaging, onSelectDocument }: ImagingListProps) {
  return (
    <div className="space-y-4">
      {/* Header bar */}
      <div className="flex items-center justify-between bg-card p-4 rounded-xl border border-border shadow-sm">
        <div>
          <h3 className="text-sm font-bold text-foreground">Diagnostic Imaging Studies</h3>
          <p className="text-xs text-muted-foreground mt-0.5">
            Radiology investigations, scans, and verified reports
          </p>
        </div>
        <div className="text-xs text-muted-foreground px-2.5 py-1 rounded bg-secondary font-medium">
          {imaging.length} studies recorded
        </div>
      </div>

      {/* Grid or Table */}
      {imaging.length === 0 ? (
        <div className="bg-card border border-border rounded-xl p-12 text-center text-muted-foreground">
          <Camera className="h-8 w-8 mx-auto mb-2 text-muted-foreground/40" />
          <p className="font-semibold text-sm">No imaging studies recorded</p>
          <p className="text-xs text-muted-foreground mt-1">
            There are no radiology or diagnostic imaging procedures in this patient record.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {imaging.map((study) => (
            <div
              key={study.id}
              className="bg-card border border-border rounded-xl p-5 shadow-sm space-y-4 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-0.5 rounded text-xs font-bold uppercase tracking-wider bg-purple-500/10 text-purple-700 dark:text-purple-400 border border-purple-500/20">
                      {study.modality.replace(/_/g, " ")}
                    </span>
                    <span className="font-mono text-xs font-semibold text-foreground">
                      {study.id}
                    </span>
                  </div>
                  <span className="px-2 py-0.5 rounded text-[11px] font-medium bg-secondary text-secondary-foreground capitalize">
                    {study.status}
                  </span>
                </div>

                <h4 className="text-base font-bold text-foreground capitalize">
                  {study.body_region} {study.modality.replace(/_/g, " ")}
                </h4>

                <div className="mt-3 space-y-1.5 text-xs text-muted-foreground font-mono">
                  <div>
                    Performed:{" "}
                    <span className="text-foreground">
                      {formatDateTime(study.performed_at)}
                    </span>
                  </div>
                  {study.reported_at && (
                    <div>
                      Reported:{" "}
                      <span className="text-foreground">
                        {formatDateTime(study.reported_at)}
                      </span>
                    </div>
                  )}
                  {study.encounter_id && (
                    <div>Encounter: {study.encounter_id}</div>
                  )}
                </div>
              </div>

              {/* Linked Report Action */}
              <div className="pt-3 border-t border-border/80 flex items-center justify-between">
                {study.report_document_id ? (
                  <div className="flex items-center justify-between w-full">
                    <span className="text-xs text-muted-foreground font-mono">
                      Report: <strong>{study.report_document_id}</strong>
                    </span>
                    {onSelectDocument && (
                      <button
                        onClick={() => onSelectDocument(study.report_document_id!)}
                        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-secondary hover:bg-primary hover:text-primary-foreground text-xs font-semibold text-secondary-foreground transition-all shadow-sm"
                      >
                        <FileText className="h-3.5 w-3.5" />
                        <span>Inspect Radiology Report</span>
                      </button>
                    )}
                  </div>
                ) : (
                  <span className="text-xs text-muted-foreground italic">
                    No linked radiology report document.
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
