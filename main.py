import os
import zipfile
import json
import random
import argparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.os_manager import ChromeType

from config import Config
import logging_config
logging = logging_config.setup_logging(__name__)

from selenium_stealth import stealth


def load_previous_proxy_settings(settings_file):
    try:
        logging.debug(f"Attempting to load previous proxy settings from {settings_file}")
        if not os.path.exists(settings_file):
            logging.debug("No previous proxy settings found.")
            return None
        with open(settings_file, 'r') as f:
            data = json.load(f)
            logging.debug(f"Previous proxy settings loaded: {data}")
            return data
    except Exception as e:
        logging.error(f"Failed to load previous proxy settings: {e}")
        return None


def save_current_proxy_settings(settings_file, proxy_data):
    try:
        logging.debug(f"Attempting to save current proxy settings: {proxy_data}")
        with open(settings_file, 'w') as f:
            json.dump(proxy_data, f)
        logging.info("Current proxy settings saved successfully.")
    except Exception as e:
        logging.error(f"Failed to save current proxy settings: {e}")


def save_cookies(driver, file_name):
    try:
        logging.debug(f"Attempting to save cookies to {file_name}")
        cookies = driver.get_cookies()
        file_path = f"{Config.cookies_path}/{file_name}"
        folder = os.path.dirname(file_path)
        if folder and not os.path.exists(folder):
            os.makedirs(folder)
        with open(file_path, 'w') as file:
            json.dump(cookies, file)
        logging.info(f"Cookies saved in {file_name}")
    except Exception as e:
        logging.error(f"Failed to save cookies: {e}")


def load_random_cookie(driver):
    try:
        logging.debug("Attempting to load a random cookie file.")
        if not os.path.exists(Config.cookies_path) or not os.listdir(Config.cookies_path):
            logging.warning(f"Folder '{Config.cookies_path}' is empty or does not exist. Running without cookies.")
            return
        cookie_file = random.choice(os.listdir(Config.cookies_path))
        cookie_path = os.path.join(Config.cookies_path, cookie_file)
        with open(cookie_path, 'r') as file:
            cookies = json.load(file)
        for cookie in cookies:
            driver.add_cookie(cookie)
        logging.info(f"Cookies loaded from {cookie_path}")
    except Exception as e:
        logging.error(f"Failed to load random cookie: {e}")


def create_proxy_extension(proxy_host, proxy_port, proxy_user, proxy_pass, extension_dir, extension_zip):
    try:
        logging.debug("Attempting to create proxy extension.")
        if not os.path.exists(extension_dir):
            os.makedirs(extension_dir)

        manifest_json = """
        {
            "version": "1.0.0",
            "manifest_version": 2,
            "name": "Proxy Auth Extension",
            "permissions": [
                "proxy",
                "tabs",
                "unlimitedStorage",
                "storage",
                "<all_urls>",
                "webRequest",
                "webRequestBlocking"
            ],
            "background": {
                "scripts": ["background.js"]
            }
        }
        """

        background_js = f"""
        var config = {{
                mode: "fixed_servers",
                rules: {{
                  singleProxy: {{
                    scheme: "http",
                    host: "{proxy_host}",
                    port: parseInt({proxy_port})
                  }},
                  bypassList: ["localhost"]
                }}
              }};
        
        chrome.proxy.settings.set({{value: config, scope: "regular"}}, function() {{}});
        
        function callbackFn(details) {{
            return {{
                authCredentials: {{
                    username: "{proxy_user}",
                    password: "{proxy_pass}"
                }}
            }};
        }}
        
        chrome.webRequest.onAuthRequired.addListener(
            callbackFn,
            {{urls: ["<all_urls>"]}},
            ['blocking']
        );
        """

        manifest_path = os.path.join(extension_dir, 'manifest.json')
        background_path = os.path.join(extension_dir, 'background.js')
        
        with open(manifest_path, 'w') as f:
            f.write(manifest_json)
        with open(background_path, 'w') as f:
            f.write(background_js)

        with zipfile.ZipFile(extension_zip, 'w') as zipf:
            zipf.write(manifest_path, 'manifest.json')
            zipf.write(background_path, 'background.js')

        logging.info(f"Extension created and saved to path: {extension_zip}")
    except Exception as e:
        logging.error(f"Failed to create proxy extension: {e}")


