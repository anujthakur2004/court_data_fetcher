import asyncio
import base64
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

_browser = None
_page = None
_frame = None
_pw = None

async def init_session():
    """
    Start browser session, get captcha image, keep iframe alive.
    """
    global _browser, _page, _frame, _pw

    _pw = await async_playwright().start()
    _browser = await _pw.chromium.launch(headless=False)
    _page = await _browser.new_page()

    url = "https://delhihighcourt.nic.in/app/get-case-type-status"
    await _page.goto(url, wait_until="domcontentloaded")

    # Get iframe
    for f in _page.frames:
        if "get-case-type-status" in f.url:
            _frame = f
            break

    if not _frame:
        raise Exception("Form iframe not found.")

    # Wait for captcha image
    captcha_elem = await _frame.wait_for_selector(
        "#captcha_image, #captcha-image, img",
        timeout=20000,
        state="visible"
    )
    if not captcha_elem:
        raise Exception("Captcha image not found inside iframe.")

    try:
        await captcha_elem.scroll_into_view_if_needed()
        img_bytes = await captcha_elem.screenshot()
    except:
        src = await captcha_elem.get_attribute("src")
        if src and src.startswith("data:image"):
            img_bytes = base64.b64decode(src.split(",")[1])
        else:
            raise Exception("Could not capture captcha image.")

    captcha_b64 = base64.b64encode(img_bytes).decode()

    return {"captcha_img": captcha_b64}


async def submit_case_form(case_type, case_number, case_year, captcha_value):
    """
    Submit details in same browser session and fetch results.
    """
    global _frame, _browser, _pw

    if not _frame:
        raise Exception("Invalid session ID")

    await _frame.select_option("#case_type", case_type)
    await _frame.fill("#case_number", case_number)
    await _frame.select_option("#case_year", str(case_year))
    await _frame.fill("#captchaInput", captcha_value)
    await _frame.click("#search")

    await _frame.wait_for_selector("table", timeout=20000)
    html_content = await _frame.content()

    # Close after fetch
    await _browser.close()
    await _pw.stop()
    _frame = None
    _browser = None
    _pw = None

    return parse_results(html_content)


def parse_results(html):
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return {"error": "No case data found."}

    headers = [th.get_text(strip=True) for th in table.find_all("th")]
    rows = []
    for tr in table.find_all("tr")[1:]:
        cols = [td.get_text(strip=True) for td in tr.find_all("td")]
        if cols:
            rows.append(dict(zip(headers, cols)))

    return {"table": rows}
