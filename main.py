import aiohttp
import asyncio
import json
from utils import send_discord_update, send_discord_webhook
import discord
import datetime

class ClassLookup:
    def __init__(self, session: aiohttp.ClientSession=None):
        self.session = session

        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
            'X-Requested-With': 'XMLHttpRequest',
        }

    async def __aenter__(self):
        if (not self.session): 
            self.session = aiohttp.ClientSession()
        
        await self.instantiate_session()
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        await self.session.close()

    def convert_course_code(self, course_code: str) -> tuple[str, int]:
        return (course_code[:-4], int(course_code[-4:]))

    async def search_course(self, course_code: str):
        subject, coursenum = self.convert_course_code(course_code)

        params = {
            'txt_subject': subject,
            'txt_courseNumber': str(coursenum),
            'txt_term': TERM,
            'startDatepicker': '',
            'endDatepicker': '',
            'pageOffset': '0',
            'pageMaxSize': '100', # Adjust as needed, but 100 is a good maximum page size
            'sortColumn': 'subjectDescription',
            'sortDirection': 'asc',
        }

        response = await self.session.get(
            f'https://{SIGNUP_DOMAIN}/StudentRegistrationSsb/ssb/searchResults/searchResults',
            params=params,
            headers=self.headers
        )
        return (await response.json())['data']

    async def instantiate_session(self):
        # Request 1
        await self.session.get(
            f'https://{SIGNUP_DOMAIN}/StudentRegistrationSsb/ssb/registration/registration',
            headers=self.headers
        )

        # Request 2
        params = {
            'mode': 'search',
        }
        data = {
            'term': TERM,
            'studyPath': '',
            'studyPathText': '',
            'startDatepicker': '',
            'endDatepicker': '',
        }
        await self.session.post(
            f'https://{SIGNUP_DOMAIN}/StudentRegistrationSsb/ssb/term/search',
            params=params,
            headers=self.headers,
            data=data,
        )
    
async def main(courses: list[str]) -> None:
    before_data = {}
    async with ClassLookup() as cl:
        while True:
            for course in courses:
                try:
                    class_data = await cl.search_course(course)
                except Exception as e:
                    print(f"Error occurred: {e}. Restarting session...")

                    embed = discord.Embed(
                        title="Session Error",
                        description=f"An error occurred while fetching data for course {course}. Restarting session...",
                        color=discord.Color.red(),
                        timestamp=datetime.datetime.now()
                    )
                    embed.set_footer(
                        text=config['footer_text'], 
                        icon_url="https://cdn.discordapp.com/attachments/891493636611641345/1405892671225991311/georgia-tech-seeklogo.png"
                    )
                    embed.add_field(name='Traceback', value=f"```{str(e)}```", inline=False)

                    send_discord_webhook(embed)
                    await cl.close()
                    await main(courses)
                class_data = {section['courseReferenceNumber']: section for section in class_data}

                # Initialization
                if (course not in before_data):
                    before_data[course] = class_data
                    continue

                # Retrieving class information from before_data
                before_class_data = before_data[course]
                # class_data[list(before_class_data.keys())[0]]['enrollment'] -= 1 # Debugging for hard check
                # before_class_data.pop(list(before_class_data.keys())[0]) # Debugging for soft check

                # Hard checking if there is a change in the size of a class
                for crn, section_data in class_data.items():
                    before_section_data = before_class_data[crn]
                    # If there is a change in enrollment, maximum enrollment, wait count, or wait capacity -> send a webhook
                    if (section_data['enrollment'] < before_section_data['enrollment'] 
                        or section_data['maximumEnrollment'] > before_section_data['maximumEnrollment']
                        or section_data['waitCount'] < before_section_data['waitCount']
                        or section_data['waitCapacity'] > before_section_data['waitCapacity']
                        ):
                            print(f"Course {course} has changed in section {crn}")
                            await send_discord_update(
                                section_data,
                                title=f"Course Section Updated",
                                color=discord.Color.orange()
                            )
                            before_data[course] = class_data

                # Soft checking if a difference in the number of classes exists
                print(class_data)
                if (len(before_class_data) != len(class_data)):
                    # Course data changed. Now finding the difference

                    print(f"Course {course} has changed in number of sections")
                    for crn in class_data.keys():
                        if (crn not in before_class_data):
                            print(f"New section found: {crn}. Sending webhook")
                            await send_discord_update(
                                class_data[crn],
                                title=f"Course Section Added",
                                color=discord.Color.green()
                                )

                    before_data[course] = class_data
            
            await asyncio.sleep(1) # Avoid rate limiting issues

if __name__ == '__main__':
    with open('config.json', 'r') as f:
        config = json.load(f)

    TERM = config['term']
    SIGNUP_DOMAIN = config['signup_domain_api']
    asyncio.run(main(config['courses']))