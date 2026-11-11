"""Deterministic synthetic data for the fictional smart city of Mji Mpya.

Everything is drawn from one seeded RNG, so the same seed and scale always
produce byte-identical Parquet files. District affluence is the hidden variable
that ties the domains together: it shapes income, housing, car ownership,
transit use, amenities (pools and gyms cluster in rich districts) and so on.
"""

import math
import random
from datetime import date, datetime, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from .catalog import BY_SLUG

END = datetime(2026, 11, 1)
DAYS = 30
CENTRE = (-1.2921, 36.8219)

# name, affluence 0..1, (lat offset, lon offset), population weight
DISTRICTS = [
    ("Kilele Heights", 0.92, (0.030, -0.040), 0.6),
    ("Ziwa Lakeside", 0.85, (-0.035, -0.030), 0.6),
    ("Nyota Tech Park", 0.75, (0.020, 0.035), 0.7),
    ("Bustani Gardens", 0.68, (0.045, 0.010), 0.8),
    ("Soko Central", 0.55, (0.000, 0.000), 1.2),
    ("Upepo Ridge", 0.50, (0.055, -0.010), 0.8),
    ("Kisima Old Town", 0.40, (-0.010, 0.020), 1.1),
    ("Bandari Port", 0.35, (-0.045, 0.045), 1.0),
    ("Msitu Greens", 0.45, (0.010, -0.060), 0.7),
    ("Mto Riverside", 0.28, (-0.025, 0.060), 1.3),
    ("Mawe Industrial", 0.22, (-0.060, 0.010), 1.0),
    ("Jua Plains", 0.18, (-0.050, -0.055), 1.4),
]
AFFLUENCE = {d[0]: d[1] for d in DISTRICTS}
OFFSET = {d[0]: d[2] for d in DISTRICTS}

