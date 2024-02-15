# """
# OK SO TODO IS THIS A GOOD IDEA?
# IF NOT, JUST DON'T USE IT
# IT'S A MESS
# ANYWAYS LOOK AT THE FLASK SITE AND SEE IF YOU CAN IMPLEMENT IT
# THEN ADD IT TO THE COG IF POSSIBLE
#
#
#
# PUSH TO GIT LATER PLEASEEEEEEE!!!!!!!!
# pushed to git hopefully
# tis a mess lol
# """

# IMPORTANT SHIT
'''
onReady : "ready"
onMessage : "message"
onMessageEdit : "message_update"
onmessageDelete : "message_delete"
onChannelCreate : "channel_create"
oncChannelEdit : "channel_update"
onChannelDelete : "channel_delete"
onGroupChannelJoin : "group_channel_join"
onGroupChannelLeave : "group_channel_leave"
onUserStartsTyping : "channel_start_typing"
onUserStopsTyping : "channel_stop_typing"
onServerEdit : "server_update"
onServerDelete : "server_delete"
onServerMemberEdit : "server_member_update"
onMemberJoin : "member_join"
onMemberLeave : "member_leave"
onRoleEdit : "server_role_update"
onRoleDelete : "server_role_delete"
onUserEdit : "user_update"
'''

import random, pymongo, json, time, asyncio, datetime
import voltage, os
from voltage.ext import commands
from voltage.errors import CommandNotFound, NotBotOwner, NotEnoughArgs, NotEnoughPerms, NotFoundException, BotNotEnoughPerms, RoleNotFound, UserNotFound, MemberNotFound, ChannelNotFound
from host import alive
from time import time
from functools import wraps

from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi

with open("json/config.json", "r") as f:
  config = json.load(f)

DBclient = MongoClient(config['MONGOURI'], server_api=ServerApi('1'))

db = DBclient['beta']
userdb = db['users']
serverdb = db['servers']
settingsdb = db['settings']
cooldowns = db['cooldowns']

import time

def update_level(user:voltage.User):
  if userdb.find_one({'userid':user.id}):
    user_data = userdb.find_one({'userid':user.id})
    if 0 >= (5 * (user_data['levels']['level'] ^ 2) + (50 * user_data['levels']['level']) + 100 - user_data['levels']['xp']):
      userdb.update_one({'userid':user.id}, {'$inc':{'levels.level':1}})
      return True
    else:
      return False
  else:
    return add_user(user)


def check_xp(user: voltage.User):
  user_id = str(user.id)
  user_data = userdb.find_one({'userid': user_id})
  if user_data:
    return user_data['levels']['xp']
  else:
    return 0

def add_user(user: voltage.User, isbot:bool=False): # long ass fucking function to add users to the database if they dont exist yet. but it works..
  if userdb.find_one({"userid": user.id}):
    return "User already exists."
  id = 1
  for i in userdb.find({}):
    id += 1
  try:
    userdb.insert_one({
        "_id": id,
        "username": user.name,
        "userid": user.id,
        "levels": {
            "xp": 0,
            "level": 1
        },
        "economy": {
            "wallet": 0,
            "bank": 0,
            "data": {
                "inventory": {
                    "bank_loan": 1
                },
                "job": "unemployed"
            },
            "buffs": {
                "beginner_luck": 100
            },
            "debuffs": {},
            "achievements": {
                "early_user": True,
                "beta_tester": True
            }
        },
        "status": {
            "beta": False,
            "familyfriendly": False,
            "premium": False,
            "admin": False,
            "isBot": isbot,
            "banned": False
        }
    })
    return "Added"
  except Exception as e:
    return f"Sorry, An Error Occured!\n\n```\n{e}\n```"

async def update_stats(users, servers):
  if settingsdb.find_one(
    {
      "_id": 1
    }
  ):
    settingsdb.update_one(
      {
        "_id": 1,
        "setting": "stats"
      },
      {
        "$set": {
          "users": users,
          "servers": servers
        }
      }
    )
  else:
    settingsdb.insert_one(
      {
        "_id": 1,
        "setting": "stats",
        "users": users,
        "servers": servers
      }
    )
  print("Updated stats! Users: " + str(users) + " Servers: " + str(servers))

def pingDB(): # ping the database; never gonna use this, might need it, add it.
  try:
    DBclient.admin.command('ping')
    return "[+] Pinged your deployment. Successfully connected to MongoDB!"
  except Exception as e:
    return f"[-] ERROR! \n\n\n{e}"

