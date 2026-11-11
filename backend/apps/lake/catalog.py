"""Catalog of the smart-city data lake.

Each dataset is one Parquet file. A column's ``kind`` tells the policy engine how
a transform applies to it: masking an email keeps the domain, masking a phone
keeps the last digits, generalising a date of birth yields an age band, and so on.

``dimensions`` and ``measures`` are the only expressions aggregate queries may use.
They are SQL over the *raw* columns and are fixed here, never supplied by clients.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Column:
    name: str
    type: str
    kind: str
    description: str
    pii: bool = False


@dataclass(frozen=True)
class Dataset:
    slug: str
    title: str
    domain: str
    icon: str
    description: str
    columns: tuple[Column, ...]
    dimensions: dict[str, str] = field(default_factory=dict)
    measures: dict[str, str] = field(default_factory=dict)

    @property
    def filename(self) -> str:
        return f"{self.slug}.parquet"

    def column(self, name: str) -> Column | None:
        return next((c for c in self.columns if c.name == name), None)


C = Column
AGE = "date_diff('year', date_of_birth, current_date)"

DATASETS: tuple[Dataset, ...] = (
    Dataset(
        slug="citizens",
        title="Citizen Registry",
        domain="Living locales",
        icon="users",
        description="Every registered resident: identity, contact, demographics and home.",
        columns=(
            C("citizen_id", "VARCHAR", "id", "Registry key", pii=True),
            C("national_id", "VARCHAR", "national_id", "National ID number", pii=True),
            C("ssn", "VARCHAR", "ssn", "Social security number", pii=True),
            C("first_name", "VARCHAR", "first_name", "Given name", pii=True),
            C("last_name", "VARCHAR", "last_name", "Family name", pii=True),
            C("date_of_birth", "DATE", "dob", "Date of birth", pii=True),
            C("sex", "VARCHAR", "category", "Sex recorded at registration"),
            C("phone", "VARCHAR", "phone", "Mobile number", pii=True),
            C("email", "VARCHAR", "email", "Email address", pii=True),
            C("occupation", "VARCHAR", "category", "Occupation"),
            C("education", "VARCHAR", "category", "Highest education level"),
            C("income_band", "VARCHAR", "category", "Household income band"),
            C("disability", "VARCHAR", "category", "Disability needing assistance, if any"),
            C("residence_id", "VARCHAR", "ref", "Home (→ residences)", pii=True),
            C("district", "VARCHAR", "category", "Home district"),
            C("registered_at", "TIMESTAMP", "datetime", "Registration time"),
        ),
        dimensions={
            "district": "district",
            "sex": "sex",
            "age_band": f"CAST(floor({AGE} / 10) * 10 AS INTEGER) || '–' || CAST(floor({AGE} / 10) * 10 + 9 AS INTEGER)",
            "income_band": "income_band",
            "education": "education",
            "occupation": "occupation",
            "disability": "disability",
        },
        measures={"age": AGE},
    ),
    Dataset(
        slug="residences",
        title="Residences",
        domain="Living locales",
        icon="home",
        description="Dwellings: street address, coordinates, building type and occupancy.",
        columns=(
            C("residence_id", "VARCHAR", "id", "Residence key", pii=True),
            C("address", "VARCHAR", "address", "Street address", pii=True),
            C("district", "VARCHAR", "category", "District"),
            C("lat", "DOUBLE", "geo", "Latitude", pii=True),
            C("lon", "DOUBLE", "geo", "Longitude", pii=True),
            C("dwelling_type", "VARCHAR", "category", "Dwelling type"),
            C("building_id", "VARCHAR", "category", "Building / complex"),
            C("floor", "INTEGER", "number", "Floor number"),
            C("occupants", "INTEGER", "number", "Number of occupants"),
            C("monthly_rent_kes", "INTEGER", "money", "Monthly rent (KES)"),
            C("access_notes", "VARCHAR", "text", "Gate codes / access notes for responders", pii=True),
        ),
        dimensions={"district": "district", "dwelling_type": "dwelling_type"},
        measures={"occupants": "occupants", "monthly_rent_kes": "monthly_rent_kes", "floor": "floor"},
    ),
    Dataset(
        slug="medical_records",
        title="Medical Records",
        domain="Medical care",
        icon="heart-pulse",
        description="Clinical encounters across city hospitals and clinics.",
        columns=(
            C("record_id", "VARCHAR", "id", "Encounter key"),
            C("citizen_id", "VARCHAR", "ref", "Patient (→ citizens)", pii=True),
            C("visit_at", "TIMESTAMP", "datetime", "Admission time"),
            C("facility", "VARCHAR", "category", "Facility"),
            C("department", "VARCHAR", "category", "Department"),
            C("diagnosis_code", "VARCHAR", "category", "ICD-10 code"),
            C("diagnosis", "VARCHAR", "category", "Diagnosis"),
            C("severity", "VARCHAR", "category", "Triage severity"),
            C("blood_type", "VARCHAR", "category", "Blood type"),
            C("allergies", "VARCHAR", "text", "Known allergies", pii=True),
            C("chronic_conditions", "VARCHAR", "text", "Chronic conditions", pii=True),
            C("length_of_stay_days", "INTEGER", "number", "Length of stay (days)"),
            C("attending_physician", "VARCHAR", "full_name", "Attending physician"),
            C("emergency_contact_phone", "VARCHAR", "phone", "Emergency contact", pii=True),
        ),
        dimensions={
            "facility": "facility",
            "department": "department",
            "diagnosis": "diagnosis",
            "severity": "severity",
            "blood_type": "blood_type",
            "month": "strftime(visit_at, '%Y-%m')",
        },
        measures={"length_of_stay_days": "length_of_stay_days"},
    ),
    Dataset(
        slug="transit_trips",
        title="Public Transit Trips",
        domain="Public transit",
        icon="bus",
        description="Smart-card taps: where and when riders board and alight.",
        columns=(
            C("trip_id", "VARCHAR", "id", "Trip key"),
            C("card_id", "VARCHAR", "card", "Transit card number", pii=True),
            C("citizen_id", "VARCHAR", "ref", "Rider (→ citizens)", pii=True),
            C("mode", "VARCHAR", "category", "Bus / BRT / light rail / matatu"),
            C("route_id", "VARCHAR", "category", "Route"),
            C("vehicle_id", "VARCHAR", "category", "Vehicle"),
            C("board_stop", "VARCHAR", "category", "Boarding stop"),
            C("board_at", "TIMESTAMP", "datetime", "Boarding time"),
            C("alight_stop", "VARCHAR", "category", "Alighting stop"),
            C("alight_at", "TIMESTAMP", "datetime", "Alighting time"),
            C("fare_kes", "INTEGER", "money", "Fare (KES)"),
            C("assistance_requested", "BOOLEAN", "bool", "Boarding assistance requested"),
        ),
        dimensions={
            "mode": "mode",
            "route_id": "route_id",
            "board_stop": "board_stop",
            "hour": "hour(board_at)",
            "weekday": "dayname(board_at)",
            "assistance_requested": "assistance_requested",
        },
        measures={"fare_kes": "fare_kes", "duration_min": "date_diff('minute', board_at, alight_at)"},
    ),
    Dataset(
        slug="vehicle_tracking",
        title="Private Vehicle Tracking",
        domain="Private vehicles",
        icon="car",
        description="ANPR and telematics pings of privately owned vehicles.",
        columns=(
            C("ping_id", "VARCHAR", "id", "Ping key"),
            C("plate", "VARCHAR", "plate", "Number plate", pii=True),
            C("owner_id", "VARCHAR", "ref", "Registered owner (→ citizens)", pii=True),
            C("make_model", "VARCHAR", "category", "Make and model"),
            C("colour", "VARCHAR", "category", "Body colour"),
            C("recorded_at", "TIMESTAMP", "datetime", "Ping time"),
            C("lat", "DOUBLE", "geo", "Latitude", pii=True),
            C("lon", "DOUBLE", "geo", "Longitude", pii=True),
            C("district", "VARCHAR", "category", "District"),
            C("speed_kph", "DOUBLE", "number", "Speed (km/h)"),
        ),
        dimensions={"district": "district", "make_model": "make_model", "hour": "hour(recorded_at)"},
        measures={"speed_kph": "speed_kph"},
    ),
    Dataset(
        slug="felonies",
        title="Felony Cases",
        domain="Felonies",
        icon="gavel",
        description="Serious criminal cases and their court outcomes.",
        columns=(
            C("case_id", "VARCHAR", "id", "Case number"),
            C("citizen_id", "VARCHAR", "ref", "Accused (→ citizens)", pii=True),
            C("offence", "VARCHAR", "category", "Offence"),
            C("offence_date", "DATE", "date", "Date of offence"),
            C("district", "VARCHAR", "category", "District"),
            C("status", "VARCHAR", "category", "Case status"),
            C("court", "VARCHAR", "category", "Court"),
            C("sentence_months", "INTEGER", "number", "Sentence (months)"),
            C("officer_badge", "VARCHAR", "category", "Investigating officer"),
        ),
        dimensions={
            "offence": "offence",
            "district": "district",
            "status": "status",
            "year": "CAST(year(offence_date) AS VARCHAR)",
        },
        measures={"sentence_months": "sentence_months"},
    ),
    Dataset(
        slug="infractions",
        title="Criminal Infractions",
        domain="Criminal infractions",
        icon="siren",
        description="Minor offences and fines: traffic, littering, noise, by-laws.",
        columns=(
            C("infraction_id", "VARCHAR", "id", "Ticket number"),
            C("citizen_id", "VARCHAR", "ref", "Offender (→ citizens)", pii=True),
            C("infraction_type", "VARCHAR", "category", "Infraction"),
            C("issued_at", "TIMESTAMP", "datetime", "Issued at"),
            C("district", "VARCHAR", "category", "District"),
            C("fine_kes", "INTEGER", "money", "Fine (KES)"),
            C("paid", "BOOLEAN", "bool", "Fine paid"),
            C("plate", "VARCHAR", "plate", "Vehicle plate, if traffic", pii=True),
        ),
        dimensions={
            "infraction_type": "infraction_type",
            "district": "district",
            "paid": "paid",
            "month": "strftime(issued_at, '%Y-%m')",
        },
        measures={"fine_kes": "fine_kes"},
    ),
    Dataset(
        slug="relationships",
        title="Social Relationships",
        domain="Sociological relationships",
        icon="network",
        description="Edges of the city's social graph: family, friends, colleagues, neighbours.",
        columns=(
            C("relationship_id", "VARCHAR", "id", "Edge key"),
            C("citizen_a", "VARCHAR", "ref", "Person A (→ citizens)", pii=True),
            C("citizen_b", "VARCHAR", "ref", "Person B (→ citizens)", pii=True),
            C("relation_type", "VARCHAR", "category", "Relationship"),
            C("strength", "DOUBLE", "number", "Tie strength 0–1"),
            C("since_year", "INTEGER", "number", "Known since"),
            C("interaction_freq", "VARCHAR", "category", "Interaction frequency"),
        ),
        dimensions={"relation_type": "relation_type", "interaction_freq": "interaction_freq"},
        measures={"strength": "strength", "since_year": "since_year"},
    ),
    Dataset(
        slug="amenities",
        title="Amenities",
        domain="Amenities",
        icon="trees",
        description="Pools, gyms, clinics, schools, parks and other facilities.",
        columns=(
            C("amenity_id", "VARCHAR", "id", "Amenity key"),
            C("name", "VARCHAR", "category", "Name"),
            C("amenity_type", "VARCHAR", "category", "Type"),
            C("district", "VARCHAR", "category", "District"),
            C("building_id", "VARCHAR", "category", "Building / complex, if private"),
            C("lat", "DOUBLE", "geo", "Latitude"),
            C("lon", "DOUBLE", "geo", "Longitude"),
            C("condition", "VARCHAR", "category", "Condition"),
            C("capacity", "INTEGER", "number", "Capacity"),
            C("is_private", "BOOLEAN", "bool", "Private (residents only)"),
        ),
        dimensions={
            "amenity_type": "amenity_type",
            "district": "district",
            "condition": "condition",
            "is_private": "is_private",
        },
        measures={"capacity": "capacity"},
    ),
    Dataset(
        slug="weather",
        title="Weather & Microclimate",
        domain="Weather and microclimate",
        icon="cloud-sun",
        description="Hourly readings from street-level sensors, incl. surface heat and air quality.",
        columns=(
            C("reading_id", "VARCHAR", "id", "Reading key"),
            C("sensor_id", "VARCHAR", "category", "Sensor"),
            C("district", "VARCHAR", "category", "District"),
            C("recorded_at", "TIMESTAMP", "datetime", "Reading time"),
            C("temperature_c", "DOUBLE", "number", "Air temperature (°C)"),
            C("surface_temp_c", "DOUBLE", "number", "Surface temperature (°C)"),
            C("humidity_pct", "DOUBLE", "number", "Relative humidity (%)"),
            C("rainfall_mm", "DOUBLE", "number", "Rainfall (mm/h)"),
            C("wind_kph", "DOUBLE", "number", "Wind speed (km/h)"),
            C("pm25", "DOUBLE", "number", "PM2.5 (µg/m³)"),
            C("aqi", "INTEGER", "number", "Air quality index"),
        ),
        dimensions={
            "district": "district",
            "sensor_id": "sensor_id",
            "day": "CAST(CAST(recorded_at AS DATE) AS VARCHAR)",
            "hour": "hour(recorded_at)",
        },
        measures={
            "temperature_c": "temperature_c",
            "surface_temp_c": "surface_temp_c",
            "humidity_pct": "humidity_pct",
            "rainfall_mm": "rainfall_mm",
            "wind_kph": "wind_kph",
            "pm25": "pm25",
            "aqi": "aqi",
        },
    ),
    Dataset(
        slug="infrastructure",
        title="Infrastructure Health",
        domain="Infrastructure health",
        icon="construction",
        description="Structural-health telemetry for bridges, roads, pipes, lights and substations.",
        columns=(
            C("asset_id", "VARCHAR", "id", "Asset key"),
            C("asset_type", "VARCHAR", "category", "Asset type"),
            C("district", "VARCHAR", "category", "District"),
            C("lat", "DOUBLE", "geo", "Latitude"),
            C("lon", "DOUBLE", "geo", "Longitude"),
            C("installed_year", "INTEGER", "number", "Installed"),
            C("health_score", "DOUBLE", "number", "Health score 0–100"),
            C("load_pct", "DOUBLE", "number", "Load (% of design)"),
            C("vibration_mm_s", "DOUBLE", "number", "Vibration (mm/s)"),
            C("last_inspected", "DATE", "date", "Last inspection"),
            C("status", "VARCHAR", "category", "Status"),
            C("contractor", "VARCHAR", "category", "Maintenance contractor"),
        ),
        dimensions={"asset_type": "asset_type", "district": "district", "status": "status"},
        measures={
            "health_score": "health_score",
            "load_pct": "load_pct",
            "vibration_mm_s": "vibration_mm_s",
            "age_years": "year(current_date) - installed_year",
        },
    ),
    Dataset(
        slug="feedback",
        title="Citizen Feedback",
        domain="Citizen feedback",
        icon="message-square",
        description="Suggestions and complaints submitted through city channels.",
        columns=(
            C("feedback_id", "VARCHAR", "id", "Submission key"),
            C("citizen_id", "VARCHAR", "ref", "Author (→ citizens)", pii=True),
            C("submitted_at", "TIMESTAMP", "datetime", "Submitted at"),
            C("district", "VARCHAR", "category", "Author's district"),
            C("channel", "VARCHAR", "category", "Channel"),
            C("topic", "VARCHAR", "category", "Topic"),
            C("message", "VARCHAR", "text", "Message"),
            C("sentiment", "VARCHAR", "category", "Sentiment"),
            C("upvotes", "INTEGER", "number", "Upvotes"),
        ),
        dimensions={
            "topic": "topic",
            "sentiment": "sentiment",
            "channel": "channel",
            "district": "district",
            "month": "strftime(submitted_at, '%Y-%m')",
        },
        measures={"upvotes": "upvotes"},
    ),
    Dataset(
        slug="hazard_alerts",
        title="Disaster & Hazard Alerts",
        domain="Disaster and hazard alerts",
        icon="triangle-alert",
        description="Floods, fires, heatwaves, gas leaks and other alerts issued to the public.",
        columns=(
            C("alert_id", "VARCHAR", "id", "Alert key"),
            C("hazard_type", "VARCHAR", "category", "Hazard"),
            C("severity", "VARCHAR", "category", "Severity"),
            C("district", "VARCHAR", "category", "District"),
            C("issued_at", "TIMESTAMP", "datetime", "Issued at"),
            C("expires_at", "TIMESTAMP", "datetime", "Expires at"),
            C("lat", "DOUBLE", "geo", "Epicentre latitude"),
            C("lon", "DOUBLE", "geo", "Epicentre longitude"),
            C("affected_estimate", "INTEGER", "number", "People affected (est.)"),
            C("status", "VARCHAR", "category", "Status"),
            C("issued_by", "VARCHAR", "category", "Issuing agency"),
        ),
        dimensions={
            "hazard_type": "hazard_type",
            "severity": "severity",
            "district": "district",
            "status": "status",
            "month": "strftime(issued_at, '%Y-%m')",
        },
        measures={"affected_estimate": "affected_estimate"},
    ),
    Dataset(
        slug="egov_logs",
        title="E-Government Logs",
        domain="E-government",
        icon="landmark",
        description="Citizen sessions on city e-services: permits, taxes, licences, certificates.",
        columns=(
            C("log_id", "VARCHAR", "id", "Event key"),
            C("citizen_id", "VARCHAR", "ref", "Citizen (→ citizens)", pii=True),
            C("service", "VARCHAR", "category", "Service"),
            C("action", "VARCHAR", "category", "Action"),
            C("occurred_at", "TIMESTAMP", "datetime", "Time"),
            C("ip_address", "VARCHAR", "ip", "Client IP", pii=True),
            C("device", "VARCHAR", "category", "Device"),
            C("outcome", "VARCHAR", "category", "Outcome"),
            C("duration_s", "INTEGER", "number", "Duration (s)"),
            C("amount_kes", "INTEGER", "money", "Amount paid (KES)"),
        ),
        dimensions={
            "service": "service",
            "action": "action",
            "device": "device",
            "outcome": "outcome",
            "hour": "hour(occurred_at)",
        },
        measures={"duration_s": "duration_s", "amount_kes": "amount_kes"},
    ),
)

BY_SLUG = {d.slug: d for d in DATASETS}
