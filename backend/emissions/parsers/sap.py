import csv
import io
from datetime import date, datetime

from ..emission_factors import get_fuel_factor
from ..models import ImportJob, NormalizedEmissionRecord, RawRecord

COLUMN_MAP = {
    'Belegnummer':         'doc_number',
    'Belegdatum':          'doc_date',
    'Buchungsdatum':       'posting_date',
    'Materialbezeichnung': 'material_desc',
    'Materialnummer':      'material_number',
    'Menge':               'quantity',
    'Einheit':             'unit',
    'Betrag':              'amount',
    'Werksplatz':          'plant',
    'Lagerort':            'storage_location',
    'Lieferant':           'vendor',
    'doc_number':          'doc_number',
    'doc_date':            'doc_date',
    'posting_date':        'posting_date',
    'material_desc':       'material_desc',
    'material_number':     'material_number',
    'quantity':            'quantity',
    'unit':                'unit',
    'amount':              'amount',
    'plant':               'plant',
    'storage_location':    'storage_location',
    'vendor':              'vendor',
}

SAP_UNIT_TO_STANDARD = {
    'L':   'L',
    'LT':  'L',
    'KG':  'kg',
    'M3':  'm3',
    'M³':  'm3',
    'TON': 't',
    'TO':  't',
    'ST':  'unit',
    'KWH': 'kWh',
}


def _parse_date(s: str):
    if not s:
        return None
    s = s.strip()
    for fmt in ('%Y%m%d', '%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _map_row(row: dict) -> dict:
    mapped = {}
    for key, val in row.items():
        internal = COLUMN_MAP.get(key.strip()) or COLUMN_MAP.get(key.strip().lower())
        if internal:
            mapped[internal] = val.strip() if isinstance(val, str) else val
        else:
            mapped[key.strip()] = val.strip() if isinstance(val, str) else val
    return mapped


def parse_sap_csv(file_obj, import_job: ImportJob, tenant):
    raw_bytes = file_obj.read()
    for enc in ('utf-8-sig', 'utf-8', 'latin-1', 'cp1252'):
        try:
            text = raw_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        return 0, 1, ['Could not decode file']

    sample = text[:2048]
    delimiter = ';' if sample.count(';') > sample.count(',') else ','

    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    success, errors = 0, []

    for line_no, raw_row in enumerate(reader, start=2):
        try:
            row = _map_row(raw_row)
            raw_dict = dict(raw_row)

            material_desc = row.get('material_desc', '')
            factor_tuple = get_fuel_factor(material_desc)
            if not factor_tuple:
                continue

            ef_value, ef_unit, scope, ef_source = factor_tuple

            try:
                qty = float(str(row.get('quantity', '0')).replace(',', '.'))
            except ValueError:
                errors.append(f'Row {line_no}: bad quantity "{row.get("quantity")}"')
                continue

            raw_unit = str(row.get('unit', '')).upper().strip()
            std_unit = SAP_UNIT_TO_STANDARD.get(raw_unit, raw_unit)
            doc_date = _parse_date(row.get('doc_date', ''))
            calculated = round(qty * ef_value, 4)

            suspicious = False
            suspicious_reason = ''
            if qty <= 0:
                suspicious = True
                suspicious_reason = 'Non-positive quantity'
            elif qty > 50000:
                suspicious = True
                suspicious_reason = f'Unusually large single-purchase quantity: {qty} {std_unit}'
            elif doc_date and doc_date > date.today():
                suspicious = True
                suspicious_reason = f'Future document date: {doc_date}'

            raw_record = RawRecord.objects.create(import_job=import_job, raw_data=raw_dict)

            NormalizedEmissionRecord.objects.create(
                tenant=tenant,
                raw_record=raw_record,
                source_type='SAP',
                activity_type=f"{material_desc} ({row.get('plant', 'unknown plant')})",
                quantity=qty,
                normalized_unit=std_unit,
                scope=scope,
                emission_factor=ef_value,
                calculated_emissions=calculated,
                suspicious=suspicious,
                suspicious_reason=suspicious_reason if suspicious else None,
                review_status='PENDING',
                date=doc_date,
                source_metadata={
                    'doc_number': row.get('doc_number', ''),
                    'material_number': row.get('material_number', ''),
                    'plant': row.get('plant', ''),
                    'vendor': row.get('vendor', ''),
                    'ef_source': ef_source,
                    'raw_unit': raw_unit,
                },
            )
            success += 1
        except Exception as exc:
            errors.append(f'Row {line_no}: {exc}')

    return success, len(errors), errors
