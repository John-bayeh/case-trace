import { NextRequest, NextResponse } from "next/server";
import { getDocumentById } from "@/lib/fixtures/case-fixtures";

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ documentId: string }> }
) {
  try {
    const { documentId } = await context.params;
    const document = getDocumentById(documentId);

    if (!document) {
      return NextResponse.json(
        {
          error: {
            code: "DOCUMENT_NOT_FOUND",
            message: `Document ${documentId} was not found.`,
          },
          meta: { request_id: `req-${Date.now()}` },
        },
        { status: 404 }
      );
    }

    return NextResponse.json({
      ...document,
      data: document,
    });
  } catch (error) {
    console.error("GET /api/documents/[documentId] error:", error);
    return NextResponse.json(
      {
        error: { code: "INTERNAL_ERROR", message: "Failed to fetch document" },
      },
      { status: 500 }
    );
  }
}
