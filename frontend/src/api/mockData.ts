// Auto-generated golden mock state from data/golden/
import type {
  Run,
  Receipt,
  BankLine,
  Match,
  RiskFlag,
  JournalEntry,
  TrialBalance,
  PnL,
  DeductionSchedule,
  ITRDraft,
  AuditEvent,
  EgressResponse,
} from '../types/api';

export const initialRun: Run = {
  "id": "run:2025-26-demo",
  "period_start": "2025-04-01",
  "period_end": "2026-03-31",
  "regime": "ITA_1961",
  "status": "AWAITING_REVIEW",
  "config": {
    "period_start": "2025-04-01",
    "period_end": "2026-03-31",
    "date_window_days": 3,
    "amount_tolerance": "5.00",
    "cash_limit": "10000.00",
    "tax_regime_choice": "old",
    "regime": "ITA_1961"
  },
  "created_at": "2026-03-31T09:00:00Z"
};

export const initialReceipts: Receipt[] = [
  {
    "doc_type": "gst_invoice",
    "vendor_name": "Aravali Stationers",
    "vendor_gstin": "08AAAFA1234B1ZC",
    "invoice_no": "INV-2041",
    "invoice_date": "2025-06-12",
    "line_items": [
      {
        "description": "Office stationery and printing paper",
        "quantity": "1",
        "unit_price": "10000.00",
        "amount": "10000.00",
        "hsn_sac": "4817",
        "tax_rate_pct": "18.00"
      }
    ],
    "subtotal": "10000.00",
    "cgst": "900.00",
    "sgst": "900.00",
    "igst": "0.00",
    "total": "11800.00",
    "payment_mode": "upi",
    "field_confidence": {
      "vendor_gstin": 0.99,
      "invoice_date": 0.98,
      "total": 0.99
    },
    "id": "rcpt:G01",
    "run_id": "run:2025-26-demo",
    "source_file": "receipts/g01_invoice_2041.png",
    "file_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "vendor_key": "aravali-stationers|08AAAFA1234B1ZC",
    "extraction_status": "OK",
    "check_messages": []
  },
  {
    "doc_type": "fuel_slip",
    "vendor_name": "Pink City Fuels",
    "vendor_gstin": "08AAACP5678C1ZD",
    "invoice_no": "7781",
    "invoice_date": "2025-07-03",
    "line_items": [
      {
        "description": "Diesel fuel",
        "quantity": "35.5",
        "unit_price": "90.14",
        "amount": "3200.00",
        "hsn_sac": "2710",
        "tax_rate_pct": "0.00"
      }
    ],
    "subtotal": "3200.00",
    "cgst": "0.00",
    "sgst": "0.00",
    "igst": "0.00",
    "total": "3200.00",
    "payment_mode": "card",
    "field_confidence": {
      "vendor_gstin": 0.98,
      "invoice_date": 0.97,
      "total": 0.99
    },
    "id": "rcpt:G02",
    "run_id": "run:2025-26-demo",
    "source_file": "receipts/g02_fuel_7781.png",
    "file_hash": "5d41402abc4b2a76b9719d911017c592",
    "vendor_key": "pink-city-fuels|08AAACP5678C1ZD",
    "extraction_status": "OK",
    "check_messages": []
  },
  {
    "doc_type": "gst_invoice",
    "vendor_name": "CloudNimbus Software",
    "vendor_gstin": "29AABCC2345D1Z1",
    "invoice_no": "CN-2025-881",
    "invoice_date": "2025-08-01",
    "line_items": [
      {
        "description": "Cloud hosting subscription (IGST)",
        "quantity": "1",
        "unit_price": "5000.00",
        "amount": "5000.00",
        "hsn_sac": "998315",
        "tax_rate_pct": "18.00"
      }
    ],
    "subtotal": "5000.00",
    "cgst": "0.00",
    "sgst": "0.00",
    "igst": "900.00",
    "total": "5900.00",
    "payment_mode": "bank_transfer",
    "field_confidence": {
      "vendor_gstin": 0.99,
      "invoice_date": 0.99,
      "total": 0.99
    },
    "id": "rcpt:G03",
    "run_id": "run:2025-26-demo",
    "source_file": "receipts/g03_cloudnimbus.png",
    "file_hash": "7d793037a0760186574b0282f2f435e7",
    "vendor_key": "cloudnimbus-software|29AABCC2345D1Z1",
    "extraction_status": "OK",
    "check_messages": []
  },
  {
    "doc_type": "dining_bill",
    "vendor_name": "Spice Route Restaurant",
    "vendor_gstin": "08AABFS3456E1ZB",
    "invoice_no": "SR-4402",
    "invoice_date": "2025-09-14",
    "line_items": [
      {
        "description": "Client dining and restaurant meals",
        "quantity": "1",
        "unit_price": "2000.00",
        "amount": "2000.00",
        "hsn_sac": "996331",
        "tax_rate_pct": "5.00"
      }
    ],
    "subtotal": "2000.00",
    "cgst": "50.00",
    "sgst": "50.00",
    "igst": "0.00",
    "total": "2100.00",
    "payment_mode": "card",
    "field_confidence": {
      "vendor_gstin": 0.97,
      "invoice_date": 0.98,
      "total": 0.99
    },
    "id": "rcpt:G04",
    "run_id": "run:2025-26-demo",
    "source_file": "receipts/g04_spice_route.png",
    "file_hash": "1f3870be274f6c49b3e31a0c6728957f",
    "vendor_key": "spice-route-restaurant|08AABFS3456E1ZB",
    "extraction_status": "OK",
    "check_messages": []
  },
  {
    "doc_type": "fare",
    "vendor_name": "QuickCab Mobility",
    "vendor_gstin": "08AAACQ4567F1ZC",
    "invoice_no": "RCP-5529",
    "invoice_date": "2025-10-06",
    "line_items": [
      {
        "description": "Local city cab fare trip",
        "quantity": "1",
        "unit_price": "609.52",
        "amount": "609.52",
        "hsn_sac": "996412",
        "tax_rate_pct": "5.00"
      }
    ],
    "subtotal": "609.52",
    "cgst": "15.24",
    "sgst": "15.24",
    "igst": "0.00",
    "total": "640.00",
    "payment_mode": "upi",
    "field_confidence": {
      "vendor_gstin": 0.99,
      "invoice_date": 0.99,
      "total": 0.99
    },
    "id": "rcpt:G05",
    "run_id": "run:2025-26-demo",
    "source_file": "receipts/g05_quickcab.png",
    "file_hash": "d67c5cbf5b01c9f91932e3b8def5e9f8",
    "vendor_key": "quickcab-mobility|08AAACQ4567F1ZC",
    "extraction_status": "OK",
    "check_messages": []
  },
  {
    "doc_type": "fare",
    "vendor_name": "QuickCab Mobility",
    "vendor_gstin": "08AAACQ4567F1ZC",
    "invoice_no": "RCP-5529",
    "invoice_date": "2025-10-06",
    "line_items": [
      {
        "description": "Local city cab fare trip (re-upload)",
        "quantity": "1",
        "unit_price": "609.52",
        "amount": "609.52",
        "hsn_sac": "996412",
        "tax_rate_pct": "5.00"
      }
    ],
    "subtotal": "609.52",
    "cgst": "15.24",
    "sgst": "15.24",
    "igst": "0.00",
    "total": "640.00",
    "payment_mode": "upi",
    "field_confidence": {
      "vendor_gstin": 0.99,
      "invoice_date": 0.99,
      "total": 0.99
    },
    "id": "rcpt:G06",
    "run_id": "run:2025-26-demo",
    "source_file": "receipts/g06_quickcab_duplicate.png",
    "file_hash": "d67c5cbf5b01c9f91932e3b8def5e9f8",
    "vendor_key": "quickcab-mobility|08AAACQ4567F1ZC",
    "extraction_status": "OK",
    "check_messages": []
  },
  {
    "doc_type": "premium_receipt",
    "vendor_name": "Shield Health Insurance",
    "vendor_gstin": "27AAACS5678G1Z2",
    "invoice_no": "SHI-8801",
    "invoice_date": "2026-04-12",
    "line_items": [
      {
        "description": "Health insurance premium annual policy (FY 2026-27)",
        "quantity": "1",
        "unit_price": "24000.00",
        "amount": "24000.00",
        "hsn_sac": "997133",
        "tax_rate_pct": "0.00"
      }
    ],
    "subtotal": "24000.00",
    "cgst": "0.00",
    "sgst": "0.00",
    "igst": "0.00",
    "total": "24000.00",
    "payment_mode": "bank_transfer",
    "field_confidence": {
      "vendor_gstin": 0.99,
      "invoice_date": 0.99,
      "total": 0.99
    },
    "id": "rcpt:G07",
    "run_id": "run:2025-26-demo",
    "source_file": "receipts/g07_shield_health_apr.png",
    "file_hash": "4a7d1ed414474e4033ac29ccb8653d9b",
    "vendor_key": "shield-health-insurance|27AAACS5678G1Z2",
    "extraction_status": "OK",
    "check_messages": []
  },
  {
    "doc_type": "premium_receipt",
    "vendor_name": "Shield Health Insurance",
    "vendor_gstin": "27AAACS5678G1Z2",
    "invoice_no": "SHI-6512",
    "invoice_date": "2026-02-10",
    "line_items": [
      {
        "description": "Family medical insurance policy premium",
        "quantity": "1",
        "unit_price": "18000.00",
        "amount": "18000.00",
        "hsn_sac": "997133",
        "tax_rate_pct": "0.00"
      }
    ],
    "subtotal": "18000.00",
    "cgst": "0.00",
    "sgst": "0.00",
    "igst": "0.00",
    "total": "18000.00",
    "payment_mode": "bank_transfer",
    "field_confidence": {
      "vendor_gstin": 0.99,
      "invoice_date": 0.99,
      "total": 0.99
    },
    "id": "rcpt:G08",
    "run_id": "run:2025-26-demo",
    "source_file": "receipts/g08_shield_health_feb.png",
    "file_hash": "202cb962ac59075b964b07152d234b70",
    "vendor_key": "shield-health-insurance|27AAACS5678G1Z2",
    "extraction_status": "OK",
    "check_messages": []
  },
  {
    "doc_type": "receipt",
    "vendor_name": "Rajputana Hardware",
    "vendor_gstin": null,
    "invoice_no": "RH-1092",
    "invoice_date": "2025-11-20",
    "line_items": [
      {
        "description": "Office workshop hardware and electrical fixtures",
        "quantity": "1",
        "unit_price": "12000.00",
        "amount": "12000.00",
        "hsn_sac": null,
        "tax_rate_pct": null
      }
    ],
    "subtotal": "12000.00",
    "cgst": "0.00",
    "sgst": "0.00",
    "igst": "0.00",
    "total": "12000.00",
    "payment_mode": "cash",
    "field_confidence": {
      "invoice_date": 0.95,
      "total": 0.98
    },
    "id": "rcpt:G09",
    "run_id": "run:2025-26-demo",
    "source_file": "receipts/g09_rajputana_hardware.png",
    "file_hash": "c81e728d9d4c2f636f067f89cc14862c",
    "vendor_key": "rajputana-hardware|nogstin",
    "extraction_status": "OK",
    "check_messages": []
  },
  {
    "doc_type": "gst_invoice",
    "vendor_name": "Metro Print House",
    "vendor_gstin": "08AAAFM6789H1ZX",
    "invoice_no": "INV-118",
    "invoice_date": "2025-12-02",
    "line_items": [
      {
        "description": "Catalog printing, brochures and annual reports",
        "quantity": "1",
        "unit_price": "20000.00",
        "amount": "20000.00",
        "hsn_sac": "9989",
        "tax_rate_pct": "18.00"
      }
    ],
    "subtotal": "20000.00",
    "cgst": "1800.00",
    "sgst": "1800.00",
    "igst": "0.00",
    "total": "23600.00",
    "payment_mode": "bank_transfer",
    "field_confidence": {
      "vendor_gstin": 0.99,
      "invoice_date": 0.98,
      "total": 0.99
    },
    "id": "rcpt:G10",
    "run_id": "run:2025-26-demo",
    "source_file": "receipts/g10_metro_print_house.png",
    "file_hash": "eccbc87e4b5ce2fe28308fd9f2a7baf3",
    "vendor_key": "metro-print-house|08AAAFM6789H1ZX",
    "extraction_status": "OK",
    "check_messages": []
  },
  {
    "doc_type": "premium_receipt",
    "vendor_name": "Bharat Life Insurance",
    "vendor_gstin": null,
    "invoice_no": "BLI-99231",
    "invoice_date": "2026-01-15",
    "line_items": [
      {
        "description": "Term life insurance premium policy annual",
        "quantity": "1",
        "unit_price": "30000.00",
        "amount": "30000.00",
        "hsn_sac": "997132",
        "tax_rate_pct": "0.00"
      }
    ],
    "subtotal": "30000.00",
    "cgst": "0.00",
    "sgst": "0.00",
    "igst": "0.00",
    "total": "30000.00",
    "payment_mode": "bank_transfer",
    "field_confidence": {
      "invoice_date": 0.99,
      "total": 0.99
    },
    "id": "rcpt:G11",
    "run_id": "run:2025-26-demo",
    "source_file": "receipts/g11_bharat_life.png",
    "file_hash": "a87ff679a2f3e71d9181a67b7542122c",
    "vendor_key": "bharat-life-insurance|nogstin",
    "extraction_status": "OK",
    "check_messages": []
  },
  {
    "doc_type": "gst_invoice",
    "vendor_name": "Sunrise Auto Care",
    "vendor_gstin": "08AAAFS8901K1ZZ",
    "invoice_no": "INV-3307",
    "invoice_date": "2026-01-22",
    "line_items": [
      {
        "description": "Car service routine maintenance and spare parts passenger motor vehicle",
        "quantity": "1",
        "unit_price": "5000.00",
        "amount": "5000.00",
        "hsn_sac": "998729",
        "tax_rate_pct": "18.00"
      }
    ],
    "subtotal": "5000.00",
    "cgst": "450.00",
    "sgst": "450.00",
    "igst": "0.00",
    "total": "5900.00",
    "payment_mode": "upi",
    "field_confidence": {
      "vendor_gstin": 0.99,
      "invoice_date": 0.98,
      "total": 0.99
    },
    "id": "rcpt:G12",
    "run_id": "run:2025-26-demo",
    "source_file": "receipts/g12_sunrise_auto.png",
    "file_hash": "e4da3b7fbbce2345d7772b0674a318d5",
    "vendor_key": "sunrise-auto-care|08AAAFS8901K1ZZ",
    "extraction_status": "OK",
    "check_messages": []
  },
  {
    "doc_type": "receipt",
    "vendor_name": "Local tea stall",
    "vendor_gstin": null,
    "invoice_no": null,
    "invoice_date": "2025-12-18",
    "line_items": [
      {
        "description": "Office refreshments, tea, coffee and snacks",
        "quantity": "1",
        "unit_price": "450.00",
        "amount": "450.00",
        "hsn_sac": null,
        "tax_rate_pct": null
      }
    ],
    "subtotal": "450.00",
    "cgst": "0.00",
    "sgst": "0.00",
    "igst": "0.00",
    "total": "450.00",
    "payment_mode": "cash",
    "field_confidence": {
      "invoice_date": 0.9,
      "total": 0.92
    },
    "id": "rcpt:G13",
    "run_id": "run:2025-26-demo",
    "source_file": "receipts/g13_local_tea_stall.png",
    "file_hash": "1679091c5a880faf6fb5e6087eb1b2dc",
    "vendor_key": "local-tea-stall|nogstin",
    "extraction_status": "OK",
    "check_messages": []
  },
  {
    "doc_type": "gst_invoice",
    "vendor_name": "DeskCraft Furniture",
    "vendor_gstin": "29AAACD9012L1ZI",
    "invoice_no": "INV-7710",
    "invoice_date": "2025-11-05",
    "line_items": [
      {
        "description": "Ergonomic mesh office work chair (IGST)",
        "quantity": "1",
        "unit_price": "3500.00",
        "amount": "3500.00",
        "hsn_sac": "9403",
        "tax_rate_pct": "18.00"
      }
    ],
    "subtotal": "3500.00",
    "cgst": "0.00",
    "sgst": "0.00",
    "igst": "630.00",
    "total": "4130.00",
    "payment_mode": "bank_transfer",
    "field_confidence": {
      "vendor_gstin": 0.99,
      "invoice_date": 0.98,
      "total": 0.99
    },
    "id": "rcpt:G14",
    "run_id": "run:2025-26-demo",
    "source_file": "receipts/g14_deskcraft_furniture.png",
    "file_hash": "8f14e45fceea167a5a36dedd4bea2543",
    "vendor_key": "deskcraft-furniture|29AAACD9012L1ZI",
    "extraction_status": "OK",
    "check_messages": []
  },
  {
    "doc_type": "gst_invoice",
    "vendor_name": "Aravali Stationers",
    "vendor_gstin": "08AAAFA1234B1ZC",
    "invoice_no": "INV-2102",
    "invoice_date": "2025-12-03",
    "line_items": [
      {
        "description": "Printer ink toner cartridges batch A",
        "quantity": "1",
        "unit_price": "6000.00",
        "amount": "6000.00",
        "hsn_sac": "8443",
        "tax_rate_pct": "18.00"
      }
    ],
    "subtotal": "6000.00",
    "cgst": "540.00",
    "sgst": "540.00",
    "igst": "0.00",
    "total": "7080.00",
    "payment_mode": "bank_transfer",
    "field_confidence": {
      "vendor_gstin": 0.99,
      "invoice_date": 0.98,
      "total": 0.99
    },
    "id": "rcpt:G15a",
    "run_id": "run:2025-26-demo",
    "source_file": "receipts/g15a_aravali_inv2102.png",
    "file_hash": "c9f0f895fb98ab9159f51fd0297e236d",
    "vendor_key": "aravali-stationers|08AAAFA1234B1ZC",
    "extraction_status": "OK",
    "check_messages": []
  },
  {
    "doc_type": "gst_invoice",
    "vendor_name": "Aravali Stationers",
    "vendor_gstin": "08AAAFA1234B1ZC",
    "invoice_no": "INV-2105",
    "invoice_date": "2025-12-05",
    "line_items": [
      {
        "description": "Printer ink toner cartridges batch B",
        "quantity": "1",
        "unit_price": "6000.00",
        "amount": "6000.00",
        "hsn_sac": "8443",
        "tax_rate_pct": "18.00"
      }
    ],
    "subtotal": "6000.00",
    "cgst": "540.00",
    "sgst": "540.00",
    "igst": "0.00",
    "total": "7080.00",
    "payment_mode": "bank_transfer",
    "field_confidence": {
      "vendor_gstin": 0.99,
      "invoice_date": 0.98,
      "total": 0.99
    },
    "id": "rcpt:G15b",
    "run_id": "run:2025-26-demo",
    "source_file": "receipts/g15b_aravali_inv2105.png",
    "file_hash": "45c48cce2e2d7fbdea1afc51c7c6ad26",
    "vendor_key": "aravali-stationers|08AAAFA1234B1ZC",
    "extraction_status": "OK",
    "check_messages": []
  }
];

