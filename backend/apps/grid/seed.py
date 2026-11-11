"""Default roles and the default permission grid.

Seeded on first boot. A super-admin can change any of it later in the Django
admin; ``seed_lab --reset-grid`` restores these defaults.
"""

from apps.accounts import capabilities as cap
from apps.lake.catalog import BY_SLUG, DATASETS

BASE = [cap.BROWSE, cap.AGGREGATE, cap.AUDIT_OWN]

ROLES = [
    {
        "slug": "medical",
        "name": "Medical Personnel",
        "icon": "stethoscope",
        "username": "medic",
        "first_name": "Wanjiru",
        "last_name": "Kamau",
        "capabilities": BASE + [cap.SQL],
        "description": "Clinicians who need a patient's identity, history and home address to treat and "
        "reach them, and nothing about their criminal record, car, commute or amenities.",
    },
    {
        "slug": "rapid_response",
        "name": "Rapid Response",
        "icon": "ambulance",
        "username": "responder",
        "first_name": "Baraka",
        "last_name": "Otieno",
        "capabilities": BASE + [cap.SQL],
        "description": "Paramedics and rescue crews: where people live, how to get in, who needs help "
        "moving, live hazards and road conditions. Only the medical facts that matter in the field.",
    },
    {
        "slug": "law_enforcement",
        "name": "Law Enforcement Official",
        "icon": "shield",
        "username": "officer",
        "first_name": "Kiprono",
        "last_name": "Keter",
        "capabilities": BASE + [cap.SQL],
        "description": "Investigators: identities, felonies, infractions and vehicle movements. "
        "Medical data is off limits and transit use is only visible in aggregate without a warrant.",
    },
    {
        "slug": "civil_engineer",
        "name": "Civil Engineering Contractor",
        "icon": "hard-hat",
        "username": "engineer",
        "first_name": "Achieng",
        "last_name": "Onyango",
        "capabilities": BASE,
        "description": "Maintenance contractors: full infrastructure telemetry, and only k-anonymous "
        "summaries of the people, climate and housing around an asset. No personal data at all.",
    },
    {
        "slug": "sociologist",
        "name": "Sociologist",
        "icon": "graduation-cap",
        "username": "sociologist",
        "first_name": "Imani",
        "last_name": "Wekesa",
        "capabilities": BASE + [cap.SQL],
        "description": "Researchers studying how people relate. Record-level data, but every name and "
        "identifier is swapped for a pseudorandom stand-in so subjects cannot easily be located.",
    },
    {
        "slug": "policy_maker",
        "name": "Policy Maker",
        "icon": "landmark",
        "username": "policymaker",
        "first_name": "Halima",
        "last_name": "Abdi",
        "capabilities": BASE + [cap.GRID_ALL],
        "description": "Legislators reading citizen feedback stripped of anything that hints at who sent it, "
        "so suggestions are judged on merit, plus city-wide aggregates for planning.",
    },
    {
        "slug": "transport_official",
        "name": "Transport Official",
        "icon": "bus",
        "username": "transport",
        "first_name": "Juma",
        "last_name": "Mwangi",
        "capabilities": BASE + [cap.SQL],
        "description": "Transit operators: boarding and alighting events joined to a thin slice of the "
        "rider (name, age band, disability) so staff can assist when needed.",
    },
    {
        "slug": "climatologist",
        "name": "Climatologist",
        "icon": "cloud-sun",
        "username": "climatologist",
        "first_name": "Zawadi",
        "last_name": "Chebet",
        "capabilities": BASE + [cap.SQL],
        "description": "Climate scientists: raw sensor readings and hazard history, with population, "
        "housing and infrastructure only as aggregates for exposure modelling.",
    },
    {
        "slug": "administrator",
        "name": "Administrator",
        "icon": "server-cog",
        "username": "admin",
        "first_name": "Daniel",
        "last_name": "Njoroge",
        "capabilities": BASE + [cap.SQL, cap.AUDIT_ALL, cap.GRID_ALL],
        "description": "Operators who keep the platform running. They can prove every silo is reachable, "
        "but only through a pseudonymised lens, and they cannot edit the grid or any record.",
    },
]


