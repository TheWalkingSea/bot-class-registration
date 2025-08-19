import aiohttp
from discord import Webhook
import discord
import json
import datetime

with open('config.json', 'r') as f:
    config = json.load(f)

async def send_discord_webhook(embed: discord.Embed) -> None:
    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(config['webhook_url'], session=session)
        await webhook.send(embed=embed)

async def send_discord_update(payload: dict[str, str], *args, **kwargs) -> None:
    # Description
    description = f"**{payload['subjectCourse']}** - {payload['courseTitle']} ({payload['creditHours']} Credit{'s' if int(payload['creditHours'] > 1) else ''})"

    # Meeting Times
    meeting_times = []
    DAYS = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
    for day in DAYS:
        if (payload['meetingsFaculty'][0]['meetingTime'][day]):
            meeting_times.append(day.capitalize())

    meeting_times = ' & '.join(meeting_times)

    # Time
    startTime = datetime.datetime.strptime(payload['meetingsFaculty'][0]['meetingTime']['beginTime'], '%H%M')
    endTime = datetime.datetime.strptime(payload['meetingsFaculty'][0]['meetingTime']['endTime'], '%H%M')
    time = f"{startTime.strftime('%I:%M %p')} - {endTime.strftime('%I:%M %p')}"

    # Status
    status = f"{payload['enrollment']}/{payload['maximumEnrollment']} Seats"
    if (payload['waitCapacity']):
        status += f"\n{payload['waitCount']}/{payload['waitCapacity']} Waitlist Seats"
    
    
    embed = discord.Embed(description=description, timestamp=datetime.datetime.now(), *args, **kwargs)
    embed.set_footer(
        text=config['footer_text'], 
        icon_url="https://cdn.discordapp.com/attachments/891493636611641345/1405892671225991311/georgia-tech-seeklogo.png"
    )
    embed.add_field(name='Schedule Type', value=payload['scheduleTypeDescription'], inline=True)
    embed.add_field(name='CRN', value=payload['courseReferenceNumber'], inline=True)
    embed.add_field(name='Section', value=payload['sequenceNumber'], inline=True)


    embed.add_field(name='Meeting Times', value=f'{meeting_times}\n{time}', inline=False)
    embed.add_field(name='Status', value=status, inline=False)

    await send_discord_webhook(embed)