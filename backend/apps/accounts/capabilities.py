"""API-level capabilities. A role's capabilities decide which endpoints it may
call at all; the permission grid then decides what data those endpoints return."""

BROWSE = "lake.browse"  # record-level reads of row-mode datasets
AGGREGATE = "lake.aggregate"  # group-by summaries
SQL = "lake.sql"  # SQL workbench / cross-analysis across datasets
AUDIT_OWN = "audit.view_own"  # read one's own audit trail
AUDIT_ALL = "audit.view_all"  # read everyone's audit trail + SIEM detections
GRID_ALL = "grid.view_all"  # read every role's column rules, not just one's own

ALL = {
    BROWSE: "Read record-level rows the grid allows",
    AGGREGATE: "Run k-anonymous group-by summaries",
    SQL: "Cross-analyse datasets in the SQL workbench",
    AUDIT_OWN: "View own audit trail",
    AUDIT_ALL: "View all audit logs and SIEM detections",
    GRID_ALL: "Inspect every role's column rules",
}
