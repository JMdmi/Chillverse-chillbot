from dataclasses import replace
import datetime, asyncio
from collections import deque
from tempfile import TemporaryFile
import json, asyncpg
import gtts
import ast
import os
import discord #importamos para conectarnos con el bot
from discord.ext import commands #importamos los comandos
from discord.ext.commands import has_permissions, MissingPermissions
from gtts import gTTS

invite_link = "https://discord.com/api/oauth2/authorize?client_id=1002579077879824384&permissions=8&scope=bot"
bot_prefix = ";"
bot_desc = "Siempre chill"


db_uri = os.environ["DB_URI"]

table_name = "guilds"
config_options = ["whitelist", "blacklist", "blacklist_role", "whitelist_role","lang","tdl","tts_channel"]


intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=bot_prefix, intents=intents, description=bot_desc)
bot.remove_command("help")

#FUNCIONES SOBRE BASE DE DATOS
async def get_db_con():
    db = await asyncpg.connect(db_uri)
    return db
async def update_config(guild, column, value):
    db = await get_db_con()
    await db.execute(f'UPDATE guilds SET {column} = $2 WHERE id = $1', guild.id, value)
    await db.close()
async def get_dbvalue(guild, value):
    db = await get_db_con()
    val = None
    for option in config_options:
        if value == option:
            val = await db.fetchval(f'SELECT {value} FROM guilds WHERE id = {guild}')
    await db.close()
    return val
async def get_conf(guild, value):
    return await get_dbvalue(guild, value)

#SECCION DE FUNCIONES QUE AUN NO SE QUE HACEN(COPIA Y PEGA NO MAS)
def insert_returns(body):
    # insert return stmt if the last expression is a expression statement
    if isinstance(body[-1], ast.Expr):
        body[-1] = ast.Return(body[-1].value)
        ast.fix_missing_locations(body[-1])

    # for if statements, we insert returns into the body and the or else
    if isinstance(body[-1], ast.If):
        insert_returns(body[-1].body)
        insert_returns(body[-1].orelse)

    # for with blocks, again we insert returns into the body
    if isinstance(body[-1], ast.With):
        insert_returns(body[-1].body)
async def status_task():
    while True:
        game = discord.Game(f"In {len(bot.guilds)} servers.")
        await bot.change_presence(status=discord.Status.online, activity=game)
        await asyncio.sleep(30)
@bot.command()
@commands.is_owner()
async def eval_fn(ctx, *, cmd):
    fn_name = "_eval_expr"

    cmd = cmd.strip("` ")

    # add a layer of indentation
    cmd = "\n".join(f"    {i}" for i in cmd.splitlines())

    # wrap in async def body
    body = f"async def {fn_name}():\n{cmd}"

    parsed = ast.parse(body)
    body = parsed.body[0].body

    insert_returns(body)

    env = {
        'bot': ctx.bot,
        'discord': discord,
        'commands': commands,
        'ctx': ctx,
        '__import__': __import__
    }
    exec(compile(parsed, filename="<ast>", mode="exec"), env)

    result = (await eval(f"{fn_name}()", env))
    await ctx.send(result)

#SECCION DE COMANDOS DE BOT

#Comando para probar la respuesta del bot
@bot.command()
async def ping(ctx):
    await ctx.channel.send("pong")
