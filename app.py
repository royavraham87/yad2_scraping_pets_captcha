from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import sqlite3
import time
import requests

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

# This section is all about solving the captcha problem automatically 

# CAPTCHA solving service (2Captcha example)
# This function is responsible for sending a CAPTCHA-solving request to a service like 2Captcha,
# which will solve the CAPTCHA for you.
def solve_captcha(site_key, url):
    api_key = "your_2captcha_api_key"
    captcha_id = None
    try:
        # Send CAPTCHA solving request
        response = requests.post("http://2captcha.com/in.php", data={
            'key': api_key,
            'method': 'userrecaptcha',
            'googlekey': site_key,
            'pageurl': url,
            'json': 1
        }).json()

        if response["status"] == 1:
            captcha_id = response["request"]
            print("CAPTCHA request sent, waiting for solution...")

            # Wait for CAPTCHA solution
            # If the CAPTCHA-solving request is accepted (response["status"] == 1), 
            # the service returns a captcha_id, which identifies your specific CAPTCHA-solving request.
            # The script prints that the request has been sent and waits for the solution.
            # If the solution is available (result_response["status"] == 1), it returns the CAPTCHA token, 
            # which can then be injected into the webpage to simulate the human solving the CAPTCHA.
            # If the CAPTCHA hasn't been solved yet, it prints a message saying it's waiting.
            for _ in range(10):  # retry 10 times
                time.sleep(10)  # 10 seconds wait between retries
                result_response = requests.get(f"http://2captcha.com/res.php?key={api_key}&action=get&id={captcha_id}&json=1").json()
                
                if result_response["status"] == 1:
                    print("CAPTCHA solved!")
                    return result_response["request"]  # Return CAPTCHA token
                print("Waiting for CAPTCHA solution...")
        else:
            print("Error submitting CAPTCHA request:", response["request"])
    except Exception as e:
        print(f"Error during CAPTCHA solving: {e}")

    return None

# Function to check and handle CAPTCHA
# This function detects whether a CAPTCHA is present on the page, and either tries to solve it automatically using the 
# service or prompts for manual resolution if the automated attempt fails.
def check_and_solve_captcha(url):
    site_key = None

    try:
        # Detect CAPTCHA presence (using a CAPTCHA-specific selector)
        captcha_frame = driver.find_element(By.CSS_SELECTOR, 'iframe[src*="recaptcha"]')
        site_key = captcha_frame.get_attribute("src").split("k=")[1].split("&")[0]
    except Exception:
        return False  # No CAPTCHA detected

    # Try solving the CAPTCHA using an automated service
    captcha_solution = solve_captcha(site_key, url)

    if captcha_solution:
        # Inject the CAPTCHA solution
        driver.execute_script(f"document.getElementById('g-recaptcha-response').innerHTML = '{captcha_solution}';")
        driver.execute_script("recaptchaCallback();")  # Trigger the form submission
        return True

    # If CAPTCHA solving fails, allow manual solving
    print("Automatic CAPTCHA solving failed. Please solve the CAPTCHA manually.")
    input("Solve the CAPTCHA and press Enter to continue...")

    return True  # CAPTCHA solved manually
# This is the end of trying to solve the CAPTCHA automatically or manually if CAPTCHA solving fails. 

# This section is all about scraping the pet details from each page
# Function to scrape a single page
def scrape_page(url):
    print(f"Scraping {url}...")

    driver.get(url)

    # Handle CAPTCHA if present
    check_and_solve_captcha(url)

    # Wait for the main container to load
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, '.feeditem.table'))
        )
    except Exception as e:
        print(f"Failed to load page content: {e}")
        return

    # Give additional time for all content to fully load
    time.sleep(5)  # Adjust the waiting time as needed

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