export const initialBankLines: BankLine[] = [
  {
    "id": "bank:0001",
    "run_id": "run:2025-26-demo",
    "txn_date": "2025-06-12",
    "narration": "UPI/ARAVALI STATIONERS/INV2041",
    "debit": "11800.00",
    "credit": "0.00",
    "balance": "188200.00",
    "ref_no": "UPI902812"
  },
  {
    "id": "bank:0002",
    "run_id": "run:2025-26-demo",
    "txn_date": "2025-07-04",
    "narration": "POS/PINK CITY FUELS/7781",
    "debit": "3200.00",
    "credit": "0.00",
    "balance": "185000.00",
    "ref_no": "POS889102"
  },
  {
    "id": "bank:0003",
    "run_id": "run:2025-26-demo",
    "txn_date": "2025-07-15",
    "narration": "NEFT/CLIENT INVOICE SETTLEMENT C-101",
    "debit": "0.00",
    "credit": "50000.00",
    "balance": "235000.00",
    "ref_no": "NEFT29841"
  },
  {
    "id": "bank:0004",
    "run_id": "run:2025-26-demo",
    "txn_date": "2025-08-01",
    "narration": "NEFT/CLOUDNIMBUS SOFTWARE",
    "debit": "5900.00",
    "credit": "0.00",
    "balance": "229100.00",
    "ref_no": "NEFT33910"
  },
  {
    "id": "bank:0005",
    "run_id": "run:2025-26-demo",
    "txn_date": "2025-09-14",
    "narration": "POS/SPICE ROUTE RESTAURANT",
    "debit": "2100.00",
    "credit": "0.00",
    "balance": "227000.00",
    "ref_no": "POS440211"
  },
  {
    "id": "bank:0006",
    "run_id": "run:2025-26-demo",
    "txn_date": "2025-10-06",
    "narration": "UPI/QUICKCAB MOBILITY/5529",
    "debit": "640.00",
    "credit": "0.00",
    "balance": "226360.00",
    "ref_no": "UPI552901"
  },
  {
    "id": "bank:0007",
    "run_id": "run:2025-26-demo",
    "txn_date": "2025-11-08",
    "narration": "NEFT/DESKCRAFT FURNITURE",
    "debit": "4128.00",
    "credit": "0.00",
    "balance": "222232.00",
    "ref_no": "NEFT77102"
  },
  {
    "id": "bank:0008",
    "run_id": "run:2025-26-demo",
    "txn_date": "2025-11-25",
    "narration": "RTGS/CLIENT RETAINER PAYMENT C-102",
    "debit": "0.00",
    "credit": "75000.00",
    "balance": "297232.00",
    "ref_no": "RTGS99210"
  },
  {
    "id": "bank:0009",
    "run_id": "run:2025-26-demo",
    "txn_date": "2025-12-02",
    "narration": "NEFT/METRO PRINT HOUSE",
    "debit": "23600.00",
    "credit": "0.00",
    "balance": "273632.00",
    "ref_no": "NEFT11890"
  },
  {
    "id": "bank:0010",
    "run_id": "run:2025-26-demo",
    "txn_date": "2025-12-04",
    "narration": "NEFT/ARAVALI STATIONERS/2102",
    "debit": "7080.00",
    "credit": "0.00",
    "balance": "266552.00",
    "ref_no": "NEFT21021"
  },
  {
    "id": "bank:0011",
    "run_id": "run:2025-26-demo",
    "txn_date": "2025-12-06",
    "narration": "NEFT/ARAVALI STATIONERS/2105",
    "debit": "7080.00",
    "credit": "0.00",
    "balance": "259472.00",
    "ref_no": "NEFT21051"
  },
  {
    "id": "bank:0012",
    "run_id": "run:2025-26-demo",
    "txn_date": "2026-01-15",
    "narration": "ACH/BHARAT LIFE INSURANCE/99231",
    "debit": "30000.00",
    "credit": "0.00",
    "balance": "229472.00",
    "ref_no": "ACH992310"
  },
  {
    "id": "bank:0013",
    "run_id": "run:2025-26-demo",
    "txn_date": "2026-01-22",
    "narration": "UPI/SUNRISE AUTO CARE/3307",
    "debit": "5900.00",
    "credit": "0.00",
    "balance": "223572.00",
    "ref_no": "UPI330799"
  },
  {
    "id": "bank:0014",
    "run_id": "run:2025-26-demo",
    "txn_date": "2026-02-10",
    "narration": "NEFT/SHIELD HEALTH INSURANCE/6512",
    "debit": "18000.00",
    "credit": "0.00",
    "balance": "205572.00",
    "ref_no": "NEFT65120"
  },
  {
    "id": "bank:0015",
    "run_id": "run:2025-26-demo",
    "txn_date": "2026-03-05",
    "narration": "UPI/UNKNOWN PAYEE",
    "debit": "9999.00",
    "credit": "0.00",
    "balance": "195573.00",
    "ref_no": "UPI999999"
  },
  {
    "id": "bank:0016",
    "run_id": "run:2025-26-demo",
    "txn_date": "2026-04-13",
    "narration": "NEFT/SHIELD HEALTH INSURANCE/8801",
    "debit": "24000.00",
    "credit": "0.00",
    "balance": "171573.00",
    "ref_no": "NEFT88010"
  }
];

