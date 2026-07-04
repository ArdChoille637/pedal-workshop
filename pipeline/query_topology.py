import sqlite3
from pathlib import Path

def query_topology():
    db_path = Path(__file__).resolve().parent / "pedal_schematics.db"
    if not db_path.exists():
        print("Database not found. Please run build_database.py first.")
        return
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print("--- Patent Infringement Research Query Tool ---")
    print("Example Query: Find pedals where a Diode (clipping) connects to the output of an OpAmp")
    
    # This query finds instances where a Diode is connected to an OpAmp
    # Often a signature of specific overdrive/distortion topologies (e.g. Tube Screamer feedback clipping vs Rat hard clipping)
    query = """
    SELECT s.name, c1.name AS opamp, c2.name AS diode, conn.from_pin, conn.to_pin
    FROM connections conn
    JOIN schematics s ON conn.schematic_id = s.id
    JOIN components c1 ON conn.schematic_id = c1.schematic_id 
        AND (conn.from_pin LIKE c1.name || '%' OR conn.to_pin LIKE c1.name || '%')
    JOIN components c2 ON conn.schematic_id = c2.schematic_id 
        AND (conn.from_pin LIKE c2.name || '%' OR conn.to_pin LIKE c2.name || '%')
    WHERE (c1.type LIKE '%OpAmp%' OR c1.type LIKE '%IC%') 
      AND (c2.type LIKE '%Diode%' OR c2.type LIKE '%LED%')
      AND c1.id != c2.id
    GROUP BY s.id, c1.name, c2.name
    LIMIT 10;
    """
    
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        if not results:
            print("No matching topologies found (or connections are loosely defined).")
        else:
            print(f"Found {len(results)} matching connections:")
            for row in results:
                print(f"Schematic: {row[0]}")
                print(f"  Connection: {row[1]} <-> {row[2]} ({row[3]} to {row[4]})")
                print("-" * 40)
    except Exception as e:
        print(f"Query Error: {e}")
        
    print("\nExample Query 2: List the most common components used across all pedals")
    query2 = """
    SELECT type, COUNT(*) as count 
    FROM components 
    WHERE type != '' 
    GROUP BY type 
    ORDER BY count DESC 
    LIMIT 5;
    """
    cursor.execute(query2)
    print(cursor.fetchall())
    
    conn.close()

if __name__ == "__main__":
    query_topology()
