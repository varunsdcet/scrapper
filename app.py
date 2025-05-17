from flask import Flask, render_template, request
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
import time
import logging
import random
import re
import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def extract_emails(text):
    email_pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
    return re.findall(email_pattern, text)

def extract_indian_mobile_numbers(text):
    mobile_pattern = r'\b[6-9]\d{9}\b'
    return re.findall(mobile_pattern, text)
def scrape_google(query):
    logging.info(f"Starting Google scrape for query: {query}")
    results_data = []

    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="Asia/Kolkata",
                geolocation={"latitude": 28.6139, "longitude": 77.2090},
                permissions=["geolocation"]
            )
            page = context.new_page()
            stealth_sync(page)

            # First page
            url = f"https://www.google.com/search?q={query.replace(' ', '+')}&gl=in&hl=en"
            logging.info(f"Navigating to: {url}")
            page.goto(url, wait_until="networkidle", timeout=30000)

            # Handle consent popup
            consent_button = page.query_selector("button[id='L2AGLb']") or page.query_selector("button[aria-label*='Accept']")
            if consent_button:
                consent_button.click()
                logging.info("Clicked consent button")
                page.wait_for_load_state("networkidle")

            # Process first page
            process_google_results(page, results_data, 1, context)

            # Try to get pages 2 and 3
            for page_num in range(2, 4):
                try:
                    # Find and click the next page button
                    next_button = page.query_selector(f"a[aria-label='Page {page_num}']")
                    if not next_button:
                        next_button = page.query_selector("a#pnnext")
                    
                    if next_button:
                        logging.info(f"Navigating to page {page_num}")
                        next_button.click()
                        page.wait_for_load_state("networkidle")
                        time.sleep(random.uniform(2, 4))  # Wait for results to load
                        
                        # Process current page results
                        process_google_results(page, results_data, page_num, context)
                    else:
                        logging.warning(f"Could not find navigation to page {page_num}")
                        break
                except Exception as e:
                    logging.error(f"Error navigating to page {page_num}: {e}")
                    break

            if not results_data:
                logging.error("No results found. Check serp_content.html for CAPTCHA or issues.")

        except Exception as e:
            logging.error(f"Error during Google scraping: {e}")
            raise e
        finally:
            if browser:
                browser.close()
                logging.info("Browser closed after Google scraping")

    return results_data

def process_google_results(page, results_data, page_num, context):
    """Helper function to process results from a single Google results page"""
    results = page.query_selector_all("div.tF2Cxc") or page.query_selector_all("div.g") or page.query_selector_all("div.VkpGBb")
    logging.info(f"Page {page_num}: Found {len(results)} results")

    for i, result in enumerate(results, 1):
        rank = (page_num - 1) * 10 + i
        title = result.query_selector("h3") or result.query_selector("div[role='heading']")
        link = result.query_selector("a")
        snippet = result.query_selector("div.VwiC3b") or result.query_selector("span:not([class])")

        title_text = title.inner_text() if title else "N/A"
        url_result = link.get_attribute("href") if link else "N/A"
        snippet_text = snippet.inner_text() if snippet else "N/A"
        emails = []
        mobiles = []

        if url_result and url_result.startswith("http"):
            try:
                logging.info(f"Visiting URL {rank}: {url_result}")
                linked_page = context.new_page()
                stealth_sync(linked_page)
                linked_page.goto(url_result, wait_until="networkidle", timeout=20000)

                linked_content = linked_page.content()
                emails = extract_emails(linked_content)
                mobiles = extract_indian_mobile_numbers(linked_content)

                if not emails:
                    contact_link = linked_page.query_selector("a[href*='contact'], a[href*='about']")
                    if contact_link:
                        contact_url = contact_link.get_attribute("href")
                        if not contact_url.startswith("http"):
                            contact_url = url_result.rstrip("/") + "/" + contact_url.lstrip("/")
                        logging.info(f"Visiting contact/about page: {contact_url}")
                        linked_page.goto(contact_url, wait_until="networkidle", timeout=20000)
                        contact_content = linked_page.content()
                        emails = extract_emails(contact_content)
                        mobiles += extract_indian_mobile_numbers(contact_content)

                mailto_links = linked_page.query_selector_all("a[href^='mailto:']")
                emails += [link.get_attribute("href").replace("mailto:", "") for link in mailto_links]

                logging.info(f"Found {len(emails)} emails and {len(mobiles)} mobiles on {url_result}")
                linked_page.close()
            except Exception as e:
                logging.error(f"Error scraping {url_result}: {e}")

        results_data.append({
            "rank": rank,
            "title": title_text,
            "url": url_result,
            "snippet": snippet_text,
            "emails": ", ".join(set(emails)) if emails else "None",
            "mobiles": ", ".join(set(mobiles)) if mobiles else "None"
        })

        time.sleep(random.uniform(2, 5))