export const initialMatches: Match[] = [
  {
    "id": "match:G11_0012",
    "run_id": "run:2025-26-demo",
    "receipt_id": "rcpt:G11",
    "bank_line_id": "bank:0012",
    "score": 0.96,
    "date_delta_days": 0,
    "amount_delta": "0.00",
    "kind": "MATCHED"
  },
  {
    "id": "match:G12_0013",
    "run_id": "run:2025-26-demo",
    "receipt_id": "rcpt:G12",
    "bank_line_id": "bank:0013",
    "score": 0.96,
    "date_delta_days": 0,
    "amount_delta": "0.00",
    "kind": "MATCHED"
  },
  {
    "id": "match:G08_0014",
    "run_id": "run:2025-26-demo",
    "receipt_id": "rcpt:G08",
    "bank_line_id": "bank:0014",
    "score": 0.96,
    "date_delta_days": 0,
    "amount_delta": "0.00",
    "kind": "MATCHED"
  },
  {
    "id": "match:G05_0006",
    "run_id": "run:2025-26-demo",
    "receipt_id": "rcpt:G05",
    "bank_line_id": "bank:0006",
    "score": 0.95,
    "date_delta_days": 0,
    "amount_delta": "0.00",
    "kind": "MATCHED"
  },
  {
    "id": "match:G04_0005",
    "run_id": "run:2025-26-demo",
    "receipt_id": "rcpt:G04",
    "bank_line_id": "bank:0005",
    "score": 0.92,
    "date_delta_days": 0,
    "amount_delta": "0.00",
    "kind": "MATCHED"
  },
  {
    "id": "match:G10_0009",
    "run_id": "run:2025-26-demo",
    "receipt_id": "rcpt:G10",
    "bank_line_id": "bank:0009",
    "score": 0.92,
    "date_delta_days": 0,
    "amount_delta": "0.00",
    "kind": "MATCHED"
  },
  {
    "id": "match:G01_0001",
    "run_id": "run:2025-26-demo",
    "receipt_id": "rcpt:G01",
    "bank_line_id": "bank:0001",
    "score": 0.9,
    "date_delta_days": 0,
    "amount_delta": "0.00",
    "kind": "MATCHED"
  },
  {
    "id": "match:G02_0002",
    "run_id": "run:2025-26-demo",
    "receipt_id": "rcpt:G02",
    "bank_line_id": "bank:0002",
    "score": 0.9,
    "date_delta_days": 1,
    "amount_delta": "0.00",
    "kind": "MATCHED"
  },
  {
    "id": "match:G03_0004",
    "run_id": "run:2025-26-demo",
    "receipt_id": "rcpt:G03",
    "bank_line_id": "bank:0004",
    "score": 0.88,
    "date_delta_days": 0,
    "amount_delta": "0.00",
    "kind": "MATCHED"
  },
  {
    "id": "match:G07_0016",
    "run_id": "run:2025-26-demo",
    "receipt_id": "rcpt:G07",
    "bank_line_id": "bank:0016",
    "score": 0.86,
    "date_delta_days": 1,
    "amount_delta": "0.00",
    "kind": "MATCHED"
  },
  {
    "id": "match:G15a_0010",
    "run_id": "run:2025-26-demo",
    "receipt_id": "rcpt:G15a",
    "bank_line_id": "bank:0010",
    "score": 0.85,
    "date_delta_days": 1,
    "amount_delta": "0.00",
    "kind": "MATCHED"
  },
  {
    "id": "match:G15b_0011",
    "run_id": "run:2025-26-demo",
    "receipt_id": "rcpt:G15b",
    "bank_line_id": "bank:0011",
    "score": 0.85,
    "date_delta_days": 1,
    "amount_delta": "0.00",
    "kind": "MATCHED"
  },
  {
    "id": "match:G14_0007",
    "run_id": "run:2025-26-demo",
    "receipt_id": "rcpt:G14",
    "bank_line_id": "bank:0007",
    "score": 0.4,
    "date_delta_days": 3,
    "amount_delta": "-2.00",
    "kind": "MATCHED"
  },
  {
    "id": "match:bank:0015",
    "run_id": "run:2025-26-demo",
    "receipt_id": null,
    "bank_line_id": "bank:0015",
    "score": 0.0,
    "date_delta_days": null,
    "amount_delta": null,
    "kind": "UNMATCHED_BANK"
  }
];