def cols(**rules: str) -> dict[str, str]:
    """cols(clear="a b", mask="c") → {"a": "clear", "b": "clear", "c": "mask"}"""
    return {c: rule for rule, names in rules.items() for c in names.split()}


def row(rules, why, cross=True, max_rows=200, group_by=(), k=1):
    return {"mode": "row", "column_rules": rules, "rationale": why, "cross_analyze": cross,
            "max_rows": max_rows, "group_by": list(group_by), "min_group_size": k}


def agg(why, group_by=(), metrics=(), k=5):
    return {"mode": "aggregate", "rationale": why, "group_by": list(group_by),
            "metrics": list(metrics), "min_group_size": k}


def deny(why):
    return {"mode": "deny", "rationale": why}


def everything(slug):
    return cols(clear=" ".join(c.name for c in BY_SLUG[slug].columns))


def light_obfuscation(slug):
    """Administrator lens: data provably flows, but nobody is identifiable."""
    by_kind = {
        "id": "pseudonym", "ref": "pseudonym", "national_id": "mask", "ssn": "mask", "card": "mask",
        "plate": "mask", "phone": "mask", "email": "mask", "ip": "mask", "first_name": "fake",
        "last_name": "fake", "full_name": "fake", "dob": "generalize", "address": "generalize",
        "geo": "generalize",
    }
    return {c.name: by_kind.get(c.kind, "mask" if c.kind == "text" and c.pii else "clear")
            for c in BY_SLUG[slug].columns}


CITIZEN_DEMOGRAPHICS = ("district", "sex", "age_band", "income_band", "education", "disability")
NOT_YOUR_JOB = "Irrelevant to the role's duties; withheld under data minimisation."

