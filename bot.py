import os
import discord
from discord.ext import commands, tasks
from dotenv import load_dotenv
import requests

# Load environment variables from token.env file
load_dotenv(dotenv_path='./token.env')

# Initialize bot client with intents
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True  # Enable message content intent

bot = commands.Bot(command_prefix='!', intents=intents)

# Global variables
github_token = os.getenv('GITHUB_TOKEN')
owner = 'changcheng967'  # Replace with your GitHub username or organization
repo = 'kata_speed'  # The repository name where issues are created
issue_updates_channel_id = 1261472570088358079  # Replace with your channel ID
last_comment_id = None

# Background task to check for new issue comments and send updates
@tasks.loop(seconds=30)  # Adjust as needed
async def check_issue_updates():
    global github_token, last_comment_id

    if not github_token:
        print('GitHub token not found. Skipping issue update check.')
        return

    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    url = f'https://api.github.com/repos/{owner}/{repo}/issues/comments'
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            comments_data = response.json()
            new_comments = []

            for comment in comments_data:
                comment_id = comment['id']
                if last_comment_id is None or comment_id > last_comment_id:
                    new_comments.append(comment)
                    if last_comment_id is None or comment_id > last_comment_id:
                        last_comment_id = comment_id

            for comment in new_comments:
                issue_number = comment['issue_url'].split('/')[-1]
                author = comment['user']['login']
                message = f'New comment by {author} on issue #{issue_number}: {comment["body"]}'

                # Send the message to a specific Discord channel
                channel = bot.get_channel(issue_updates_channel_id)
                if channel:
                    await channel.send(message)
                else:
                    print(f'Channel with ID {issue_updates_channel_id} not found.')

        else:
            print(f'Failed to fetch issue comments. Status code: {response.status_code}')
    except requests.exceptions.RequestException as e:
        print(f'Error fetching issue comments: {e}')

# Set bot's initial presence status and start issue update monitoring
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="!bot_help to show available commands"))
    check_issue_updates.start()
    print(f'Logged in as {bot.user.name}')

# Command: Create an issue via DM
@bot.command(name='createissue')
async def create_issue(ctx, creator_name: str, *, title: str):
    global github_token

    if not title:
        await ctx.send('Please provide a title for the issue!')
        return

    # Determine the issue creator's name
    if creator_name.strip():
        issue_creator = creator_name
    else:
        issue_creator = 'Anonymous'

    # Construct the issue body with user information
    issue_body = f'Issue created by {issue_creator}'

    # Post issue to GitHub
    headers = {
        'Authorization': f'token {github_token}',
        'Accept': 'application/vnd.github.v3+json'
    }

    url = f'https://api.github.com/repos/{owner}/{repo}/issues'
    payload = {
        'title': title,
        'body': issue_body
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 201:
            issue_data = response.json()
            issue_number = issue_data['number']
            await ctx.send(f'Issue created successfully in {repo} repository by {issue_creator}!')
            await ctx.send(f'Issue #{issue_number} created: {issue_data["html_url"]}')
        else:
            await ctx.send(f'Failed to create issue. Status code: {response.status_code}')
    except requests.exceptions.RequestException as e:
        print(f'Error creating issue: {e}')
        await ctx.send('Failed to create issue. Please try again later.')

# Command: Help command to display available commands and usage
@bot.command(name='bot_help')
async def bot_help(ctx):
    help_message = """
    **Available Commands:**
    `!createissue <name> <title>` - Creates a new issue in the Kata_speed repository.
      - `<name>`: Name of the issue creator (default is Anonymous).
      - `<title>`: Title of the issue.

    **Example Usage:**
    To create a new issue with a specific title:
    ```
    !createissue Anonymous Bug Report
    ```

    To create a new issue with a title and specify the creator's name:
    ```
    !createissue John Doe Feature Request
    ```
    """
    await ctx.send(help_message)

# Event: Handle DM messages from users to reply to issues
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return  # Ignore messages sent by the bot itself

    # Check if the message is a reply to a bot message in DM
    if isinstance(message.channel, discord.DMChannel) and message.reference:
        referenced_message = await message.channel.fetch_message(message.reference.message_id)
        if referenced_message.author == bot.user:
            issue_number = referenced_message.content.split('#')[1].split(' ')[0]  # Extract issue number from bot's message
            comment_body = message.content  # The reply content from the user

            # Post comment to GitHub issue
            headers = {
                'Authorization': f'token {github_token}',
                'Accept': 'application/vnd.github.v3+json'
            }

            url = f'https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}/comments'
            payload = {
                'body': comment_body
            }

            try:
                response = requests.post(url, headers=headers, json=payload)
                if response.status_code == 201:
                    await message.channel.send(f'Reply added to issue #{issue_number} successfully!')
                else:
                    await message.channel.send(f'Failed to add reply to issue #{issue_number}. Status code: {response.status_code}')
            except requests.exceptions.RequestException as e:
                print(f'Error adding reply to issue: {e}')
                await message.channel.send(f'Failed to add reply to issue #{issue_number}. Please try again later.')

    await bot.process_commands(message)

# Run the bot with the token loaded from environment variable
bot_token = os.getenv('DISCORD_TOKEN')
if bot_token:
    bot.run(bot_token)
else:
    print('DISCORD_TOKEN environment variable not found in token.env.')
