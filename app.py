from flask import Flask, render_template
from datetime import datetime, timedelta
from db_driver import MealDatabase
from scheduler import start_scheduler
import locale

app = Flask(__name__)
db = MealDatabase()  # Initialize database at module level

# Set German locale for date formatting
locale.setlocale(locale.LC_TIME, 'de_DE.UTF-8')


def convert_price_to_float(price_str):
    price_str = price_str.replace('€', '').strip()
    try:
        return float(price_str.replace(',', '.'))
    except ValueError:
        return 0.0

def group_meals_by_date(meals):
    meals_by_date = {}
    for meal in meals:
        date = meal['date']
        if date not in meals_by_date:
            meals_by_date[date] = []
        meals_by_date[date].append(meal)

        meal['price'] = convert_price_to_float(meal['price'])

    return meals_by_date

def get_meals_by_date_range(start_date, end_date):
    print(f"Fetching meals from {start_date} to {end_date}")
    meals = db.get_meals_by_date_range(start_date, end_date)
    print(f"Found {len(meals)} meals")
    
    # Group meals by date
    meals_by_date = {}
    for meal in meals:
        date = meal['date']
        if date not in meals_by_date:
            meals_by_date[date] = []
        meals_by_date[date].append(meal)
        
        # Convert price from "X,XX €" format to float
        price_str = meal['price'].replace('€', '').strip()
        try:
            meal['price'] = float(price_str.replace(',', '.'))
        except ValueError:
            meal['price'] = 0.0
            
        # Use dish_name as title
        meal['title'] = meal['dish_name']

    
    
    # Sort meals within each date by location priority
    location_priority = {
        'Essen 1': 1,
        'Essen 2': 2,
        'Grill': 3,
        'Salatbüfett': 4
    }
    
    for date in meals_by_date:
        meals_by_date[date].sort(key=lambda x: location_priority.get(x['location'], 999))
    
    print(f"Grouped meals by date: {list(meals_by_date.keys())}")
    return meals_by_date

@app.route('/')
def home():
    # Use a fixed date range for testing (2025-04-02 to 2025-04-04)
    start_date = "2025-04-02"
    end_date = "2025-04-04"
    
    print(f"\nProcessing request for meals from {start_date} to {end_date}")
    
    # Get meals from database
    meals_by_date = get_meals_by_date_range(start_date, end_date)
    
    # Format dates for display
    formatted_dates = {}
    for date_str in meals_by_date:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        if date_str == start_date:
            formatted_dates[date_str] = "Heute"
        else:
            formatted_dates[date_str] = date_obj.strftime('%A, %d.%m.%Y')
    
    print(f"Rendering template with {len(meals_by_date)} dates")
    return render_template('index.html', 
                         meals_by_date=meals_by_date,
                         formatted_dates=formatted_dates,
                         today=start_date)

if __name__ == '__main__':
    # Start the scheduler
    scheduler = start_scheduler()
    app.run(debug=True) 