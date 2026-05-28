import csv
import io
from datetime import datetime

from ..emission_factors import ELECTRICITY_FACTOR
from ..models import ImportJob, NormalizedEmissionRecord, RawRecord

COLUMN_ALIASES = {
    'meter_id':        ['meter id', 'meter no', 'meter number', 'consumer no', 'consumer number',
                        'account no', 'account number', 'meter_id'],
    'bill_date':       ['bill date', 'billing date', 'invoice date', 'bill_date'],
    'period_start':    ['billing period start', 'from date', 'period from', 'reading from',
                        'meter reading from', 'period_start', 'from'],
    'period_end':      ['billing period end', 'to date', 'period to', 'reading to',
                        'meter reading to', 'period_end', 'to'],
    'opening_reading': ['opening reading', 'previous reading', 'opening (kwh)', 'prev reading',
                        'previous (kwh)', 'opening_reading'],
    'closing_reading': ['closing reading', 'current reading', 'closing (kwh)', 'curr reading',
                        'current (kwh)', 'closing_reading'],
    'total_units':     ['total units', 'units consumed', 'consumption (kwh)', 'kwh consumed',
                        'units (kwh)', 'net units', 'total_units', 'energy consumed (kwh)',
                        'consumption'],
    'tariff_code':     ['tariff code', 'tariff', 'category', 'consumer category', 'tariff_code',
                        'lt/ht', 'voltage'],
    'amount':          ['amount', 'amount due', 'bill amount', 'total amount (inr)', 'net payable',
                        'net amount', 'total bill amount'],
}


def _build_alias_map(headers: list) -> dict:
    lower_headers = {h.lower().strip(): h for h in headers}
    result = {}
    for internal, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in lower_headers:
                result[internal] = lower_headers[alias]
                break
    return result


def parse_date_flexible(s: str):
    if not s:
        return None
    s = s.strip()
    for fmt in ('%d-%b-%Y', '%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y', '%d.%m.%Y',
                '%b %d, %Y', '%B %d, %Y', '%d %b %Y'):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_utility_csv(file_obj, import_job: ImportJob, tenant):
    raw_bytes = file_obj.read()
    for enc in ('utf-8-sig', 'utf-8', 'latin-1'):
        try:
            text = raw_bytes.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        return 0, 1, ['Could not decode file']

    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        return 0, 1, ['Empty or header-less CSV']

    alias_map = _build_alias_map(reader.fieldnames)
    ef_value, ef_unit, scope, ef_source = ELECTRICITY_FACTOR
    success, errors = 0, []

    for line_no, raw_row in enumerate(reader, start=2):
        try:
            raw_dict = dict(raw_row)

            def get(key):
                col = alias_map.get(key)
                return raw_row.get(col, '').strip() if col else ''

            meter_id = get('meter_id') or f'METER-{line_no}'
            tariff = get('tariff_code') or 'UNKNOWN'

            total_str = get('total_units')
            opening_str = get('opening_reading')
            closing_str = get('closing_reading')

            kwh = None
            if total_str:
                try:
                    kwh = float(total_str.replace(',', ''))
                except ValueError:
                    pass
            if kwh is None and opening_str and closing_str:
                try:
                    kwh = float(closing_str.replace(',', '')) - float(opening_str.replace(',', ''))
                except ValueError:
                    pass
            if kwh is None:
                errors.append(f'Row {line_no}: cannot determine kWh consumption')
                continue

            period_start = parse_date_flexible(get('period_start'))
            period_end = parse_date_flexible(get('period_end'))

            days = None
            if period_start and period_end:
                days = (period_end - period_start).days

            suspicious = False
            suspicious_reason = ''
            if kwh <= 0:
                suspicious = True
                suspicious_reason = 'Non-positive consumption'
            elif period_end and period_start and period_end < period_start:
                suspicious = True
                suspicious_reason = 'Period end is before period start'
            elif days and days > 0 and (kwh / days) > 5000:
                suspicious = True
                suspicious_reason = f'Daily consumption {kwh/days:.0f} kWh exceeds 5000 kWh threshold'

            calculated = round(kwh * ef_value, 4)
            raw_record = RawRecord.objects.create(import_job=import_job, raw_data=raw_dict)

            NormalizedEmissionRecord.objects.create(
                tenant=tenant,
                raw_record=raw_record,
                source_type='UTILITY',
                activity_type=f'Electricity consumption - {meter_id}',
                quantity=kwh,
                normalized_unit='kWh',
                scope=scope,
                emission_factor=ef_value,
                calculated_emissions=calculated,
                suspicious=suspicious,
                suspicious_reason=suspicious_reason if suspicious else None,
                review_status='PENDING',
                period_start=period_start,
                period_end=period_end,
                source_metadata={
                    'meter_id': meter_id,
                    'tariff_code': tariff,
                    'opening_reading': opening_str,
                    'closing_reading': closing_str,
                    'ef_source': ef_source,
                },
            )
            success += 1
        except Exception as exc:
            errors.append(f'Row {line_no}: {exc}')

    return success, len(errors), errors
