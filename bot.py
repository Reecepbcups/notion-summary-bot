# pip install notion-client --break-system-packages

outputFormat = """Y: %YESTERDAY%
T: %TODAY%
H: None
"""

import datetime
import os

import httpx
from notion_client import Client

# https://developers.notion.com/reference/create-a-token
DB="112bf17dad05808b93aff5525170c5ae" # from url. Make sure to add to page: 3 dots in the top right, connections. add bot.


# load NOTION_TOKEN from .env
from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
if NOTION_TOKEN is None:
    raise Exception("NOTION_TOKEN not found in .env")

notion = Client(auth=NOTION_TOKEN)

# query content within DB
response = notion.databases.query(database_id=DB)

# get the first page (when do we need more?)
page_id = response["results"][0]["id"]

class NotionObject:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

todays_date = datetime.datetime.now().strftime("%Y-%m-%d")
yesterdays_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")

todays_tasks: list[NotionObject] = []
yesterdays_tasks = []

yesterday_output = []
today_output = []

for result in response["results"]:
    obj = NotionObject(**result)

    name = obj.properties["Task name"]["title"][0]["plain_text"]
    date = obj.properties["Date"]["date"]["start"]
    repo_pr = obj.properties["Repo/PR"]["rich_text"]
    notes = obj.properties["Notes"]["rich_text"]

    tag_names = []
    for tag in obj.properties["Tags"]["multi_select"]:
        tag_names.append(tag["name"])

    tags = ",".join(tag_names)

    fmt = f"({tags}) {name}"

    if date == todays_date:
        today_output.append(fmt)
    elif yesterdays_date == date:
        yesterday_output.append(fmt)

yesterday_output = "; ".join(yesterday_output)
today_output = "; ".join(today_output)

output = outputFormat.replace("%YESTERDAY%", yesterday_output).replace("%TODAY%", today_output)

print(output)