FIRST_NAMES = [
    "Amani", "Baraka", "Wanjiru", "Achieng", "Kamau", "Otieno", "Njeri", "Mwangi", "Akinyi",
    "Kiprono", "Chebet", "Wafula", "Nafula", "Mutua", "Mumbua", "Omondi", "Atieno", "Kipchoge",
    "Jelagat", "Kariuki", "Wairimu", "Ochieng", "Adhiambo", "Muthoni", "Juma", "Zawadi", "Imani",
    "Neema", "Faraji", "Halima", "Hassan", "Fatuma", "Ali", "Aisha", "Daniel", "Grace", "Brian",
    "Faith", "Kevin", "Mercy", "Dennis", "Joy", "Victor", "Esther", "Collins", "Sharon", "Ian",
    "Purity", "Samuel", "Ruth", "Peter", "Mary", "Liam", "Sofia", "Arjun", "Priya", "Chen", "Mei",
    "Mateo", "Lucia",
]
LAST_NAMES = [
    "Kamau", "Odhiambo", "Wanjala", "Mwangi", "Otieno", "Kiplagat", "Njoroge", "Ochieng",
    "Mutua", "Wekesa", "Kiprotich", "Achieng", "Omondi", "Kariuki", "Nyambane", "Onyango",
    "Chege", "Barasa", "Keter", "Muriuki", "Gitau", "Owino", "Ndungu", "Korir", "Waweru",
    "Okoth", "Mohamed", "Abdi", "Hussein", "Said", "Mbugua", "Kibet", "Rotich", "Ngugi",
    "Langat", "Maina", "Atieno", "Musyoka", "Nzioka", "Kilonzo", "Patel", "Shah", "Wang",
    "Garcia", "Okafor", "Mensah", "Haile", "Mbeki", "Tembo", "Banda",
]
STREETS = [
    "Mvule", "Mugumo", "Jacaranda", "Baobab", "Mwembe", "Mnazi", "Msonobari", "Mkuyu",
    "Mwarubaini", "Mninga", "Muhuhu", "Mpingo", "Mkomamanga", "Mchungwa", "Mkaratusi", "Mitende",
]
STREET_SUFFIX = ["Lane", "Road", "Avenue", "Close", "Drive", "Crescent", "Way"]
DWELLINGS_RICH = ["apartment", "maisonette", "bungalow", "townhouse"]
DWELLINGS_POOR = ["apartment", "informal", "bedsitter", "apartment"]
OCC_RICH = ["software engineer", "doctor", "lawyer", "architect", "banker", "consultant", "lecturer"]
OCC_MID = ["teacher", "nurse", "civil servant", "accountant", "police officer", "technician", "trader"]
OCC_LOW = ["casual labourer", "boda boda rider", "market vendor", "driver", "security guard", "artisan", "domestic worker"]
EDUCATION = ["primary", "secondary", "diploma", "bachelor's", "master's", "doctorate"]
INCOME = ["< 20k", "20k–50k", "50k–100k", "100k–250k", "> 250k"]
DISABILITIES = ["wheelchair user", "visual impairment", "hearing impairment", "mobility aid", "cognitive"]
FACILITIES = [
    "Mji Mpya General Hospital", "Ziwa Women's Hospital", "Jua Plains Health Centre",
    "Bandari Port Clinic", "Kilele Private Hospital", "Mto Riverside Dispensary",
]
DIAGNOSES = [
    ("J06.9", "Upper respiratory infection", "Outpatient", 0),
    ("B54", "Malaria", "Internal medicine", 2),
    ("A09", "Gastroenteritis", "Outpatient", 1),
    ("I10", "Hypertension", "Cardiology", 0),
    ("E11.9", "Type 2 diabetes", "Internal medicine", 0),
    ("S52.5", "Fractured radius", "Orthopaedics", 2),
    ("O80", "Normal delivery", "Maternity", 2),
    ("J45.9", "Asthma attack", "Emergency", 1),
    ("S06.0", "Concussion", "Emergency", 3),
    ("T30.0", "Burns", "Emergency", 4),
    ("F32.9", "Depressive episode", "Psychiatry", 0),
    ("I21.9", "Myocardial infarction", "Cardiology", 7),
    ("N39.0", "Urinary tract infection", "Outpatient", 0),
    ("U07.1", "COVID-19", "Internal medicine", 4),
]
BLOOD = ["O+", "O+", "O+", "A+", "A+", "B+", "B+", "AB+", "O-", "A-", "B-", "AB-"]
ALLERGIES = ["penicillin", "sulfa drugs", "peanuts", "latex", "shellfish", "aspirin", "pollen"]
CHRONIC = ["hypertension", "type 2 diabetes", "asthma", "sickle cell disease", "HIV (managed)", "epilepsy", "CKD"]
ROUTES = {
    "BRT-1": ("brt", ["Jua Plains Terminus", "Mawe Junction", "Soko Central", "Nyota Tech Park", "Kilele Gate"]),
    "BRT-2": ("brt", ["Bandari Port", "Kisima Old Town", "Soko Central", "Bustani Gardens", "Upepo Ridge"]),
    "LRT-A": ("light_rail", ["Mto Riverside", "Kisima Old Town", "Soko Central", "Ziwa Lakeside"]),
    "BUS-14": ("bus", ["Jua Plains Market", "Msitu Greens", "Soko Central", "Ziwa Mall"]),
    "BUS-23": ("bus", ["Mawe Industrial", "Bandari Port", "Mto Riverside", "Soko Central"]),
    "MAT-46": ("matatu", ["Jua Plains Market", "Mto Riverside", "Kisima Old Town", "Soko Central"]),
    "MAT-58": ("matatu", ["Mawe Industrial", "Jua Plains Terminus", "Msitu Greens"]),
}
FARES = {"brt": 80, "light_rail": 100, "bus": 60, "matatu": 50}
CARS = ["Toyota Axio", "Toyota Probox", "Mazda Demio", "Subaru Forester", "Toyota Prado",
        "Nissan Note", "Honda Fit", "Mercedes C200", "VW Golf", "BYD Atto 3", "Isuzu D-Max"]
COLOURS = ["white", "silver", "black", "grey", "blue", "red", "maroon"]
FELONIES = ["robbery with violence", "burglary", "fraud", "assault causing harm", "drug trafficking",
            "carjacking", "cybercrime", "arson", "manslaughter", "embezzlement"]
