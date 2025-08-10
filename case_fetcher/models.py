from django.db import models

class CaseQuery(models.Model):
    case_type = models.CharField(max_length=50)
    case_number = models.CharField(max_length=50)
    year = models.CharField(max_length=4)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField()
    raw_response = models.TextField(blank=True, null=True)
    success = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.case_type}/{self.case_number}/{self.year}"

class CaseData(models.Model):
    query = models.OneToOneField(CaseQuery, on_delete=models.CASCADE)
    parties = models.TextField()
    filing_date = models.DateField(null=True, blank=True)
    next_hearing = models.DateField(null=True, blank=True)
    orders = models.JSONField(default=list)  # Stores list of {date: str, pdf_link: str}

    def __str__(self):
        return f"Data for {self.query}"