export const initialFlags: RiskFlag[] = [
  {
    "id": "flag:0001",
    "run_id": "run:2025-26-demo",
    "rule_id": "CASH_LIMIT",
    "severity": "HIGH",
    "entity_ids": [
      "rcpt:G09"
    ],
    "legal_ref": "s.40A(3)",
    "evidence": {
      "vendor_key": "rajputana-hardware|nogstin",
      "vendor_name": "Rajputana Hardware",
      "invoice_date": "2025-11-20",
      "cash_total": "12000.00",
      "cash_limit": "10000.00",
      "receipt_ids": [
        "rcpt:G09"
      ],
      "reason": "Cash expense 12000.00 exceeds statutory limit 10000.00"
    },
    "suggested_action": "Treat as disallowed or obtain evidence of exception",
    "status": "OPEN",
    "decided_by": null,
    "decision_reason": null,
    "decided_at": null
  },
  {
    "id": "flag:0002",
    "run_id": "run:2025-26-demo",
    "rule_id": "DUP_FARE",
    "severity": "HIGH",
    "entity_ids": [
      "rcpt:G06"
    ],
    "legal_ref": "Internal Audit Control \u2014 Duplicate Claim",
    "evidence": {
      "duplicate_of": "rcpt:G05",
      "kind": "exact",
      "vendor_key": "quickcab-mobility|08AAACQ4567F1ZC",
      "vendor_name": "QuickCab Mobility",
      "total": "640.00",
      "invoice_date": "2025-10-06",
      "invoice_no": "RCP-5529",
      "reason": "Duplicate of rcpt:G05 (exact duplicate)"
    },
    "suggested_action": "Reject the later document",
    "status": "OPEN",
    "decided_by": null,
    "decision_reason": null,
    "decided_at": null
  },
  {
    "id": "flag:0003",
    "run_id": "run:2025-26-demo",
    "rule_id": "GSTIN_INVALID",
    "severity": "HIGH",
    "entity_ids": [
      "rcpt:G10"
    ],
    "legal_ref": "CGST Act s.16(2)(aa) \u2014 Valid Tax Invoice / GSTIN",
    "evidence": {
      "vendor_name": "Metro Print House",
      "vendor_gstin": "08AAAFM6789H1ZX",
      "reason": "checksum_mismatch",
      "expected_check_char": "U",
      "tax_claimed": "3600.00"
    },
    "suggested_action": "Deny ITC until corrected",
    "status": "OPEN",
    "decided_by": null,
    "decision_reason": null,
    "decided_at": null
  },
  {
    "id": "flag:0004",
    "run_id": "run:2025-26-demo",
    "rule_id": "OUT_OF_PERIOD",
    "severity": "HIGH",
    "entity_ids": [
      "rcpt:G07"
    ],
    "legal_ref": "Matching & Cut-off Principle (FY Boundary)",
    "evidence": {
      "vendor_name": "Shield Health Insurance",
      "invoice_date": "2026-04-12",
      "period_start": "2025-04-01",
      "period_end": "2026-03-31",
      "total": "24000.00",
      "reason": "Invoice date 2026-04-12 falls outside reconciliation period 2025-04-01 to 2026-03-31"
    },
    "suggested_action": "Move to correct period or approve with reason",
    "status": "OPEN",
    "decided_by": null,
    "decision_reason": null,
    "decided_at": null
  },
  {
    "id": "flag:0005",
    "run_id": "run:2025-26-demo",
    "rule_id": "ITC_BLOCKED",
    "severity": "MEDIUM",
    "entity_ids": [
      "rcpt:G04"
    ],
    "legal_ref": "CGST Act s.17(5)(b)",
    "evidence": {
      "category": "FOOD_BEVERAGE",
      "matched_keyword": "restaurant",
      "vendor_name": "Spice Route Restaurant",
      "tax_claimed": "100.00",
      "total": "2100.00",
      "reason": "Blocked ITC under CGST Act s.17(5)(b) for food_beverage"
    },
    "suggested_action": "Book tax as expense; ITC = 0",
    "status": "OPEN",
    "decided_by": null,
    "decision_reason": null,
    "decided_at": null
  },
  {
    "id": "flag:0006",
    "run_id": "run:2025-26-demo",
    "rule_id": "ITC_BLOCKED",
    "severity": "MEDIUM",
    "entity_ids": [
      "rcpt:G12"
    ],
    "legal_ref": "CGST Act s.17(5)(a)",
    "evidence": {
      "category": "MOTOR_VEHICLE",
      "matched_keyword": "car service",
      "vendor_name": "Sunrise Auto Care",
      "tax_claimed": "900.00",
      "total": "5900.00",
      "reason": "Blocked ITC under CGST Act s.17(5)(a) for motor_vehicle"
    },
    "suggested_action": "Book tax as expense; ITC = 0",
    "status": "OPEN",
    "decided_by": null,
    "decision_reason": null,
    "decided_at": null
  },
  {
    "id": "flag:0007",
    "run_id": "run:2025-26-demo",
    "rule_id": "UNMATCHED_BANK",
    "severity": "MEDIUM",
    "entity_ids": [
      "bank:0015"
    ],
    "legal_ref": "Bank Reconciliation \u2014 Unexplained Bank Debit",
    "evidence": {
      "bank_line_id": "bank:0015",
      "reason": "Bank debit has no matching receipt",
      "amount": "9999.00",
      "txn_date": "2026-03-05",
      "narration": "UPI/UNKNOWN PAYEE"
    },
    "suggested_action": "Obtain document or classify",
    "status": "OPEN",
    "decided_by": null,
    "decision_reason": null,
    "decided_at": null
  }
];

