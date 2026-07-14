from typing import List as TypeList
from .client import SharePointClient
from .models import ListModel

class ListService:
    """
    Handles operations for retrieving and listing SharePoint lists.
    """

    def __init__(self, client: SharePointClient):
        self.client = client

    def get_lists(self, site_id: str) -> TypeList[ListModel]:
        """
        Fetch lists for a site and construct domain models.
        """
        raw_lists = self.client.fetch_lists(site_id)
        lists = []
        
        for rl in raw_lists:
            lists.append(
                ListModel(
                    id=rl.get("id", ""),
                    name=rl.get("name", ""),
                    display_name=rl.get("displayName", ""),
                    web_url=rl.get("webUrl", ""),
                    fields=[],
                )
            )
        return lists
