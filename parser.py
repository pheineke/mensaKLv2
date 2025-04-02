from bs4 import BeautifulSoup
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
from db_driver import MealDatabase
import requests
import re
import logging
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MealParser:
    def __init__(self):
        self.db = MealDatabase()

    def parse_german_date(self, date_str):
        """Parse German date string into datetime object"""
        # Dictionary to map German month names to numbers
        month_map = {
            'Januar': 1, 'Februar': 2, 'März': 3, 'April': 4,
            'Mai': 5, 'Juni': 6, 'Juli': 7, 'August': 8,
            'September': 9, 'Oktober': 10, 'November': 11, 'Dezember': 12
        }
        
        # Split the date string into components
        parts = date_str.split(',')
        if len(parts) != 2:
            raise ValueError(f"Invalid date format: {date_str}")
        
        # Get the date part (e.g., "1. April 2025")
        date_part = parts[1].strip()
        
        # Split into day, month, year
        date_components = date_part.split()
        if len(date_components) != 3:
            raise ValueError(f"Invalid date components: {date_part}")
        
        day = int(date_components[0].replace('.', ''))
        month = month_map[date_components[1]]
        year = int(date_components[2])
        
        return datetime(year, month, day)

    def get_icon_from_title(self, title, description=""):
        """Determine the appropriate icon based on the meal title and description"""
        title_lower = title.lower()
        description_lower = description.lower()
        
        # First check for vegetarian/vegan meals
        if any(word in description_lower for word in ['veganes menü', 'vegetarisches menü']):
            if 'vegan' in description_lower:
                return 'vegan'
            return 'vegetarian'
        
        # Then check for specific meat types
        if any(word in title_lower for word in ['rind', 'steak', 'bolognese', 'gulasch', 'burger']):
            return 'beef'
        elif any(word in title_lower for word in ['huhn', 'hähnchen', 'geflügel', 'chicken', 'cordon bleu']):
            return 'chicken'
        elif any(word in title_lower for word in ['schwein', 'schnitzel', 'spareribs', 'pork']):
            return 'pork'
        elif any(word in title_lower for word in ['fisch', 'zander', 'fish', 'lachs', 'forelle']):
            return 'fish'
        elif any(word in title_lower for word in ['currywurst']):
            return 'berk'
        
        # Check description for vegetarian/vegan indicators
        if any(word in description_lower for word in ['vegan', 'vegetarisch']):
            if 'vegan' in description_lower:
                return 'vegan'
            return 'vegetarian'
        
        # Check for pasta and salad dishes
        if any(word in title_lower for word in ['pasta', 'nudel', 'tortellini', 'spaghetti']):
            return 'vegetarian'
        elif any(word in title_lower for word in ['salat']):
            return 'vegetarian'
        
        return 'beef'  # Default icon

    def convert_to_json_format(self, meals):
        json_meals = []
        for i, meal in enumerate(meals):
            json_meals.append(meal)
        
        return json_meals

    def parse_meals(self, html_content):
        print("Starting to parse meals...")
        soup = BeautifulSoup(html_content, 'html.parser')
        meals = []
        
        # Find all meal cards
        meal_cards = soup.find_all('li', class_='card')
        print(f"\nFound {len(meal_cards)} meal cards")
        
        for card in meal_cards:
            # Extract date and meal type
            plan_header = card.find('p', class_='plan')
            if not plan_header:
                print("No plan header found, skipping card")
                continue
                
            date_text = plan_header.find('span').text.strip()
            date_str = date_text.split('·')[0].strip()
            meal_type = date_text.split('·')[1].strip()
            
            print(f"Processing meal for date: {date_str}, type: {meal_type}")
            
            # Parse date
            try:
                date = self.parse_date(date_str)
            except ValueError as e:
                print(f"Error parsing date {date_str}: {e}")
                continue
                
            # Extract main dish information
            std_card = card.find('div', class_='std-card')
            if not std_card:
                print("No std-card found, skipping card")
                continue
                
            # Get main dish title
            main_dish = std_card.find('h3', class_='std')
            if not main_dish:
                print("No main dish found, skipping card")
                continue
                
            dish_name = main_dish.text.strip()
            
            # Get description
            description = std_card.find('p')
            description_text = self.get_description(description)
            
            # Get prices
            price_text = card.find('p', class_='preis-text')
            print(price_text)
            prices = self.get_prices(price_text)
            
            # Check for vegetarian/vegan alternatives
            vegetarian_alt = card.find('div', class_='vegetarian')
            vegan_alt = card.find('div', class_='vegan')
            
            vegetarian_alternative = None
            vegan_alternative = None
            
            if vegetarian_alt:
                veg_title = vegetarian_alt.find('h3', class_='alternative')
                if veg_title:
                    vegetarian_alternative = veg_title.text.strip()
            
            if vegan_alt:
                veg_title = vegan_alt.find('h3', class_='alternative')
                if veg_title:
                    vegan_alternative = veg_title.text.strip()
            
            meal_info = self.meal_info(
                date=date, 
                location=meal_type, 
                meal_type=meal_type, 
                dish_name=dish_name, 
                description=description_text, 
                prices=prices,
                vegetarian_alternative=vegetarian_alternative,
                vegan_alternative=vegan_alternative)
            
            meals.append(meal_info)
            print(f"Successfully parsed meal: {dish_name}")
        
        print(f"Finished parsing. Total meals found: {len(meals)}")
        return meals

    def parse_date(self, date_str):
        # Convert German day abbreviations to full names
        date_str = date_str.replace('Di.', 'Dienstag')
        date_str = date_str.replace('Mi.', 'Mittwoch')
        date_str = date_str.replace('Do.', 'Donnerstag')
        date_str = date_str.replace('Fr.', 'Freitag')
        date_str = date_str.replace('Mo.', 'Montag')
        
        # Convert German month abbreviations to full names
        date_str = date_str.replace('Jan.', 'Januar')
        date_str = date_str.replace('Feb.', 'Februar')
        date_str = date_str.replace('Mär.', 'März')
        date_str = date_str.replace('Apr.', 'April')
        date_str = date_str.replace('Mai.', 'Mai')
        date_str = date_str.replace('Jun.', 'Juni')
        date_str = date_str.replace('Jul.', 'Juli')
        date_str = date_str.replace('Aug.', 'August')
        date_str = date_str.replace('Sep.', 'September')
        date_str = date_str.replace('Okt.', 'Oktober')
        date_str = date_str.replace('Nov.', 'November')
        date_str = date_str.replace('Dez.', 'Dezember')
        
        # Parse the date using our custom function
        return self.parse_german_date(date_str)

    def get_description(self, description):
        description_text = description.text.strip() if description else ""
        return description_text

    def get_prices(self, price_text):
        prices = {}
        if price_text:
            for price_span in price_text.find_all('span'):
                text = price_span.text.strip()
                if 'Studierende' in text:
                    prices['student'] = text.replace('Studierende', '').strip()
                elif 'Bedienstete' in text:
                    prices['staff'] = text.replace('Bedienstete', '').strip()
                elif 'Gäste' in text:
                    prices['guest'] = text.replace('Gäste', '').strip()
        
        print(prices)
        return prices

    def meal_info(self, date, location, meal_type, dish_name, description, prices, 
                 vegetarian_alternative=None, vegan_alternative=None):
        # Generate a unique ID for the meal
        m_id = 50000 + hash(f"{date.strftime('%Y-%m-%d')}_{location}_{dish_name}") % 10000
        
        # Format the date as YYYY-MM-DD
        date_str = date.strftime('%Y-%m-%d')
        
        # Determine the icon based on the dish name and description
        icon = self.get_icon_from_title(dish_name, description)
        
        # Create the meal info dictionary
        meal_info = {
            'm_id': m_id,
            'date': date_str,
            'location': location,
            'dish_name': dish_name,
            'title_with_additives': dish_name,  # You can add additives if needed
            'price': prices.get('student', '0.00'),  # Default to student price
            'description': description,
            'meal_type': meal_type,
            'image': '',  # No image for now
            'icon': icon,
            'vegetarian_alternative': vegetarian_alternative,
            'vegan_alternative': vegan_alternative
        }
        
        return meal_info

    def get_meals_from_internet(self):
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in headless mode (no GUI)
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')

        try:
            # Initialize the Chrome WebDriver
            driver = webdriver.Chrome(options=chrome_options)
            print("WebDriver initialized")
            
            # Load the page
            url = "https://www.studierendenwerk-kaiserslautern.de/de/essen/speiseplaene"
            print(f"Loading URL: {url}")
            driver.get(url)
            
            # Wait for the meal cards to load (wait up to 10 seconds)
            print("Waiting for meal cards to load...")
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "card"))
            )
            
            # Give a little extra time for all content to load
            time.sleep(2)
            
            # Get the page source after JavaScript has run
            html_content = driver.page_source
            
            # Save the HTML for debugging
            with open('page_content.html', 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Parse the meals
            meals = self.parse_meals(html_content)
            
            if not meals:
                print("No meals were parsed!")
            else:
                # Convert to JSON format
                json_meals = self.convert_to_json_format(meals)
                
                # Save to database
                print("\nSaving meals to database...")
                self.db.save_meals(json_meals)
                
                # Export to JSON file
                print("Exporting to JSON file...")
                self.db.export_to_json()
                
                print("\nMeals saved to database and exported to meals.json")
                
                # Print some statistics
                all_meals = self.db.get_all_meals()
                print(f"\nTotal meals in database: {len(all_meals)}")
                print(all_meals)
                
                # Get meals for today
                today = datetime.now().strftime("%Y-%m-%d")
                today_meals = self.db.get_meals_by_date(today)
                print(f"Meals for today ({today}): {len(today_meals)}")
            
            # Close the browser
            driver.quit()
            
        except Exception as e:
            print(f"An error occurred: {e}")
            if 'driver' in locals():
                driver.quit()

    def scrape_and_save_meals(self):
        print("Starting to scrape meals...")
        
        # Set up Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # Run in headless mode
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        
        # Initialize the Chrome WebDriver
        driver = webdriver.Chrome(options=chrome_options)
        
        try:
            # Load the webpage
            url = "https://www.studierendenwerk-kaiserslautern.de/de/essen/speiseplaene"
            driver.get(url)
            
            # Wait for the meal cards to load
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "card")))
            
            # Get the page source after JavaScript has executed
            html_content = driver.page_source
            
            # Parse the meals
            meals = self.parse_meals(html_content)
            
            # Save meals to database
            if meals:
                self.db.save_meals(meals)
                print(f"Successfully saved {len(meals)} meals to database")
                
                # Export to JSON for debugging
                with open('meals.json', 'w', encoding='utf-8') as f:
                    json.dump(meals, f, ensure_ascii=False, indent=2)
                print("Exported meals to meals.json")
            else:
                print("No meals were parsed")
                
        finally:
            driver.quit()
            
        # Print statistics
        total_meals = len(self.db.get_all_meals())
        today = datetime.now().strftime('%Y-%m-%d')
        today_meals = len(self.db.get_meals_by_date(today))
        print(f"\nDatabase Statistics:")
        print(f"Total meals in database: {total_meals}")
        print(f"Meals for today ({today}): {today_meals}")