export const initialJournalEntries: JournalEntry[] = [
  {
    "id": "je:0001",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-06-12",
    "narration": "Aravali Stationers - gst_invoice (Invoice: INV-2041)",
    "lines": [
      {
        "account_code": "5000-Office & Stationery Expense",
        "debit": "10000.00",
        "credit": "0.00"
      },
      {
        "account_code": "1200-Input CGST",
        "debit": "900.00",
        "credit": "0.00"
      },
      {
        "account_code": "1210-Input SGST",
        "debit": "900.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "11800.00"
      }
    ],
    "status": "DRAFT",
    "source_receipt_id": "rcpt:G01",
    "flag_ids": [],
    "deduction_tag": null
  },
  {
    "id": "je:0002",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-07-03",
    "narration": "Pink City Fuels - fuel_slip (Invoice: 7781)",
    "lines": [
      {
        "account_code": "5010-Fuel Expense",
        "debit": "3200.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "3200.00"
      }
    ],
    "status": "DRAFT",
    "source_receipt_id": "rcpt:G02",
    "flag_ids": [],
    "deduction_tag": null
  },
  {
    "id": "je:0003",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-08-01",
    "narration": "CloudNimbus Software - gst_invoice (Invoice: CN-2025-881)",
    "lines": [
      {
        "account_code": "5020-Software & IT Expense",
        "debit": "5000.00",
        "credit": "0.00"
      },
      {
        "account_code": "1220-Input IGST",
        "debit": "900.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "5900.00"
      }
    ],
    "status": "DRAFT",
    "source_receipt_id": "rcpt:G03",
    "flag_ids": [],
    "deduction_tag": null
  },
  {
    "id": "je:0004",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-09-14",
    "narration": "Spice Route Restaurant - dining_bill (Invoice: SR-4402)",
    "lines": [
      {
        "account_code": "5030-Food & Beverage Expense",
        "debit": "2100.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "2100.00"
      }
    ],
    "status": "DRAFT",
    "source_receipt_id": "rcpt:G04",
    "flag_ids": [
      "flag:0005"
    ],
    "deduction_tag": null
  },
  {
    "id": "je:0005",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-10-06",
    "narration": "QuickCab Mobility - fare (Invoice: RCP-5529)",
    "lines": [
      {
        "account_code": "5040-Travel & Cab Expense",
        "debit": "609.52",
        "credit": "0.00"
      },
      {
        "account_code": "1200-Input CGST",
        "debit": "15.24",
        "credit": "0.00"
      },
      {
        "account_code": "1210-Input SGST",
        "debit": "15.24",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "640.00"
      }
    ],
    "status": "DRAFT",
    "source_receipt_id": "rcpt:G05",
    "flag_ids": [],
    "deduction_tag": null
  },
  {
    "id": "je:0006",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-10-06",
    "narration": "QuickCab Mobility - fare (Invoice: RCP-5529)",
    "lines": [
      {
        "account_code": "5040-Travel & Cab Expense",
        "debit": "609.52",
        "credit": "0.00"
      },
      {
        "account_code": "1200-Input CGST",
        "debit": "15.24",
        "credit": "0.00"
      },
      {
        "account_code": "1210-Input SGST",
        "debit": "15.24",
        "credit": "0.00"
      },
      {
        "account_code": "2000-Sundry Creditors",
        "debit": "0.00",
        "credit": "640.00"
      }
    ],
    "status": "DRAFT",
    "source_receipt_id": "rcpt:G06",
    "flag_ids": [
      "flag:0002"
    ],
    "deduction_tag": null
  },
  {
    "id": "je:0007",
    "run_id": "run:2025-26-demo",
    "entry_date": "2026-04-12",
    "narration": "Shield Health Insurance - premium_receipt (Invoice: SHI-8801)",
    "lines": [
      {
        "account_code": "5080-Insurance Expense",
        "debit": "24000.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "24000.00"
      }
    ],
    "status": "DRAFT",
    "source_receipt_id": "rcpt:G07",
    "flag_ids": [
      "flag:0004"
    ],
    "deduction_tag": "80D"
  },
  {
    "id": "je:0008",
    "run_id": "run:2025-26-demo",
    "entry_date": "2026-02-10",
    "narration": "Shield Health Insurance - premium_receipt (Invoice: SHI-6512)",
    "lines": [
      {
        "account_code": "5080-Insurance Expense",
        "debit": "18000.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "18000.00"
      }
    ],
    "status": "DRAFT",
    "source_receipt_id": "rcpt:G08",
    "flag_ids": [],
    "deduction_tag": "80D"
  },
  {
    "id": "je:0009",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-11-20",
    "narration": "Rajputana Hardware - receipt (Invoice: RH-1092)",
    "lines": [
      {
        "account_code": "5050-Hardware & Repairs Expense",
        "debit": "12000.00",
        "credit": "0.00"
      },
      {
        "account_code": "1010-Cash in Hand",
        "debit": "0.00",
        "credit": "12000.00"
      }
    ],
    "status": "DRAFT",
    "source_receipt_id": "rcpt:G09",
    "flag_ids": [
      "flag:0001"
    ],
    "deduction_tag": null
  },
  {
    "id": "je:0010",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-12-02",
    "narration": "Metro Print House - gst_invoice (Invoice: INV-118)",
    "lines": [
      {
        "account_code": "5060-Printing Expense",
        "debit": "23600.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "23600.00"
      }
    ],
    "status": "DRAFT",
    "source_receipt_id": "rcpt:G10",
    "flag_ids": [
      "flag:0003"
    ],
    "deduction_tag": null
  },
  {
    "id": "je:0011",
    "run_id": "run:2025-26-demo",
    "entry_date": "2026-01-15",
    "narration": "Bharat Life Insurance - premium_receipt (Invoice: BLI-99231)",
    "lines": [
      {
        "account_code": "5080-Insurance Expense",
        "debit": "30000.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "30000.00"
      }
    ],
    "status": "DRAFT",
    "source_receipt_id": "rcpt:G11",
    "flag_ids": [],
    "deduction_tag": "80C"
  },
  {
    "id": "je:0012",
    "run_id": "run:2025-26-demo",
    "entry_date": "2026-01-22",
    "narration": "Sunrise Auto Care - gst_invoice (Invoice: INV-3307)",
    "lines": [
      {
        "account_code": "5070-Motor Vehicle Expense",
        "debit": "5900.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "5900.00"
      }
    ],
    "status": "DRAFT",
    "source_receipt_id": "rcpt:G12",
    "flag_ids": [
      "flag:0006"
    ],
    "deduction_tag": null
  },
  {
    "id": "je:0013",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-12-18",
    "narration": "Local tea stall - receipt (Invoice: N/A)",
    "lines": [
      {
        "account_code": "5090-General / Petty Expense",
        "debit": "450.00",
        "credit": "0.00"
      },
      {
        "account_code": "1010-Cash in Hand",
        "debit": "0.00",
        "credit": "450.00"
      }
    ],
    "status": "DRAFT",
    "source_receipt_id": "rcpt:G13",
    "flag_ids": [],
    "deduction_tag": null
  },
  {
    "id": "je:0014",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-11-05",
    "narration": "DeskCraft Furniture - gst_invoice (Invoice: INV-7710)",
    "lines": [
      {
        "account_code": "5050-Hardware & Repairs Expense",
        "debit": "3500.00",
        "credit": "0.00"
      },
      {
        "account_code": "1220-Input IGST",
        "debit": "630.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "4130.00"
      }
    ],
    "status": "DRAFT",
    "source_receipt_id": "rcpt:G14",
    "flag_ids": [],
    "deduction_tag": null
  },
  {
    "id": "je:0015",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-12-03",
    "narration": "Aravali Stationers - gst_invoice (Invoice: INV-2102)",
    "lines": [
      {
        "account_code": "5000-Office & Stationery Expense",
        "debit": "6000.00",
        "credit": "0.00"
      },
      {
        "account_code": "1200-Input CGST",
        "debit": "540.00",
        "credit": "0.00"
      },
      {
        "account_code": "1210-Input SGST",
        "debit": "540.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "7080.00"
      }
    ],
    "status": "DRAFT",
    "source_receipt_id": "rcpt:G15a",
    "flag_ids": [],
    "deduction_tag": null
  },
  {
    "id": "je:0016",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-12-05",
    "narration": "Aravali Stationers - gst_invoice (Invoice: INV-2105)",
    "lines": [
      {
        "account_code": "5000-Office & Stationery Expense",
        "debit": "6000.00",
        "credit": "0.00"
      },
      {
        "account_code": "1200-Input CGST",
        "debit": "540.00",
        "credit": "0.00"
      },
      {
        "account_code": "1210-Input SGST",
        "debit": "540.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "7080.00"
      }
    ],
    "status": "DRAFT",
    "source_receipt_id": "rcpt:G15b",
    "flag_ids": [],
    "deduction_tag": null
  }
];

