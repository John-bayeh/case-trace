import { NextRequest, NextResponse } from "next/server";
import { getMedications } from "@/lib/fixtures/case-fixtures";

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ patientId: string }> }
) {
  try {
    const { patientId } = await context.params;
    const items = getMedications(patientId);

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
    console.error("GET medications error:", error);
    return NextResponse.json(
      {
        error: { code: "INTERNAL_ERROR", message: "Failed to fetch medications" },
        meta: { request_id: `req-${Date.now()}` },
      },
      { status: 500 }
    );
  }
}
