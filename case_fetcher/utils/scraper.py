import asyncio
import base64
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import time

async def get_delhi_hc_captcha():
    """Fetch CAPTCHA from Delhi High Court website"""
    url = "https://delhihighcourt.nic.in/app/get-case-type-status"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            await page.goto(url, timeout=30000)
            
            # Try to find CAPTCHA image first
            captcha_img = await page.query_selector("#captchaRefresh img")
            if captcha_img:
                img_bytes = await captcha_img.screenshot()
                return {
                    "type": "image",
                    "value": base64.b64encode(img_bytes).decode("utf-8")
                }
            
            # Fallback to text CAPTCHA
            captcha_text_element = await page.query_selector("#captcha-code")
            if captcha_text_element:
                captcha_text = await captcha_text_element.inner_text()
                return {
                    "type": "text",
                    "value": captcha_text.strip()
                }
            
            raise Exception("No CAPTCHA found on page")
            
        except Exception as e:
            raise Exception(f"CAPTCHA fetch error: {str(e)}")
        finally:
            await browser.close()

async def fetch_case_details(case_type, case_number, year, captcha_value):
    """Submit case search form and return parsed results"""
    url = "https://delhihighcourt.nic.in/app/get-case-type-status"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            viewport={"width": 1280, "height": 1024}
        )
        page = await context.new_page()
        
        try:
            # Navigate to case status page
            await page.goto(url, timeout=30000, wait_until="networkidle")
            
            # Fill form data
            await page.select_option("#case_type", value=case_type)
            await page.fill("#case_number", case_number)
            await page.select_option("#case_year", value=str(year))
            await page.fill("#captchaInput", captcha_value)
            
            # Submit form
            await page.click("#search")
            
            # Wait for results or error
            try:
                await page.wait_for_selector(".case-details, .error-message", timeout=15000)
            except:
                # Check if CAPTCHA failed
                if await page.query_selector("#captchaInput:invalid"):
                    raise Exception("Invalid CAPTCHA entered")
                raise Exception("Results not loaded in time")
            
            # Check for error messages
            error_msg = await page.query_selector(".error-message")
            if error_msg:
                error_text = await error_msg.inner_text()
                raise Exception(error_text.strip())
            
            # Get and parse results
            html = await page.content()
            return parse_case_results(html)
            
        except Exception as e:
            await page.screenshot(path="debug_search_fail.png")
            raise Exception(f"Case search failed: {str(e)}")
        finally:
            await context.close()

def parse_case_results(html):
    """Parse case details from HTML response"""
    soup = BeautifulSoup(html, "html.parser")
    result = {
        "parties": [],
        "dates": {},
        "orders": []
    }
    
    # Extract parties
    party_elements = soup.select(".party-row")
    for party in party_elements:
        result["parties"].append(party.get_text(strip=True))
    
    # Extract important dates
    date_labels = ["Filing Date", "Next Hearing", "Disposal Date"]
    for label in date_labels:
        element = soup.find("td", string=label)
        if element and element.find_next_sibling("td"):
            result["dates"][label] = element.find_next_sibling("td").get_text(strip=True)
    
    # Extract orders/judgments
    order_rows = soup.select(".order-row")
    for row in order_rows:
        date = row.select_one(".order-date")
        link = row.select_one("a[href$='.pdf']")
        if date and link:
            result["orders"].append({
                "date": date.get_text(strip=True),
                "pdf_url": link["href"]
            })
    
    return result

# For testing
async def test_captcha():
    print(await get_delhi_hc_captcha())

async def test_case_search():
    result = await fetch_case_details(
        case_type="WP(C)",
        case_number="1234",
        year="2023",
        captcha_value="ABCD12"  # You'll need to get this manually
    )
    print(result)

if __name__ == "__main__":
    # asyncio.run(test_captcha())
    asyncio.run(test_case_search())