FELONY_STATUS = ["under investigation", "charged", "convicted", "acquitted"]
COURTS = ["Mji Mpya High Court", "Soko Law Courts", "Bandari Magistrates' Court"]
INFRACTIONS = [
    ("speeding", 5000, True), ("illegal parking", 2000, True), ("running red light", 3000, True),
    ("no seatbelt", 1000, True), ("littering", 1500, False), ("noise nuisance", 2500, False),
    ("public drinking", 2000, False), ("jaywalking", 500, False), ("unlicensed hawking", 1000, False),
]
RELATIONS = ["spouse", "sibling", "parent", "friend", "coworker", "neighbour"]
FREQ = ["daily", "weekly", "monthly", "rarely"]
AMENITIES_RICH = ["swimming_pool", "gym", "tennis_court", "ev_charger", "coworking_space"]
AMENITIES_ALL = ["clinic", "school", "park", "playground", "library", "market", "police_post",
                 "fire_station", "community_hall", "water_kiosk"]
CONDITION = ["excellent", "good", "fair", "poor"]
ASSETS = ["bridge", "road_segment", "water_main", "sewer", "streetlight", "substation", "culvert"]
CONTRACTORS = ["Imara Civil Works", "Daraja Engineering", "Mawe Contractors", "Nuru Electrical", "Maji Utilities"]
TOPICS = {
    "roads": ["The potholes on {s} Road are damaging vehicles, please resurface.",
              "Add speed bumps near the school on {s} Avenue."],
    "water": ["Water rationing in {d} has lasted three weeks.", "Burst pipe on {s} Lane wasting water since Monday."],
    "safety": ["Streetlights on {s} Close are out, it is unsafe at night.", "More patrols needed around {d} market."],
    "health": ["The clinic in {d} needs longer opening hours.", "Ambulance response in {d} is too slow."],
    "transport": ["Add more buses on the {r} route during rush hour.", "Make {r} stops wheelchair accessible."],
    "housing": ["Rents in {d} are rising faster than incomes.", "Affordable housing plan for {d} please."],
    "environment": ["Plant trees along {s} Drive, it is very hot in afternoons.", "Garbage collection in {d} is irregular."],
    "governance": ["The permit portal times out when paying.", "Publish the {d} ward budget online."],
}
CHANNELS = ["mobile_app", "web_portal", "ussd", "kiosk", "town_hall"]
HAZARDS = [("flood", "Kenya Meteorological Dept"), ("fire", "City Fire & Rescue"), ("heatwave", "Kenya Meteorological Dept"),
           ("gas_leak", "City Fire & Rescue"), ("building_collapse", "Disaster Mgmt Unit"),
           ("air_quality", "Environment Authority"), ("landslide", "Disaster Mgmt Unit")]
SEVERITY = ["advisory", "watch", "warning", "emergency"]
SERVICES = ["business permit", "land rates", "parking fees", "birth certificate", "building approval",
            "liquor licence", "waste collection", "rent tax"]
DEVICES = ["android", "ios", "desktop", "ussd"]


class Gen:
    def __init__(self, seed: int, scale: float):
        self.r = random.Random(seed)
        self.scale = scale

    def n(self, base: int) -> int:
        return max(10, int(base * self.scale))

    def when(self, days: int = DAYS, peak: bool = False) -> datetime:
        day = self.r.randrange(days)
        if peak and self.r.random() < 0.6:
            hour = self.r.choice([6, 7, 7, 8, 8, 17, 17, 18, 18, 19])
        else:
            hour = self.r.randrange(24)
        return END - timedelta(days=day + 1) + timedelta(hours=hour, minutes=self.r.randrange(60), seconds=self.r.randrange(60))

    def district(self) -> str:
        return self.r.choices([d[0] for d in DISTRICTS], weights=[d[3] for d in DISTRICTS])[0]

    def point(self, district: str, spread: float = 0.007) -> tuple[float, float]:
        dlat, dlon = OFFSET[district]
        return (
            round(CENTRE[0] + dlat + self.r.gauss(0, spread), 6),
            round(CENTRE[1] + dlon + self.r.gauss(0, spread), 6),
        )

    def phone(self) -> str:
        return f"+2547{self.r.randrange(10_000_000, 99_999_999)}"

    def by_affluence(self, district: str, rich: list, mid: list, poor: list):
        a = AFFLUENCE[district] + self.r.gauss(0, 0.15)
        return self.r.choice(rich if a > 0.7 else mid if a > 0.4 else poor)


