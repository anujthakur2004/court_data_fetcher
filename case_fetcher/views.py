from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import asyncio
from .utils import scraper

CASE_TYPES = [
    "W.P.(C)", "W.P.(CRL)", "LPA", "FAO", "CS(OS)", "CS(COMM)"  # Add all if needed
]
YEARS = list(range(2025, 1950, -1))

@csrf_exempt
def fetch_case_view(request):
    if request.method == "GET":
        captcha_info = asyncio.run(scraper.init_session())
        return render(request, "index.html", {
            "case_types": CASE_TYPES,
            "years": YEARS,
            "captcha_img": captcha_info["captcha_img"]
        })

    elif request.method == "POST":
        case_type = request.POST.get("case_type")
        case_number = request.POST.get("case_number")
        case_year = request.POST.get("case_year")
        captcha_value = request.POST.get("captcha_value")

        results = asyncio.run(
            scraper.submit_case_form(case_type, case_number, case_year, captcha_value)
        )
        return render(request, "results.html", {"case_data": results})
