import discord
from discord.ext import commands
import json
import random
import os
import asyncio

bot = commands.Bot(command_prefix='/')
DATABASE_FILE = 'database.json'


# Check if the database file exists
def database_exists():
    return os.path.isfile(DATABASE_FILE)


# Load the JSON database
def load_database():
    if not database_exists():
        return {'players': {}}

    with open(DATABASE_FILE, 'r') as file:
        try:
            data = json.load(file)
        except json.JSONDecodeError:
            data = {'players': {}}
        return data


# Save the JSON database
def save_database(data):
    with open(DATABASE_FILE, 'w') as file:
        json.dump(data, file, indent=4)


def player_exists(player_id):
    database = load_database()
    players = database['players']
    return player_id in players


def create_player(player_id):
    player = {
        'id': player_id,
        'name': None,
        'level': 1,
        'experience': 0,
        'health': 100,
        'max_health': 100,
        'inventory': [],
        'currency': 0,
        'party': []
    }
    database = load_database()
    database['players'][player_id] = player
    save_database(database)


def get_player(player_id):
    database = load_database()
    players = database['players']
    return players.get(player_id, None)


def add_item(player_id, item):
    database = load_database()
    player = database['players'].get(player_id)
    if player:
        inventory = player.setdefault('inventory', [])  # Retrieve or initialize the inventory list
        inventory.append(item)  # Add the item to the player's inventory
        if item['type'] == 'currency':
            player['currency'] += item['value']  # Update the currency value
        save_database(database)


def remove_item(player_id, item):
    player = get_player(player_id)
    if player and 'inventory' in player:
        player['inventory'] = [
            inv_item for inv_item in player['inventory'] if inv_item != item
        ]
        save_database(load_database())


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    owner = await bot.application_info()
    await owner.owner.send(f'{bot.user.name} is now online.')


@bot.event
async def on_command_error(ctx, error):
    # Send a DM notification to the bot owner about the error
    owner = await bot.application_info()
    await owner.owner.send(f'An error occurred while executing the command: {str(error)}')


@bot.event
async def on_shutdown():
    # Send a DM notification to the bot owner when the Python script is shutting down
    owner = await bot.application_info()
    await owner.owner.send(f'The Python script is shutting down.')


@bot.event
async def on_error(event, *args, **kwargs):
    # Send a DM notification to the bot owner about the error in the Python script
    owner = await bot.application_info()
    await owner.owner.send(f'An error occurred in the Python script:\nEvent: {event}\nArgs: {args}\nKwargs: {kwargs}')


@bot.event
async def on_disconnect():
    # Send a DM notification to the bot owner when the bot disconnects from the server
    owner = await bot.application_info()
    await owner.owner.send(f'{bot.user.name} has disconnected from the server.')


@bot.command(name='create')
async def create(ctx):
    player_id = str(ctx.author.id)
    if not player_exists(player_id):
        create_player(player_id)
        await ctx.send(f'<@{player_id}>, your character has been created!')
    else:
        await ctx.send(f'<@{player_id}>, you already have a character!')


@bot.command(name='battle')
async def battle(ctx):
    player_id = str(ctx.author.id)
    player = get_player(player_id)
    if player:
        monsters = [
            {
                'name': 'Goblin',
                'level': 3,
                'health': 50,
                'damage': 8,
                'max_health': 50,
                'loot': [
                    {
                        'name': 'Gold',
                        'type': 'currency',
                        'value': 50
                    }
                ]
            },
            {
                'name': 'Orc',
                'level': 5,
                'health': 80,
                'damage': 12,
                'max_health': 80,
                'loot': [
                    {
                        'name': 'Gold',
                        'type': 'currency',
                        'value': 80
                    }
                ]
            }
        ]

        # Select a random monster from the list
        monster = random.choice(monsters)

        party_members = [player_id] + player.get('party', [])

        party_rewards = {member_id: {'damage': 0, 'rewards': []} for member_id in party_members}

        while player['health'] > 0 and monster['health'] > 0:
            monster_damage = random.randint(5, 12)

            for member_id in party_members:
                member = get_player(member_id)
                if member:
                    member_damage = random.randint(5, 15)
                    monster['health'] -= member_damage
                    party_rewards[member_id]['damage'] += member_damage

            player['health'] -= monster_damage

            player_health_percentage = player['health'] / player['max_health'] * 100
            monster_health_percentage = monster['health'] / monster['max_health'] * 100

            await ctx.send(f'{ctx.author.mention}\'s Health: {player_health_percentage:.2f}%')
            await asyncio.sleep(1)  # Delay for 1 second before sending the next message
            await ctx.send(f'{monster["name"]}\'s Health: {monster_health_percentage:.2f}%')
            await asyncio.sleep(1)  # Delay for 1 second before sending the next message

        if player['health'] <= 0:
            await ctx.send(f'<@{player_id}>, you were defeated by the {monster["name"]}!')
            for member_id in party_members:
                await ctx.send(f'<@{member_id}>, your party member {ctx.author.mention} was defeated in battle!')
        else:
            await ctx.send(f'<@{player_id}>, you defeated the {monster["name"]}!')

            total_damage = sum(party_rewards[member_id]['damage'] for member_id in party_members)
            total_rewards = []

            for member_id, rewards in party_rewards.items():
                member = get_player(member_id)
                if member:
                    member_damage = rewards['damage']
                    member_share = int(member_damage / total_damage * 100)
                    member_rewards = rewards['rewards']
                    for reward in monster['loot']:
                        reward_value = int(reward['value'] * member_share / 100)
                        if reward_value > 0:
                            reward_copy = reward.copy()
                            reward_copy['value'] = reward_value
                            member_rewards.append(reward_copy)
                            total_rewards.append(reward_copy)

                    member['inventory'] += member_rewards

            await ctx.send("Battle Results:")
            for member_id, rewards in party_rewards.items():
                member = get_player(member_id)
                if member:
                    member_rewards = rewards['rewards']
                    if member_rewards:
                        embed = discord.Embed(
                            title=f'Rewards for <@{member_id}>', color=discord.Color.green())
                        for reward in member_rewards:
                            reward_name = reward.get('name', 'Unnamed Reward')
                            reward_value = reward.get('value', 0)
                            embed.add_field(name=reward_name, value=f'Value: {reward_value}', inline=False)
                        await ctx.send(embed=embed)

            if total_rewards:
                await ctx.send("Total Rewards:")
                embed = discord.Embed(title='Total Rewards', color=discord.Color.green())
                for reward in total_rewards:
                    reward_name = reward.get('name', 'Unnamed Reward')
                    reward_value = reward.get('value', 0)
                    embed.add_field(name=reward_name, value=f'Value: {reward_value}', inline=False)
                await ctx.send(embed=embed)

            save_database(load_database())
    else:
        await ctx.send(f'<@{player_id}>, you need to create a character using the `create` command first!')

