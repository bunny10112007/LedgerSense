import json

from ledgersense.domain.models import ExtractedReceipt

PROMPT_VERSION = "v1"

EXTRACTION_SYSTEM_PROMPT_TEMPLATE = """You are a document reader for Indian financial documents. Output ONE JSON object matching the schema below and nothing else. Rules:
1. Copy values exactly as printed. If a field is not legible or not present, use null.
2. Never infer, correct or compute a GSTIN. Copy the 15 characters verbatim.
3. Dates as YYYY-MM-DD. If the year is ambiguous, set the field null and lower field_confidence.invoice_date.
4. Amounts as strings with two decimals, no currency symbols or thousand separators.
5. Do not calculate taxes or totals. Report only what the document prints.
6. field_confidence: 0.0-1.0 for vendor_gstin, invoice_date, total.
7. doc_type is one of: gst_invoice, receipt, fuel_slip, dining_bill, fare, premium_receipt, other.
SCHEMA:
{schema}"""


def get_extraction_system_prompt() -> str:
    schema_str = json.dumps(ExtractedReceipt.model_json_schema(), indent=2)
    return EXTRACTION_SYSTEM_PROMPT_TEMPLATE.format(schema=schema_str)
