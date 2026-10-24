
"use client";

import { useState } from "react";
import {
  Activity,
  ArrowDownRight,
  ArrowRight,
  Bell,
  CheckCircle2,
  ChevronDown,
  Clock3,
  FileSearch,
  FolderKanban,
  LayoutDashboard,
  Menu,
  Plus,
  Search,
  Settings,
  ShieldCheck,
  Users,
  X,
} from "lucide-react";

const cases = [
  {
    id: "CT-2026-024",
    title: "Unexpected clinical deterioration",
    patient: "Patient A",
    department: "Internal Medicine",
    status: "Under investigation",
    updated: "Today",
  },
  {
    id: "CT-2026-023",
    title: "Conflicting laboratory findings",
    patient: "Patient B",
    department: "Emergency",
    status: "Pending review",
    updated: "Yesterday",
  },
  {
    id: "CT-2026-022",
    title: "Delayed diagnosis review",
    patient: "Patient C",
    department: "Cardiology",
    status: "Completed",
    updated: "Oct 21",
  },
  {
    id: "CT-2026-021",
    title: "Treatment response discrepancy",
    patient: "Patient D",
    department: "Internal Medicine",
    status: "Under investigation",
    updated: "Oct 20",
  },
];

const navigation = [
  { label: "Overview", icon: LayoutDashboard },
  { label: "Cases", icon: FolderKanban },
  { label: "Patients", icon: Users },
  { label: "Investigations", icon: FileSearch },
  { label: "Reports", icon: Activity },
];

