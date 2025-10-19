import os

from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_next_day_deadlines(message_text: str, tomorrow_date: str) -> str:
    """
    Sends the entire pinned message to GPT and asks which line(s)
    correspond to the given tomorrow date (in dd.mm format).
    If none, GPT must answer exactly 'NO_DEADLINE_FOUND'.
    """
    prompt = f"""
You are given a message listing assignment deadlines from a Discord channel.

Your task: from this message, extract the exact line(s) that correspond to the date {tomorrow_date}. 

Return the line(s) exactly as they appear in the message, one per line.

If there is no matching deadline, reply ONLY with:
NO_DEADLINE_FOUND

Message content:
{message_text}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    return response.choices[0].message.content.strip()
