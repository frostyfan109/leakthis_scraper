import chromedriver_autoinstaller
from selenium import webdriver as driver
from selenium.webdriver.chrome.options import Options

chromedriver_autoinstaller.install()

def create_chrome_driver(*args, **kwargs):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-logging"])
    chromedriver = driver.Chrome(*args, **kwargs, chrome_options=chrome_options)
    return chromedriver