#Comando help para proporcionar info de ayuda sobre el bot
@bot.command()
async def help(ctx):
    des = '''

    Comandos de Chillbot

    > {0}ping: El bot te responde pong

    > {0}say <message>: Habla (con TTS) en el chat de voz en el que estas.(metodo abreviado: ñ). Tambien puedes hacer que el tts hable con un idioma en particular uniendo la ñ con un sufijo de idioma, por ejemplo: ñen Hello there!
    
    > {0}join: Se une al chat de voz en el que estas.

    > {0}leave: Deja de hablar y se va del canal de voz

    > {0}stop: Hace lo mismo que {0}leave

    > {0}lang <language>: puedes cambiar el lenguaje de la voz tts(para saber cual es el lenguaje actual dejar el comando vacío)

    > {0}langs: te permite cosultar todos los idiomas disponible por el tts

    > {0}help: te permite ver este texto.

    > {0}blacklist <role>(aun no funciona): permite seleccionar un rol para una blacklist y asi evitar que ciertas personas usen el tts. Para desactivar este metodo es {0}blacklist False.
    
    > Comandos informales: tengo comandos informales y secretos que tendras que descubrir.
    '''.format(bot.command_prefix)
    embed = discord.Embed(title="Una taza de cafe? Soy Chillbot",url="https://cdn.discordapp.com/attachments/983683993436319774/1002579883802755092/unknown.png",description= des,
    timestamp=datetime.datetime.utcnow(),
    color=discord.Color.blue())
    embed.set_footer(text="solicitado por: {}".format(ctx.author.name))
    embed.set_author(name="JMdmi",icon_url="https://cdn.discordapp.com/attachments/983683993436319774/1003672968741785700/avatar_2.png")
    await ctx.channel.send(embed=embed)

#Agrega o quita de la lista negra para el uso de TTS con este bot
#role: se debe colocar el rol a poner en la blacklist
#si se pone el comando con el parametro false entonces se desactiva la blacklist
@bot.command()
@has_permissions(administrator=True)
async def blacklist(ctx, role):
    guild = ctx.message.guild
    if role == "false" or role == "False":
        await update_config(guild, "blacklist", "False")
        await ctx.message.channel.send("La blacklist esta desactivada")
    else:
        await update_config(guild, "blacklist", True)
        await update_config(guild, "blacklist_role", role)
#Cambia el idioma o muestra el idioma configurado
@bot.command()
@has_permissions(administrator=True)
async def lang(ctx):
    guild = ctx.message.guild
    tts_lang = await get_conf(guild,"lang")
    if ctx.message.content[6:]=="":
        await ctx.channel.send("El idioma de la voz es {}".format(tts_lang))
    else:
        if ctx.message.content[6:] in gtts.tts.tts_langs().keys():
            tts_lang=ctx.message.content[6:]
            await update_config(guild,"lang",tts_lang)
            await ctx.channel.send("El idioma ha sido cambiado a {}".format(gtts.tts.tts_langs()[tts_lang]))
        else:
            await ctx.channel.send("Lo siento, no pude cambiar el idioma. Consulte el menu de opciones con {}langs".format(bot_prefix))
@bot.command()
async def langs(ctx):
    langs_text=""
    for key in gtts.tts.tts_langs().keys():
        langs_text=langs_text+"-"+key+" : "+gtts.tts.tts_langs()[key]+"\n"
    await ctx.channel.send("Aqui una lista de opciones de idioma\n"+langs_text)
#Comando con privilegios de owner del bot

#Agrega todos los servers a la base de datos, solo para uso del propietario
@bot.command()
@commands.is_owner()
async def make_databases(ctx):
    guild_list = bot.fetch_guilds()
    db = await get_db_con()
    print("1")
    await db.execute('''
            CREATE TABLE IF NOT EXISTS guilds(
                id bigint PRIMARY KEY,
                whitelist_role text,
                blacklist_role text,
                whitelist bool,
                blacklist bool,
                lang text,
                tld text,
                tts_channel bigint
            )
        ''')
    print("2")
    async for guild in guild_list:
        await db.execute('''
                INSERT INTO guilds(id, whitelist,blacklist,blacklist_role,whitelist_role,lang,tld,tts_channel) VALUES($1, $2, $3, $4, $5, $6, $7, &8)
            ''', guild.id, False, False, 'none set', 'none set','none set','none set',1003775002656653482)
    print("3")
    db.close()

#Muestra el link de invitacion del link, por el momento restringido al propietario
@bot.command()
@commands.is_owner()
async def invite(ctx):
    msg = await ctx.send(f"Mi link de invitacion es {invite_link} ")
    await asyncio.sleep(3)
    await msg.delete()
#Comando para agregar al bot al canal de voz
@bot.command()
async def join(ctx):
    try:
        channel = ctx.message.author.voice.channel
        await channel.connect()
        return
    except(TypeError, AttributeError):
        await ctx.send("Necesito que estes en un canal de voz para unirme...")
        return
