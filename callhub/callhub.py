import requests
from .auth import CallHubAuth


class CallHub:
    def __init__(self, api_key=None):
        session = requests.Session()
        session.auth = CallHubAuth(api_key=api_key)
        self.session = session

    def agent_stats(self, start, end):
        params = {"start_date":start, "end_date":end}
        response = self.session.get("https://api.callhub.io/v1/analytics/agent-leaderboard", params=params)
        return response.json().get("plot_data")
