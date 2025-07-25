import discord
import os
import json
from datetime import datetime
from discord import app_commands
from discord.ext import commands

TOKEN = os.getenv("TOKEN")
ADMIN_CHANNEL_ID = int(os.getenv("ADMIN_CHANNEL_ID"))
BAN_LIST_CHANNEL_ID = int(os.getenv("BAN_LIST_CHANNEL_ID"))
GUILD_ID = int(os.getenv("GUILD_ID"))
TECH_SUPPORT_CATEGORY = int(os.getenv("TECH_SUPPORT_CATEGORY"))
REPORT_CHANNEL_ID = int(os.getenv("REPORT_CHANNEL_ID"))
SUPPORT_CHANNEL_ID = int(os.getenv("SUPPORT_CHANNEL_ID"))

BLACKLIST_FILE = "blacklist.json"
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

def load_blacklist():
    try:
        with open(BLACKLIST_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"banned_players": []}

def save_blacklist(data):
    with open(BLACKLIST_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def add_to_blacklist(player_name, reason, moderator):
    blacklist = load_blacklist()
    ban_entry = {
        "player": player_name,
        "reason": reason,
        "moderator": moderator,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M")
    }
    blacklist["banned_players"].append(ban_entry)
    save_blacklist(blacklist)
    return ban_entry

class ReportModal(discord.ui.Modal, title='📢 Player Report'):
    player = discord.ui.TextInput(
        label='Player Name',
        placeholder='Enter nickname or tag (e.g.: User#1234)',
        style=discord.TextStyle.short,
        max_length=32,
        required=True
    )
    
    reason = discord.ui.TextInput(
        label='Report Reason',
        placeholder='Describe the issue in detail...',
        style=discord.TextStyle.paragraph,
        max_length=1024,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        channel = interaction.guild.get_channel(ADMIN_CHANNEL_ID)
        
        if not channel:
            return await interaction.response.send_message(
                '❌ Error: Report channel not found!',
                ephemeral=True
            )

        embed = discord.Embed(
            title='🚨 New Report',
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name='👤 Player', value=self.player.value, inline=False)
        embed.add_field(name='📝 Reason', value=self.reason.value, inline=False)
        embed.add_field(name='🛡️ Reporter', value=interaction.user.mention, inline=False)
        embed.set_footer(text=f'User ID: {interaction.user.id}')

        view = ReportActionView()
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            f'✅ Your report on **{self.player.value}** has been submitted!',
            ephemeral=True
        )

class ReportActionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label='Accept', style=discord.ButtonStyle.green, custom_id='report_accept')
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = interaction.message.embeds[0]
        player_name = embed.fields[0].value
        reason = embed.fields[1].value
        
        ban_entry = add_to_blacklist(
            player_name=player_name,
            reason=reason,
            moderator=interaction.user.name
        )
        
        await update_ban_list(interaction.guild)
        
        embed.color = discord.Color.green()
        embed.title = '✅ Report Accepted'
        self.disable_all_items()
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(
            f"Report accepted by {interaction.user.mention}. Player {player_name} added to blacklist.",
            ephemeral=True
        )
    
    @discord.ui.button(label='Reject', style=discord.ButtonStyle.red, custom_id='report_reject')
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = '❌ Report Rejected'
        self.disable_all_items()
        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(
            f"Report rejected by {interaction.user.mention}",
            ephemeral=True
        )

async def update_ban_list(guild):
    channel = guild.get_channel(BAN_LIST_CHANNEL_ID)
    if not channel:
        return
    
    async for message in channel.history(limit=100):
        await message.delete()
    
    blacklist = load_blacklist()
    if not blacklist["banned_players"]:
        embed = discord.Embed(
            title='🔴 Banned Players',
            description='The list is currently empty',
            color=discord.Color.red()
        )
        return await channel.send(embed=embed)
    
    embed = discord.Embed(
        title='🔴 Banned Players List',
        color=discord.Color.red()
    )
    
    for entry in blacklist["banned_players"]:
        embed.add_field(
            name=f"• {entry['player']} ({entry['date']})",
            value=f"**Reason:** {entry['reason']}\n**Moderator:** {entry['moderator']}",
            inline=False
        )
    
    await channel.send(embed=embed)

class SupportTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label='Create Ticket', style=discord.ButtonStyle.blurple, custom_id='create_ticket')
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        category = interaction.guild.get_channel(TECH_SUPPORT_CATEGORY)
        if not category:
            return await interaction.response.send_message(
                "❌ Ticket system not configured!",
                ephemeral=True
            )
        
        ticket_channel = await category.create_text_channel(
            name=f"ticket-{interaction.user.name}",
            topic=f"Ticket for {interaction.user.name}",
            reason=f"Ticket created by {interaction.user.name}"
        )
        
        await ticket_channel.set_permissions(
            interaction.user,
            read_messages=True,
            send_messages=True
        )
        
        embed = discord.Embed(
            title='🛠️ Support Ticket',
            description=f"Hello {interaction.user.mention}!\n\nPlease describe your issue and our team will assist you.",
            color=discord.Color.blue()
        )
        
        await ticket_channel.send(
            content=f"{interaction.user.mention} ticket created!",
            embed=embed
        )
        
        await interaction.response.send_message(
            f"✅ Ticket created: {ticket_channel.mention}",
            ephemeral=True
        )

@bot.event
async def on_ready():
    print(f'🔗 Bot {bot.user} is online!')
    
    bot.add_view(ReportActionView())
    bot.add_view(SupportTicketView())
    
    try:
        await bot.tree.sync()
        guild = discord.Object(id=GUILD_ID)
        await bot.tree.sync(guild=guild)
        print('🔄 Commands synced')
    except Exception as e:
        print(f'❌ Sync error: {e}')
    
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return
    
    report_channel = guild.get_channel(REPORT_CHANNEL_ID)
    if report_channel:
        embed = discord.Embed(
            title='📢 Report System',
            description='Use `/report` command to report a player',
            color=discord.Color.green()
        )
        await report_channel.purge(limit=10)
        await report_channel.send(embed=embed)
    
    support_channel = guild.get_channel(SUPPORT_CHANNEL_ID)
    if support_channel:
        embed = discord.Embed(
            title='🛠️ Support System',
            description='Click the button below to create a private ticket',
            color=discord.Color.blue()
        )
        view = SupportTicketView()
        await support_channel.purge(limit=10)
        await support_channel.send(embed=embed, view=view)
    
    await update_ban_list(guild)

@bot.tree.command(name="report", description="Report a player")
async def report_command(interaction: discord.Interaction):
    await interaction.response.send_modal(ReportModal())

@bot.tree.command(name="blacklist", description="View banned players")
async def blacklist_command(interaction: discord.Interaction):
    blacklist = load_blacklist()
    
    if not blacklist["banned_players"]:
        return await interaction.response.send_message(
            "The blacklist is empty",
            ephemeral=True
        )
    
    embed = discord.Embed(
        title='🔴 Banned Players',
        color=discord.Color.red()
    )
    
    for entry in blacklist["banned_players"]:
        embed.add_field(
            name=f"• {entry['player']} ({entry['date']})",
            value=f"**Reason:** {entry['reason']}\n**Moderator:** {entry['moderator']}",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

bot.run(TOKEN)