def scrape_bing(query):
    logging.info(f"Starting Bing scrape for query: {query}")
    results_data = []

    with sync_playwright() as p:
        browser = None
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36",
                locale="en-US",
                timezone_id="Asia/Kolkata",
                geolocation={"latitude": 28.6139, "longitude": 77.2090},
                permissions=["geolocation"]
            )
            page = context.new_page()
            stealth_sync(page)

            url = f"https://www.bing.com/search?q={query.replace(' ', '+')}"
            logging.info(f"Navigating to: {url}")
            page.goto(url, wait_until="networkidle", timeout=30000)

            # Handle cookie consent if it appears
            consent_button = page.query_selector("button[id='bnp_btn_accept']")
            if consent_button:
                consent_button.click()
                logging.info("Clicked consent button")
                page.wait_for_load_state("networkidle")

            results = page.query_selector_all("li.b_algo")
            logging.info(f"Found {len(results)} Bing results")

            for i, result in enumerate(results[:10], 1):
                title_el = result.query_selector("h2")
                link_el = result.query_selector("h2 a") if title_el else None
                snippet_el = result.query_selector("div.b_caption p") or result.query_selector("p")

                title_text = title_el.inner_text() if title_el else "N/A"
                url = link_el.get_attribute("href") if link_el else "N/A"
                snippet_text = snippet_el.inner_text() if snippet_el else "N/A"
                emails = []
                mobiles = []

                if url and url.startswith("http"):
                    try:
                        logging.info(f"Visiting Bing result URL {i}: {url}")
                        linked_page = context.new_page()
                        stealth_sync(linked_page)
                        linked_page.goto(url, wait_until="networkidle", timeout=20000)

                        linked_content = linked_page.content()
                        emails = extract_emails(linked_content)
                        mobiles = extract_indian_mobile_numbers(linked_content)

                        if not emails:
                            contact_link = linked_page.query_selector("a[href*='contact'], a[href*='about']")
                            if contact_link:
                                contact_url = contact_link.get_attribute("href")
                                if not contact_url.startswith("http"):
                                    contact_url = url.rstrip("/") + "/" + contact_url.lstrip("/")
                                logging.info(f"Visiting contact/about page: {contact_url}")
                                linked_page.goto(contact_url, wait_until="networkidle", timeout=20000)
                                contact_content = linked_page.content()
                                emails = extract_emails(contact_content)
                                mobiles += extract_indian_mobile_numbers(contact_content)

                        mailto_links = linked_page.query_selector_all("a[href^='mailto:']")
                        emails += [link.get_attribute("href").replace("mailto:", "") for link in mailto_links]

                        logging.info(f"Found {len(emails)} emails and {len(mobiles)} mobiles on {url}")
                        linked_page.close()
                    except Exception as e:
                        logging.error(f"Error scraping Bing result {url}: {e}")

                results_data.append({
                    "rank": i,
                    "title": title_text,
                    "url": url,
                    "snippet": snippet_text,
                    "emails": ", ".join(set(emails)) if emails else "None",
                    "mobiles": ", ".join(set(mobiles)) if mobiles else "None"
                })

                time.sleep(random.uniform(2, 5))

            if not results:
                logging.error("No results found on Bing. Possible CAPTCHA or layout changes.")

        except Exception as e:
            logging.error(f"Error during Bing scraping: {e}")
            raise e
        finally:
            if browser:
                browser.close()
                logging.info("Browser closed after Bing scraping")

    return results_data

