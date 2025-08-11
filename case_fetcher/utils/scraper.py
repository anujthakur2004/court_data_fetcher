import asyncio
import base64
import base64
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

sessions = {}  # Store browser/page objects by session_id

async def init_session(session_id):
    url = "https://delhihighcourt.nic.in/app/get-case-type-status"

    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False)
    page = await browser.new_page()
    await page.goto(url, wait_until="domcontentloaded")

    # Detect iframe
    form_frame = None
    for f in page.frames:
        if "get-case-type-status" in f.url:
            form_frame = f
            break
    if not form_frame:
        raise Exception("Form iframe not found")

    # Wait for dropdowns
    await form_frame.wait_for_selector("#case_type")
    await form_frame.wait_for_selector("#case_year")

    # Fetch case types & years
    case_types = await form_frame.eval_on_selector_all(
        "#case_type option", "opts => opts.map(o => o.textContent.trim()).filter(t => t)"
    )
    years = await form_frame.eval_on_selector_all(
        "#case_year option", "opts => opts.map(o => o.textContent.trim()).filter(t => t)"
    )

    # Fetch captcha (text or image)
    captcha_img_b64 = None
    if await form_frame.query_selector("#captcha-code"):
        captcha_text = await form_frame.locator("#captcha-code").inner_text()
        from PIL import Image, ImageDraw
        import io, base64
        img = Image.new("RGB", (120, 40), color=(255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), captcha_text, fill=(0, 0, 0))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        captcha_img_b64 = base64.b64encode(buf.getvalue()).decode()
    else:
        captcha_element = await form_frame.query_selector("img")
        if not captcha_element:
            raise Exception("Captcha image not found inside iframe")
        img_bytes = await captcha_element.screenshot()
        import base64
        captcha_img_b64 = base64.b64encode(img_bytes).decode()

    # Store session for reuse
    sessions[session_id] = {
        "playwright": p,
        "browser": browser,
        "page": page,
        "form_frame": form_frame
    }

    return {
        "case_types": case_types,
        "years": years,
        "captcha_img": captcha_img_b64
    }

async def start_case_session(session_id, case_type, case_number, year, captcha_value):
    if session_id not in sessions:
        return {"error": "Session expired or not found"}

    sess = sessions.pop(session_id)
    browser = sess["browser"]
    form_frame = sess["form_frame"]

    # Fill details in same session
    await form_frame.select_option("#case_type", case_type)
    await form_frame.fill("#case_number", case_number)
    await form_frame.select_option("#case_year", str(year))
    await form_frame.fill("#captchaInput", captcha_value)

    # Submit
    await form_frame.click("#search")
    await form_frame.wait_for_selector("table", timeout=60000)

    html_content = await form_frame.content()
    await browser.close()
    await sess["playwright"].stop()

    return parse_case_results(html_content)



async def start_case_session(session_id, case_type, case_number, case_year, captcha_value):
    """Fill form & fetch results using stored session."""
    if session_id not in sessions:
        raise Exception("Session expired or not found.")

    session = sessions.pop(session_id)
    browser = session["browser"]
    frame = session["form_frame"]

    try:
        # Fill details
        await frame.select_option("#case_type", case_type)
        await frame.fill("#case_number", case_number)
        await frame.select_option("#case_year", str(case_year))
        await frame.fill("#captchaInput", captcha_value)

        # Submit form
        await frame.click("#search")

        # Wait for results table
        await frame.wait_for_selector("table", timeout=60000)
        html = await frame.content()

    finally:
        await browser.close()

    return parse_case_results(html)


def parse_case_results(html):
    """Parse HTML table into list of dicts."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return {"error": "No data found"}

    rows = []
    for tr in table.find_all("tr"):
        cols = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        rows.append(cols)

    return {"table": rows}
