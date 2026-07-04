CREATE TABLE schematics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_image TEXT NOT NULL,
    name TEXT,
    design_notes TEXT
);

CREATE TABLE components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schematic_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    type TEXT,
    value TEXT,
    FOREIGN KEY(schematic_id) REFERENCES schematics(id)
);

CREATE TABLE connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    schematic_id INTEGER NOT NULL,
    from_pin TEXT NOT NULL,
    to_pin TEXT NOT NULL,
    FOREIGN KEY(schematic_id) REFERENCES schematics(id)
);

-- Indexes to speed up topology queries
CREATE INDEX idx_components_schematic ON components(schematic_id);
CREATE INDEX idx_connections_schematic ON connections(schematic_id);
CREATE INDEX idx_connections_from ON connections(from_pin);
CREATE INDEX idx_connections_to ON connections(to_pin);
