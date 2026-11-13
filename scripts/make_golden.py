"""Generate the 16 synthetic receipt images (g01.png to g15b.png) and data/golden/bank.csv

matching Section 10 of the LedgerSense Complete Engineering Blueprint.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def get_font(size: int = 20, bold: bool = False) -> ImageFont.ImageFont | ImageFont.FreeTypeFont:
    """Try to load a readable truetype font, fallback to default."""
    try:
        # Common Windows fonts
        font_name = "arialbd.ttf" if bold else "arial.ttf"
        return ImageFont.truetype(font_name, size)
    except Exception:
        try:
            return ImageFont.truetype("DejaVuSans.ttf", size)
        except Exception:
            return ImageFont.load_default()


def render_receipt_image(receipt_data: dict, output_path: Path) -> None:
    """Render a clean, high-contrast, synthetic receipt image."""
    width = 900
    height = 1150
    image = Image.new("RGB", (width, height), color="#FFFFFF")
    draw = ImageDraw.Draw(image)

    # Fonts
    title_font = get_font(32, bold=True)
    header_font = get_font(22, bold=True)
    regular_font = get_font(20, bold=False)
    bold_font = get_font(20, bold=True)
    mono_font = get_font(18, bold=False)

    # Outer border
    draw.rectangle([(20, 20), (width - 20, height - 20)], outline="#0F172A", width=2)
    draw.rectangle([(30, 30), (width - 30, height - 30)], outline="#E2E8F0", width=1)

    y = 50

    # Document Header / Type
    doc_type_title = receipt_data.get("doc_type", "INVOICE").replace("_", " ").upper()
    draw.text((width // 2, y), doc_type_title, fill="#0F172A", font=header_font, anchor="mm")
    y += 40

    # Vendor Name
    vendor_name = receipt_data.get("vendor_name", "RETAIL MERCHANT")
    draw.text((width // 2, y), vendor_name, fill="#0F172A", font=title_font, anchor="mm")
    y += 35

    # Vendor GSTIN & Details
    gstin = receipt_data.get("vendor_gstin")
    if gstin:
        draw.text((width // 2, y), f"GSTIN: {gstin}", fill="#1E293B", font=bold_font, anchor="mm")
        y += 28
    else:
        draw.text((width // 2, y), "(Unregistered Dealer / Non-GST Entity)", fill="#64748B", font=mono_font, anchor="mm")
        y += 28

    draw.text((width // 2, y), "Tax Invoice / Payment Voucher / Commercial Receipt", fill="#64748B", font=mono_font, anchor="mm")
    y += 25

    draw.line([(40, y), (width - 40, y)], fill="#CBD5E1", width=2)
    y += 25

    # Metadata columns (Invoice No, Date, Payment Mode)
    inv_no = receipt_data.get("invoice_no") or "N/A"
    inv_date = receipt_data.get("invoice_date") or "N/A"
    pay_mode = (receipt_data.get("payment_mode") or "UNKNOWN").upper()

    draw.text((50, y), f"Invoice / Slip No: {inv_no}", fill="#0F172A", font=bold_font)
    draw.text((50, y + 30), f"Date of Issue:    {inv_date}", fill="#0F172A", font=bold_font)

    draw.text((width - 320, y), f"Payment Mode: {pay_mode}", fill="#0F172A", font=bold_font)
    draw.text((width - 320, y + 30), f"Place of Supply: Rajasthan (08)", fill="#334155", font=regular_font)
    y += 85

    # Table Header
    draw.rectangle([(40, y), (width - 40, y + 35)], fill="#F1F5F9", outline="#CBD5E1")
    draw.text((55, y + 8), "Description", fill="#0F172A", font=bold_font)
    draw.text((480, y + 8), "HSN/SAC", fill="#0F172A", font=bold_font)
    draw.text((600, y + 8), "Qty", fill="#0F172A", font=bold_font)
    draw.text((width - 60, y + 8), "Amount (INR)", fill="#0F172A", font=bold_font, anchor="ra")
    y += 45

    # Line items
    for item in receipt_data.get("line_items", []):
        desc = item.get("description", "")
        hsn = item.get("hsn_sac") or "-"
        qty = str(item.get("quantity") or "1")
        amt = f"{float(item.get('amount', 0)):,.2f}"

        draw.text((55, y), desc[:40], fill="#1E293B", font=regular_font)
        draw.text((480, y), hsn, fill="#334155", font=mono_font)
        draw.text((600, y), qty, fill="#334155", font=regular_font)
        draw.text((width - 60, y), amt, fill="#0F172A", font=bold_font, anchor="ra")
        y += 35

    y += 20
    draw.line([(40, y), (width - 40, y)], fill="#CBD5E1", width=1)
    y += 25

    # Tax & Subtotal summary block
    subtotal = float(receipt_data.get("subtotal") or receipt_data.get("total") or 0)
    cgst = float(receipt_data.get("cgst") or 0)
    sgst = float(receipt_data.get("sgst") or 0)
    igst = float(receipt_data.get("igst") or 0)
    total = float(receipt_data.get("total") or subtotal + cgst + sgst + igst)

    summary_x_label = width - 360
    summary_x_val = width - 60

    if subtotal > 0:
        draw.text((summary_x_label, y), "Subtotal (Taxable):", fill="#475569", font=regular_font)
        draw.text((summary_x_val, y), f"INR {subtotal:,.2f}", fill="#0F172A", font=bold_font, anchor="ra")
        y += 30

    if cgst > 0:
        draw.text((summary_x_label, y), "CGST (Central Tax):", fill="#475569", font=regular_font)
        draw.text((summary_x_val, y), f"INR {cgst:,.2f}", fill="#0F172A", font=bold_font, anchor="ra")
        y += 28

    if sgst > 0:
        draw.text((summary_x_label, y), "SGST (State Tax):", fill="#475569", font=regular_font)
        draw.text((summary_x_val, y), f"INR {sgst:,.2f}", fill="#0F172A", font=bold_font, anchor="ra")
        y += 28

    if igst > 0:
        draw.text((summary_x_label, y), "IGST (Integrated Tax):", fill="#475569", font=regular_font)
        draw.text((summary_x_val, y), f"INR {igst:,.2f}", fill="#0F172A", font=bold_font, anchor="ra")
        y += 28

    # Final Total Box
    y += 10
    draw.rectangle([(summary_x_label - 15, y), (width - 40, y + 48)], fill="#0F172A")
    draw.text((summary_x_label, y + 12), "GRAND TOTAL:", fill="#FFFFFF", font=header_font)
    draw.text((summary_x_val, y + 12), f"INR {total:,.2f}", fill="#FFFFFF", font=header_font, anchor="ra")
    y += 80

    # Verification and Footer Notes
    draw.text((width // 2, y), f"Certified Original Document · Code: {receipt_data.get('id', '')}", fill="#64748B", font=mono_font, anchor="mm")
    y += 25
    draw.text((width // 2, y), "Generated synthetically for LedgerSense Benchmark & Demo", fill="#94A3B8", font=mono_font, anchor="mm")

    image.save(output_path, "PNG")


def generate_bank_csv(csv_path: Path) -> None:
    """Generate the synthetic bank statement CSV matching Section 10."""
    rows = [
        # G01
        {"date": "2025-06-12", "narration": "UPI/ARAVALI STATIONERS/INV2041", "ref_no": "UPI902812", "debit": "11800.00", "credit": "0.00", "balance": "188200.00"},
        # G02 (bank date +1 day)
        {"date": "2025-07-04", "narration": "POS/PINK CITY FUELS/7781", "ref_no": "POS889102", "debit": "3200.00", "credit": "0.00", "balance": "185000.00"},
        # Credit Line 1 (client receipt, matching must ignore)
        {"date": "2025-07-15", "narration": "NEFT/CLIENT INVOICE SETTLEMENT C-101", "ref_no": "NEFT29841", "debit": "0.00", "credit": "50000.00", "balance": "235000.00"},
        # G03
        {"date": "2025-08-01", "narration": "NEFT/CLOUDNIMBUS SOFTWARE", "ref_no": "NEFT33910", "debit": "5900.00", "credit": "0.00", "balance": "229100.00"},
        # G04
        {"date": "2025-09-14", "narration": "POS/SPICE ROUTE RESTAURANT", "ref_no": "POS440211", "debit": "2100.00", "credit": "0.00", "balance": "227000.00"},
        # G05
        {"date": "2025-10-06", "narration": "UPI/QUICKCAB MOBILITY/5529", "ref_no": "UPI552901", "debit": "640.00", "credit": "0.00", "balance": "226360.00"},
        # G14 (receipt 4130.00 on 2025-11-05; bank debit 4128.00 on 2025-11-08; amount delta -2.00)
        {"date": "2025-11-08", "narration": "NEFT/DESKCRAFT FURNITURE", "ref_no": "NEFT77102", "debit": "4128.00", "credit": "0.00", "balance": "222232.00"},
        # Credit Line 2 (client receipt, matching must ignore)
        {"date": "2025-11-25", "narration": "RTGS/CLIENT RETAINER PAYMENT C-102", "ref_no": "RTGS99210", "debit": "0.00", "credit": "75000.00", "balance": "297232.00"},
        # G10
        {"date": "2025-12-02", "narration": "NEFT/METRO PRINT HOUSE", "ref_no": "NEFT11890", "debit": "23600.00", "credit": "0.00", "balance": "273632.00"},
        # G15a (receipt 2025-12-03, bank 2025-12-04)
        {"date": "2025-12-04", "narration": "NEFT/ARAVALI STATIONERS/2102", "ref_no": "NEFT21021", "debit": "7080.00", "credit": "0.00", "balance": "266552.00"},
        # G15b (receipt 2025-12-05, bank 2025-12-06)
        {"date": "2025-12-06", "narration": "NEFT/ARAVALI STATIONERS/2105", "ref_no": "NEFT21051", "debit": "7080.00", "credit": "0.00", "balance": "259472.00"},
        # G11
        {"date": "2026-01-15", "narration": "ACH/BHARAT LIFE INSURANCE/99231", "ref_no": "ACH992310", "debit": "30000.00", "credit": "0.00", "balance": "229472.00"},
        # G12
        {"date": "2026-01-22", "narration": "UPI/SUNRISE AUTO CARE/3307", "ref_no": "UPI330799", "debit": "5900.00", "credit": "0.00", "balance": "223572.00"},
        # G08
        {"date": "2026-02-10", "narration": "NEFT/SHIELD HEALTH INSURANCE/6512", "ref_no": "NEFT65120", "debit": "18000.00", "credit": "0.00", "balance": "205572.00"},
        # Bank-only trap: debit 9999.00 on 2026-03-05
        {"date": "2026-03-05", "narration": "UPI/UNKNOWN PAYEE", "ref_no": "UPI999999", "debit": "9999.00", "credit": "0.00", "balance": "195573.00"},
        # G07 (dated 2026-04-12, bank line on 2026-04-13)
        {"date": "2026-04-13", "narration": "NEFT/SHIELD HEALTH INSURANCE/8801", "ref_no": "NEFT88010", "debit": "24000.00", "credit": "0.00", "balance": "171573.00"},
    ]

    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        fieldnames = ["date", "narration", "ref_no", "debit", "credit", "balance"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    # Resolve paths
    base_dir = Path(__file__).resolve().parents[1]
    golden_dir = base_dir / "data" / "golden"
    receipts_dir = golden_dir / "receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)

    expected_receipts_path = golden_dir / "expected_receipts.json"
    with open(expected_receipts_path, encoding="utf-8") as f:
        expected_receipts = json.load(f)

    # Filename map for g01 to g15b
    file_map = {
        "rcpt:G01": "g01.png",
        "rcpt:G02": "g02.png",
        "rcpt:G03": "g03.png",
        "rcpt:G04": "g04.png",
        "rcpt:G05": "g05.png",
        "rcpt:G06": "g06.png",
        "rcpt:G07": "g07.png",
        "rcpt:G08": "g08.png",
        "rcpt:G09": "g09.png",
        "rcpt:G10": "g10.png",
        "rcpt:G11": "g11.png",
        "rcpt:G12": "g12.png",
        "rcpt:G13": "g13.png",
        "rcpt:G14": "g14.png",
        "rcpt:G15a": "g15a.png",
        "rcpt:G15b": "g15b.png",
    }

    cache_dir = golden_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    print(f"Generating 16 receipt images in {receipts_dir}...")
    for receipt in expected_receipts:
        rcpt_id = receipt["id"]
        fname = file_map.get(rcpt_id, f"{rcpt_id.replace('rcpt:', '').lower()}.png")
        out_file = receipts_dir / fname
        render_receipt_image(receipt, out_file)
        print(f"  [OK] Rendered {fname} ({receipt['vendor_name']} - INR {receipt['total']})")

        # Cache fixture for replay mode
        img_bytes = out_file.read_bytes()
        file_hash = hashlib.sha256(img_bytes).hexdigest()
        cache_file = cache_dir / f"{file_hash}.json"
        with open(cache_file, "w", encoding="utf-8") as cf:
            json.dump(
                {
                    "file_hash": file_hash,
                    "model_id": "moonshot-v1-8k-vision-preview",
                    "prompt_version": "v1",
                    "response_json": json.dumps(receipt),
                },
                cf,
                indent=2,
            )

    bank_csv_path = golden_dir / "bank.csv"
    print(f"\nGenerating {bank_csv_path}...")
    generate_bank_csv(bank_csv_path)
    print("  [OK] bank.csv generated with 16 lines (14 debits including 9,999.00 trap, 2 credit lines)")


if __name__ == "__main__":
    main()