#Comando para dejar el canal de voz
@bot.command()
async def leave(ctx):
    try:
        await ctx.voice_client.disconnect(force=True)
        return
    except(TypeError, AttributeError):
        await ctx.send("Necesito estar en un canal de voz salir de el")
        return
#Lo mismo que leave pero con otro nombre
@bot.command()
async def stop(ctx):  # Solo es un alias de leave
    await leave(ctx)
@bot.command()
async def say(ctx):
    can_speak = True
    try:
        blacklist_status = await get_conf(ctx.message.guild, 'blacklist')
        if blacklist_status:
            blacklist_role = await get_conf(ctx.message.guild, 'blacklist_role')
            for role in ctx.message.author.roles:
                if role.name == blacklist_role:
                    can_speak = False
        tts_lang = await get_conf(ctx.message.guild, 'lang')
    except:
        tts_lang = 'es'
    if can_speak == False:
        return
    message = ctx.message.content[5:]
    #usernick = ctx.message.author.display_name
    #message = usernick + " dice " + message
    tts_channel = await get_conf(ctx.message.guild,"tts_channel")
    if ctx.channel.id == tts_channel:
        await tts_speech(ctx.message,message)
    else:
        msg = await ctx.channel.send("Por favor, solo envieme ese comando en el canal de "+str(bot.get_channel(tts_channel)))
        await asyncio.sleep(3)
        await msg.delete()
        await ctx.message.delete()
    
    
    
async def tts_speech(message,text="test",tts_lang=None,tld=None):
    if tts_lang == None:
        tts_lang = await get_conf(message.guild,"lang")
    message_queue = deque([])
    if "@" in text:
        text = "Lo siento, no voy a decir eso"
    if "chill" == text:
        text = "No digas chill, que te baneo"
    try:
        vc = message.guild.voice_client
        if not vc.is_playing():
            tts = gTTS(text,lang=tts_lang)
            f = TemporaryFile()
            tts.write_to_fp(f)
            f.seek(0)
            vc.play(discord.FFmpegPCMAudio(f, pipe=True))
        else:
            message_queue.append(text)
            while vc.is_playing():
                await asyncio.sleep(0.1)
            tts = gTTS(message_queue.popleft(),lang=tts_lang)
            f = TemporaryFile()
            tts.write_to_fp(f)
            f.seek(0)
            vc.play(discord.FFmpegPCMAudio(f, pipe=True))
    except(TypeError, AttributeError):
        try:
            tts = gTTS(text,lang=tts_lang)
            f = TemporaryFile()
            tts.write_to_fp(f)
            f.seek(0)
            channel = message.author.voice.channel
            vc = await channel.connect()
            vc.play(discord.FFmpegPCMAudio(f, pipe=True))
        except(AttributeError, TypeError):
            await message.channel.send("Primero debes estar en un canal de voz")
        return
    f.close()

@bot.command()
@commands.is_owner()
async def die(ctx):
    game = discord.Game("")
    await bot.change_presence(status=discord.Status.offline, activity=game)
    await ctx.channel.send("Hasta nunca, mundo cruel")
    bot.active = False
    await ctx.bot.logout()

@bot.command()
@has_permissions(administrator=True)
async def getchannel(ctx,channel):
    await ctx.channel.send("Su canal es: "+str(bot.get_channel(int(channel[2:-1]))))
@bot.command()
@has_permissions(administrator=True)
async def set_tts_channel(ctx,channel):
    await update_config(ctx.message.guild,"tts_channel",int(channel[2:-1]))
    await ctx.channel.send("Canal "+str(bot.get_channel(int(channel[2:-1])))+" agregado para el tts.")
#SECCION DE EVENTOS

#Cada que entra a un server de discord
@bot.event
async def on_guild_join(guild):
    db = await get_db_con()
    await db.execute('''
                    INSERT INTO guilds(id, whitelist,blacklist,blacklist_role,whitelist_role) VALUES($1, $2, $3,$4,$5,$6)
                ''', guild.id, False, False, 'none set', 'none set','es')

