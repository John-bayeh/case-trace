import { NextRequest, NextResponse } from "next/server";
import { getImaging } from "@/lib/fixtures/case-fixtures";

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ patientId: string }> }
) {
  try {
    const { patientId } = await context.params;
    const items = getImaging(patientId);

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
    console.error("GET imaging error:", error);
    return NextResponse.json(
      {
        error: { code: "INTERNAL_ERROR", message: "Failed to fetch imaging studies" },
        meta: { request_id: `req-${Date.now()}` },
      },
      { status: 500 }
    );
  }
}
