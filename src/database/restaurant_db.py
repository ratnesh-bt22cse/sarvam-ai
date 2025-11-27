"""
Restaurant Database - SQLite implementation
Manages 87+ restaurant locations and reservations
"""

import sqlite3
import random
import string
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path


class RestaurantDatabase:
    """SQLite database for restaurant reservation system"""
    
    def __init__(self, db_path: str = "goodfoods.db"):
        """Initialize database"""
        self.db_path = db_path
        self.conn = None
        self.init_database()
    
    def init_database(self):
        """Initialize database tables and populate data"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        cursor = self.conn.cursor()
        
        # Locations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS locations (
                location_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                address TEXT NOT NULL,
                city TEXT NOT NULL,
                phone TEXT NOT NULL,
                cuisine TEXT NOT NULL,
                seating_capacity INTEGER NOT NULL,
                avg_rating REAL DEFAULT 4.5,
                price_range TEXT DEFAULT 'moderate',
                hours_open TEXT DEFAULT '11:00',
                hours_close TEXT DEFAULT '23:00',
                special_features TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Reservations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reservations (
                confirmation_number TEXT PRIMARY KEY,
                location_id TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                party_size INTEGER NOT NULL,
                customer_name TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                customer_email TEXT,
                special_requests TEXT,
                occasion TEXT,
                status TEXT DEFAULT 'confirmed',
                table_number TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(location_id) REFERENCES locations(location_id)
            )
        """)
        
        self.conn.commit()
        
        # Populate if empty
        cursor.execute("SELECT COUNT(*) as count FROM locations")
        if cursor.fetchone()["count"] == 0:
            self._populate_locations()
    
    def _populate_locations(self):
        """Populate 87 restaurant locations"""
        cursor = self.conn.cursor()
        
        # Base restaurant data
        cuisines = ["Italian", "Japanese", "French", "Indian", "Chinese", "Mexican", "Thai", 
                   "Korean", "Spanish", "American", "Mediterranean", "Turkish", "Vietnamese",
                   "Greek", "Brazilian", "Lebanese", "Malaysian", "Moroccan"]
        
        # Real US cities
        cities = ["San Francisco", "New York", "Los Angeles", "Chicago", "Austin", 
                 "Seattle", "Miami", "Boston"]
        
        restaurant_types = ["Kitchen", "Bistro", "Table", "House", "Restaurant", "Grill",
                          "Tavern", "Lounge", "Bar & Grill", "Eatery"]
        
        price_ranges = ["budget", "moderate", "upscale", "fine_dining"]
        
        for i in range(1, 88):
            location_id = f"LOC{i:03d}"
            cuisine = random.choice(cuisines)
            city = random.choice(cities)
            restaurant_type = random.choice(restaurant_types)
            
            name = f"{cuisine} {restaurant_type}"
            if i <= 10:
                # Premium locations
                name = f"The {cuisine} {restaurant_type}"
            
            address = f"{random.randint(100, 9999)} {random.choice(['Main', 'Oak', 'Elm', 'Market', 'Grand'])} St"
            phone = f"555-{random.randint(1000, 9999)}"
            capacity = random.randint(40, 150)
            rating = round(3.5 + random.random() * 1.5, 1)
            price = random.choice(price_ranges)
            
            cursor.execute("""
                INSERT INTO locations (
                    location_id, name, address, city, phone, cuisine, seating_capacity,
                    avg_rating, price_range, special_features
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (location_id, name, address, city, phone, cuisine, capacity, rating, price, ""))
        
        self.conn.commit()
    
    def get_available_slots(
        self,
        date: str,
        time: str,
        party_size: int,
        location_id: Optional[str] = None,
        cuisine: Optional[str] = None,
        city: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get available reservation slots"""
        cursor = self.conn.cursor()
        
        query = """
            SELECT 
                l.location_id, l.name, l.cuisine, l.address, l.city,
                l.avg_rating, l.seating_capacity, l.price_range,
                COUNT(r.confirmation_number) as reserved_count
            FROM locations l
            LEFT JOIN reservations r ON l.location_id = r.location_id 
                AND r.date = ? AND r.time = ? AND r.status = 'confirmed'
            WHERE 1=1
        """
        params = [date, time]
        
        if location_id:
            query += " AND l.location_id = ?"
            params.append(location_id)
        
        if cuisine:
            query += " AND l.cuisine LIKE ?"
            params.append(f"%{cuisine}%")
        
        if city:
            query += " AND l.city LIKE ?"
            params.append(f"%{city}%")
        
        query += " GROUP BY l.location_id ORDER BY l.avg_rating DESC LIMIT 20"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        slots = []
        for row in rows:
            available = row["seating_capacity"] - (row["reserved_count"] * 4)  # Rough estimate
            if available >= party_size:
                slots.append({
                    "location_id": row["location_id"],
                    "restaurant_name": row["name"],
                    "cuisine": row["cuisine"],
                    "address": row["address"],
                    "city": row["city"],
                    "rating": row["avg_rating"],
                    "price_range": row["price_range"],
                    "available_capacity": available
                })
        
        return slots
    
    def create_reservation(
        self,
        location_id: str,
        date: str,
        time: str,
        party_size: int,
        customer_name: str,
        customer_phone: str,
        customer_email: str = "",
        special_requests: str = "",
        occasion: str = ""
    ) -> Dict[str, Any]:
        """Create a new reservation"""
        cursor = self.conn.cursor()
        
        # Generate confirmation number
        confirmation_number = f"GF-{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}"
        
        # Get location details
        cursor.execute("SELECT name, address FROM locations WHERE location_id = ?", (location_id,))
        location = cursor.fetchone()
        
        if not location:
            raise ValueError(f"Location {location_id} not found")
        
        # Insert reservation
        cursor.execute("""
            INSERT INTO reservations (
                confirmation_number, location_id, date, time, party_size,
                customer_name, customer_phone, customer_email,
                special_requests, occasion, table_number
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            confirmation_number, location_id, date, time, party_size,
            customer_name, customer_phone, customer_email,
            special_requests, occasion, f"T{random.randint(1, 30)}"
        ))
        
        self.conn.commit()
        
        return {
            "confirmation_number": confirmation_number,
            "restaurant_name": location["name"],
            "location": location["address"],
            "date": date,
            "time": time,
            "party_size": party_size,
            "customer_name": customer_name,
            "table_number": f"T{random.randint(1, 30)}"
        }
    
    def modify_reservation(self, confirmation_number: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Modify an existing reservation"""
        cursor = self.conn.cursor()
        
        set_clause = ", ".join([f"{key} = ?" for key in updates.keys()])
        query = f"UPDATE reservations SET {set_clause} WHERE confirmation_number = ?"
        params = list(updates.values()) + [confirmation_number]
        
        cursor.execute(query, params)
        self.conn.commit()
        
        return {"success": True, "confirmation_number": confirmation_number}
    
    def cancel_reservation(self, confirmation_number: str, reason: str = "") -> Dict[str, Any]:
        """Cancel a reservation"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE reservations 
            SET status = 'cancelled'
            WHERE confirmation_number = ?
        """, (confirmation_number,))
        
        self.conn.commit()
        return {"success": True, "confirmation_number": confirmation_number}
    
    def get_location_details(self, location_id: str) -> Dict[str, Any]:
        """Get location details"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM locations WHERE location_id = ?", (location_id,))
        location = cursor.fetchone()
        
        if not location:
            raise ValueError(f"Location {location_id} not found")
        
        return dict(location)
    
    def predict_demand(self, location_id: str, date: str, time: str) -> Dict[str, Any]:
        """Predict demand (simplified)"""
        return {
            "location_id": location_id,
            "occupancy_percent": random.random() * 0.5 + 0.3,
            "predicted_covers": random.randint(30, 80),
            "recommendation": "Moderately busy - book soon"
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get system statistics"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT COUNT(*) as count FROM locations")
        total_restaurants = cursor.fetchone()["count"]
        
        cursor.execute("SELECT COUNT(*) as count FROM reservations WHERE status = 'confirmed'")
        total_reservations = cursor.fetchone()["count"]
        
        return {
            "total_restaurants": total_restaurants,
            "total_reservations": total_reservations,
            "avg_no_show_rate": 0.15
        }
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
