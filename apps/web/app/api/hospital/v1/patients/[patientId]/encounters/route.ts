import { NextRequest, NextResponse } from "next/server";
import { getEncounters } from "@/lib/fixtures/case-fixtures";

export async function GET(
  request: NextRequest,
  context: { params: Promise<{ patientId: string }> }
) {
  try {
    const { patientId } = await context.params;
    const searchParams = request.nextUrl.searchParams;
    const department = searchParams.get("department") || undefined;
    const encounter_type = searchParams.get("encounter_type") || undefined;

    const items = getEncounters(patientId, { department, encounter_type });

    return NextResponse.json({
      data: items,
      items: items,
      total: items.length,
      pagination: {
        limit: items.length,
        offset: 0,
        total: items.length,
        has_more: false,
      },
      meta: { request_id: `req-${Date.now()}` },
    });
  } catch (error) {
    console.error("GET encounters error:", error);
    return NextResponse.json(
      {
        error: { code: "INTERNAL_ERROR", message: "Failed to fetch encounters" },
        meta: { request_id: `req-${Date.now()}` },
      },
      { status: 500 }
    );
  }
}