def main():
    try:
        logging.debug("Parsing command line arguments.")
        parser = argparse.ArgumentParser()
        parser.add_argument(
            '--save-cookie', 
            type=str, 
            help="Path to save the cookie file"
        )
        args = parser.parse_args()

        ext_dir = 'proxy_auth_extension'
        ext_zip = os.path.join(ext_dir, 'proxy_auth_extension.zip')
        proxy_file = os.path.join(ext_dir, 'proxy_settings.json')

        proxy_settings = {
            'host': Config.proxy_host,
            'port': Config.proxy_port,
            'user': Config.proxy_user,
            'pass': Config.proxy_pass
        }

        arguments = [
            "--disable-logging",
            "--disable-dev-shm-usage",
            "--mute-audio",
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--disable-dev-tools",
            "--disable-sync",
            "--disable-translate",
            "--no-first-run",
            "--no-default-browser-check",
            "--ignore-certificate-errors",
        ]

        previous_proxy_settings = load_previous_proxy_settings(proxy_file)

        if proxy_settings != previous_proxy_settings:
            logging.info("Proxy settings have changed or are missing. Creating or updating the extension...")
            create_proxy_extension(proxy_settings.get('host'),
                                   proxy_settings.get('port'),
                                   proxy_settings.get('user'),
                                   proxy_settings.get('pass'),
                                   ext_dir, ext_zip)
            save_current_proxy_settings(proxy_file, proxy_settings)
        else:
            logging.info("Proxy settings have not changed. Using the existing extension.")

        if not os.path.exists(ext_zip):
            logging.error(f"Error: Extension not found at path {ext_zip}. Terminating.")
            return

        chrome_options = Options()
        try:
            chrome_options.add_extension(ext_zip)
            chrome_options.add_argument(
                f"user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            )
            for arg in arguments:
                chrome_options.add_argument(arg)

            preferences = {
                "webrtc.ip_handling_policy": "disable_non_proxied_udp",
                "webrtc.multiple_routes_enabled": False,
                "webrtc.nonproxied_udp_enabled": False
            }
            chrome_options.add_experimental_option("prefs", preferences)
        except Exception as e:
            logging.error(f"Failed to configure Chrome options: {e}")
            return

        try:
            logging.debug("Attempting to install and start ChromeDriver.")
            driver_path = ChromeDriverManager(chrome_type=ChromeType.CHROMIUM).install()
            service = Service(driver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception as e:
            logging.error(f"Failed to start WebDriver: {e}")
            return

        try:
            logging.debug("Applying stealth settings to the driver.")
            stealth(
                driver,
                languages=["nl-NL", "NL"],
                vendor="Google Inc.",
                platform="Win32",
                webgl_vendor="Intel Inc.",
                renderer="Intel Iris OpenGL Engine",
                fix_hairline=False,
                run_on_insecure_origins=False
            )
        except Exception as e:
            logging.error(f"Failed to apply stealth settings: {e}")
            driver.quit()
            return

        try:
            logging.debug("Navigating to the target URL.")
            driver.get(Config.url)
            if not args.save_cookie:
                load_random_cookie(driver)
                driver.refresh()

            input("Press Enter to exit...")
        except Exception as e:
            logging.error(f"An error occurred during browser operations: {e}")
        finally:
            try:
                if args.save_cookie:
                    save_cookies(driver, args.save_cookie)
            except Exception as e:
                logging.error(f"Failed to save cookies in the finally block: {e}")
            driver.quit()

    except Exception as e:
        logging.error(f"An unexpected error occurred in main: {e}")


if __name__ == '__main__':
    try:
        logging.info(f"Proxy: {Config.proxy_host}:{Config.proxy_port}, login: {Config.proxy_user}, pass: {Config.proxy_pass}")
        main()
    except Exception as e:
        logging.error(f"Unhandled exception at startup: {e}")

