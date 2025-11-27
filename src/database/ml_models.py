"""
ML Models for recommendations and predictions
"""

import random
from typing import Dict, List, Any, Optional


class NoShowPredictor:
    """Predicts probability of reservation no-show"""
    
    def predict_risk(
        self,
        party_size: int,
        advance_days: int,
        occasion: str = "casual",
        customer_phone: Optional[str] = None
    ) -> float:
        """Predict no-show probability (0-1)"""
        risk_score = 0.20  # Base 20% no-show rate
        
        # Adjust based on factors
        if party_size <= 2:
            risk_score -= 0.05
        elif party_size >= 8:
            risk_score += 0.15
        
        if advance_days <= 1:
            risk_score += 0.20
        elif advance_days >= 14:
            risk_score -= 0.10
        
        if "romantic" in occasion.lower() or "anniversary" in occasion.lower():
            risk_score -= 0.15
        elif "business" in occasion.lower():
            risk_score -= 0.05
        
        return max(0.0, min(1.0, risk_score))


class RecommendationEngine:
    """Generates personalized restaurant recommendations"""
    
    def __init__(self, db):
        """Initialize with database"""
        self.db = db
    
    def get_recommendations(
        self,
        party_size: int,
        cuisine: Optional[str] = None,
        occasion: str = "casual",
        budget: str = "moderate",
        date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get personalized restaurant recommendations"""
        cursor = self.db.conn.cursor()
        
        query = "SELECT * FROM locations WHERE 1=1"
        params = []
        
        if cuisine:
            query += " AND cuisine LIKE ?"
            params.append(f"%{cuisine}%")
        
        query += " ORDER BY avg_rating DESC LIMIT 10"
        
        cursor.execute(query, params)
        locations = cursor.fetchall()
        
        recommendations = []
        for location in locations:
            score = self._calculate_score(location, party_size, occasion, budget)
            
            recommendations.append({
                "location_id": location["location_id"],
                "name": location["name"],
                "cuisine": location["cuisine"],
                "address": location["address"],
                "city": location["city"],
                "rating": location["avg_rating"],
                "price_range": location["price_range"],
                "match_score": round(score, 3),
                "match_reason": self._get_match_reason(location, cuisine, occasion)
            })
        
        recommendations.sort(key=lambda x: x["match_score"], reverse=True)
        return recommendations[:5]
    
    def _calculate_score(self, location: Dict, party_size: int, occasion: str, budget: str) -> float:
        """Calculate recommendation score"""
        score = 0.5
        
        # Rating factor
        score += (location["avg_rating"] / 5.0) * 0.3
        
        # Price match
        budget_map = {"budget": "budget", "moderate": "moderate", "upscale": "upscale"}
        if location["price_range"] == budget_map.get(budget, "moderate"):
            score += 0.2
        
        return min(1.0, score)
    
    def _get_match_reason(self, location: Dict, cuisine: Optional[str], occasion: str) -> str:
        """Generate match reason"""
        reasons = []
        
        if cuisine and cuisine.lower() in location["cuisine"].lower():
            reasons.append(f"Specializes in {location['cuisine']}")
        
        if location["avg_rating"] >= 4.5:
            reasons.append("Highly-rated")
        
        return " • ".join(reasons) if reasons else "Good match for your needs"
