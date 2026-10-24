"use client";

import React, { useState, useMemo } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Search,
  User,
  Calendar,
  Clock,
  FileText,
  ChevronRight,
  Filter,
  Sparkles,
  ArrowUpDown,
} from "lucide-react";
import { PatientSummary } from "@/types/patient";
import { calculateAge, formatDate, formatDateTime } from "@/lib/utils";

interface PatientTableProps {
  patients: PatientSummary[];
}

export function PatientTable({ patients }: PatientTableProps) {
  const router = useRouter();
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedSex, setSelectedSex] = useState<string>("all");
  const [sortBy, setSortBy] = useState<"id" | "name" | "encounters" | "latest">("id");
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  const filteredPatients = useMemo(() => {
    let list = [...patients];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      list = list.filter(
        (p) =>
          p.display_name.toLowerCase().includes(q) ||
          p.id.toLowerCase().includes(q) ||
          p.synthetic_identifier.toLowerCase().includes(q) ||
          p.case_id.toLowerCase().includes(q)
      );
    }

    if (selectedSex !== "all") {
      list = list.filter((p) => p.sex?.toLowerCase() === selectedSex.toLowerCase());
    }

    list.sort((a, b) => {
      let comparison = 0;
      if (sortBy === "id") {
        comparison = a.id.localeCompare(b.id);
      } else if (sortBy === "name") {
        comparison = a.display_name.localeCompare(b.display_name);
      } else if (sortBy === "encounters") {
        const encA = a.summary?.encounter_count || a.counts?.encounter_count || 0;
        const encB = b.summary?.encounter_count || b.counts?.encounter_count || 0;
        comparison = encA - encB;
      } else if (sortBy === "latest") {
        const timeA = new Date(a.latest_encounter_at || 0).getTime();
        const timeB = new Date(b.latest_encounter_at || 0).getTime();
        comparison = timeA - timeB;
      }

      return sortDirection === "asc" ? comparison : -comparison;
    });

    return list;
  }, [patients, searchQuery, selectedSex, sortBy, sortDirection]);

  const handleSort = (field: "id" | "name" | "encounters" | "latest") => {
    if (sortBy === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortBy(field);
      setSortDirection("asc");
    }
  };

  return (
    <div className="space-y-4">
      {/* Controls Bar: Search & Filters */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 bg-card p-4 rounded-xl border border-border shadow-sm">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by name, patient ID, MRN, or case ID..."
            className="w-full pl-9 pr-4 py-2 text-xs sm:text-sm bg-background border border-input rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/40 focus:border-primary placeholder:text-muted-foreground transition-all"
            aria-label="Search patient records"
          />
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Filter className="h-3.5 w-3.5" />
            <span>Sex:</span>
            <select
              value={selectedSex}
              onChange={(e) => setSelectedSex(e.target.value)}
              className="bg-background border border-input rounded-lg px-2.5 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary"
            >
              <option value="all">All</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
            </select>
          </div>

          <div className="text-xs text-muted-foreground px-2 py-1 rounded bg-secondary font-medium">
            {filteredPatients.length} of {patients.length} records
          </div>
        </div>
      </div>

      {/* Directory Table */}
      <div className="bg-card border border-border rounded-xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs sm:text-sm border-collapse">
            <thead>
              <tr className="border-b border-border bg-muted/40 text-muted-foreground font-semibold text-xs uppercase tracking-wider">
                <th
                  onClick={() => handleSort("id")}
                  className="py-3 px-4 cursor-pointer hover:text-foreground transition-colors"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Patient ID / MRN</span>
                    <ArrowUpDown className="h-3 w-3" />
                  </div>
                </th>
                <th
                  onClick={() => handleSort("name")}
                  className="py-3 px-4 cursor-pointer hover:text-foreground transition-colors"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Patient Name</span>
                    <ArrowUpDown className="h-3 w-3" />
                  </div>
                </th>
                <th className="py-3 px-4">Demographics</th>
                <th
                  onClick={() => handleSort("encounters")}
                  className="py-3 px-4 text-center cursor-pointer hover:text-foreground transition-colors"
                >
                  <div className="flex items-center justify-center gap-1.5">
                    <span>Encounters</span>
                    <ArrowUpDown className="h-3 w-3" />
                  </div>
                </th>
                <th className="py-3 px-4 text-center">Reports</th>
                <th
                  onClick={() => handleSort("latest")}
                  className="py-3 px-4 cursor-pointer hover:text-foreground transition-colors"
                >
                  <div className="flex items-center gap-1.5">
                    <span>Latest Encounter</span>
                    <ArrowUpDown className="h-3 w-3" />
                  </div>
                </th>
                <th className="py-3 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border/60">
              {filteredPatients.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-muted-foreground">
                    <User className="h-8 w-8 mx-auto mb-2 text-muted-foreground/40" />
                    <p className="font-medium text-sm">No synthetic patients found</p>
                    <p className="text-xs text-muted-foreground mt-1">
                      Try adjusting your search criteria or clear the active filter.
                    </p>
                  </td>
                </tr>
              ) : (
                filteredPatients.map((patient) => {
                  const counts = patient.summary || patient.counts || {
                    encounter_count: 0,
                    document_count: 0,
                  };

                  return (
                    <tr
                      key={patient.id}
                      onClick={() => router.push(`/patients/${patient.id}`)}
                      className="hover:bg-muted/40 cursor-pointer transition-colors group"
                    >
                      {/* ID / MRN */}
                      <td className="py-3.5 px-4">
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-foreground text-xs sm:text-sm">
                            {patient.id}
                          </span>
                          <span className="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground font-mono">
                            {patient.case_id}
                          </span>
                        </div>
                        <div className="text-[11px] text-muted-foreground font-mono mt-0.5">
                          {patient.synthetic_identifier}
                        </div>
                      </td>

                      {/* Name */}
                      <td className="py-3.5 px-4 font-semibold text-foreground group-hover:text-primary transition-colors">
                        {patient.display_name}
                      </td>

                      {/* Demographics */}
                      <td className="py-3.5 px-4 text-muted-foreground">
                        <div>
                          {calculateAge(patient.date_of_birth)} •{" "}
                          <span className="capitalize">{patient.sex || "Unknown"}</span>
                        </div>
                        <div className="text-[11px] text-muted-foreground/80">
                          DOB: {formatDate(patient.date_of_birth)}
                        </div>
                      </td>

                      {/* Encounters Count */}
                      <td className="py-3.5 px-4 text-center">
                        <span className="inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-secondary text-foreground">
                          {counts.encounter_count}
                        </span>
                      </td>

                      {/* Documents Count */}
                      <td className="py-3.5 px-4 text-center">
                        <span className="inline-flex items-center justify-center px-2.5 py-0.5 rounded-full text-xs font-semibold bg-secondary text-foreground">
                          {counts.document_count}
                        </span>
                      </td>

                      {/* Latest Encounter */}
                      <td className="py-3.5 px-4 text-muted-foreground text-xs">
                        {patient.latest_encounter_at ? (
                          formatDateTime(patient.latest_encounter_at)
                        ) : (
                          <span className="text-muted-foreground/50">—</span>
                        )}
                      </td>

                      {/* Action */}
                      <td className="py-3.5 px-4 text-right">
                        <Link
                          href={`/patients/${patient.id}`}
                          onClick={(e) => e.stopPropagation()}
                          className="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs font-semibold bg-secondary hover:bg-primary hover:text-primary-foreground text-secondary-foreground transition-all shadow-sm"
                        >
                          <span>Open Chart</span>
                          <ChevronRight className="h-3 w-3" />
                        </Link>
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