#Cada que se activa el bot
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="cosas chill"))
    print('El bot esta listo')
    #loop para actualizar los canales en los que se tiene el bot
    #bot.loop.create_task(status_task())

#Cada que llega un mensaje
@bot.event
async def on_message(message):
    await bot.process_commands(message)
    if message.author.bot:
        return
    print(str(message.channel)+": "+message.content)
    private=str(message.channel.type)=="private"
    channel = message.channel
    calltext='<@'+str(bot.user.id)+'>'
    
    #Si el mensaje es un DM, a partir de aca ignora el mensaje
    if private:
        return
    #Peticiones informales
    if message.content.startswith(calltext):
        request=message.content.replace(calltext,"")
        #Peticiones publicas
        if request=="":
            await channel.send("Aqui estoy. ¿Necesita algo?")
        if request in [" dime las reglas"," decime las reglas"," reglas"]:
            des='''1️⃣Trata a todo el mundo con respeto. No se tolerará ningún tipo de acoso, caza de brujas, sexismo, racismo o discurso de odio. sino serás baneado temporalmente y estarás en el CANAL de #『🚫』baneados⚖ hasta que cumplas tu sanción y si vuelves hacer lo mismo serás expulsado para siempre.

2️⃣ No se permite el spam ni la autopromoción (invitaciones al servidor, anuncios, etc.) sin permiso de un miembro del personal. Esto también incluye mandar MD a otros miembros. Para eso hicimos un canal de spam en #『🆙』spam

3️⃣ No se permite contenido NSFW ni obsceno. Esto incluye texto ( EN CASO DE TEXTO SOLO EN EL CANAL DE#『🎴』sala-de-rol ) , imágenes o enlaces que presenten desnudos, sexo, violencia u otro tipo de contenido gráfico que pueda herir la sensibilidad del espectador.

4️⃣ Si ves algo que va en contra de las normas o que no te haga sentir seguro, informa al personal. Enviando un ticket para cualquier ayuda o consulta en el canal de #『📩』crear-ticket¡Queremos que este servidor sea un lugar acogedor!*
            '''
            embed = discord.Embed(title="Reglas del server",description=des,timestamp=datetime.datetime.utcnow())
            embed.set_image(url="https://cdn.discordapp.com/attachments/983683993436319774/985197047932137502/Sprite-judge.png")
            await channel.send(embed=embed)

        #Peticiones con requisitos de administrador
        if message.author.guild_permissions.administrator:
            if request.startswith(" quiero que veas"):
                await channel.send("¡A la orden!")
                await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name=request.replace(" quiero que veas ","")))
            if request.startswith(" quiero que juegues"):
                await channel.send("¡A la orden!")
                await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.playing, name=request.replace(" quiero que juegues ","")))
        else:
            await message.delete()
            msg = await channel.send("Lo siento. Necesita ser un administrador para pedirme eso.")
            await asyncio.sleep(3)
            await msg.delete()
    if message.content.lower().startswith('ñ'):
        tts_channel = await get_conf(message.guild.id,"tts_channel")
        print(message.guild.id,"   ",tts_channel)
        if channel.id == tts_channel:
            if message.content.lower().startswith('ñ '):
                await tts_speech(message,message.content[2:])
            else:
                if message.content.lower().split()[0][1:] in gtts.tts.tts_langs().keys():
                    await tts_speech(message,message.content[4:],message.content.lower().split()[0][1:])
        else:
            msg = await channel.send("Por favor, solo envieme ese comando en el canal de "+str(bot.get_channel(tts_channel)))
            await asyncio.sleep(3)
            await msg.delete()
            await message.delete()
    #Momento meme
    if message.content == 'chill':
        await message.delete()
        msg = await channel.send("Decir chill es motivo de ban, basta.")
        await asyncio.sleep(3)
        await msg.delete()
#Actualizacion cada que alguien entra o sale
@bot.event
async def on_voice_state_update(member, before, after):
    voice_state = member.guild.voice_client
    if voice_state is None:
        # Exiting if the bot it's not connected to a voice channel
        return 

    if len(voice_state.channel.members) == 1:
        await voice_state.disconnect()

bot.run(os.environ["DISCORD_TOKEN"])
