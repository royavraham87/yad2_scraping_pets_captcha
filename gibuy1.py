from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import sqlite3

# Set up Chrome options (disable headless for debugging)
chrome_options = Options()
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920x1080")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

# Initialize the Selenium WebDriver with WebDriver Manager
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

# Set up SQLite database connection
conn = sqlite3.connect('pets.db')
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS pets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT,
        location TEXT,
        price TEXT
    )
''')
conn.commit()

# Function to scrape a single page
def scrape_page(url):
    print(f"Scraping {url}...")

    driver.get(url)
    
    # Add delay for CAPTCHA solving manually on first load
    if "page=" not in url:  # This is the first page
        input("Solve the CAPTCHA and press Enter to continue...")

    # Wait for the page to load and select the pet containers
    WebDriverWait(driver, 20).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, '.feeditem.table'))
    )

    # Find all pet containers
    pet_containers = driver.find_elements(By.CSS_SELECTOR, '.feeditem.table')

    # Iterate through each pet container and extract the data
    for pet in pet_containers:
        try:
            # Extract description text from 'row-1' inside '.cell-table'
            description_element = pet.find_element(By.CSS_SELECTOR, '.row-1')
            description = description_element.text.strip()

            # Extract location from '.second-obj .val'
            location_element = pet.find_element(By.CSS_SELECTOR, '.second-obj .val')
            location = location_element.text.strip() if location_element else "No location available"

            # Extract price from '.third-obj .price'
            price_element = pet.find_element(By.CSS_SELECTOR, '.third-obj .price')
            price = price_element.text.strip() if price_element else "No price available"

            # Print the extracted data
            print(f"Description: {description}, Location: {location}, Price: {price}")

            # Insert data into SQLite database
            cursor.execute('''
                INSERT INTO pets (description, location, price)
                VALUES (?, ?, ?)''', (description, location, price))
            conn.commit()

        except Exception as e:
            print(f"Error extracting data for one pet: {e}")

# Iterate through pages 1 to 10
base_url = "https://www.yad2.co.il/pets/all"
scrape_page(base_url)  # Scrape the first page

# Scrape pages 2 to 10
for page_num in range(2, 11):
    url = f"https://www.yad2.co.il/pets/all?page={page_num}"
    scrape_page(url)

# Close the driver when done
driver.quit()

# Close the database connection
conn.close()
