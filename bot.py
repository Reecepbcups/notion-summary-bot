# pip install notion-client --break-system-packages
import datetime
import os

import httpx
from discord import Embed, SyncWebhook, Webhook
from notion_client import Client

# https://developers.notion.com/reference/create-a-token
DB="112bf17dad05808b93aff5525170c5ae" # from url. Make sure to add to page: 3 dots in the top right, connections. add bot.

from dotenv import load_dotenv

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
if NOTION_TOKEN is None:
    raise Exception("NOTION_TOKEN not found in .env")

class NotionObject:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

outputFormat = """Y: %YESTERDAY%
T: %TODAY%
H: None
"""

today = datetime.datetime.now() - datetime.timedelta(days=+2)
todays_date = today.strftime("%Y-%m-%d")

def main():
    notion = Client(auth=NOTION_TOKEN)
    response = notion.databases.query(database_id=DB)
    # get the first page (when do we need more?)
    page_id = response["results"][0]["id"]

    # dates to check
    previous_dates = add_previous_event_dates(today)

    today_output = []
    yesterday_output = []

    todays_events = filter_events_for_date(response, todays_date)
    yesterday_events = get_previous_events(response, previous_dates)

    assert_require_events_to_post(todays_events, yesterday_events)

    output = outputFormat.replace("%YESTERDAY%", f"{format_output(yesterday_events)}").replace("%TODAY%", f"{format_output(todays_events)}")
    msg_output(output)

def get_random_hex_color() -> int:
    return int("0x" + os.urandom(3).hex(), 16)

def getProposalEmbed(name, desc) -> Embed:
    embed = Embed(title=f"{name}", description=desc, color=get_random_hex_color())

    # embed.add_field(name="", value=line, inline=False)
    # embed.set_image(url=IMAGE)
    return embed

def msg_output(output: str):
    print(output)

    WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK")
    if not WEBHOOK_URL:
        print("No DISCORD_WEBHOOK found in .env. Not sending message.")
        return

    webhook = SyncWebhook.from_url(WEBHOOK_URL)
    webhook.send(username="Slack Updates", embed=getProposalEmbed(f"Updates {todays_date}", output))

def add_previous_event_dates(today: datetime.datetime) -> list[str]:
    todays_day = today.strftime("%A")
    if todays_day in ["Sunday", "Saturday"]:
        print(f"(add_previous_event_dates) It's {todays_day}, the weekend! No message to post.")
        exit(0)

    # (always) add yesterdays date
    pv_e_dates = [(today - datetime.timedelta(days=1)).strftime("%Y-%m-%d")]

    # if today is Monday, we add Sunday and Sat to the
    # previous_events_dates (since it has not been posted yet)
    if todays_day == "Monday":
        pv_e_dates.append((today - datetime.timedelta(days=2)).strftime("%Y-%m-%d"))
        pv_e_dates.append((today - datetime.timedelta(days=3)).strftime("%Y-%m-%d"))
        # print("It's Monday! Adding Sunday and Saturday to previous events.")

    # remove any duplicates
    return list(set(pv_e_dates))




def filter_events_for_date(notion_db_response: dict, date: str) -> list[NotionObject]:
    if date is None:
        raise ValueError("date cannot be None")
    events = []
    for result in notion_db_response["results"]:
        obj = NotionObject(**result)
        if obj.properties["Date"]["date"]["start"] == date:
            events.append(obj)
    return events

def format_output(events: list[NotionObject]) -> str:
    # andromeda: ["some value", "other value"]
    similar_tags: dict[str, list[notion]] = {}

    for event in events:
        name = event.properties["Task name"]["title"][0]["plain_text"]
        repo_pr = event.properties["Repo/PR"]["rich_text"]
        notes = event.properties["Notes"]["rich_text"]

        tag_names = []
        for tag in event.properties["Tags"]["multi_select"]:
            tag_names.append(tag["name"])

        similar_tags[','.join(tag_names)] = similar_tags.get(','.join(tag_names), []) + [name]

    output = []
    for t, v in similar_tags.items():
        output.append(f"[{t}] {', '.join(v)}")
    return "; ".join(output)


def get_previous_events(notion_db_resp: dict, prev_dates_to_check: list[str]) -> list[NotionObject]:
    if prev_dates_to_check is None:
        raise ValueError("prev_dates_to_check cannot be None")
    prev_events = []
    for date in prev_dates_to_check:
        prev_events += filter_events_for_date(notion_db_resp, date)
    return prev_events

def assert_require_events_to_post(todays_events: list[NotionObject], yesterday_events: list[NotionObject]):
    if len(todays_events) == 0:
        print(f"No events for today. Not posting."); exit(0)
    elif len(yesterday_events) == 0:
        print(f"No events for yesterday. Not posting."); exit(0)

if __name__ == '__main__':
    main()
