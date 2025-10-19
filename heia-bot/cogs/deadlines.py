import datetime
import os
from zoneinfo import ZoneInfo

import discord
from discord.ext import commands, tasks
from utils.gpt_utils import extract_next_day_deadlines
from utils.state_manager import has_already_sent, save_last_sent_hash

RENDU_CHANNEL_ID = int(os.getenv("RENDU_CHANNEL_ID"))
RENDU_MESSAGE_ID = int(os.getenv("RENDU_MESSAGE_ID"))
GENERAL_CHANNEL_ID = int(os.getenv("GENERAL_CHANNEL_ID"))

ZURICH_TZ = ZoneInfo("Europe/Zurich")

# Load the HH:MM time from env or fallback to 17:08 if not set
DAILY_ALERT_TIME = os.getenv("DEADLINE_ALERT_HOUR", "17:17")
alert_hour, alert_minute = map(int, DAILY_ALERT_TIME.split(":"))
time = datetime.time(hour=alert_hour, minute=alert_minute, tzinfo=ZURICH_TZ)


class DeadlinesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_deadlines.start()

    def cog_unload(self):
        self.check_deadlines.cancel()

    @tasks.loop(time=time)
    async def check_deadlines(self):
        print("🔍 Checking deadlines...")
        # Use Zurich local time here
        now = datetime.datetime.now(ZURICH_TZ)
        tomorrow = (now + datetime.timedelta(days=1)).strftime("%d.%m")

        rendu_channel = self.bot.get_channel(RENDU_CHANNEL_ID)
        general_channel = self.bot.get_channel(GENERAL_CHANNEL_ID)

        if not rendu_channel or not general_channel:
            print("❌ Missing channel references.")
            return

        try:
            msg = await rendu_channel.fetch_message(RENDU_MESSAGE_ID)
        except Exception as e:
            print(f"❌ Could not fetch message: {e}")
            return

        result = extract_next_day_deadlines(msg.content, tomorrow)
        print(f"🔍 GPT result for {tomorrow}: {result}")

        if result == "NO_DEADLINE_FOUND":
            return

        if has_already_sent(result):
            print("✅ Already sent reminder for today.")
            return

        embed = discord.Embed(
            title=f"📅 Rendu prévu pour le {tomorrow}",
            description=result,
            color=discord.Color.blue(),
        )

        await general_channel.send(
            content="@everyone Rappel de rendu pour demain 👇",
            embed=embed,
            allowed_mentions=discord.AllowedMentions(everyone=True),
        )

        save_last_sent_hash(result)
        print("✅ Reminder sent and saved.")


async def setup(bot):
    await bot.add_cog(DeadlinesCog(bot))
