from scrapers.strategy.ats.atsbasestrategy import ATSBaseStrategy
from scrapers.models.bronze.bronze_payload import BronzePayload
class GreenhouseStrategy(ATSBaseStrategy):
    def map_response_to_bronze_payload(self, company_name, headquarter, json_raw_response):
        job_list_information : list[BronzePayload] = []
        # Extract data information
        for job in json_raw_response["jobs"]:
            job_list_information.append(
                BronzePayload(
                    ats_name=self.source_system,
                    company_name = company_name,
                    headquarter = headquarter,
                    job_name = job["title"],
                    job_description = job["content"],
                    location = job["location"]["name"],
                    job_uploaded_at = job["first_published"],
                    job_url = job["absolute_url"],
                    employment_type = "Full Time",
                )
            )

        return job_list_information