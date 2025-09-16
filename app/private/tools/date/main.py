import datetime
from typing import Optional, Dict, Any, List

from ..base import BaseTool
from config.logger import logger

class DateTool(BaseTool):
    """Date calculation tool for relative date operations"""
    
    def authenticate(self) -> bool:
        """No authentication needed for date calculations"""
        if not self.validate_config():
            return False
        self.authenticated = True
        return True
    
    def execute(self, action: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a date action"""
        params = params or {}
        
        if not self.is_authenticated():
            return {"error": "Not authenticated"}
        
        try:
            if action == "calculate_date":
                return self._calculate_date(params)
            else:
                return {"error": f"Action {action} not supported"}
        except Exception as e:
            logger.error(f"Error executing {action}: {e}")
            return {"error": str(e)}
    
    def get_available_actions(self) -> List[str]:
        """Available actions"""
        return ["calculate_date"]
    
    def _calculate_date(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate relative date with enhanced logic from core"""
        days = params.get('days', 0)
        weeks = params.get('weeks', 0)
        weekday = params.get('weekday')
        format_str = params.get('format', '%d/%m/%Y')
        
        # Validate weekday
        if weekday is not None and not (0 <= weekday <= 6):
            return {"error": f"weekday ({weekday}) must be between 0 (Monday) and 6 (Sunday)"}
        
        today = datetime.datetime.now()
        
        weekday_names = {
            0: "Monday", 1: "Tuesday", 2: "Wednesday", 3: "Thursday",
            4: "Friday", 5: "Saturday", 6: "Sunday"
        }
        
        description = "today"
        new_date = today

        if days != 0 or weeks != 0:
            delta = datetime.timedelta(days=days + (weeks*7) if weeks is not None else days)
            new_date = today + delta
            
            # Enhanced description logic from core
            if days == 1 and weeks == 0:
                description = "tomorrow"
            elif days == -1 and weeks == 0:
                description = "yesterday"
            elif days == 2 and weeks == 0:
                description = "day after tomorrow"
            elif days == -2 and weeks == 0:
                description = "day before yesterday"
            elif weeks == 1 and days == 0:
                description = "in one week"
            elif weeks == -1 and days == 0:
                description = "one week ago"
            else:
                parts = []
                if weeks is not None and weeks != 0:
                    parts.append(f"{abs(weeks)} week{'s' if abs(weeks) > 1 else ''}")
                if days is not None and days != 0:
                    parts.append(f"{abs(days)} day{'s' if abs(days) > 1 else ''}")
                
                if not parts:
                    description = "today"
                elif (weeks or 0) > 0 or (days or 0) > 0:
                    description = f"in {' and '.join(parts)}"
                else:
                    description = f"{' and '.join(parts)} ago"
                    
        elif weekday is not None:
            current_weekday = today.weekday()
            days_ahead = weekday - current_weekday
            
            if days_ahead <= 0:  # If it's today or already passed this week
                days_ahead += 7  # Move to next week
                
            new_date = today + datetime.timedelta(days=days_ahead)
            description = f"next {weekday_names[weekday]}"
        
        formatted_date = new_date.strftime(format_str)
        day_name = weekday_names[new_date.weekday()]
        
        return {
            "status": "success",
            "data": {
                "date": formatted_date,
                "day": day_name,
                "description": description,
                "calculation": {
                    "days": days,
                    "weeks": weeks,
                    "weekday": weekday
                }
            }
        }