@bot.command(name='inventory')
async def inventory(ctx):
    player_id = str(ctx.author.id)
    if player_exists(player_id):
        player = get_player(player_id)
        if 'inventory' in player and player['inventory']:
            embed = discord.Embed(
                title='Inventory', color=discord.Color.blue())
            for item in player['inventory']:
                embed.add_field(name=item, value='-', inline=False)
            await ctx.send(embed=embed)
        else:
            await ctx.send(f'<@{player_id}>, your inventory is empty!')
    else:
        await ctx.send(f'<@{player_id}>, you need to create a character first!')


@bot.command(name='currency')
async def currency(ctx):
    player_id = str(ctx.author.id)
    if player_exists(player_id):
        player = get_player(player_id)
        currency = player.get('currency', 0)
        await ctx.send(f'<@{player_id}>, your current currency balance is {currency}.')
    else:
        await ctx.send(f'<@{player_id}>, you need to create a character first!')


@bot.command(name='use')
async def use(ctx, item_name):
    player_id = str(ctx.author.id)
    player = get_player(player_id)
    if player:
        if 'inventory' in player and player['inventory']:
            for item in player['inventory']:
                if item['name'] == item_name and item['type'] == 'healing':
                    player['health'] += item['value']
                    if player['health'] > player['max_health']:
                        player['health'] = player['max_health']
                    player['inventory'].remove(item)
                    save_database(load_database())
                    await ctx.send(f'<@{player_id}>, you used the {item_name} and restored {item["value"]} health!')
                    return
            await ctx.send(f'<@{player_id}>, you do not have the {item_name} in your inventory or it cannot be used for healing.')
        else:
            await ctx.send(f'<@{player_id}>, your inventory is empty!')
    else:
        await ctx.send(f'<@{player_id}>, you need to create a character first!')

@bot.command(name='delete')
async def delete(ctx):
    player_id = str(ctx.author.id)
    if player_exists(player_id):
        database = load_database()
        del database['players'][player_id]
        save_database(database)
        await ctx.send(f'<@{player_id}>, your character has been deleted!')
    else:
        await ctx.send(f'<@{player_id}>, you do not have a character!')

@bot.command(name='shop')
async def shop(ctx):
    player_id = ctx.author.id
    player = get_player(player_id)  # Assuming there's a function to get the player data
    
    if player:
        items = [
            {
                'name': 'Health Potion',
                'type': 'healing',
                'value': 20,
                'price': 50
            },
            {
                'name': 'Super Potion',
                'type': 'healing',
                'value': 50,
                'price': 100
            },
            {
                'name': 'Mega Potion',
                'type': 'healing',
                'value': 100,
                'price': 200
            }
        ]
        embed = discord.Embed(
            title='Shop', description='Available items for purchase:', color=discord.Color.gold())

        for item in items:
            item_name = item.get('name', 'Unnamed Item')
            item_type = item.get('type', 'Unknown Type')
            item_price = item.get('price', 0)
            embed.add_field(name=item_name, value=f'Type: {item_type}\nPrice: {item_price}', inline=False)

        await ctx.send(embed=embed)
        await ctx.send(f'<@{player_id}>, type the name of the item you want to buy.')

        def check(m):
            return m.author == ctx.author

        try:
            message = await bot.wait_for('message', check=check, timeout=30.0)
        except asyncio.TimeoutError:
            await ctx.send(f'<@{player_id}>, you took too long to respond. The shop session has ended.')
            return

        item_name = message.content.strip()

        for item in items:
            if item['name'].lower() == item_name.lower():
                item_price = item.get('price', 0)
                if player['currency'] >= item_price:
                    add_item(player_id, item)  # Assuming there's a function to add an item to the player's inventory
                    player['currency'] -= item_price
                    save_database(load_database())  # Assuming there's a function to save the player's data
                    await ctx.send(f'<@{player_id}>, you bought the {item_name} for {item_price} currency.')
                else:
                    await ctx.send(f'<@{player_id}>, you do not have enough currency to buy the {item_name}.')
                return

        await ctx.send(f'<@{player_id}>, the {item_name} is not available in the shop.')
    else:
        await ctx.send(f'<@{player_id}>, you need to create a character first!')

bot.run(os.environ['DISCORD_TOKEN'])
