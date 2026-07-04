import sqlite3
import json
from pathlib import Path

def build_db():
    pipeline_dir = Path(__file__).resolve().parent
    extractions_dir = pipeline_dir / "extractions"
    db_path = pipeline_dir / "pedal_schematics.db"
    schema_path = pipeline_dir / "schema.sql"
    
    if db_path.exists():
        db_path.unlink()
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    with open(schema_path, "r") as f:
        cursor.executescript(f.read())
        
    conn.commit()
    
    files = list(extractions_dir.glob("*.json"))
    print(f"Found {len(files)} extractions to import.")
    
    imported = 0
    for file in files:
        try:
            with open(file, "r") as f:
                data = json.load(f)
                
            source_image = data.get("source_image", file.name)
            name = data.get("name", "")
            issues_list = data.get("issues", [])
            issues = "\n".join(issues_list) if isinstance(issues_list, list) else str(issues_list)
            
            cursor.execute("INSERT INTO schematics (source_image, name, design_notes) VALUES (?, ?, ?)", 
                           (source_image, name, issues))
            schematic_id = cursor.lastrowid
            
            parts = data.get("parts", [])
            for comp in parts:
                c_name = comp.get("ref", comp.get("name", ""))
                c_type = comp.get("type", "")
                c_val = comp.get("value", "")
                cursor.execute("INSERT INTO components (schematic_id, name, type, value) VALUES (?, ?, ?, ?)",
                               (schematic_id, c_name, c_type, c_val))
                               
            nets = data.get("nets", [])
            for net in nets:
                net_name = net.get("name", "")
                pins = net.get("pins", [])
                
                # We want from_pin and to_pin. If a net has N pins, we can create connections between all of them or just sequential.
                # A better representation for a netlist is a "net_pins" table or just fully connected edges.
                # Since the schema expects (from_pin, to_pin), we can just pair them sequentially: A->B, B->C
                for i in range(len(pins) - 1):
                    cursor.execute("INSERT INTO connections (schematic_id, from_pin, to_pin) VALUES (?, ?, ?)",
                                   (schematic_id, pins[i], pins[i+1]))
                               
            imported += 1
        except Exception as e:
            print(f"Error importing {file.name}: {e}")
            
    conn.commit()
    
    cursor.execute("SELECT COUNT(*) FROM schematics")
    print(f"Imported {cursor.fetchone()[0]} schematics.")
    
    cursor.execute("SELECT COUNT(*) FROM components")
    print(f"Imported {cursor.fetchone()[0]} components.")
    
    cursor.execute("SELECT COUNT(*) FROM connections")
    print(f"Imported {cursor.fetchone()[0]} connections.")
    
    conn.close()

if __name__ == "__main__":
    build_db()