def scrape_meals():
    """Main function to scrape meals and save them to the database."""
    logger.info("Starting to scrape meals")
    
    # Initialize database
    db = MealDatabase()
    
    # URL of the mensa page
    url = "https://www.studentenwerk-muenchen.de/mensa/speiseplan/speiseplan_422_-de.html"
    
    try:
        # Send GET request to the URL
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes

        # Parse the HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all meal cards
        meal_cards = soup.find_all('div', class_='meal-card')
        logger.info(f"Found {len(meal_cards)} meal cards")
        
        # List to store all meals
        all_meals = []
        
        # Process each meal card
        for card in meal_cards:
            try:
                # Extract date
                date_element = card.find('div', class_='date')
                if not date_element:
                    continue
                    
                date_text = date_element.text.strip()
                # Convert German date format to standard format
                date_text = date_text.replace('Di.', 'Dienstag').replace('Mo.', 'Montag').replace('Mi.', 'Mittwoch').replace('Do.', 'Donnerstag').replace('Fr.', 'Freitag')
                date_text = date_text.replace('Jan.', 'Januar').replace('Feb.', 'Februar').replace('Mär.', 'März').replace('Apr.', 'April').replace('Mai.', 'Mai').replace('Jun.', 'Juni')
                date_text = date_text.replace('Jul.', 'Juli').replace('Aug.', 'August').replace('Sep.', 'September').replace('Okt.', 'Oktober').replace('Nov.', 'November').replace('Dez.', 'Dezember')
                
                try:
                    date = datetime.strptime(date_text, '%A, %d. %B %Y').strftime('%Y-%m-%d')
                except ValueError as e:
                    logger.error(f"Error parsing date '{date_text}': {e}")
                    continue
                
                # Extract location
                location_element = card.find('div', class_='location')
                location = location_element.text.strip() if location_element else "Unbekannt"
                
                # Extract dish name and additives
                dish_element = card.find('div', class_='dish-name')
                if not dish_element:
                    continue
                    
                dish_text = dish_element.text.strip()
                title_with_additives = None
                
                # Split dish name and additives if present
                if '(' in dish_text and ')' in dish_text:
                    dish_name = dish_text[:dish_text.find('(')].strip()
                    title_with_additives = dish_text
                else:
                    dish_name = dish_text
                
                # Extract price
                price_element = card.find('div', class_='price')
                price = price_element.text.strip() if price_element else "0,00 €"
                
                # Extract description
                description_element = card.find('div', class_='description')
                description = description_element.text.strip() if description_element else None
                
                # Extract meal type
                meal_type_element = card.find('div', class_='meal-type')
                meal_type = meal_type_element.text.strip() if meal_type_element else None
                
                # Generate unique meal ID
                m_id = f"{date}_{location}_{dish_name}"
                
                # Determine icon based on meal type
                icon = None
                if 'vegan' in meal_type.lower() if meal_type else False:
                    icon = 'vegan'
                elif 'hähnchen' in dish_name.lower() or 'chicken' in dish_name.lower():
                    icon = 'chicken'
                elif 'rind' in dish_name.lower() or 'beef' in dish_name.lower() or 'burger' in dish_name.lower():
                    icon = 'beef'
                
                # Create meal dictionary
                meal = {
                    'm_id': m_id,
                    'date': date,
                    'location': location,
                    'dish_name': dish_name,
                    'title_with_additives': title_with_additives,
                    'price': price,
                    'description': description,
                    'meal_type': meal_type,
                    'image': None,  # Add image handling if needed
                    'icon': icon
                }
                
                all_meals.append(meal)
                logger.info(f"Processed meal: {dish_name} on {date}")
                
            except Exception as e:
                logger.error(f"Error processing meal card: {e}")
                continue
        
        # Save all meals to database
        if all_meals:
            db.save_meals(all_meals)
            logger.info(f"Successfully saved {len(all_meals)} meals to database")
            
            # Export to JSON for backup
            db.export_to_json()
            logger.info("Exported meals to meals.json")
        else:
            logger.warning("No meals were found to save")
            
    except Exception as e:
        logger.error(f"Error during scraping: {e}")
        raise

