from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
import asyncio
import uuid

from .utils.scraper import init_session, start_case_session

@csrf_exempt
def fetch_case_view(request):
    if request.method == "GET":
        # Generate unique session ID for the captcha session
        session_id = str(uuid.uuid4())

        # Init session & get dropdowns + captcha
        try:
            data = asyncio.run(init_session(session_id))
        except Exception as e:
            return HttpResponse(f"Error: {str(e)}")

        return render(request, "index.html", {
            "session_id": session_id,
            "case_types": data["case_types"],
            "years": data["years"],
            "captcha_img": data["captcha_img"]
        })

    elif request.method == "POST":
        session_id = request.POST.get("session_id")
        case_type = request.POST.get("case_type")
        case_number = request.POST.get("case_number")
        case_year = request.POST.get("case_year")
        captcha_value = request.POST.get("captcha_value")

        try:
            result_data = asyncio.run(
                start_case_session(session_id, case_type, case_number, case_year, captcha_value)
            )
        except Exception as e:
            return HttpResponse(f"Error: {str(e)}")

        return render(request, "results.html", {"case_data": result_data})
