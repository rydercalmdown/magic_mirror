"""
Configuration management for the backend
"""

import json
import os
from pathlib import Path


class Config:
    """Configuration class for backend settings"""
    
    def __init__(self):
        self.BASE_DIR = Path(__file__).resolve().parent
        self.PORT = int(os.environ.get('PORT', 8000))
        self.DATA_FILE = self.BASE_DIR / 'data' / 'habits_data.json'
        
        # Ensure data directory exists
        self.DATA_FILE.parent.mkdir(exist_ok=True)
        
        # Initialize data file if it doesn't exist
        if not self.DATA_FILE.exists():
            self.DATA_FILE.write_text('{}')
        
        # Load settings
        self.settings = self._load_settings()
    
    def _load_settings(self):
        """Load settings from JSON file"""
        settings_file = self.BASE_DIR / 'settings.json'
        try:
            with open(settings_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"⚠️ Could not load settings.json: {e}")
            print("Using default settings...")
            return {
                'port': 8000,
                'data': {'file': 'data/habits_data.json'},
                'habits': ['Brush teeth', 'Floss'],
                'module': {
                    'updateInterval': 60000,
                    'showCompletedCount': True,
                    'showProgressBar': True
                }
            }
    
    def get_habits_for_date(self, date):
        """Get habits for a specific date, creating default if not exists"""
        try:
            with open(self.DATA_FILE, 'r') as f:
                data = json.load(f)
            
            if date in data:
                return data[date]
            else:
                # Initialize with settings habits
                habits = [{'name': habit, 'completed': False, 'date': date} for habit in self.settings['habits']]
                data[date] = habits
                with open(self.DATA_FILE, 'w') as f:
                    json.dump(data, f, indent=2)
                return habits
        except Exception as e:
            print(f"❌ Error loading habits for date {date}: {e}")
            return []
    
    def save_habits_for_date(self, habits, date):
        """Save habits for a specific date"""
        try:
            with open(self.DATA_FILE, 'r') as f:
                all_data = json.load(f)
            
            all_data[date] = habits
            
            with open(self.DATA_FILE, 'w') as f:
                json.dump(all_data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"❌ Error saving habits for date {date}: {e}")
            return False
    
    def mark_habit_completed(self, habit_name: str):
        """Mark a habit complete for today and return updated habits list, or None on failure"""
        from datetime import datetime
        date = datetime.now().strftime('%Y-%m-%d')
        
        try:
            with open(self.DATA_FILE, 'r') as f:
                all_data = json.load(f)
        except json.JSONDecodeError:
            all_data = {}
        
        if date not in all_data:
            all_data[date] = [{'name': h, 'completed': False, 'date': date} for h in self.settings['habits']]
        
        updated = False
        for h in all_data[date]:
            if h.get('name') == habit_name:
                if not h.get('completed'):
                    h['completed'] = True
                    updated = True
                break
        
        with open(self.DATA_FILE, 'w') as f:
            json.dump(all_data, f, indent=2)
        
        return all_data[date] if updated else None
    
    def get_all_habits_data(self):
        """Get all habits data for debugging"""
        try:
            with open(self.DATA_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading all habits data: {e}")
            return {}


# Global config instance
config = Config()