def add_example_alternatives():
    """Add example vegetarian/vegan alternatives to existing meals for testing."""
    db = MealDatabase()
    meals = db.get_all_meals()
    
    # Example alternatives
    vegetarian_options = [
        "Gemüsepfanne mit Kartoffeln",
        "Käse-Spätzle mit Röstzwiebeln",
        "Spinat-Ricotta-Cannelloni",
        "Gegrillter Halloumi mit Gemüse",
        "Kräuterrisotto mit Parmesan"
    ]
    
    vegan_options = [
        "Gebratener Tofu mit Gemüse",
        "Linsen-Curry mit Basmatireis",
        "Vegane Gemüse-Bolognese",
        "Gefüllte Paprika mit Couscous",
        "Süßkartoffel-Kichererbsen-Eintopf"
    ]
    
    # Add alternatives to non-vegetarian/vegan meals
    for meal in meals:
        if meal.get('icon') != 'vegan':  # Only add alternatives to non-vegan meals
            # 70% chance to add vegetarian alternative
            if random.random() < 0.7:
                meal['vegetarian_alternative'] = random.choice(vegetarian_options)
            
            # 50% chance to add vegan alternative
            if random.random() < 0.5:
                meal['vegan_alternative'] = random.choice(vegan_options)
    
    # Save updated meals back to database
    db.save_meals(meals)
    print(f"Added example alternatives to {len(meals)} meals")
    
    # Export to JSON
    db.export_to_json()
    print("Exported updated meals to meals.json")

# Example usage
if __name__ == "__main__":
    print("Starting script...")
    
    parser = MealParser()
    parser.scrape_and_save_meals()
    
    # Add example alternatives for testing
    add_example_alternatives()
    
    scrape_meals()
    
    
    