def get_user(user: voltage.User):
  if user := userdb.find_one({"userid": user.id}):
    return user
  else:
    return "User not found."  
 
def give_xp(user: voltage.User):   
  userdb.update_one(
      {"userid":user.id},
      {
          "$inc": {
          "levels.xp": random.randint(1, 5)
          }
      }
  )

prefixes = ["m!"]
client = commands.CommandsClient(prefix=prefixes)

async def update():
  print("Started Update Loop")
  while True:
    for i in userdb.find():
      total = 0
      total += int(i["economy"]["wallet"]) 
      total += int(i["economy"]["bank"])
      userdb.update_many(
        {
          "_id": i["_id"]
        },
        {
          "$set": {
            "economy.total": total
          }
        }
      )
    await asyncio.sleep(120) # sleep for 2 minutes

async def add_cooldown(ctx, command_name:str, seconds:int):
  cooldowns[ctx.author.id][str(command_name)] = time() + seconds
  return True

async def check_cooldown(ctx, command_name:str, seconds:int):
  try:
    if (time() < cooldowns[ctx.author.id][command_name]):
      return True
    else:
      del cooldowns[ctx.author.id][command_name]
  except KeyError:
    await add_cooldown(ctx, command_name=command_name, seconds=seconds)
  return False

#cooldowns = {}
# THANK YOU VLF I LOVE YOU :kisses:
def limiter(cooldown: int, *, on_ratelimited = None, key = None):
  cooldowns = {}
  getter = key or (lambda ctx, *_1, **_2: ctx.author.id)
  def wrapper(callback):
    @wraps(callback)
    async def wrapped(ctx, *args, **kwargs):
      k = getter(ctx, *args, **kwargs)
      v = (time.time() - cooldowns.get(k, 0))
      if v < cooldown and 0 > v:
        if on_ratelimited:
          return await on_ratelimited(ctx, -v, *args, **kwargs)
        return
      cooldowns[k] = time.time() + cooldown
      return await callback(ctx, *args, **kwargs)
    return wrapped
  return wrapper 

async def status():
  print("Started Status Loop")
  while True:
    statuses = [
      f"Playing with {len(client.cache.servers)} servers and {len(client.members)} users!",
      f"Watching {len(client.members)} users!",
      f"My waifu is better than yours!!! | {len(client.cache.servers)} servers",
      f"Jan | {len(client.cache.servers)} servers",
      f"guys my father just came back with the milk O_O - delta2571 | {len(client.cache.servers)} servers",
      f"Revolt > shitcord | {len(client.cache.servers)} servers",
      f"Jans Onlyfans: onlyfans.com/linustechtips | {len(client.cache.servers)} servers",
      f"William Says HI! | {len(client.cache.servers)} servers",
    ]
    status = random.choice(statuses)
    await client.set_status(status, voltage.PresenceType.online)
    await asyncio.sleep(5)

@client.listen("ready")
async def ready():
  with open("json/data.json", "r") as f:
    data = json.load(f)
    data['uptime'] =  int(time.time())
  with open("json/data.json", "w") as r:
    json.dump(data, r, indent=2)
  print("Up and running") # Prints when the client is ready. You should know this
  await asyncio.gather(update_stats(users=len(client.users), servers=len(client.servers)), update(), status())

@client.command()
@limiter(5, on_ratelimited=lambda ctx, delay, *_1, **_2: ctx.send(f"You're on cooldown! Please wait `{round(delay, 2)}s`!"))
async def foo(ctx):
  await ctx.send(f"Not on cooldown, but now you are!\nCooldown is `5` seconds!")

@client.listen("member_join")
async def member_join(member:voltage.Member, server:voltage.Server):
  if member.bot:
    membertype = "Bot"
  else:
    membertype = "User"
  if server.id == config['SERVER_ID']:
    print(f"A {membertype} named {member.name} has joined the server!")
    if membertype == "User":
      await member.send(f"Hello {membertype} {member.mention}! Welcome to the server!\nIf you're here to report a bug, head over to <#01HPPPXPV451RWSPN7NRQRBDS5>\nIf you want to suggest a feature.. head over to <#01HPPPXW6T37Z0MHNNXRQ461TT>!")
    await member.add_roles(config['MEMBER_ROLE'])