export const committedGoldenEntries: JournalEntry[] = [
  {
    "id": "je:0001",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-06-12",
    "narration": "Aravali Stationers - gst_invoice (Invoice: INV-2041)",
    "lines": [
      {
        "account_code": "5000-Office & Stationery Expense",
        "debit": "10000.00",
        "credit": "0.00"
      },
      {
        "account_code": "1200-Input CGST",
        "debit": "900.00",
        "credit": "0.00"
      },
      {
        "account_code": "1210-Input SGST",
        "debit": "900.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "11800.00"
      }
    ],
    "status": "COMMITTED",
    "source_receipt_id": "rcpt:G01",
    "flag_ids": [],
    "deduction_tag": null
  },
  {
    "id": "je:0002",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-07-03",
    "narration": "Pink City Fuels - fuel_slip (Invoice: 7781)",
    "lines": [
      {
        "account_code": "5010-Fuel Expense",
        "debit": "3200.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "3200.00"
      }
    ],
    "status": "COMMITTED",
    "source_receipt_id": "rcpt:G02",
    "flag_ids": [],
    "deduction_tag": null
  },
  {
    "id": "je:0003",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-08-01",
    "narration": "CloudNimbus Software - gst_invoice (Invoice: CN-2025-881)",
    "lines": [
      {
        "account_code": "5020-Software & IT Expense",
        "debit": "5000.00",
        "credit": "0.00"
      },
      {
        "account_code": "1220-Input IGST",
        "debit": "900.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "5900.00"
      }
    ],
    "status": "COMMITTED",
    "source_receipt_id": "rcpt:G03",
    "flag_ids": [],
    "deduction_tag": null
  },
  {
    "id": "je:0004",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-09-14",
    "narration": "Spice Route Restaurant - dining_bill (Invoice: SR-4402)",
    "lines": [
      {
        "account_code": "5030-Food & Beverage Expense",
        "debit": "2100.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "2100.00"
      }
    ],
    "status": "COMMITTED",
    "source_receipt_id": "rcpt:G04",
    "flag_ids": [
      "flag:0005"
    ],
    "deduction_tag": null
  },
  {
    "id": "je:0005",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-10-06",
    "narration": "QuickCab Mobility - fare (Invoice: RCP-5529)",
    "lines": [
      {
        "account_code": "5040-Travel & Cab Expense",
        "debit": "609.52",
        "credit": "0.00"
      },
      {
        "account_code": "1200-Input CGST",
        "debit": "15.24",
        "credit": "0.00"
      },
      {
        "account_code": "1210-Input SGST",
        "debit": "15.24",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "640.00"
      }
    ],
    "status": "COMMITTED",
    "source_receipt_id": "rcpt:G05",
    "flag_ids": [],
    "deduction_tag": null
  },
  {
    "id": "je:0006",
    "run_id": "run:2025-26-demo",
    "entry_date": "2026-02-10",
    "narration": "Shield Health Insurance - premium_receipt (Invoice: SHI-6512)",
    "lines": [
      {
        "account_code": "5080-Insurance Expense",
        "debit": "18000.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "18000.00"
      }
    ],
    "status": "COMMITTED",
    "source_receipt_id": "rcpt:G08",
    "flag_ids": [],
    "deduction_tag": "80D"
  },
  {
    "id": "je:0007",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-11-20",
    "narration": "Rajputana Hardware - receipt (Invoice: RH-1092)",
    "lines": [
      {
        "account_code": "5050-Hardware & Repairs Expense",
        "debit": "12000.00",
        "credit": "0.00"
      },
      {
        "account_code": "1010-Cash in Hand",
        "debit": "0.00",
        "credit": "12000.00"
      }
    ],
    "status": "COMMITTED",
    "source_receipt_id": "rcpt:G09",
    "flag_ids": [
      "flag:0001"
    ],
    "deduction_tag": null
  },
  {
    "id": "je:0008",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-12-02",
    "narration": "Metro Print House - gst_invoice (Invoice: INV-118)",
    "lines": [
      {
        "account_code": "5060-Printing Expense",
        "debit": "23600.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "23600.00"
      }
    ],
    "status": "COMMITTED",
    "source_receipt_id": "rcpt:G10",
    "flag_ids": [
      "flag:0003"
    ],
    "deduction_tag": null
  },
  {
    "id": "je:0009",
    "run_id": "run:2025-26-demo",
    "entry_date": "2026-01-15",
    "narration": "Bharat Life Insurance - premium_receipt (Invoice: BLI-99231)",
    "lines": [
      {
        "account_code": "5080-Insurance Expense",
        "debit": "30000.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "30000.00"
      }
    ],
    "status": "COMMITTED",
    "source_receipt_id": "rcpt:G11",
    "flag_ids": [],
    "deduction_tag": "80C"
  },
  {
    "id": "je:0010",
    "run_id": "run:2025-26-demo",
    "entry_date": "2026-01-22",
    "narration": "Sunrise Auto Care - gst_invoice (Invoice: INV-3307)",
    "lines": [
      {
        "account_code": "5070-Motor Vehicle Expense",
        "debit": "5900.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "5900.00"
      }
    ],
    "status": "COMMITTED",
    "source_receipt_id": "rcpt:G12",
    "flag_ids": [
      "flag:0006"
    ],
    "deduction_tag": null
  },
  {
    "id": "je:0011",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-12-18",
    "narration": "Local tea stall - receipt (Invoice: N/A)",
    "lines": [
      {
        "account_code": "5090-General / Petty Expense",
        "debit": "450.00",
        "credit": "0.00"
      },
      {
        "account_code": "1010-Cash in Hand",
        "debit": "0.00",
        "credit": "450.00"
      }
    ],
    "status": "COMMITTED",
    "source_receipt_id": "rcpt:G13",
    "flag_ids": [],
    "deduction_tag": null
  },
  {
    "id": "je:0012",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-11-05",
    "narration": "DeskCraft Furniture - gst_invoice (Invoice: INV-7710)",
    "lines": [
      {
        "account_code": "5050-Hardware & Repairs Expense",
        "debit": "3500.00",
        "credit": "0.00"
      },
      {
        "account_code": "1220-Input IGST",
        "debit": "630.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "4130.00"
      }
    ],
    "status": "COMMITTED",
    "source_receipt_id": "rcpt:G14",
    "flag_ids": [],
    "deduction_tag": null
  },
  {
    "id": "je:0013",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-12-03",
    "narration": "Aravali Stationers - gst_invoice (Invoice: INV-2102)",
    "lines": [
      {
        "account_code": "5000-Office & Stationery Expense",
        "debit": "6000.00",
        "credit": "0.00"
      },
      {
        "account_code": "1200-Input CGST",
        "debit": "540.00",
        "credit": "0.00"
      },
      {
        "account_code": "1210-Input SGST",
        "debit": "540.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "7080.00"
      }
    ],
    "status": "COMMITTED",
    "source_receipt_id": "rcpt:G15a",
    "flag_ids": [],
    "deduction_tag": null
  },
  {
    "id": "je:0014",
    "run_id": "run:2025-26-demo",
    "entry_date": "2025-12-05",
    "narration": "Aravali Stationers - gst_invoice (Invoice: INV-2105)",
    "lines": [
      {
        "account_code": "5000-Office & Stationery Expense",
        "debit": "6000.00",
        "credit": "0.00"
      },
      {
        "account_code": "1200-Input CGST",
        "debit": "540.00",
        "credit": "0.00"
      },
      {
        "account_code": "1210-Input SGST",
        "debit": "540.00",
        "credit": "0.00"
      },
      {
        "account_code": "1000-Bank",
        "debit": "0.00",
        "credit": "7080.00"
      }
    ],
    "status": "COMMITTED",
    "source_receipt_id": "rcpt:G15b",
    "flag_ids": [],
    "deduction_tag": null
  }
];

