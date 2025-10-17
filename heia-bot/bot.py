#!/usr/bin/env python3
import asyncio
import json
import os
from typing import List
from urllib.parse import quote

import discord
from discord import app_commands
from dotenv import load_dotenv
from openai import OpenAI

# Load environment variables from .env file
load_dotenv()

# --------------------------
# Config
# --------------------------
FILES_JSON = os.getenv("FILES_JSON", "files.json")
# Switch Drive share base (keep your token here or via env)
SHARE_BASE_URL = os.getenv(
    "SHARE_BASE_URL",
    "https://drive.switch.ch/index.php/s/BnL19x4G1Xk0Ran",
)
# LLM model (fast + cheap)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Hard cap of candidates passed to LLM to keep prompt reasonable
MAX_CANDIDATES_FOR_LLM = int(os.getenv("MAX_CANDIDATES_FOR_LLM", "350"))


# --------------------------
# Helpers
# --------------------------
def load_files() -> List[str]:
    with open(FILES_JSON, "r", encoding="utf-8") as f:
        files = json.load(f)
    # Ensure unique + sorted
    return sorted(set(files))


ALL_FILES = load_files()


def filter_by_year(files: List[str], year: int) -> List[str]:
    prefix = {1: "1ere/", 2: "2eme/", 3: "3eme/"}.get(year)
    if not prefix:
        raise ValueError("Year must be 1, 2, or 3.")
    return [p for p in files if p.startswith(prefix)]


def simple_substring_prefilter(
    query: str, candidates: List[str], limit: int
) -> List[str]:
    """
    Deterministic substring filter (NOT fuzzy):
      - lowercases both sides
      - keeps items that contain ANY token from query
      - if nothing matches, fall back to first `limit`
      - always cap length to `limit`
    """
    q = query.lower()
    # split on whitespace only; we don't want to be too aggressive
    tokens = [t for t in q.replace("%20", " ").split() if t]
    if not tokens:
        return candidates[:limit]

    def keep(path: str) -> bool:
        l = path.lower()
        return any(tok in l for tok in tokens)

    filtered = [p for p in candidates if keep(p)]
    if not filtered:
        return candidates[:limit]
    return filtered[:limit]


def folder_url_from_file_path(path: str) -> str:
    """
    Build a Switch Drive public link that opens the folder in the built-in PDF viewer.
    Example: https://.../index.php/s/<token>?path=%2F1ere%2FTeleinformatique%2F1er_Semestre%2FTE1#pdfviewer
    """
    folder = path.rsplit("/", 1)[0]
    encoded = quote("/" + folder)
    return f"{SHARE_BASE_URL}?path={encoded}#pdfviewer"


def filename_from_path(path: str) -> str:
    return path.rsplit("/", 1)[-1]


def build_llm_prompt(query: str, candidates: List[str]) -> str:
    # One-per-line to keep it simple and copy/paste safe for model
    listing = "\n".join(candidates)
    return (
        "You are given a user request for an exam file.\n"
        "From the list of file paths below, pick the most relevant path(s) that best match the request.\n"
        "Respond with ONLY the exact path(s) from the list, one per line. Do not add explanations.\n\n"
        f"User request: {query}\n\n"
        f"{listing}\n"
    )


# --------------------------
# LLM client
# --------------------------
openai_client = OpenAI()  # requires OPENAI_API_KEY in env


async def llm_select_paths(query: str, candidates: List[str], n: int) -> List[str]:
    """
    Ask LLM to select the best file path(s) (exactly as in candidates).
    We request the list; if it returns more lines than n, we take top n.
    """
    prompt = build_llm_prompt(query, candidates)
    resp = openai_client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )
    content = resp.choices[0].message.content.strip()
    # Split lines, keep those that are EXACT candidates (safety)
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    # De-dup and keep order
    seen = set()
    exact = []
    cand_set = set(candidates)
    for l in lines:
        if l in cand_set and l not in seen:
            exact.append(l)
            seen.add(l)
        if len(exact) >= n:
            break
    # Fallback: if LLM didn't return anything valid, just take first n candidates
    if not exact:
        exact = candidates[:n]
    return exact


# --------------------------
# Discord bot
# --------------------------
class ExamBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.none()
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Global commands; you can also sync to a single guild during development for faster updates:
        # test_guild = discord.Object(id=YOUR_GUILD_ID)
        # self.tree.copy_global_to(guild=test_guild)
        # await self.tree.sync(guild=test_guild)
        await self.tree.sync()


bot = ExamBot()


@bot.tree.command(
    name="old-exam",
    description="Find an old exam and return a folder link that opens the PDF viewer.",
)
@app_commands.describe(
    query="What you’re looking for (e.g., 'Teleinformatique TE1 2024')",
    year="1=1ere, 2=2eme, 3=3eme",
    n="How many results to return (1-5)",
)
@app_commands.choices(
    year=[
        app_commands.Choice(name="1ère (year 1)", value=1),
        app_commands.Choice(name="2ème (year 2)", value=2),
        app_commands.Choice(name="3ème (year 3)", value=3),
    ]
)
async def old_exam(
    interaction: discord.Interaction,
    query: str,
    year: app_commands.Choice[int],
    n: int = 1,
):
    await interaction.response.defer(thinking=True, ephemeral=False)
    n = max(1, min(n, 5))

    try:
        # 1) Filter by year
        year_num = year.value
        year_files = filter_by_year(ALL_FILES, year_num)

        # 2) Deterministic substring prefilter (keeps prompt small; NOT fuzzy)
        candidates = simple_substring_prefilter(
            query, year_files, MAX_CANDIDATES_FOR_LLM
        )
        if not candidates:
            await interaction.followup.send(
                f"🤷 No files found for year {year_num} after filtering. Try a different query."
            )
            return

        # 3) LLM disambiguation
        picks = await llm_select_paths(query, candidates, n=n)

        # 4) Reply
        embeds = []
        for p in picks:
            folder_url = folder_url_from_file_path(p)
            fname = filename_from_path(p)
            e = discord.Embed(
                title=fname,
                description=f"**Folder** (opens viewer): {folder_url}",
                color=0x2F3136,
            )
            # Show a monospace path
            e.add_field(name="Path", value=f"`{p}`", inline=False)
            embeds.append(e)

        await interaction.followup.send(
            content=f"🔎 **Query:** `{query}` • **Year:** {year_num}",
            embeds=embeds,
        )

    except Exception as e:
        await interaction.followup.send(f"❌ Error: {e}")


# --------------------------
# Entry
# --------------------------
if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        raise SystemExit("Missing DISCORD_TOKEN env var.")
    bot.run(token)
