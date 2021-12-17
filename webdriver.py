from selenium import webdriver as driver
from selenium.webdriver.chrome.options import Options
import chromedriver_autoinstaller

chromedriver_autoinstaller.install()

def create_chrome_driver(*args, **kwargs):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chromedriver = driver.Chrome(*args, **kwargs, chrome_options=chrome_options)
    return chromedriver