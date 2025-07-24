import discord
import os
from discord import app_commands
from discord.ext import commands

# Конфігурація
ADMIN_CHANNEL_ID = 1396137647243661492  # ID каналу для репортів
GUILD_ID = 1396069780766724186         # ID вашого сервера (для швидкої синхронізації)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# Модальне вікно для репорту
class ReportModal(discord.ui.Modal, title='📢 Репорт на гравця'):
    player = discord.ui.TextInput(
        label='Імʼя гравця',
        placeholder='Введіть нікнейм або тег (наприклад: User#1234)',
        style=discord.TextStyle.short,
        max_length=32,
        required=True
    )
    
    reason = discord.ui.TextInput(
        label='Причина скарги',
        placeholder='Детально опишіть проблему...',
        style=discord.TextStyle.paragraph,
        max_length=1024,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Створюємо канал для адмінів
        channel = interaction.guild.get_channel(ADMIN_CHANNEL_ID)
        
        if not channel:
            return await interaction.response.send_message(
                '❌ Помилка: канал для репортів не знайдено!',
                ephemeral=True
            )

        # Готуємо Embed
        embed = discord.Embed(
            title='🚨 Новий репорт',
            color=discord.Color.orange(),
            timestamp=discord.utils.utcnow()
        )
        embed.add_field(name='👤 Гравець', value=self.player.value, inline=False)
        embed.add_field(name='📝 Причина', value=self.reason.value, inline=False)
        embed.add_field(name='🛡️ Модератор', value=interaction.user.mention, inline=False)
        embed.set_footer(text=f'User ID: {interaction.user.id}')

        # Додаємо кнопки для обробки
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.green,
            label='Прийняти',
            custom_id='report_accept'
        ))
        view.add_item(discord.ui.Button(
            style=discord.ButtonStyle.red,
            label='Відхилити',
            custom_id='report_reject'
        ))

        # Відправляємо репорт
        await channel.send(embed=embed, view=view)
        await interaction.response.send_message(
            f'✅ Ваш репорт на **{self.player.value}** успішно відправлено!',
            ephemeral=True
        )

@bot.event
async def on_ready():
    print(f'🔗 Бот {bot.user} підключений до Discord!')
    
    # Синхронізація команд
    try:
        # Глобальна синхронізація (працює до 1 години)
        await bot.tree.sync()
        
        # Швидка синхронізація для конкретного сервера
        guild = discord.Object(id=GUILD_ID)
        await bot.tree.sync(guild=guild)
        
        print(f'🔄 Успішно синхронізовано {len(await bot.tree.fetch_commands())} команд')
    except Exception as e:
        print(f'❌ Помилка синхронізації: {e}')

# Слеш-команда
@bot.tree.command(
    name="report",
    description="Надіслати скаргу на гравця",
    guild=discord.Object(id=GUILD_ID)  # Додаємо конкретний сервер
)
async def report_command(interaction: discord.Interaction):
    await interaction.response.send_modal(ReportModal())

# Запуск бота
bot.run(os.getenv("TOKEN"))
