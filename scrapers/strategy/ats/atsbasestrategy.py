from abc import ABC, abstractmethod
from typing import List


BUCKET_NAME = "api"

class ATSBaseStrategy(ABC):
    def __init__(self, source_system):
        self.source_system = source_system

    @abstractmethod
    def map_response_to_bronze_payload(self, company_name, headquarter, json_raw_response):
        pass