def send_email(selected_items):
    sender_email = "varun.singhal78@gmail.com"
    sender_password = "hrnk zfpf alrl uscj"

    all_emails = []
    for item in selected_items:
        emails_str = item.get('emails', '')
        emails_list = [email.strip() for email in emails_str.split(',') if email.strip()]
        all_emails.extend(emails_list)

    unique_emails = list(set(all_emails))

    if not unique_emails:
        logging.warning("No emails found in selected items to send to.")
        return "No recipient emails found in selected items."

    html_body = """
    <html>
    <head>
    <style>
        body {font-family: Arial, sans-serif; background-color: #f4f6f8; color: #333;}
        .container {max-width: 600px; margin: 20px auto; background: white; border-radius: 8px; padding: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1);}
        h1 {color: #0b74de;}
        p {font-size: 16px; line-height: 1.5;}
        .button {display: inline-block; padding: 12px 20px; margin-top: 20px; background-color: #0b74de; color: white; text-decoration: none; border-radius: 5px;}
        .footer {font-size: 12px; color: #999; margin-top: 30px; text-align: center;}
    </style>
    </head>
    <body>
    <div class="container">
        <h1>Appslure Websolution</h1>
        <p>Dear Valued Customer,</p>
        <p>We are excited to offer you our premium web development and digital marketing services tailored to help your business grow in the digital landscape.</p>
        <ul>
            <li>Custom Website Development</li>
            <li>Responsive & Mobile-Friendly Designs</li>
            <li>SEO & Online Marketing</li>
            <li>E-commerce Solutions</li>
            <li>24/7 Customer Support</li>
        </ul>
        <p>Let us help you create a powerful online presence with innovative technology and creative design.</p>
        <p>Get in touch with us today and take the first step towards digital success!</p>
        <a href="mailto:contact@appslure.com" class="button">Contact Us Now</a>
        <div class="footer">© 2025 Appslure Websolution. All rights reserved.</div>
    </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg['Subject'] = "Exclusive Service Offer from Appslure Websolution"
    msg['From'] = sender_email
    msg['To'] = ", ".join(unique_emails)

    mime_text = MIMEText(html_body, "html")
    msg.attach(mime_text)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, unique_emails, msg.as_string())
        logging.info(f"Email sent successfully to {unique_emails}")
        return f"Email sent successfully to {len(unique_emails)} recipients!"
    except Exception as e:
        logging.error(f"Error sending email: {e}")
        return f"Error sending email: {e}"

@app.route('/')
def index():
    return render_template('index.html', results=None, message=None)

@app.route('/scrape', methods=['POST'])
def scrape():
    keyword = request.form.get('keyword')
    engine = request.form.get('engine', 'google').lower()

    if not keyword:
        return render_template('index.html', results=None, message="Please enter a search keyword.")

    try:
        if engine == 'bing':
            results = scrape_bing(keyword)
        else:
            results = scrape_google(keyword)

        return render_template('index.html', results=results, message=f"Scraped {len(results)} results from {engine.title()}.")

    except Exception as e:
        logging.error(f"Scraping failed: {e}")
        return render_template('index.html', results=None, message=f"Error occurred: {e}")

@app.route('/send-email', methods=['POST'])
def send_email_route():
    selected_items = request.form.getlist('selectedItems')
    if not selected_items:
        return render_template('index.html', results=None, message="Please select at least one item.")

    selected_data = []
    for item in selected_items:
        try:
            selected_data.append(json.loads(item))
        except Exception as e:
            logging.error(f"Error parsing item: {e}")

    if not selected_data:
        return render_template('index.html', results=None, message="Error parsing selected items.")

    message = send_email(selected_data)
    return render_template('index.html', results=None, message=message)

if __name__ == '__main__':
  app.run(host='0.0.0.0', port=8080, debug=False)