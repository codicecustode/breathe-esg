import json
from datetime import datetime

from ..emission_factors import TRAVEL_FACTORS, haversine_km
from ..models import ImportJob, NormalizedEmissionRecord, RawRecord

CABIN_TO_FACTOR_KEY = {
    'ECONOMY':  'economy_flight',
    'ECONOMY+': 'economy_flight',
    'PREMIUM':  'business_flight',
    'BUSINESS': 'business_flight',
    'FIRST':    'first_flight',
}


def _parse_date(s: str):
    if not s:
        return None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%d-%m-%Y', '%d-%b-%Y'):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except ValueError:
            continue
    return None


def _process_airfare(entry, import_job, tenant, raw_record, success_count, errors, line_label):
    count = 0
    for seg in entry.get('AirSegments', []):
        dep = (seg.get('DepartureCity') or '').upper().strip()
        arr = (seg.get('ArrivalCity') or '').upper().strip()
        flight_no = seg.get('FlightNumber', '')
        cabin = (seg.get('CabinClass') or 'ECONOMY').upper().strip()
        dep_date = _parse_date(seg.get('DepartureDate', ''))

        distance_km = None
        dist_raw = seg.get('Distance')
        dist_unit = (seg.get('DistanceUnit') or 'KM').upper()
        if dist_raw:
            try:
                distance_km = float(dist_raw)
                if dist_unit == 'MI':
                    distance_km *= 1.60934
            except (ValueError, TypeError):
                pass
        if not distance_km:
            distance_km = haversine_km(dep, arr)

        factor_key = CABIN_TO_FACTOR_KEY.get(cabin, 'economy_flight')
        ef_value, ef_unit, scope, ef_source = TRAVEL_FACTORS[factor_key]

        suspicious = False
        suspicious_reason = ''
        if not distance_km or distance_km <= 0:
            suspicious = True
            suspicious_reason = f'Could not determine flight distance ({dep}→{arr}); unknown IATA codes'
            distance_km = 0
        elif distance_km > 16000:
            suspicious = True
            suspicious_reason = f'Unusually long route: {distance_km:.0f} km ({dep}→{arr})'

        NormalizedEmissionRecord.objects.create(
            tenant=tenant,
            raw_record=raw_record,
            source_type='TRAVEL',
            activity_type=f'Air travel {dep}→{arr} ({flight_no}, {cabin})',
            quantity=distance_km or 0,
            normalized_unit='km',
            scope=scope,
            emission_factor=ef_value,
            calculated_emissions=round((distance_km or 0) * ef_value, 4),
            suspicious=suspicious,
            suspicious_reason=suspicious_reason if suspicious else None,
            review_status='PENDING',
            date=dep_date,
            source_metadata={
                'report_key': entry.get('_report_key', ''),
                'entry_id': entry.get('EntryID', ''),
                'cabin_class': cabin,
                'flight_number': flight_no,
                'dep_airport': dep,
                'arr_airport': arr,
                'distance_source': 'provided' if seg.get('Distance') else 'haversine',
                'ef_source': ef_source,
            },
        )
        count += 1
    return count


def _process_hotel(entry, import_job, tenant, raw_record, errors, line_label):
    count = 0
    for h in entry.get('HotelEntries', []):
        city = h.get('City', 'Unknown')
        hotel_name = h.get('HotelName', 'Unknown Hotel')
        check_in = _parse_date(h.get('CheckInDate', ''))
        check_out = _parse_date(h.get('CheckOutDate', ''))
        nights = h.get('NumNights')
        if nights is None and check_in and check_out:
            nights = (check_out - check_in).days
        if not nights:
            errors.append(f'{line_label}: cannot determine nights for hotel {hotel_name}')
            continue

        ef_value, ef_unit, scope, ef_source = TRAVEL_FACTORS['hotel']

        NormalizedEmissionRecord.objects.create(
            tenant=tenant,
            raw_record=raw_record,
            source_type='TRAVEL',
            activity_type=f'Hotel stay - {city} ({hotel_name}, {nights} nights)',
            quantity=nights,
            normalized_unit='room-nights',
            scope=scope,
            emission_factor=ef_value,
            calculated_emissions=round(nights * ef_value, 4),
            suspicious=False,
            review_status='PENDING',
            date=check_in,
            source_metadata={
                'hotel_name': hotel_name,
                'city': city,
                'check_in': str(check_in) if check_in else '',
                'check_out': str(check_out) if check_out else '',
                'ef_source': ef_source,
            },
        )
        count += 1
    return count