async def levelstuff(message): # running this in the on_message event drops the speed down to your grandmothers crawl. keep this in a function pls
  if update_level(message.author):
    try:
      channel = client.get_channel(config['LEVEL_CHANNEL'])
      embed = voltage.SendableEmbed(
        title = f"{message.author.name} has leveled up!",
        description = f"{message.author.name} has leveled up to level **{get_user(message.author)['levels']['level']}**!",
        color = "#44ff44",
        icon_url = message.author.avatar.url or "https://ibb.co/mcTxwnf"
      )
      msg = await channel.send(embed=embed) # praise kink? its whatever
    except KeyError:
      print("keyerror :(") # this should never happen, if it does, tell William, if it doesnt, tell William anyways.
  if userdb.find_one(
    {"userid":message.author.id}
  ): #super fucking stupid but it makes pylance happy
    update_level(message.author)
    if random.randint(25, 100) <= 75: # 75% chance to get xp off a message, im too lazy to input my own rate limit fuck that
      give_xp(message.author)
    elif message.content.startswith("m!") and random.randint(1,10) == 1: # good boy points if you use commands and a 10% chance to receive xp (will have to replace this later when custom prefixing is implemented)
      give_xp(message.author)
  else: 
    print(add_user(message))

# this shit is so fucking weird but hey, it works
# Thank TheBobBobs, bro is a fucking goat for this.
@client.listen("message")
async def on_message(message):
  if message.author.bot:
    return
  asyncio.create_task(levelstuff(message)) # pièce de résistance
  await client.handle_commands(message) # so everything else doesnt trip over its clumsy ass selves.

@client.listen("server_added")
async def server_added(server):
  channel = client.cache.get_channel("01FZBBHNBWMH46TWN0HVJT1W5F")
  embed = voltage.SendableEmbed(
    title="New Server alert!",
    description=f"## Just Joined a new server!\nNow at **{len(client.servers)}** servers!",
    color="#516BF2",
  )
  await channel.send(content="[]()", embed=embed)

@client.command(name="add", description="Adds you to the database!") # whos really using this command? Like really, move this to owner.py when pls..
async def add(ctx):
  result = add_user(ctx.author)
  await ctx.reply(f"Results are in! {result}")

errormsg = [
  "Error! Error!",
  "LOOK OUT!!! ERROR!!",
  "Whoops!",
  "Oopsie!",
  "Something went wrong!",
  "Something happened..",
  "What happened? I know!",
  "404!",
  "ERROR.. ERROR..",
  "Error Occured!",
  "An Error Occured!"
]

# error handling shit
@client.error("message")
async def on_message_error(error: Exception, message):
  if isinstance(error, CommandNotFound):
    embed = voltage.SendableEmbed(
      title=random.choice(errormsg),
      description="That command doesnt exist!",
      colour="#516BF2"
    )
    return await message.reply(message.author.mention, embed=embed)
  elif isinstance(error, NotEnoughArgs):
    embed = voltage.SendableEmbed(
      title=random.choice(errormsg),
      description="YOU'RE MISSING ARGS!",
      colour="#516BF2"
    )
    return await message.reply(message.author.mention, embed=embed)
  elif isinstance(error, NotFoundException):
    embed = voltage.SendableEmbed(
      title=random.choice(errormsg),
      description=error,
      colour="#516BF2"
    )
    return await message.reply(message.author.mention, embed=embed)
  elif isinstance(error, NotEnoughPerms):
    embed = voltage.SendableEmbed(
      title=random.choice(errormsg),
      description=error,
      colour="#516BF2"
    )
    return await message.reply(message.author.mention, embed=embed)
  elif isinstance(error, NotBotOwner):
    embed = voltage.SendableEmbed(
      title=random.choice(errormsg),
      description="You dont own me! You cant use my owner only commands!",
      colour="#516BF2"
    )
    return await message.reply(message.author.mention, embed=embed)


# Cog loading schenanigans
try:
  client.add_extension("cogs.owner")
  print("Loaded Owner Cog!")
except Exception as e:
  print(e)
try:
  client.add_extension("cogs.fun")
  print("Loaded Fun Cog!")
except Exception as e:
  print(e)
try:
  client.add_extension("cogs.utility")
  print("Loaded Utility Cog!")
except Exception as e:
  print(e)
try:
  client.add_extension("cogs.giveaway")
  print("Loaded Giveaway Cog!")
except Exception as e:
  print(e)
try:
  client.add_extension("cogs.moderation")
  print("Loaded Moderation Cog!")
except Exception as e:
  print(e)
try:
  client.add_extension("cogs.economy")
  print("Loaded Economy Cog!")
except Exception as e:
  print(e)

alive() #yeah blah blah stolen from old Mecha but hey, it works so why not copy and paste it, we're developers.
client.run(config['TOKEN']) # Replace with your token in config, config.json to be exact, for everyone else, you know what this does stop fucking stalling pls :).