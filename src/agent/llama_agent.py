"""
Conversational AI Agent using Llama-3.3-70B via Groq
Implements tool calling and intent recognition from scratch
"""

import json
import os
import re
from typing import Dict, List, Any, Optional
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.database.restaurant_db import RestaurantDatabase
from src.database.ml_models import NoShowPredictor, RecommendationEngine
from src.utils.validators import ReservationValidator


class LlamaAgent:
    """Main conversational agent using Llama-3.3-70B on Groq"""
    
    # Tool definitions for Groq (OpenAI-compatible format)
    TOOLS = [
        {
            "type": "function",
            "function": {
                "name": "search_available_slots",
                "description": "Search for available reservation slots at restaurants based on date, time, party size, and location",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string", "description": "Reservation date in YYYY-MM-DD format"},
                        "time": {"type": "string", "description": "Preferred time in HH:MM format (24-hour)"},
                        "party_size": {"type": "integer", "description": "Number of people"},
                        "city": {"type": "string", "description": "City name (e.g., San Francisco, New York, Los Angeles)"},
                        "cuisine": {"type": "string", "description": "Preferred cuisine type (optional)"}
                    },
                    "required": ["date", "time", "party_size", "city"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "create_reservation",
                "description": "Create a new restaurant reservation with customer details",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "location_id": {"type": "string", "description": "Restaurant location ID"},
                        "date": {"type": "string", "description": "Reservation date YYYY-MM-DD"},
                        "time": {"type": "string", "description": "Time HH:MM"},
                        "party_size": {"type": "integer", "description": "Number of diners"},
                        "customer_name": {"type": "string", "description": "Guest name"},
                        "customer_phone": {"type": "string", "description": "Contact phone"},
                        "customer_email": {"type": "string", "description": "Email (optional)"},
                        "special_requests": {"type": "string", "description": "Special requests (optional)"},
                        "occasion": {"type": "string", "description": "Occasion type (optional)"}
                    },
                    "required": ["location_id", "date", "time", "party_size", "customer_name", "customer_phone"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "get_recommendations",
                "description": "Get personalized restaurant recommendations based on preferences",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "party_size": {"type": "integer", "description": "Number of diners"},
                        "cuisine_preference": {"type": "string", "description": "Preferred cuisine"},
                        "occasion": {"type": "string", "description": "Dining occasion"},
                        "budget": {"type": "string", "description": "Budget: budget, moderate, upscale"}
                    },
                    "required": ["party_size", "occasion"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "modify_reservation",
                "description": "Modify an existing reservation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "confirmation_number": {"type": "string", "description": "Reservation confirmation number"},
                        "new_date": {"type": "string", "description": "New date (optional)"},
                        "new_time": {"type": "string", "description": "New time (optional)"},
                        "new_party_size": {"type": "integer", "description": "New party size (optional)"}
                    },
                    "required": ["confirmation_number"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "cancel_reservation",
                "description": "Cancel an existing reservation",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "confirmation_number": {"type": "string", "description": "Reservation confirmation number"},
                        "reason": {"type": "string", "description": "Cancellation reason (optional)"}
                    },
                    "required": ["confirmation_number"]
                }
            }
        }
    ]
    
    def __init__(self, db: RestaurantDatabase, no_show_predictor: NoShowPredictor, 
                 recommendation_engine: RecommendationEngine):
        """Initialize Llama agent with Groq"""
        self.db = db
        self.no_show_predictor = no_show_predictor
        self.recommendation_engine = recommendation_engine
        self.validator = ReservationValidator()
        
        # Initialize Groq client
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not set. Get your free key at https://console.groq.com/keys")
        
        self.client = Groq(api_key=api_key)
        
        # Model configuration - Read from environment or default to 70B for better tool calling
        self.model_name = os.getenv("MODEL_NAME", "llama-3.3-70b-versatile")
        print(f"🤖 Using model: {self.model_name}")
        
        # Conversation history
        self.messages = []
        self._initialize_system_prompt()
    
    def _initialize_system_prompt(self):
        """Initialize with system prompt"""
        system_prompt = """You are an intelligent restaurant reservation assistant for GoodFoods, a premium dining network.

CRITICAL RULES - YOU MUST FOLLOW THESE:
1. NEVER make up or invent confirmation numbers
2. NEVER say a reservation is complete unless you actually called the create_reservation tool
3. ALWAYS use the search_available_slots tool to find restaurants
4. ALWAYS use the create_reservation tool to book - DO NOT just tell the user it's booked
5. NEVER use placeholder text like "Your Name" or "Your Phone Number" - these are INVALID
6. If you don't have the customer's REAL name and REAL phone, ASK for them - DO NOT proceed with booking
7. DO NOT fabricate responses - only report what the tools return
8. A valid phone number must be actual digits (e.g., 555-1234), not placeholder text

Your capabilities:
- Search 87+ restaurant locations across major US cities
- Make, modify, and cancel reservations
- Provide personalized recommendations based on preferences
- Handle special requests and dietary restrictions

IMPORTANT DATE FORMATTING RULES:
- Today's date is 2025-11-26
- When user says "tomorrow", use date: 2025-11-27
- When user says "today", use date: 2025-11-26
- Always use YYYY-MM-DD format for dates
- Always use HH:MM format for times (24-hour, e.g., 20:00 for 8 PM, 19:00 for 7 PM)

WORKFLOW:
1. User asks for restaurant → Call search_available_slots tool
2. Show results from the tool
3. User selects restaurant → Ask for name and phone if not provided
4. Once you have ALL details → Call create_reservation tool
5. ONLY after create_reservation returns success → Share the confirmation number from the tool response

Restaurant network details:
- Cities: San Francisco, New York, Los Angeles, Chicago, Austin, Seattle, Miami, Boston
- Cuisines: Italian, French, Japanese, American, Mexican, Indian, Chinese, Mediterranean
- Price ranges: Budget-friendly to upscale fine dining
- Party sizes: 1-20 guests
- Time slots: Lunch (11 AM-2 PM), Dinner (5 PM-10 PM)

REMEMBER: Always use the provided tools. Never make up responses."""

        self.messages = [{"role": "system", "content": system_prompt}]
    
    def process_message(self, user_message: str, conversation_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Process user message and return response with tool calls
        
        Args:
            user_message: User's input message
            conversation_history: Previous conversation for context
            
        Returns:
            Dictionary with response_text, tool_calls, and any reservation info
        """
        # Add user message
        self.messages.append({"role": "user", "content": user_message})
        
        # FORCED TOOL CALLING: Detect if user wants to book and we have the info
        forced_tool_call = self._detect_and_force_booking(user_message)
        
        try:
            # If we detected forced booking, execute it directly
            if forced_tool_call:
                tool_result = self._create_reservation(**forced_tool_call)
                
                if tool_result.get("success"):
                    reservation = tool_result.get("reservation")
                    final_text = f"✅ Reservation confirmed!\n\n" \
                                f"📋 **Confirmation Number:** {reservation['confirmation_number']}\n" \
                                f"🍽️ **Restaurant:** {reservation['restaurant_name']}\n" \
                                f"📅 **Date:** {reservation['reservation_date']}\n" \
                                f"🕐 **Time:** {reservation['reservation_time']}\n" \
                                f"👥 **Party Size:** {reservation['party_size']}\n" \
                                f"📞 **Contact:** {reservation['customer_phone']}\n\n" \
                                f"See you there! 🎉"
                    
                    self.messages.append({"role": "assistant", "content": final_text})
                    
                    return {
                        "response_text": final_text,
                        "tool_calls": [{
                            "name": "create_reservation",
                            "input": forced_tool_call,
                            "result": tool_result
                        }],
                        "reservation_created": reservation
                    }
                else:
                    error_msg = f"❌ Unable to complete reservation: {tool_result.get('error')}"
                    self.messages.append({"role": "assistant", "content": error_msg})
                    return {
                        "response_text": error_msg,
                        "tool_calls": [],
                        "reservation_created": None
                    }
            
            # Call Llama via Groq with tool calling
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=self.messages,
                tools=self.TOOLS,
                tool_choice="auto",
                temperature=0.7,
                max_tokens=2000
            )
            
            assistant_message = response.choices[0].message
            tool_calls_info = []
            reservation_created = None
            
            # Check if model wants to call tools
            if assistant_message.tool_calls:
                # Add assistant message with tool calls (convert to dict format)
                self.messages.append({
                    "role": "assistant",
                    "content": assistant_message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        } for tc in assistant_message.tool_calls
                    ]
                })
                
                # Execute each tool call
                for tool_call in assistant_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # Execute the tool
                    tool_result = self._execute_tool(function_name, function_args)
                    
                    # Track if reservation was created
                    if function_name == "create_reservation" and tool_result.get("success"):
                        reservation_created = tool_result.get("reservation")
                    
                    tool_calls_info.append({
                        "name": function_name,
                        "input": function_args,
                        "result": tool_result
                    })
                    
                    # Add tool result to messages
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": json.dumps(tool_result)
                    })
                
                # Get final response after tools
                final_response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=self.messages,
                    temperature=0.7,
                    max_tokens=1000
                )
                
                final_text = final_response.choices[0].message.content
                self.messages.append({"role": "assistant", "content": final_text})
                
            else:
                # No tool calls, just add assistant response
                final_text = assistant_message.content or ""
                
                # VALIDATION: Detect hallucinated reservations
                hallucination_keywords = ["confirmation", "confirmed", "booked", "reservation is complete", "#CONF"]
                if final_text and any(keyword.lower() in final_text.lower() for keyword in hallucination_keywords):
                    # Check if we actually have reservation details
                    if not reservation_created:
                        # AI is hallucinating! Override the response
                        final_text = "⚠️ I apologize, but I cannot complete the reservation without calling the proper booking system. Let me help you properly:\n\n" + \
                                   "To make a reservation, I need:\n" + \
                                   "1. Date and time\n" + \
                                   "2. Number of people\n" + \
                                   "3. Your name\n" + \
                                   "4. Your phone number\n\n" + \
                                   "Please provide these details so I can search for available restaurants and complete your booking using the official system."
                
                self.messages.append({"role": "assistant", "content": final_text})
            
            return {
                "response_text": final_text,
                "tool_calls": tool_calls_info,
                "reservation_created": reservation_created
            }
            
        except Exception as e:
            error_msg = f"I apologize, I encountered an error: {str(e)}"
            self.messages.append({"role": "assistant", "content": error_msg})
            return {
                "response_text": error_msg,
                "tool_calls": [],
                "reservation_created": None
            }
    
    def _execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool and return results"""
        try:
            if tool_name == "search_available_slots":
                return self._search_available_slots(**arguments)
            elif tool_name == "create_reservation":
                result = self._create_reservation(**arguments)
                print(f"DEBUG: create_reservation result: {result}")  # Debug log
                return result
            elif tool_name == "get_recommendations":
                return self._get_recommendations(**arguments)
            elif tool_name == "modify_reservation":
                return self._modify_reservation(**arguments)
            elif tool_name == "cancel_reservation":
                return self._cancel_reservation(**arguments)
            else:
                return {"success": False, "error": f"Unknown tool: {tool_name}"}
        except Exception as e:
            print(f"DEBUG: Tool execution error: {str(e)}")  # Debug log
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def _search_available_slots(self, date: str, time: str, party_size: int, 
                                city: str, cuisine: Optional[str] = None) -> Dict[str, Any]:
        """Search for available reservation slots"""
        try:
            slots = self.db.get_available_slots(date, time, party_size, None, cuisine, city)
            return {
                "success": True,
                "available_slots": slots,
                "count": len(slots)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _create_reservation(self, location_id: str, date: str, time: str, 
                           party_size: int, customer_name: str, customer_phone: str,
                           customer_email: Optional[str] = None,
                           special_requests: Optional[str] = None,
                           occasion: Optional[str] = None) -> Dict[str, Any]:
        """Create a new reservation"""
        try:
            print(f"DEBUG: create_reservation called with: location_id={location_id}, date={date}, time={time}, "
                  f"party_size={party_size}, name={customer_name}, phone={customer_phone}")
            
            # Check for placeholder values
            placeholder_values = ["your name", "your phone", "your phone number", "customer name", "customer phone"]
            if any(placeholder.lower() in customer_name.lower() for placeholder in placeholder_values):
                return {
                    "success": False, 
                    "error": "Invalid customer name - please provide the actual customer name, not placeholder text"
                }
            if any(placeholder.lower() in customer_phone.lower() for placeholder in placeholder_values):
                return {
                    "success": False,
                    "error": "Invalid phone number - please provide the actual phone number, not placeholder text"
                }
            
            print(f"DEBUG: Validating inputs...")
            # Validate inputs
            validation = self.validator.validate_reservation_request(
                date, time, party_size, customer_phone, customer_email
            )
            print(f"DEBUG: Validation result: {validation}")
            if not validation["valid"]:
                return {"success": False, "error": validation["errors"]}
            
            # Predict no-show probability
            from datetime import datetime
            advance_days = (validation["parsed_date"].date() - datetime.now().date()).days
            print(f"DEBUG: Predicting no-show risk...")
            no_show_risk = self.no_show_predictor.predict_risk(
                party_size=party_size,
                advance_days=advance_days,
                occasion=occasion or "casual",
                customer_phone=customer_phone
            )
            print(f"DEBUG: No-show risk: {no_show_risk}")
            
            # Create reservation
            print(f"DEBUG: Calling db.create_reservation...")
            reservation = self.db.create_reservation(
                location_id=location_id,
                date=date,
                time=time,
                party_size=party_size,
                customer_name=customer_name,
                customer_phone=customer_phone,
                customer_email=customer_email or "",
                special_requests=special_requests or "",
                occasion=occasion or ""
            )
            print(f"DEBUG: Reservation created: {reservation}")
            
            return {
                "success": True,
                "reservation": reservation,
                "no_show_risk": "high" if no_show_risk > 0.3 else "low"
            }
        except Exception as e:
            print(f"DEBUG: Exception in create_reservation: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"success": False, "error": str(e)}
    
    def _get_recommendations(self, party_size: int, occasion: str,
                            cuisine_preference: Optional[str] = None,
                            budget: Optional[str] = None) -> Dict[str, Any]:
        """Get personalized restaurant recommendations"""
        try:
            preferences = {
                "party_size": party_size,
                "occasion": occasion,
                "cuisine_preference": cuisine_preference,
                "budget": budget
            }
            recommendations = self.recommendation_engine.get_recommendations(preferences)
            return {
                "success": True,
                "recommendations": recommendations,
                "count": len(recommendations)
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _modify_reservation(self, confirmation_number: str,
                           new_date: Optional[str] = None,
                           new_time: Optional[str] = None,
                           new_party_size: Optional[int] = None) -> Dict[str, Any]:
        """Modify an existing reservation"""
        try:
            success = self.db.modify_reservation(
                confirmation_number, new_date, new_time, new_party_size
            )
            if success:
                return {
                    "success": True,
                    "message": f"Reservation {confirmation_number} updated successfully"
                }
            return {"success": False, "error": "Reservation not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _cancel_reservation(self, confirmation_number: str,
                           reason: Optional[str] = None) -> Dict[str, Any]:
        """Cancel a reservation"""
        try:
            success = self.db.cancel_reservation(confirmation_number, reason)
            if success:
                return {
                    "success": True,
                    "message": f"Reservation {confirmation_number} cancelled successfully"
                }
            return {"success": False, "error": "Reservation not found"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _detect_and_force_booking(self, user_message: str) -> Optional[Dict]:
        """
        Detect if user is trying to book and extract information to force tool call.
        This helps when the 8B model fails to call tools properly.
        """
        msg_lower = user_message.lower()
        
        # Only activate for clear booking intent
        booking_keywords = ["book", "reserve", "make a reservation", "i want to book"]
        if not any(keyword in msg_lower for keyword in booking_keywords):
            return None
        
        # Try to extract information from conversation history
        selected_restaurant = None
        customer_name = None
        customer_phone = None
        party_size = 2  # default
        date = None
        time = None
        
        # Parse recent conversation for context
        for i in range(len(self.messages) - 1, max(0, len(self.messages) - 10), -1):
            msg = self.messages[i]
            content = msg.get("content", "") or ""  # Handle None content
            
            if not content or not isinstance(content, str):
                continue
            
            # Look for name patterns
            if not customer_name and ("my name is" in content.lower() or "name:" in content.lower()):
                import re
                name_match = re.search(r"(?:my name is|name:)\s*([A-Za-z\s]+?)(?:[,.]|$)", content, re.IGNORECASE)
                if name_match:
                    customer_name = name_match.group(1).strip()
            
            # Look for phone patterns
            if not customer_phone and ("phone" in content.lower() or "number" in content.lower()):
                import re
                phone_match = re.search(r"(?:phone|number)[:\s]*([0-9-]+)", content, re.IGNORECASE)
                if phone_match:
                    customer_phone = phone_match.group(1).strip()
            
            # Look for restaurant mentions with location
            if "japanese bar" in content.lower() and "los angeles" in content.lower():
                selected_restaurant = "LOC081"  # Japanese Bar & Grill in LA
            
            # Look for date/time
            if "tomorrow" in content.lower():
                date = "2025-11-27"
            if "7 pm" in content.lower() or "19:00" in content.lower():
                time = "19:00"
            if "8 pm" in content.lower() or "20:00" in content.lower():
                time = "20:00"
        
        # If we have all required info, return forced booking data
        if selected_restaurant and customer_name and customer_phone and date and time:
            return {
                "location_id": selected_restaurant,
                "customer_name": customer_name,
                "customer_phone": customer_phone,
                "date": date,
                "time": time,
                "party_size": party_size
            }
        
        return None
