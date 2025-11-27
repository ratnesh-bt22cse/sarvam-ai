"""
Input validation utilities
"""

import re
from datetime import datetime, timedelta
from typing import Optional


class ReservationValidator:
    """Validates reservation inputs"""
    
    @staticmethod
    def validate_date(date_str: str) -> bool:
        """Validate date format (YYYY-MM-DD)"""
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            today = datetime.now().date()
            max_future = today + timedelta(days=365)
            return today <= date_obj.date() <= max_future
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_time(time_str: str) -> bool:
        """Validate time format (HH:MM)"""
        try:
            datetime.strptime(time_str, "%H:%M")
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_party_size(party_size: int) -> bool:
        """Validate party size"""
        try:
            size = int(party_size)
            return 1 <= size <= 20
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """Validate phone number - accepts various formats"""
        # Remove common separators
        cleaned = re.sub(r'[\s\-\(\)\+]', '', str(phone))
        # Check if it's all digits and at least 7 characters
        return bool(re.match(r'^\d{7,15}$', cleaned))
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email address"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, str(email)))
    
    @staticmethod
    def validate_reservation_request(date: str, time: str, party_size: int, 
                                     phone: str, email: Optional[str] = None) -> dict:
        """Validate all reservation request fields"""
        errors = []
        
        if not ReservationValidator.validate_date(date):
            errors.append("Invalid date format or date out of range")
        
        if not ReservationValidator.validate_time(time):
            errors.append("Invalid time format (use HH:MM)")
        
        if not ReservationValidator.validate_party_size(party_size):
            errors.append("Invalid party size (must be 1-20)")
        
        if not ReservationValidator.validate_phone(phone):
            errors.append("Invalid phone number")
        
        if email and not ReservationValidator.validate_email(email):
            errors.append("Invalid email address")
        
        # Parse date for additional validation
        parsed_date = None
        try:
            parsed_date = datetime.strptime(date, "%Y-%m-%d")
        except:
            pass
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "parsed_date": parsed_date
        }