def _table(slug: str, rows: list[dict]) -> pa.Table:
    types = {"VARCHAR": pa.string(), "DOUBLE": pa.float64(), "INTEGER": pa.int32(),
             "DATE": pa.date32(), "TIMESTAMP": pa.timestamp("us"), "BOOLEAN": pa.bool_()}
    ds = BY_SLUG[slug]
    schema = pa.schema([(c.name, types[c.type]) for c in ds.columns])
    return pa.Table.from_pylist(rows, schema=schema)


def generate(out_dir: Path, seed: int = 4030, scale: float = 1.0) -> dict[str, int]:
    g = Gen(seed, scale)
    r = g.r
    out: dict[str, list[dict]] = {}

    # ── residences ──────────────────────────────────────────
    residences = []
    building_seq = 0
    current_building: dict[str, tuple[str, int]] = {}
    for i in range(g.n(1800)):
        d = g.district()
        rich = AFFLUENCE[d] > 0.6
        dwelling = r.choice(DWELLINGS_RICH if rich else DWELLINGS_POOR)
        building = None
        floor = 0
        if dwelling in {"apartment", "bedsitter"}:
            b = current_building.get(d)
            if not b or b[1] <= 0:
                building_seq += 1
                b = (f"BLD-{building_seq:04d}", r.randint(8, 30))
            current_building[d] = (b[0], b[1] - 1)
            building = b[0]
            floor = r.randint(0, 14 if rich else 6)
        lat, lon = g.point(d)
        rent_base = 8000 + AFFLUENCE[d] ** 2 * 180_000
        residences.append({
            "residence_id": f"RES-{i + 1:05d}",
            "address": f"{r.randint(1, 240)} {r.choice(STREETS)} {r.choice(STREET_SUFFIX)}",
            "district": d,
            "lat": lat,
            "lon": lon,
            "dwelling_type": dwelling,
            "building_id": building,
            "floor": floor,
            "occupants": r.randint(1, 4 if rich else 7),
            "monthly_rent_kes": int(round(rent_base * r.uniform(0.6, 1.5), -2)),
            "access_notes": r.choice([
                None, None, f"Gate code {r.randint(1000, 9999)}", "Ask caretaker at Block B",
                "Ramp at side entrance", "Dog on premises", "Narrow stairs, no lift", "Use back gate after 10pm",
            ]),
        })
    out["residences"] = residences

    # ── citizens ────────────────────────────────────────────
    citizens = []
    for i in range(g.n(5000)):
        home = r.choice(residences)
        d = home["district"]
        a = AFFLUENCE[d]
        age = min(95, max(0, int(r.gauss(32, 17))))
        dob = date(2026, 11, 1) - timedelta(days=age * 365 + r.randrange(365))
        first, last = r.choice(FIRST_NAMES), r.choice(LAST_NAMES)
        if age < 18:
            occupation, edu = "student", r.choice(EDUCATION[:2])
        elif age > 65:
            occupation, edu = "retired", r.choice(EDUCATION[:4])
        else:
            occupation = g.by_affluence(d, OCC_RICH, OCC_MID, OCC_LOW)
            edu_idx = min(5, max(0, int(r.gauss(1 + a * 3.5, 1))))
            edu = EDUCATION[edu_idx]
        inc_idx = min(4, max(0, int(r.gauss(a * 4.2, 0.8))))
        citizens.append({
            "citizen_id": f"CIT-{i + 1:06d}",
            "national_id": str(r.randrange(10_000_000, 39_999_999)),
            "ssn": f"{r.randrange(100, 999)}-{r.randrange(10, 99)}-{r.randrange(1000, 9999)}",
            "first_name": first,
            "last_name": last,
            "date_of_birth": dob,
            "sex": r.choice(["female", "male"]) if r.random() > 0.004 else "intersex",
            "phone": g.phone(),
            "email": f"{first.lower()}.{last.lower()}{r.randrange(1, 999)}@{r.choice(['mail.ke', 'post.co.ke', 'inbox.africa', 'gmail.com'])}",
            "occupation": occupation,
            "education": edu,
            "income_band": INCOME[inc_idx],
            "disability": r.choice(DISABILITIES) if r.random() < 0.07 + (0.08 if age > 70 else 0) else "none",
            "residence_id": home["residence_id"],
            "district": d,
            "registered_at": END - timedelta(days=r.randrange(30, 3650), hours=r.randrange(24)),
        })
    out["citizens"] = citizens
    adults = [c for c in citizens if c["date_of_birth"] < date(2008, 11, 1)]
    blood = {c["citizen_id"]: r.choice(BLOOD) for c in citizens}

    # ── medical_records ─────────────────────────────────────
    med = []
    for i in range(g.n(6000)):
        c = r.choice(citizens)
        code, diag, dept, base_los = r.choice(DIAGNOSES)
        sev = r.choices(["low", "moderate", "high", "critical"], weights=[50, 30, 15, 5])[0]
        if base_los >= 4:
            sev = r.choice(["high", "critical"])
        med.append({
            "record_id": f"MED-{i + 1:06d}",
            "citizen_id": c["citizen_id"],
            "visit_at": g.when(days=365),
            "facility": r.choice(FACILITIES),
            "department": dept,
            "diagnosis_code": code,
            "diagnosis": diag,
            "severity": sev,
            "blood_type": blood[c["citizen_id"]],
            "allergies": ", ".join(r.sample(ALLERGIES, r.choice([0, 0, 0, 1, 1, 2]))) or "none known",
            "chronic_conditions": ", ".join(r.sample(CHRONIC, r.choice([0, 0, 0, 0, 1, 1, 2]))) or "none",
            "length_of_stay_days": max(0, base_los + r.randint(-1, 3)) if base_los else 0,
            "attending_physician": f"Dr. {r.choice(FIRST_NAMES)} {r.choice(LAST_NAMES)}",
            "emergency_contact_phone": g.phone(),
        })
    out["medical_records"] = med

    # ── transit_trips ───────────────────────────────────────
    riders = [c for c in citizens if r.random() < (0.95 - AFFLUENCE[c["district"]] * 0.7) and c["date_of_birth"] < date(2016, 1, 1)]
    cards = {c["citizen_id"]: f"MC-{r.randrange(1000, 9999)}-{r.randrange(1000, 9999)}-{r.randrange(1000, 9999)}" for c in riders}
    trips = []
    for i in range(g.n(30000)):
        c = r.choice(riders)
        route = r.choice(list(ROUTES))
        mode, stops = ROUTES[route]
        a, b = sorted(r.sample(range(len(stops)), 2))
        if r.random() < 0.5:
            a, b = b, a
        board = g.when(peak=True)
        alight = board + timedelta(minutes=abs(b - a) * r.randint(7, 18))
        trips.append({
            "trip_id": f"TRP-{i + 1:07d}",
            "card_id": cards[c["citizen_id"]],
            "citizen_id": c["citizen_id"],
            "mode": mode,
            "route_id": route,
            "vehicle_id": f"{route}-V{r.randint(1, 12):02d}",
            "board_stop": stops[a],
            "board_at": board,
            "alight_stop": stops[b],
            "alight_at": alight,
            "fare_kes": FARES[mode] + (20 if board.hour in (7, 8, 17, 18) else 0),
            "assistance_requested": c["disability"] != "none" and r.random() < 0.75,
        })
    out["transit_trips"] = trips

    # ── vehicle_tracking ────────────────────────────────────
    owners = [c for c in adults if r.random() < AFFLUENCE[c["district"]] * 0.55]
    vehicles = {}
    for c in owners:
        plate = f"K{r.choice('ABCD')}{r.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')} {r.randint(100, 999)}{r.choice('ABCDEFGHJKLMNPQRSTUVWXYZ')}"
        vehicles[c["citizen_id"]] = (plate, r.choice(CARS), r.choice(COLOURS), c["district"])
    owner_ids = list(vehicles)
    pings = []
    for i in range(g.n(30000)):
        oid = r.choice(owner_ids)
        plate, model, colour, home = vehicles[oid]
        d = home if r.random() < 0.45 else g.district()
        lat, lon = g.point(d, 0.01)
        at = g.when(peak=True)
        speed = max(0.0, r.gauss(22 if at.hour in (7, 8, 17, 18) else 48, 14))
        pings.append({
            "ping_id": f"PNG-{i + 1:07d}",
            "plate": plate,
            "owner_id": oid,
            "make_model": model,
            "colour": colour,
            "recorded_at": at,
            "lat": lat,
            "lon": lon,
            "district": d,
            "speed_kph": round(speed, 1),
        })
    out["vehicle_tracking"] = pings

    # ── felonies ────────────────────────────────────────────
    fel = []
    for i in range(g.n(300)):
        c = r.choice(adults)
        status = r.choices(FELONY_STATUS, weights=[30, 30, 30, 10])[0]
        fel.append({
            "case_id": f"CR-{2023 + i % 4}-{i + 1:05d}",
            "citizen_id": c["citizen_id"],
            "offence": r.choice(FELONIES),
            "offence_date": (END - timedelta(days=r.randrange(1, 1200))).date(),
            "district": c["district"] if r.random() < 0.6 else g.district(),
            "status": status,
            "court": r.choice(COURTS),
            "sentence_months": r.choice([6, 12, 18, 24, 36, 60, 84, 120]) if status == "convicted" else None,
            "officer_badge": f"PB-{r.randint(1000, 1099)}",
        })
    out["felonies"] = fel

    # ── infractions ─────────────────────────────────────────
    inf = []
    for i in range(g.n(2500)):
        kind, fine, traffic = r.choice(INFRACTIONS)
        pool = owner_ids if traffic else None
        cid = r.choice(pool) if pool else r.choice(adults)["citizen_id"]
        inf.append({
            "infraction_id": f"TKT-{i + 1:06d}",
            "citizen_id": cid,
            "infraction_type": kind,
            "issued_at": g.when(days=180),
            "district": g.district(),
            "fine_kes": fine,
            "paid": r.random() < 0.68,
            "plate": vehicles[cid][0] if traffic else None,
        })
    out["infractions"] = inf

    # ── relationships ───────────────────────────────────────
    by_res: dict[str, list[dict]] = {}
    by_district: dict[str, list[dict]] = {}
    by_occ: dict[str, list[dict]] = {}
    for c in citizens:
        by_res.setdefault(c["residence_id"], []).append(c)
        by_district.setdefault(c["district"], []).append(c)
        by_occ.setdefault(c["occupation"], []).append(c)
    rels = []
    seen = set()
    while len(rels) < g.n(8000):
        a = r.choice(citizens)
        kind = r.choices(RELATIONS, weights=[10, 12, 10, 30, 18, 20])[0]
        pool = {
            "spouse": by_res[a["residence_id"]], "sibling": by_res[a["residence_id"]] + by_district[a["district"]][:50],
            "parent": by_res[a["residence_id"]], "coworker": by_occ[a["occupation"]],
            "neighbour": by_district[a["district"]], "friend": citizens,
        }[kind]
        b = r.choice(pool)
        key = tuple(sorted((a["citizen_id"], b["citizen_id"])))
        if b is a or key in seen:
            continue
        seen.add(key)
        rels.append({
            "relationship_id": f"REL-{len(rels) + 1:06d}",
            "citizen_a": a["citizen_id"],
            "citizen_b": b["citizen_id"],
            "relation_type": kind,
            "strength": round(min(1.0, max(0.05, r.gauss(0.8 if kind in {"spouse", "parent"} else 0.5, 0.18))), 2),
            "since_year": r.randint(1975, 2026),
            "interaction_freq": r.choices(FREQ, weights=[4, 3, 2, 1] if kind in {"spouse", "coworker"} else [1, 3, 3, 2])[0],
        })
    out["relationships"] = rels

    # ── amenities ───────────────────────────────────────────
    buildings = {}
    for res in residences:
        if res["building_id"]:
            buildings.setdefault(res["building_id"], res["district"])
    am = []
    for i in range(g.n(600)):
        d = g.district()
        rich = r.random() < AFFLUENCE[d] * 0.8
        kind = r.choice(AMENITIES_RICH if rich else AMENITIES_ALL)
        private = kind in AMENITIES_RICH and r.random() < 0.7
        bld = None
        if private:
            local = [b for b, bd in buildings.items() if bd == d]
            bld = r.choice(local) if local else None
        lat, lon = g.point(d)
        am.append({
            "amenity_id": f"AMN-{i + 1:04d}",
            "name": f"{d.split()[0]} {kind.replace('_', ' ').title()} {r.randint(1, 9)}",
            "amenity_type": kind,
            "district": d,
            "building_id": bld,
            "lat": lat,
            "lon": lon,
            "condition": r.choices(CONDITION, weights=[2 + AFFLUENCE[d] * 4, 4, 3, 2 - AFFLUENCE[d] * 1.5])[0],
            "capacity": r.randint(10, 60) if private else r.randint(40, 1200),
            "is_private": private,
        })
    out["amenities"] = am

    # ── weather ─────────────────────────────────────────────
    wx = []
    rainy_days = set(r.sample(range(DAYS), 9))
    seq = 0
    for d, a, _, _ in DISTRICTS:
        heat_island = (1 - a) * 2.5 + (2.0 if d in {"Mawe Industrial", "Soko Central"} else 0)
        for s in (1, 2):
            sensor = f"WX-{d.split()[0][:3].upper()}-{s}"
            for day in range(DAYS):
                for hour in range(24):
                    seq += 1
                    t = END - timedelta(days=DAYS - day) + timedelta(hours=hour)
                    diurnal = 6.5 * math.sin((hour - 9) / 24 * 2 * math.pi)
                    rain = max(0.0, r.gauss(4, 3)) if day in rainy_days and 14 <= hour <= 19 and r.random() < 0.6 else 0.0
                    temp = 19.5 + diurnal + heat_island * 0.6 + r.gauss(0, 0.8) - (2 if rain else 0)
                    pm = max(3.0, r.gauss(18 + (1 - a) * 30 + (25 if d == "Mawe Industrial" else 0), 8))
                    wx.append({
                        "reading_id": f"WX-{seq:07d}",
                        "sensor_id": sensor,
                        "district": d,
                        "recorded_at": t,
                        "temperature_c": round(temp, 1),
                        "surface_temp_c": round(temp + heat_island + max(0, diurnal) * 1.4, 1),
                        "humidity_pct": round(min(100, max(20, 62 - diurnal * 3 + (25 if rain else 0) + r.gauss(0, 5))), 1),
                        "rainfall_mm": round(rain, 1),
                        "wind_kph": round(max(0, r.gauss(12, 5)), 1),
                        "pm25": round(pm, 1),
                        "aqi": int(min(300, pm * 2.1)),
                    })
    out["weather"] = wx

    # ── infrastructure ──────────────────────────────────────
    infra = []
    for i in range(g.n(900)):
        d = g.district()
        kind = r.choice(ASSETS)
        installed = r.randint(1965, 2025)
        health = max(2.0, min(100.0, r.gauss(95 - (2026 - installed) * 0.9 + AFFLUENCE[d] * 10, 9)))
        status = "critical" if health < 30 else "maintenance_due" if health < 50 else "watch" if health < 70 else "ok"
        lat, lon = g.point(d, 0.01)
        infra.append({
            "asset_id": f"AST-{i + 1:05d}",
            "asset_type": kind,
            "district": d,
            "lat": lat,
            "lon": lon,
            "installed_year": installed,
            "health_score": round(health, 1),
            "load_pct": round(max(5, r.gauss(70 + (1 - AFFLUENCE[d]) * 30, 15)), 1),
            "vibration_mm_s": round(max(0.1, r.gauss(2 + (100 - health) / 20, 1)), 2) if kind in {"bridge", "road_segment", "substation"} else None,
            "last_inspected": (END - timedelta(days=r.randint(5, 900))).date(),
            "status": status,
            "contractor": r.choice(CONTRACTORS),
        })
    out["infrastructure"] = infra

    # ── feedback ────────────────────────────────────────────
    fb = []
    for i in range(g.n(2000)):
        c = r.choice(adults)
        topic = r.choice(list(TOPICS))
        msg = r.choice(TOPICS[topic]).format(s=r.choice(STREETS), d=c["district"], r=r.choice(list(ROUTES)))
        a = AFFLUENCE[c["district"]]
        channel = r.choices(CHANNELS, weights=[3 + a * 4, 1 + a * 4, 4 - a * 3, 2, 1])[0]
        fb.append({
            "feedback_id": f"FB-{i + 1:05d}",
            "citizen_id": c["citizen_id"],
            "submitted_at": g.when(days=90),
            "district": c["district"],
            "channel": channel,
            "topic": topic,
            "message": msg,
            "sentiment": r.choices(["negative", "neutral", "positive"], weights=[55, 30, 15])[0],
            # Affluent users get more upvotes on the app: the bias de-identification guards against.
            "upvotes": int(max(0, r.gauss(5 + a * 30, 6))),
        })
    out["feedback"] = fb

    # ── hazard_alerts ───────────────────────────────────────
    hz = []
    for i in range(g.n(250)):
        kind, agency = r.choice(HAZARDS)
        d = g.district()
        issued = g.when(days=365)
        sev = r.choices(SEVERITY, weights=[40, 30, 20, 10])[0]
        lat, lon = g.point(d)
        hz.append({
            "alert_id": f"ALR-{i + 1:04d}",
            "hazard_type": kind,
            "severity": sev,
            "district": d,
            "issued_at": issued,
            "expires_at": issued + timedelta(hours=r.choice([3, 6, 12, 24, 48, 72])),
            "lat": lat,
            "lon": lon,
            "affected_estimate": int(r.expovariate(1 / (300 * (SEVERITY.index(sev) + 1)))),
            "status": "active" if issued > END - timedelta(days=2) else r.choices(["resolved", "cancelled"], weights=[9, 1])[0],
            "issued_by": agency,
        })
    out["hazard_alerts"] = hz

    # ── egov_logs ───────────────────────────────────────────
    eg = []
    for i in range(g.n(20000)):
        c = r.choice(adults)
        service = r.choice(SERVICES)
        action = r.choices(["start", "submit", "pay", "download"], weights=[4, 3, 2, 1])[0]
        outcome = r.choices(["success", "failed", "abandoned"], weights=[80, 8, 12])[0]
        eg.append({
            "log_id": f"EGV-{i + 1:07d}",
            "citizen_id": c["citizen_id"],
            "service": service,
            "action": action,
            "occurred_at": g.when(),
            "ip_address": f"41.{r.randint(80, 90)}.{r.randint(0, 255)}.{r.randint(1, 254)}",
            "device": r.choices(DEVICES, weights=[5, 2, 2, 1])[0],
            "outcome": outcome,
            "duration_s": int(r.expovariate(1 / 140)) + 5,
            "amount_kes": r.choice([500, 1000, 2500, 5000, 12000]) if action == "pay" and outcome == "success" else None,
        })
    out["egov_logs"] = eg

    out_dir.mkdir(parents=True, exist_ok=True)
    counts = {}
    for slug, rows in out.items():
        pq.write_table(_table(slug, rows), out_dir / BY_SLUG[slug].filename, compression="zstd")
        counts[slug] = len(rows)
    return counts