export const initialTrialBalance: TrialBalance = {
  "accounts": [
    {
      "account_code": "1000-Bank",
      "debit": "0.00",
      "credit": "119430.00"
    },
    {
      "account_code": "1010-Cash in Hand",
      "debit": "0.00",
      "credit": "12450.00"
    },
    {
      "account_code": "1200-Input CGST",
      "debit": "1995.24",
      "credit": "0.00"
    },
    {
      "account_code": "1210-Input SGST",
      "debit": "1995.24",
      "credit": "0.00"
    },
    {
      "account_code": "1220-Input IGST",
      "debit": "1530.00",
      "credit": "0.00"
    },
    {
      "account_code": "5000-Office & Stationery Expense",
      "debit": "22000.00",
      "credit": "0.00"
    },
    {
      "account_code": "5010-Fuel Expense",
      "debit": "3200.00",
      "credit": "0.00"
    },
    {
      "account_code": "5020-Software & IT Expense",
      "debit": "5000.00",
      "credit": "0.00"
    },
    {
      "account_code": "5030-Food & Beverage Expense",
      "debit": "2100.00",
      "credit": "0.00"
    },
    {
      "account_code": "5040-Travel & Cab Expense",
      "debit": "609.52",
      "credit": "0.00"
    },
    {
      "account_code": "5050-Hardware & Repairs Expense",
      "debit": "15500.00",
      "credit": "0.00"
    },
    {
      "account_code": "5060-Printing Expense",
      "debit": "23600.00",
      "credit": "0.00"
    },
    {
      "account_code": "5070-Motor Vehicle Expense",
      "debit": "5900.00",
      "credit": "0.00"
    },
    {
      "account_code": "5080-Insurance Expense",
      "debit": "48000.00",
      "credit": "0.00"
    },
    {
      "account_code": "5090-General / Petty Expense",
      "debit": "450.00",
      "credit": "0.00"
    }
  ],
  "total_debit": "131880.00",
  "total_credit": "131880.00",
  "balanced": true
};

export const initialPnL: PnL = {
  "income": {},
  "expenses": {
    "5000-Office & Stationery Expense": "22000.00",
    "5010-Fuel Expense": "3200.00",
    "5020-Software & IT Expense": "5000.00",
    "5030-Food & Beverage Expense": "2100.00",
    "5040-Travel & Cab Expense": "609.52",
    "5080-Insurance Expense": "48000.00",
    "5050-Hardware & Repairs Expense": "15500.00",
    "5060-Printing Expense": "23600.00",
    "5070-Motor Vehicle Expense": "5900.00",
    "5090-General / Petty Expense": "450.00"
  },
  "total_income": "0.00",
  "total_expenses": "126359.52",
  "net_profit": "-126359.52"
};

export const initialDeductions: DeductionSchedule = {
  "label": "Draft schedule",
  "regime": "ITA_1961",
  "tax_regime_choice": "old",
  "items": [
    {
      "section": "80C",
      "legal_ref": "s.80C",
      "claimed": "30000.00",
      "cap": "150000.00",
      "allowed": "30000.00",
      "excess": "0.00"
    },
    {
      "section": "80D",
      "legal_ref": "s.80D",
      "claimed": "18000.00",
      "cap": "25000.00",
      "allowed": "18000.00",
      "excess": "0.00"
    }
  ],
  "notes": [
    "Draft schedule (old regime only)."
  ]
};

export const initialITRDraft: ITRDraft = {
  "label": "Draft JSON in LedgerSense schema",
  "form": "ITR-3",
  "regime": "ITA_1961",
  "payload": {
    "draft_watermark": "DRAFT \u2014 FOR CA / AUDITOR REVIEW ONLY",
    "financial_year": "2025-26",
    "regime": "ITA_1961",
    "tax_regime_choice": "old",
    "total_income": "0.00",
    "total_expenses": "126359.52",
    "net_profit": "-126359.52",
    "expense_breakdown": {
      "5000-Office & Stationery Expense": "22000.00",
      "5010-Fuel Expense": "3200.00",
      "5020-Software & IT Expense": "5000.00",
      "5030-Food & Beverage Expense": "2100.00",
      "5040-Travel & Cab Expense": "609.52",
      "5080-Insurance Expense": "48000.00",
      "5050-Hardware & Repairs Expense": "15500.00",
      "5060-Printing Expense": "23600.00",
      "5070-Motor Vehicle Expense": "5900.00",
      "5090-General / Petty Expense": "450.00"
    },
    "pnl_summary": {
      "total_income": "0.00",
      "total_expenses": "126359.52",
      "net_profit": "-126359.52",
      "income_breakdown": {},
      "expense_breakdown": {
        "5000-Office & Stationery Expense": "22000.00",
        "5010-Fuel Expense": "3200.00",
        "5020-Software & IT Expense": "5000.00",
        "5030-Food & Beverage Expense": "2100.00",
        "5040-Travel & Cab Expense": "609.52",
        "5080-Insurance Expense": "48000.00",
        "5050-Hardware & Repairs Expense": "15500.00",
        "5060-Printing Expense": "23600.00",
        "5070-Motor Vehicle Expense": "5900.00",
        "5090-General / Petty Expense": "450.00"
      }
    },
    "deductions_summary": {
      "80C": {
        "section": "80C",
        "legal_ref": "s.80C",
        "claimed": "30000.00",
        "cap": "150000.00",
        "allowed": "30000.00",
        "excess": "0.00"
      },
      "80D": {
        "section": "80D",
        "legal_ref": "s.80D",
        "claimed": "18000.00",
        "cap": "25000.00",
        "allowed": "18000.00",
        "excess": "0.00"
      }
    },
    "deductions": {
      "80C": {
        "section": "80C",
        "legal_ref": "s.80C",
        "claimed": "30000.00",
        "cap": "150000.00",
        "allowed": "30000.00",
        "excess": "0.00"
      },
      "80D": {
        "section": "80D",
        "legal_ref": "s.80D",
        "claimed": "18000.00",
        "cap": "25000.00",
        "allowed": "18000.00",
        "excess": "0.00"
      }
    },
    "notes": [
      "Draft schedule (old regime only)."
    ]
  },
  "field_mapping_ref": "data/golden/field_mapping.csv"
};

