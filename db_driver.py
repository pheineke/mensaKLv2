import sqlite3
from datetime import datetime
import json

class MealDatabase:
    def __init__(self, db_path='meals.db'):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create meals table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS meals (
            m_id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            location TEXT NOT NULL,
            dish_name TEXT NOT NULL,
            title_with_additives TEXT,
            description TEXT,
            meal_type TEXT,
            price TEXT NOT NULL,
            image TEXT,
            icon TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        conn.close()

    def save_meals(self, meals):
        """Save meals to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for meal in meals:
            # Check if meal already exists
            cursor.execute('SELECT m_id FROM meals WHERE m_id = ?', (meal['m_id'],))
            if cursor.fetchone() is None:
                cursor.execute('''
                INSERT INTO meals (
                    m_id, date, location, dish_name, title_with_additives, 
                    description, meal_type, price, image, icon
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    meal['m_id'],
                    meal['date'],
                    meal['location'],
                    meal['dish_name'],
                    meal['title_with_additives'],
                    meal.get('description', ''),
                    meal.get('meal_type', ''),
                    meal['price'],
                    meal['image'],
                    meal['icon'],
                ))
        
        conn.commit()
        conn.close()

    def get_meals_by_date(self, date):
        """Get all meals for a specific date"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM meals WHERE date = ?
        ORDER BY m_id
        ''', (date,))
        
        columns = [description[0] for description in cursor.description]
        meals = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return meals

    def get_meals_by_date_range(self, start_date, end_date):
        """Get all meals within a date range"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT * FROM meals 
        WHERE date BETWEEN ? AND ?
        ORDER BY date, m_id
        ''', (start_date, end_date))
        
        columns = [description[0] for description in cursor.description]
        meals = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return meals

    def get_all_meals(self):
        """Get all meals from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM meals ORDER BY date, m_id')
        
        columns = [description[0] for description in cursor.description]
        meals = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        conn.close()
        return meals

    def clear_meals(self):
        """Clear all meals from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM meals')
        
        conn.commit()
        conn.close()

    def export_to_json(self, output_file='meals.json'):
        """Export all meals to a JSON file"""
        meals = self.get_all_meals()
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(meals, f, indent=4, ensure_ascii=False) 