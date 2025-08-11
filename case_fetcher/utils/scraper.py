import base64
from playwright.async_api import async_playwright

# Keep sessions alive between GET and POST
sessions = {}

async def init_session():
    """Launch browser, get captcha image, return session_id + captcha"""
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=False)
    page = await browser.new_page()

    await page.goto("https://delhihighcourt.nic.in/app/get-case-type-status", wait_until="domcontentloaded")

    # Find iframe
    form_frame = None
    for f in page.frames:
        if "get-case-type-status" in f.url:
            form_frame = f
            break
    if not form_frame:
        raise Exception("Captcha form iframe not found.")

    # Try text captcha first
    captcha_text_el = await form_frame.query_selector("#captcha-code")
    captcha_img_data = None
    if captcha_text_el:
        text_val = (await captcha_text_el.inner_text()).strip()
        captcha_img_data = f"data:image/png;base64,{base64.b64encode(text_val.encode()).decode()}"
    else:
        # Image captcha
        captcha_img_el = await form_frame.query_selector("img")
        if not captcha_img_el:
            raise Exception("Captcha image not found inside iframe.")
        img_bytes = await captcha_img_el.screenshot()
        captcha_img_data = f"data:image/png;base64,{base64.b64encode(img_bytes).decode()}"

    # Save session
    session_id = str(len(sessions) + 1)
    sessions[session_id] = {
        "browser": browser,
        "page": page,
        "frame_url_pattern": "get-case-type-status"
    }
    return {"session_id": session_id, "captcha_img": captcha_img_data}

async def submit_case(session_id, case_type, case_number, case_year, captcha_value):
    """Re-find iframe, fill details, scrape results"""
    sess = sessions.get(session_id)
    if not sess:
        return {"error": "Session expired or not found"}

    page = sess["page"]
    form_frame = None
    for f in page.frames:
        if sess["frame_url_pattern"] in f.url:
            form_frame = f
            break
    if not form_frame:
        return {"error": "Form iframe not found on submit"}

    await form_frame.select_option("#case_type", case_type)
    await form_frame.fill("#case_number", str(case_number))
    await form_frame.select_option("#case_year", str(case_year))
    await form_frame.fill("#captchaInput", captcha_value)

    await form_frame.click("#search")
    await form_frame.wait_for_selector("table", timeout=60000)

    html = await form_frame.content()
    await sess["browser"].close()
    sessions.pop(session_id, None)

    return parse_results(html)

def parse_results(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if not table:
        return {"error": "No case data found"}
    rows = []
    for tr in table.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all(["td", "th"])]
        if cells:
            rows.append(cells)
    return {"table": rows}