export default function Overview() {
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("All cases");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [showNewCase, setShowNewCase] = useState(false);
  const [selectedNav, setSelectedNav] = useState("Overview");

  const filteredCases = cases.filter((item) => {
    const matchesSearch = [
      item.id,
      item.title,
      item.patient,
      item.department,
    ]
      .join(" ")
      .toLowerCase()
      .includes(search.toLowerCase());

    const matchesStatus =
      status === "All cases" || item.status === status;

    return matchesSearch && matchesStatus;
  });

  return (
    <main className="min-h-screen bg-[#f6f8fb] text-slate-900 md:flex">
      {sidebarOpen && (
        <button
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-40 bg-black/40 md:hidden"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-slate-200 bg-white px-5 py-6 transition-transform md:sticky md:top-0 md:h-screen md:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-blue-700 text-white">
            <ShieldCheck size={25} />
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight">CASETRACE</h1>
            <p className="text-xs text-slate-500">Clinical Intelligence</p>
          </div>
        </div>

        <div className="mt-10">
          <p className="mb-3 px-3 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-400">
            WORKSPACE
          </p>

          <nav className="space-y-1">
            {navigation.map(({ label, icon: Icon }) => (
              <button
                key={label}
                onClick={() => {
                  setSelectedNav(label);
                  setSidebarOpen(false);
                }}
                className={`flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left text-sm transition ${
                  selectedNav === label
                    ? "bg-blue-50 font-semibold text-blue-700"
                    : "text-slate-600 hover:bg-slate-50"
                }`}
              >
                <Icon size={19} />
                {label}
                {label === "Investigations" && (
                  <span className="ml-auto rounded-md bg-slate-100 px-2 py-0.5 text-xs">
                    8
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        <div className="mt-8 border-t border-slate-100 pt-5">
          <p className="mb-3 px-3 text-[11px] font-bold uppercase tracking-[0.16em] text-slate-400">
            PREFERENCES
          </p>
          <button
            onClick={() => setSelectedNav("Settings")}
            className={`flex w-full items-center gap-3 rounded-lg px-3 py-3 text-sm ${
              selectedNav === "Settings"
                ? "bg-blue-50 text-blue-700"
                : "text-slate-600 hover:bg-slate-50"
            }`}
          >
            <Settings size={19} />
            Settings
          </button>
        </div>

        <div className="mt-auto border-t border-slate-100 pt-5">
          <button className="flex w-full items-center gap-3 rounded-xl p-2 text-left hover:bg-slate-50">
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100 text-sm font-bold text-blue-800">
              CT
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold">Clinical Team</p>
              <p className="text-xs text-slate-500">Hospital workspace</p>
            </div>
            <ChevronDown size={16} className="text-slate-400" />
          </button>
        </div>
      </aside>

      <section className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 flex h-[76px] items-center justify-between border-b border-slate-200 bg-white/95 px-5 backdrop-blur md:px-8">
          <div className="flex items-center gap-3">
            <button
              aria-label="Open navigation"
              onClick={() => setSidebarOpen(true)}
              className="rounded-lg p-2 hover:bg-slate-100 md:hidden"
            >
              <Menu size={21} />
            </button>
            <div>
              <p className="text-xs text-slate-500">Hospital workspace</p>
              <p className="mt-1 text-sm font-semibold">Overview</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 rounded-full border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-800 sm:flex">
              <span className="h-2 w-2 rounded-full bg-amber-500" />
              Synthetic demo data
            </div>
            <button
              aria-label="Notifications"
              className="relative rounded-xl border border-slate-200 p-2.5 hover:bg-slate-50"
            >
              <Bell size={19} />
              <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-blue-600" />
            </button>
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-200 text-xs font-bold">
              CT
            </div>
          </div>
        </header>

        <div className="mx-auto max-w-[1500px] p-5 md:p-8">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-sm font-medium text-blue-700">
                CLINICAL OVERVIEW
              </p>
              <h2 className="mt-2 text-3xl font-bold tracking-tight">
                Good day, Clinical Team
              </h2>
              <p className="mt-2 text-sm text-slate-500">
                Review case activity and monitor ongoing investigations.
              </p>
            </div>

            <button
              onClick={() => setShowNewCase(true)}
              className="flex items-center gap-2 rounded-xl bg-blue-700 px-4 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-blue-800"
            >
              <Plus size={18} />
              New case
            </button>
          </div>

          <div className="mt-6 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4">
            <ShieldCheck className="mt-0.5 shrink-0 text-amber-700" size={19} />
            <div>
              <p className="text-sm font-semibold text-amber-900">
                Demonstration environment
              </p>
              <p className="mt-1 text-sm leading-5 text-amber-800">
                All case records and statistics below are fictional sample
                data. No real patient information is displayed.
              </p>
            </div>
          </div>

          <section className="mt-8">
            <div className="mb-4">
              <h3 className="text-lg font-bold">Case overview</h3>
              <p className="mt-1 text-sm text-slate-500">
                A summary of the current investigation workload.
              </p>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {[
                {
                  label: "Total cases",
                  value: "24",
                  detail: "Registered demo cases",
                  icon: FolderKanban,
                  color: "blue",
                },
                {
                  label: "Under investigation",
                  value: "08",
                  detail: "Active demo investigations",
                  icon: Activity,
                  color: "violet",
                },
                {
                  label: "Pending review",
                  value: "05",
                  detail: "Awaiting team review",
                  icon: Clock3,
                  color: "amber",
                },
                {
                  label: "Completed",
                  value: "11",
                  detail: "Completed demo records",
                  icon: CheckCircle2,
                  color: "emerald",
                },
              ].map((stat) => {
                const Icon = stat.icon;
                const iconColors: Record<string, string> = {
                  blue: "bg-blue-50 text-blue-700",
                  violet: "bg-violet-50 text-violet-700",
                  amber: "bg-amber-50 text-amber-700",
                  emerald: "bg-emerald-50 text-emerald-700",
                };

                return (
                  <article
                    key={stat.label}
                    className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <p className="text-sm font-medium text-slate-500">
                        {stat.label}
                      </p>
                      <span
                        className={`rounded-xl p-2.5 ${iconColors[stat.color]}`}
                      >
                        <Icon size={20} />
                      </span>
                    </div>
                    <p className="mt-4 text-3xl font-bold tracking-tight">
                      {stat.value}
                    </p>
                    <p className="mt-2 text-xs text-slate-500">
                      {stat.detail}
                    </p>
                  </article>
                );
              })}
            </div>
          </section>

          <section className="mt-8 rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-100 p-5 md:p-6">
              <div>
                <h3 className="text-lg font-bold">Recent investigations</h3>
                <p className="mt-1 text-sm text-slate-500">
                  Search and filter the fictional records in this demo.
                </p>
              </div>
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <Activity size={17} />
                <span>{filteredCases.length} records</span>
              </div>
            </div>

            <div className="flex flex-col gap-3 p-5 md:flex-row md:p-6">
              <div className="relative flex-1">
                <Search
                  size={18}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                />
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder="Search cases, departments, or case IDs..."
                  className="w-full rounded-xl border border-slate-200 py-3 pl-10 pr-4 text-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
                />
              </div>
              <select
                value={status}
                onChange={(event) => setStatus(event.target.value)}
                className="rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-blue-500"
              >
                <option>All cases</option>
                <option>Under investigation</option>
                <option>Pending review</option>
                <option>Completed</option>
              </select>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full min-w-[760px] text-left text-sm">
                <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-6 py-4 font-semibold">Case</th>
                    <th className="px-6 py-4 font-semibold">Patient</th>
                    <th className="px-6 py-4 font-semibold">Department</th>
                    <th className="px-6 py-4 font-semibold">Status</th>
                    <th className="px-6 py-4 font-semibold">Updated</th>
                    <th className="px-6 py-4 font-semibold">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredCases.map((item) => (
                    <tr key={item.id} className="transition hover:bg-slate-50">
                      <td className="px-6 py-4">
                        <p className="font-semibold text-slate-800">
                          {item.id}
                        </p>
                        <p className="mt-1 text-xs text-slate-500">
                          {item.title}
                        </p>
                      </td>
                      <td className="px-6 py-4 text-slate-600">
                        {item.patient}
                      </td>
                      <td className="px-6 py-4 text-slate-600">
                        {item.department}
                      </td>
                      <td className="px-6 py-4">
                        <span
                          className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${
                            item.status === "Completed"
                              ? "bg-emerald-50 text-emerald-700"
                              : item.status === "Pending review"
                                ? "bg-amber-50 text-amber-700"
                                : "bg-blue-50 text-blue-700"
                          }`}
                        >
                          {item.status}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-500">
                        {item.updated}
                      </td>
                      <td className="px-6 py-4">
                        <button
                          onClick={() =>
                            alert(
                              `${item.id}: demo record only. Case details are not connected yet.`
                            )
                          }
                          aria-label={`View ${item.id}`}
                          className="rounded-lg p-2 text-slate-500 hover:bg-blue-50 hover:text-blue-700"
                        >
                          <ArrowRight size={18} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              {filteredCases.length === 0 && (
                <div className="p-10 text-center">
                  <Search className="mx-auto text-slate-400" size={28} />
                  <p className="mt-3 font-semibold">No matching cases</p>
                  <p className="mt-1 text-sm text-slate-500">
                    Try another search or status filter.
                  </p>
                </div>
              )}
            </div>

            <div className="border-t border-slate-100 px-6 py-4 text-xs text-slate-500">
              Sample records for frontend demonstration only.
            </div>
          </section>

          <footer className="flex flex-wrap items-center justify-between gap-3 py-6 text-xs text-slate-400">
            <p>CASETRACE · Clinical investigation workspace</p>
            <p>Frontend demonstration · Synthetic data only</p>
          </footer>
        </div>
      </section>

      {showNewCase && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/40 p-4">
          <div className="w-full max-w-md rounded-2xl bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold">New case</h3>
              <button
                aria-label="Close dialog"
                onClick={() => setShowNewCase(false)}
                className="rounded-lg p-2 hover:bg-slate-100"
              >
                <X size={20} />
              </button>
            </div>
            <p className="mt-3 text-sm leading-6 text-slate-600">
              Case creation will be connected to your team’s backend later.
              This demo does not save or submit patient information.
            </p>
            <button
              onClick={() => setShowNewCase(false)}
              className="mt-6 w-full rounded-xl bg-blue-700 px-4 py-3 text-sm font-semibold text-white hover:bg-blue-800"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </main>
  );
}
