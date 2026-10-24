"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Clock,
  FlaskConical,
  FileText,
  Pill,
  Camera,
} from "lucide-react";

interface ChartNavProps {
  patientId: string;
}

export function ChartNav({ patientId }: ChartNavProps) {
  const pathname = usePathname();

  const baseUrl = `/patients/${patientId}`;

  const tabs = [
    {
      label: "Overview",
      href: baseUrl,
      exact: true,
      icon: LayoutDashboard,
    },
    {
      label: "Encounters",
      href: `${baseUrl}/encounters`,
      exact: false,
      icon: Clock,
    },
    {
      label: "Labs & Observations",
      href: `${baseUrl}/labs`,
      exact: false,
      icon: FlaskConical,
    },
    {
      label: "Documents & Reports",
      href: `${baseUrl}/documents`,
      exact: false,
      icon: FileText,
    },
    {
      label: "Medications",
      href: `${baseUrl}/medications`,
      exact: false,
      icon: Pill,
    },
    {
      label: "Imaging",
      href: `${baseUrl}/imaging`,
      exact: false,
      icon: Camera,
    },
  ];

  return (
    <div className="border-b border-border mb-6">
      <nav className="flex space-x-1 sm:space-x-2 overflow-x-auto pb-px" aria-label="Chart sections">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = tab.exact
            ? pathname === tab.href
            : pathname.startsWith(tab.href);

          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`inline-flex items-center gap-2 px-3.5 py-2.5 text-xs sm:text-sm font-medium border-b-2 whitespace-nowrap transition-colors ${
                isActive
                  ? "border-primary text-foreground font-semibold"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:border-muted-foreground/30"
              }`}
              aria-current={isActive ? "page" : undefined}
            >
              <Icon className={`h-4 w-4 ${isActive ? "text-primary" : "text-muted-foreground"}`} />
              <span>{tab.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