export const initialAuditEvents: AuditEvent[] = [
  {
    "id": "evt:0001",
    "ts": "2026-03-31T09:00:00Z",
    "run_id": "run:2025-26-demo",
    "actor": "system",
    "action": "EXTRACTION",
    "entity_id": "run:2025-26-demo",
    "reason": "Extracted 16 receipts via Argon perception replay",
    "payload_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
  },
  {
    "id": "evt:0002",
    "ts": "2026-03-31T09:00:05Z",
    "run_id": "run:2025-26-demo",
    "actor": "system",
    "action": "STATE_CHANGE",
    "entity_id": "run:2025-26-demo",
    "reason": "Transition run from CREATED to EXTRACTED",
    "payload_hash": "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b"
  },
  {
    "id": "evt:0003",
    "ts": "2026-03-31T09:00:10Z",
    "run_id": "run:2025-26-demo",
    "actor": "system",
    "action": "STATE_CHANGE",
    "entity_id": "run:2025-26-demo",
    "reason": "Transition run from EXTRACTED to VALIDATED",
    "payload_hash": "2c26b46b68ffc68ff99b453c1d30413413422d706483bfa0f98a5e886266e7ae"
  },
  {
    "id": "evt:0004",
    "ts": "2026-03-31T09:00:15Z",
    "run_id": "run:2025-26-demo",
    "actor": "system",
    "action": "STATE_CHANGE",
    "entity_id": "run:2025-26-demo",
    "reason": "Transition run from VALIDATED to MATCHED",
    "payload_hash": "fcde2b2edba56bf408601fb721fe9b5c338d10ee429ea04fae5511b68fbf8fb9"
  },
  {
    "id": "evt:0005",
    "ts": "2026-03-31T09:00:20Z",
    "run_id": "run:2025-26-demo",
    "actor": "system",
    "action": "STATE_CHANGE",
    "entity_id": "run:2025-26-demo",
    "reason": "Transition run from MATCHED to RISK_DONE",
    "payload_hash": "7d1a54127b222502f5b79b5fb0803061152a44f92b37e23c65dd0e336d10e68f"
  },
  {
    "id": "evt:0006",
    "ts": "2026-03-31T09:00:25Z",
    "run_id": "run:2025-26-demo",
    "actor": "system",
    "action": "STATE_CHANGE",
    "entity_id": "run:2025-26-demo",
    "reason": "Transition run from RISK_DONE to AWAITING_REVIEW (4 open HIGH flags require auditor sign-off)",
    "payload_hash": "b45cffe084dd3d20d928bee85e7b0f21"
  }
];

export const initialEgress: EgressResponse = {
  "calls": 16,
  "bytes": 245000,
  "est_cost": "0.08",
  "entries": [
    {
      "id": "egress:001",
      "ts": "2026-03-31T09:00:01Z",
      "model": "argon-vision-v1 (Argon)",
      "bytes_sent": 15312,
      "est_cost": "0.005",
      "pii_masked": true,
      "doc_id": "rcpt:G01",
      "narration": "Visual perception extraction for receipts/g01_invoice_2041.png"
    },
    {
      "id": "egress:002",
      "ts": "2026-03-31T09:00:02Z",
      "model": "argon-vision-v1 (Argon)",
      "bytes_sent": 15312,
      "est_cost": "0.005",
      "pii_masked": true,
      "doc_id": "rcpt:G02",
      "narration": "Visual perception extraction for receipts/g02_fuel_7781.png"
    },
    {
      "id": "egress:003",
      "ts": "2026-03-31T09:00:03Z",
      "model": "argon-vision-v1 (Argon)",
      "bytes_sent": 15312,
      "est_cost": "0.005",
      "pii_masked": true,
      "doc_id": "rcpt:G03",
      "narration": "Visual perception extraction for receipts/g03_cloudnimbus.png"
    },
    {
      "id": "egress:004",
      "ts": "2026-03-31T09:00:04Z",
      "model": "argon-vision-v1 (Argon)",
      "bytes_sent": 15312,
      "est_cost": "0.005",
      "pii_masked": true,
      "doc_id": "rcpt:G04",
      "narration": "Visual perception extraction for receipts/g04_spice_route.png"
    },
    {
      "id": "egress:005",
      "ts": "2026-03-31T09:00:05Z",
      "model": "argon-vision-v1 (Argon)",
      "bytes_sent": 15312,
      "est_cost": "0.005",
      "pii_masked": true,
      "doc_id": "rcpt:G05",
      "narration": "Visual perception extraction for receipts/g05_quickcab.png"
    },
    {
      "id": "egress:006",
      "ts": "2026-03-31T09:00:06Z",
      "model": "argon-vision-v1 (Argon)",
      "bytes_sent": 15312,
      "est_cost": "0.005",
      "pii_masked": true,
      "doc_id": "rcpt:G06",
      "narration": "Visual perception extraction for receipts/g06_quickcab_duplicate.png"
    },
    {
      "id": "egress:007",
      "ts": "2026-03-31T09:00:07Z",
      "model": "argon-vision-v1 (Argon)",
      "bytes_sent": 15312,
      "est_cost": "0.005",
      "pii_masked": true,
      "doc_id": "rcpt:G07",
      "narration": "Visual perception extraction for receipts/g07_shield_health_apr.png"
    },
    {
      "id": "egress:008",
      "ts": "2026-03-31T09:00:08Z",
      "model": "argon-vision-v1 (Argon)",
      "bytes_sent": 15312,
      "est_cost": "0.005",
      "pii_masked": true,
      "doc_id": "rcpt:G08",
      "narration": "Visual perception extraction for receipts/g08_shield_health_feb.png"
    },
    {
      "id": "egress:009",
      "ts": "2026-03-31T09:00:09Z",
      "model": "argon-vision-v1 (Argon)",
      "bytes_sent": 15312,
      "est_cost": "0.005",
      "pii_masked": true,
      "doc_id": "rcpt:G09",
      "narration": "Visual perception extraction for receipts/g09_rajputana_hardware.png"
    },
    {
      "id": "egress:010",
      "ts": "2026-03-31T09:00:10Z",
      "model": "argon-vision-v1 (Argon)",
      "bytes_sent": 15312,
      "est_cost": "0.005",
      "pii_masked": true,
      "doc_id": "rcpt:G10",
      "narration": "Visual perception extraction for receipts/g10_metro_print_house.png"
    },
    {
      "id": "egress:011",
      "ts": "2026-03-31T09:00:11Z",
      "model": "argon-vision-v1 (Argon)",
      "bytes_sent": 15312,
      "est_cost": "0.005",
      "pii_masked": true,
      "doc_id": "rcpt:G11",
      "narration": "Visual perception extraction for receipts/g11_bharat_life.png"
    },
    {
      "id": "egress:012",
      "ts": "2026-03-31T09:00:12Z",
      "model": "argon-vision-v1 (Argon)",
      "bytes_sent": 15312,
      "est_cost": "0.005",
      "pii_masked": true,
      "doc_id": "rcpt:G12",
      "narration": "Visual perception extraction for receipts/g12_sunrise_auto.png"
    },
    {
      "id": "egress:013",
      "ts": "2026-03-31T09:00:13Z",
      "model": "argon-vision-v1 (Argon)",
      "bytes_sent": 15312,
      "est_cost": "0.005",
      "pii_masked": true,
      "doc_id": "rcpt:G13",
      "narration": "Visual perception extraction for receipts/g13_local_tea_stall.png"
    },
    {
      "id": "egress:014",
      "ts": "2026-03-31T09:00:14Z",
      "model": "argon-vision-v1 (Argon)",
      "bytes_sent": 15312,
      "est_cost": "0.005",
      "pii_masked": true,
      "doc_id": "rcpt:G14",
      "narration": "Visual perception extraction for receipts/g14_deskcraft_furniture.png"
    },
    {
      "id": "egress:015",
      "ts": "2026-03-31T09:00:15Z",
      "model": "argon-vision-v1 (Argon)",
      "bytes_sent": 15312,
      "est_cost": "0.005",
      "pii_masked": true,
      "doc_id": "rcpt:G15a",
      "narration": "Visual perception extraction for receipts/g15a_aravali_inv2102.png"
    },
    {
      "id": "egress:016",
      "ts": "2026-03-31T09:00:16Z",
      "model": "argon-vision-v1 (Argon)",
      "bytes_sent": 15312,
      "est_cost": "0.005",
      "pii_masked": true,
      "doc_id": "rcpt:G15b",
      "narration": "Visual perception extraction for receipts/g15b_aravali_inv2105.png"
    }
  ]
};
