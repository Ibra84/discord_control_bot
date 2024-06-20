import json
import os
import sqlite3
import string
import discord
from discord.ext import commands

# Создание объекта бота с префиксом команд и включением всех интентов
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())

@bot.event
async def on_ready():
    print('Человечище на связи!')

    global base, cur
    base = sqlite3.connect('Человечище.db')
    cur = base.cursor()
    if base:
        print('Подключение к базе данных... ОК')
    cur.execute(f'CREATE TABLE IF NOT EXISTS warnings (guild_id INT, user_id INT, count INT)')
    base.commit()

    global banned_words
    with open('cenz.json', 'r', encoding='utf-8') as f:
        banned_words = set(json.load(f))
    print('Запрещенные слова загружены.')

@bot.event
async def on_member_join(member):
    await member.send('Привет, я бот Человечище, просмотр команд - !инфо')
    for ch in bot.get_guild(member.guild.id).channels:
        if ch.name == 'основной':
            await ch.send(f'{member}, круто что ты с нами, в лс прислал инфо')

@bot.event
async def on_member_remove(member):
    for ch in bot.get_guild(member.guild.id).channels:
        if ch.name == 'основной':
            await ch.send(f"{member}, нам будет тебя не хватать")

@bot.command()
async def test(ctx):
    await ctx.send('Грязно выругался...')

@bot.command()
async def инфо(ctx, arg=None):
    author = ctx.message.author
    if arg is None:
        await ctx.send(f"{author.mention} Введите:\n!инфо общая\n!инфо команды")
    elif arg == 'общая':
        await ctx.send(f"{author.mention} Я Человечище, слежу за порядком в чате. Третье предупреждение за мат - БАН.")
    elif arg == 'команды':
        await ctx.send(f"{author.mention} !test - Проверить онлайн бота.\n!статус - Мои предупреждения.")
    else:
        await ctx.send(f"{author.mention} Такой команды нет...")

@bot.command()
async def статус(ctx):
    warning = cur.execute(f'SELECT * FROM warnings WHERE guild_id = ? AND user_id = ?', (ctx.message.guild.id, ctx.message.author.id)).fetchone()
    if warning is None:
        await ctx.send(f'{ctx.message.author.mention}, у вас нет предупреждений')
    else:
        await ctx.send(f'{ctx.message.author.mention}, у вас {warning[2]} предупреждений!!!')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Проверяем, является ли пользователь создателем сервера
    is_owner = message.guild.owner_id == message.author.id

    message_words = {word.lower().translate(str.maketrans('', '', string.punctuation)) for word in message.content.split()}
    if message_words.intersection(banned_words):
        try:
            await message.delete()
        except discord.Forbidden:
            await message.channel.send(f"{message.author.mention}, у меня нет прав удалять сообщения.")

        await message.channel.send(f"{message.author.mention}, yyy кого по губам отшлёпать??")

        warning = cur.execute(f'SELECT * FROM warnings WHERE guild_id = ? AND user_id = ?', (message.guild.id, message.author.id)).fetchone()
        if warning is None:
            cur.execute(f'INSERT INTO warnings (guild_id, user_id, count) VALUES (?, ?, ?)', (message.guild.id, message.author.id, 1))
            base.commit()
            await message.channel.send(f"{message.author.mention}, первое предупреждение, на 3-е БАН")
        elif warning[2] == 1:
            cur.execute(f'UPDATE warnings SET count = ? WHERE guild_id = ? AND user_id = ?', (2, message.guild.id, message.author.id))
            base.commit()
            await message.channel.send(f"{message.author.mention}, второе предупреждение, на 3-е БАН")
        elif warning[2] == 2:
            if not is_owner:  # Если пользователь не является владельцем сервера
                cur.execute(f'UPDATE warnings SET count = ? WHERE guild_id = ? AND user_id = ?', (3, message.guild.id, message.author.id))
                base.commit()
                await message.channel.send(f"{message.author.mention}, забанен за мат в чате!")
                try:
                    await message.author.ban(reason='Нецензурные выражения')
                except discord.Forbidden:
                    await message.channel.send(f"{message.author.mention}, у меня нет прав банить пользователей.")
            else:
                await message.channel.send(f"{message.author.mention},Я не могу вас забанить, хозяин!")

    await bot.process_commands(message)

bot.run(os.getenv('TOKEN'))
