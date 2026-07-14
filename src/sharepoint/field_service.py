from typing import List as TypeList
from .client import SharePointClient
from .classifier import FieldClassifier
from .models import Field

class FieldService:
    """
    Handles operations for retrieving and classifying columns (fields) in SharePoint lists.
    """

    def __init__(self, client: SharePointClient):
        self.client = client

    def get_fields(self, site_id: str, list_id: str) -> TypeList[Field]:
        """
        Fetch columns for a list, classify each, and construct Field domain models.
        """
        raw_cols = self.client.fetch_columns(site_id, list_id)
        fields = []
        
        for rc in raw_cols:
            fields.append(FieldClassifier.classify(rc))
            
        return fields
