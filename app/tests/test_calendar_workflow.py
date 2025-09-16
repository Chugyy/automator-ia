#!/usr/bin/env python3

import sys
import os
from datetime import datetime
from ..private.workflows.calendar_scheduler.main import execute

def test_calendar_workflow():
    test_data = {
        "event_name": "Test Event - Workflow Calendar",
        "base_datetime": "2024-12-15T10:00:00"
    }
    
    print(f"Testing calendar workflow with data: {test_data}")
    
    result = execute(test_data)
    
    print(f"Result: {result}")
    
    if result.get("success"):
        print("✅ Workflow executed successfully!")
        print(f"Event scheduled for: {result['result']['scheduled_date']}")
    else:
        print("❌ Workflow failed!")
        print(f"Error: {result.get('error')}")

if __name__ == "__main__":
    test_calendar_workflow()