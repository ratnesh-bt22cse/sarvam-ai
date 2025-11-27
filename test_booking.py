#!/usr/bin/env python3
"""
Direct test of the booking system without AI
"""

from src.database.restaurant_db import RestaurantDatabase
from src.database.ml_models import NoShowPredictor, RecommendationEngine
from src.utils.validators import ReservationValidator

def test_direct_booking():
    """Test creating a reservation directly"""
    
    print("🧪 Testing Direct Booking System\n")
    
    # Initialize components
    print("1. Initializing database...")
    db = RestaurantDatabase()
    
    print("2. Initializing ML models...")
    no_show = NoShowPredictor()
    validator = ReservationValidator()
    
    # Test search
    print("\n3. Searching for restaurants...")
    results = db.get_available_slots(
        date="2025-11-27",
        time="19:00",
        party_size=2,
        location_id=None,
        cuisine="Japanese",
        city="Los Angeles"
    )
    print(f"   Found {len(results)} restaurants")
    if results:
        print(f"   First result keys: {list(results[0].keys())}")
        print(f"   First result: {dict(results[0])}")

    
    # Test validation
    print("\n4. Validating booking data...")
    validation = validator.validate_reservation_request(
        date="2025-11-27",
        time="19:00",
        party_size=2,
        phone="1234567890",
        email=None
    )
    print(f"   Valid: {validation['valid']}")
    if not validation['valid']:
        print(f"   Errors: {validation['errors']}")
        return
    
    # Test no-show prediction
    print("\n5. Predicting no-show risk...")
    risk = no_show.predict_risk(
        party_size=2,
        advance_days=1,
        occasion="dinner",
        customer_phone="1234567890"
    )
    print(f"   Risk: {risk:.2%}")
    
    # Create reservation
    print("\n6. Creating reservation...")
    try:
        reservation = db.create_reservation(
            location_id="LOC081",  # Japanese Bar & Grill
            date="2025-11-27",
            time="19:00",
            party_size=2,
            customer_name="John Doe",
            customer_phone="1234567890",
            customer_email="",
            special_requests="",
            occasion="dinner"
        )
        
        print(f"   ✅ SUCCESS!")
        print(f"   Confirmation: {reservation['confirmation_number']}")
        print(f"   Restaurant: {reservation['restaurant_name']}")
        print(f"   Date: {reservation['reservation_date']}")
        print(f"   Time: {reservation['reservation_time']}")
        
    except Exception as e:
        print(f"   ❌ FAILED: {str(e)}")
        import traceback
        traceback.print_exc()
    
    # Verify in database
    print("\n7. Verifying in database...")
    import sqlite3
    conn = sqlite3.connect('goodfoods.db')
    cur = conn.cursor()
    count = cur.execute("SELECT COUNT(*) FROM reservations").fetchone()[0]
    print(f"   Total reservations in DB: {count}")
    
    if count > 0:
        latest = cur.execute("""
            SELECT confirmation_number, customer_name, restaurant_name 
            FROM reservations 
            ORDER BY created_at DESC 
            LIMIT 1
        """).fetchone()
        print(f"   Latest: {latest[0]} - {latest[1]} at {latest[2]}")
    
    conn.close()
    
    print("\n✅ Test Complete!")

if __name__ == "__main__":
    test_direct_booking()