GRID = {
    "medical": {
        "citizens": row(cols(clear="citizen_id first_name last_name date_of_birth sex phone disability residence_id district",
                             mask="national_id"),
                        "Identify the patient and reach them. SSN, income, job and email are not clinical."),
        "residences": row(cols(clear="residence_id address district lat lon dwelling_type building_id floor occupants access_notes"),
                          "Home address and access notes to extract a patient in an emergency. Rent is irrelevant."),
        "medical_records": row(everything("medical_records"), "Full clinical history for care."),
        "hazard_alerts": row(everything("hazard_alerts"), "Prepare for mass-casualty events."),
        "weather": agg("Heat and air-quality trends drive admissions.", k=1),
        "transit_trips": deny("How a patient commutes is not clinically relevant."),
        "vehicle_tracking": deny("The vehicle a patient drives is not clinically relevant."),
        "felonies": deny("A patient's criminal record must not influence care."),
        "infractions": deny("A patient's infractions must not influence care."),
        "relationships": deny(NOT_YOUR_JOB),
        "amenities": deny("Whether a patient's complex has a swimming pool is irrelevant."),
        "infrastructure": deny(NOT_YOUR_JOB),
        "feedback": deny(NOT_YOUR_JOB),
        "egov_logs": deny(NOT_YOUR_JOB),
    },
    "rapid_response": {
        "citizens": row(cols(clear="citizen_id first_name last_name sex phone disability residence_id district",
                             generalize="date_of_birth"),
                        "Who lives where and who needs help moving. An age band is enough; no IDs."),
        "residences": row(cols(clear="residence_id address district lat lon dwelling_type building_id floor occupants access_notes"),
                          "Exact location, floor, occupants and gate codes to get people out."),
        "medical_records": row(cols(clear="citizen_id blood_type allergies chronic_conditions"),
                               "Only what changes field treatment: blood type, allergies, chronic conditions. No diagnoses."),
        "hazard_alerts": row(everything("hazard_alerts"), "Live incidents drive dispatch."),
        "weather": row(everything("weather"), "Rain and heat change routes and risk."),
        "infrastructure": row(everything("infrastructure"), "Know which bridges and roads are unsafe."),
        "transit_trips": deny(NOT_YOUR_JOB),
        "vehicle_tracking": deny(NOT_YOUR_JOB),
        "felonies": deny("Responders treat everyone equally; criminal history is withheld."),
        "infractions": deny("Responders treat everyone equally; criminal history is withheld."),
        "relationships": deny(NOT_YOUR_JOB),
        "amenities": deny("Whether a building has a swimming pool is irrelevant to an extraction."),
        "feedback": deny(NOT_YOUR_JOB),
        "egov_logs": deny(NOT_YOUR_JOB),
    },
    "law_enforcement": {
        "citizens": row(cols(clear="citizen_id national_id first_name last_name date_of_birth sex phone occupation residence_id district",
                             mask="ssn email"),
                        "Positive identification of suspects. Health, income and disability are withheld."),
        "residences": row(cols(clear="residence_id address district lat lon dwelling_type building_id occupants"),
                          "Locate suspects. Responder access notes are withheld."),
        "felonies": row(everything("felonies"), "Core investigative record."),
        "infractions": row(everything("infractions"), "Core enforcement record."),
        "vehicle_tracking": row(everything("vehicle_tracking"), "ANPR and telematics for investigations."),
        "hazard_alerts": row(everything("hazard_alerts"), "Crowd control and cordons."),
        "relationships": agg("Associations need a warrant; only network-level statistics are open.", k=5),
        "transit_trips": agg("Individual journeys need a warrant; ridership patterns are open.", k=5),
        "weather": agg("Context for incident patterns.", k=1),
        "medical_records": deny("Medical confidentiality: no access without a court order."),
        "amenities": deny(NOT_YOUR_JOB),
        "infrastructure": deny(NOT_YOUR_JOB),
        "feedback": deny("Policing citizen feedback would chill free expression."),
        "egov_logs": deny("Service usage is not an investigative source."),
    },
    "civil_engineer": {
        "infrastructure": row(everything("infrastructure"), "The assets under maintenance."),
        "amenities": row(cols(clear="amenity_id name amenity_type district condition capacity is_private",
                              generalize="lat lon"),
                         "Facility condition near works; locations coarsened, private buildings not linked.",
                         cross=False),
        "citizens": agg("Demographics around a site, never individuals.", group_by=CITIZEN_DEMOGRAPHICS,
                        metrics=("age",), k=10),
        "residences": agg("Housing density and occupancy per district.", metrics=("occupants", "floor"), k=5),
        "weather": agg("Climate loads on assets.", k=1),
        "hazard_alerts": agg("Hazard frequency per district for resilience planning.", k=1),
        "transit_trips": agg("Route load for road works scheduling.", group_by=("mode", "route_id", "hour", "weekday"), k=5),
        "vehicle_tracking": agg("Traffic volume and speed by district and hour.", group_by=("district", "hour"), k=5),
        "medical_records": deny(NOT_YOUR_JOB),
        "felonies": deny(NOT_YOUR_JOB),
        "infractions": deny(NOT_YOUR_JOB),
        "relationships": deny(NOT_YOUR_JOB),
        "feedback": deny(NOT_YOUR_JOB),
        "egov_logs": deny(NOT_YOUR_JOB),
    },
    "sociologist": {
        "citizens": row(cols(pseudonym="citizen_id national_id ssn residence_id", fake="first_name last_name",
                             generalize="date_of_birth", clear="sex occupation education income_band disability district"),
                        "Rich attributes for analysis; every identifier pseudonymised and names faked.",
                        max_rows=500),
        "relationships": row(cols(pseudonym="relationship_id citizen_a citizen_b",
                                  clear="relation_type strength since_year interaction_freq"),
                             "The social graph itself, with pseudonymous nodes that still join to citizens.",
                             max_rows=500),
        "residences": row(cols(pseudonym="residence_id", clear="district dwelling_type occupants",
                               generalize="monthly_rent_kes"),
                          "Household composition without addresses or coordinates."),
        "feedback": row(cols(pseudonym="feedback_id citizen_id", generalize="submitted_at",
                             clear="district channel topic message sentiment upvotes"),
                        "Civic voice by community; authors pseudonymised."),
        "felonies": agg("Crime as a social phenomenon, never as individuals.", k=5),
        "infractions": agg("Infraction patterns by district.", k=5),
        "transit_trips": agg("Mobility patterns.", k=5),
        "egov_logs": agg("Digital inclusion: who completes e-services and how.", k=5),
        "amenities": agg("Access to amenities across districts.", k=1),
        "medical_records": agg("Population health only, with a high suppression threshold.",
                               group_by=("diagnosis", "severity", "month"), k=10),
        "hazard_alerts": agg("Exposure to hazards by community.", k=1),
        "weather": deny(NOT_YOUR_JOB),
        "vehicle_tracking": deny("Location traces are too re-identifying even when pseudonymised."),
        "infrastructure": deny(NOT_YOUR_JOB),
    },
    "policy_maker": {
        "feedback": row(cols(clear="feedback_id topic message sentiment", generalize="submitted_at"),
                        "De-identified: author, district, channel and upvotes are removed, because each one "
                        "correlates with wealth and would let affluent voices dominate.",
                        cross=False, max_rows=500, group_by=("topic", "sentiment", "month")),
        "citizens": agg("Population structure for planning.", group_by=CITIZEN_DEMOGRAPHICS, metrics=("age",), k=10),
        "residences": agg("Housing supply and affordability.", k=5),
        "medical_records": agg("Burden of disease.", group_by=("diagnosis", "facility", "severity", "month"), k=10),
        "transit_trips": agg("Ridership and fare revenue.", k=5),
        "vehicle_tracking": agg("Congestion by district and hour.", group_by=("district", "hour"), k=5),
        "felonies": agg("Crime trends.", group_by=("offence", "district", "year", "status"), k=5),
        "infractions": agg("Enforcement trends.", k=5),
        "amenities": agg("Distribution of public goods.", k=1),
        "weather": agg("Climate trends.", k=1),
        "infrastructure": agg("Asset health for budgeting.", k=1),
        "hazard_alerts": agg("Disaster history.", k=1),
        "egov_logs": agg("E-service uptake and failure rates.", k=5),
        "relationships": deny("Private social ties are not a policy input."),
    },
    "transport_official": {
        "transit_trips": row(cols(clear="trip_id citizen_id mode route_id vehicle_id board_stop board_at alight_stop alight_at fare_kes assistance_requested",
                                  mask="card_id"),
                             "Every boarding and alighting event; card numbers masked.", max_rows=500),
        "citizens": row(cols(clear="citizen_id first_name last_name sex disability", generalize="date_of_birth"),
                        "Thin slice: who the rider is and whether they need assistance. Nothing else."),
        "infrastructure": row(everything("infrastructure"), "Roads and bridges on the network."),
        "hazard_alerts": row(everything("hazard_alerts"), "Divert services around incidents."),
        "weather": agg("Weather effects on ridership.", k=1),
        "vehicle_tracking": agg("Private traffic competes for road space.", group_by=("district", "hour"), k=5),
        "infractions": agg("Traffic infraction hotspots.", group_by=("infraction_type", "district"), k=5),
        "medical_records": deny(NOT_YOUR_JOB),
        "residences": deny("Where riders live is not needed to run a bus."),
        "felonies": deny(NOT_YOUR_JOB),
        "relationships": deny(NOT_YOUR_JOB),
        "amenities": deny(NOT_YOUR_JOB),
        "feedback": deny(NOT_YOUR_JOB),
        "egov_logs": deny(NOT_YOUR_JOB),
    },
    "climatologist": {
        "weather": row(everything("weather"), "Raw sensor readings.", max_rows=1000),
        "hazard_alerts": row(everything("hazard_alerts"), "Hazard history."),
        "infrastructure": agg("Climate stress on assets.", k=1),
        "amenities": agg("Green space and cooling amenities.", k=1),
        "residences": agg("Housing exposure.", k=5),
        "citizens": agg("Vulnerable populations for heat-risk models.", group_by=("district", "age_band", "disability"), k=10),
        "vehicle_tracking": agg("Traffic as an emissions proxy.", group_by=("district", "hour"), k=5),
        "transit_trips": agg("Modal share.", group_by=("mode", "hour"), k=5),
        "medical_records": deny(NOT_YOUR_JOB),
        "felonies": deny(NOT_YOUR_JOB),
        "infractions": deny(NOT_YOUR_JOB),
        "relationships": deny(NOT_YOUR_JOB),
        "feedback": deny(NOT_YOUR_JOB),
        "egov_logs": deny(NOT_YOUR_JOB),
    },
    "administrator": {
        ds.slug: row(light_obfuscation(ds.slug),
                     "Operational lens: proves the silo is reachable while identifiers are pseudonymised, "
                     "names faked and contacts masked.", max_rows=100)
        for ds in DATASETS
    },
}