def _process_carrental(entry, import_job, tenant, raw_record, errors, line_label):
    cr = entry.get('CarRentalDetails', {})
    city = cr.get('PickupCity', 'Unknown')
    vehicle_class = cr.get('VehicleClass', 'UNKNOWN')
    pickup = _parse_date(cr.get('PickupDate', ''))
    dropoff = _parse_date(cr.get('DropoffDate', ''))

    rental_days = cr.get('RentalDays')
    if rental_days is None and pickup and dropoff:
        rental_days = max((dropoff - pickup).days, 1)
    if not rental_days:
        rental_days = 1

    est_km = cr.get('EstimatedKm')
    estimated = False
    if est_km:
        try:
            km = float(est_km)
        except (ValueError, TypeError):
            km = rental_days * 100
            estimated = True
    else:
        km = rental_days * 100
        estimated = True

    ef_value, ef_unit, scope, ef_source = TRAVEL_FACTORS['car_rental']

    NormalizedEmissionRecord.objects.create(
        tenant=tenant,
        raw_record=raw_record,
        source_type='TRAVEL',
        activity_type=f'Car rental - {city} ({vehicle_class}, {rental_days}d, {"est." if estimated else ""} {km:.0f} km)',
        quantity=km,
        normalized_unit='km',
        scope=scope,
        emission_factor=ef_value,
        calculated_emissions=round(km * ef_value, 4),
        suspicious=estimated,
        suspicious_reason='Distance estimated at 100 km/day — actual odometer not provided' if estimated else None,
        review_status='PENDING',
        date=pickup,
        source_metadata={
            'vehicle_class': vehicle_class,
            'pickup_city': city,
            'rental_days': rental_days,
            'distance_estimated': estimated,
            'ef_source': ef_source,
        },
    )
    return 1


def parse_travel_json(file_obj, import_job: ImportJob, tenant):
    try:
        raw_bytes = file_obj.read() if hasattr(file_obj, 'read') else file_obj
        data = json.loads(raw_bytes.decode('utf-8') if isinstance(raw_bytes, bytes) else raw_bytes)
    except Exception as exc:
        return 0, 1, [f'JSON parse error: {exc}']

    reports = data.get('Reports', [data] if 'Entries' in data else [])
    success, errors = 0, []

    for report in reports:
        report_key = report.get('ReportKey', '')
        for entry in report.get('Entries', []):
            entry['_report_key'] = report_key
            entry_id = entry.get('EntryID', 'unknown')
            entry_type = (entry.get('EntryType') or '').upper()
            line_label = f'Entry {entry_id} ({entry_type})'

            raw_record = RawRecord.objects.create(import_job=import_job, raw_data=entry)

            try:
                if entry_type == 'AIRFARE':
                    success += _process_airfare(entry, import_job, tenant, raw_record, success, errors, line_label)
                elif entry_type == 'HOTEL':
                    success += _process_hotel(entry, import_job, tenant, raw_record, errors, line_label)
                elif entry_type in ('CARRENTAL', 'CAR_RENTAL', 'CAR RENTAL'):
                    success += _process_carrental(entry, import_job, tenant, raw_record, errors, line_label)
                else:
                    errors.append(f'{line_label}: unknown entry type, skipped')
            except Exception as exc:
                errors.append(f'{line_label}: {exc}')

    return success, len(errors), errors
