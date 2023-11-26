import discord
from discord.ext import commands
import random
import json
import asyncio
from flask import Flask, render_template, request, jsonify


intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# Cargar o crear el archivo de datos con niveles, experiencia y monedas
def cargar_datos():
    try:
        with open("datos.json", "r") as archivo:
            datos = json.load(archivo)
    except FileNotFoundError:
        datos = {}
    except json.JSONDecodeError:
        datos = {}
    return datos

def guardar_datos(datos):
    try:
        with open("datos.json", "w") as archivo:
            json.dump(datos, archivo)
    except PermissionError:
        print("No se tienen los permisos adecuados para guardar los datos en el archivo.")

# Diccionario para almacenar la cantidad de mensajes por canal
canales_mensajes = {}

# Diccionarios para el seguimiento de acciones de los usuarios
usuarios_everyone = {}
usuarios_canales = {}

# Evento cuando se recibe un mensaje
@bot.event
async def on_message(message):
    # Verificación de spam de @everyone
    if "@everyone" in message.content:
        autor_id = str(message.author.id)

        if autor_id in usuarios_everyone:
            usuarios_everyone[autor_id] += 1
            if usuarios_everyone[autor_id] > 5:
                # Verificar si el usuario tiene un rango suficiente para evitar la expulsión
                if not tiene_permisos_suficientes(message.author):
                    await message.author.send("Has enviado @everyone demasiadas veces. Serás expulsado en breve.")
                    await expulsar_si_es_necesario(message.author)

        else:
            usuarios_everyone[autor_id] = 1

    # Verificación de canales repetidos
    canal_id = message.channel.id
    autor_id = str(message.author.id)

    if autor_id in usuarios_canales:
        if canal_id in usuarios_canales[autor_id]:
            usuarios_canales[autor_id][canal_id] += 1
            if usuarios_canales[autor_id][canal_id] == 3:
                await message.author.send("Has creado demasiados canales. Deja de hacerlo o serás expulsado.")
            elif usuarios_canales[autor_id][canal_id] == 5:
                await message.author.send("Te lo advertí. Has sido expulsado por crear demasiados canales.")
                await expulsar_si_es_necesario(message.author)
        else:
            usuarios_canales[autor_id][canal_id] = 1
    else:
        usuarios_canales[autor_id] = {canal_id: 1}

    await bot.process_commands(message)

# Función para verificar si un usuario tiene permisos suficientes
def tiene_permisos_suficientes(usuario):
    # Puedes personalizar esta función según tus criterios
    return usuario.guild_permissions.administrator

# Función para expulsar a un usuario si es necesario
async def expulsar_si_es_necesario(usuario):
    if not tiene_permisos_suficientes(usuario):
        await usuario.guild.kick(usuario, reason="Expulsado por acciones indebidas.")
        await usuario.send("Has sido expulsado del servidor por acciones indebidas.")


# Evento de inicio del bot
@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name='!ayuda'))
    print(f"Bot conectado como {bot.user.name}")

# Comando: Saludar
@bot.command()
async def saludar(ctx):
    await ctx.send("¡Hola! ¡Estoy aquí para ayudar!")

# Comando: Expulsar a un miembro
@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    await member.kick(reason=reason)
    await ctx.send(f"{member.mention} ha sido expulsado.")

# Comando: Banear a un miembro
@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    await member.ban(reason=reason)
    await ctx.send(f"{member.mention} ha sido baneado.")

# Comando: Borrar mensajes
@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount=5):
    await ctx.channel.purge(limit=amount+1)
    confirmation_message = await ctx.send(f"Se han borrado {amount} mensajes.")
    await asyncio.sleep(10)
    await confirmation_message.delete()
# Minijuego: Adivina el número
@bot.command()
async def adivina(ctx):
    numero_secreto = random.randint(1, 100)
    intentos = 0

    def check(msg):
        return msg.author == ctx.author and msg.content.isdigit()

    await ctx.send("¡Adivina un número entre 1 y 100!")

    while True:
        try:
            intentos += 1
            mensaje = await bot.wait_for("message", check=check, timeout=10.0)
            guess = int(mensaje.content)
            if guess == numero_secreto:
                await ctx.send(f"¡Correcto! Adivinaste el número en {intentos} intentos.")
                break
            elif guess < numero_secreto:
                await ctx.send("Intenta con un número más grande.")
            else:
                await ctx.send("Intenta con un número más pequeño.")
        except asyncio.TimeoutError:
            await ctx.send("Se acabó el tiempo. Inténtalo de nuevo más tarde.")
            break

# Minijuego: Piedra, Papel o Tijera
@bot.command()
async def ppt(ctx, choice: str):
    choices = ["piedra", "papel", "tijera"]
    choice = choice.lower()
    
    if choice not in choices:
        await ctx.send("Opción inválida. Las opciones son: piedra, papel o tijera.")
        return
    
    bot_choice = random.choice(choices)
    
    if choice == bot_choice:
        await ctx.send(f"Empate. Ambos eligieron {choice}.")
    elif ((choice == "piedra" and bot_choice == "tijera") or
          (choice == "papel" and bot_choice == "piedra") or
          (choice == "tijera" and bot_choice == "papel")):
        ganancia = 100

        await ctx.send(f"Ganaste. Elegiste {choice} y yo elegí {bot_choice}. Ganaste {ganancia} coinson.")
        agregar_monedas(ctx.author, ganancia)

    else:
        await ctx.send(f"Perdiste. Elegiste {choice} y yo elegí {bot_choice}. ")
    

# Comando: Mostrar información del servidor
@bot.command()
async def info(ctx):
    server = ctx.guild
    embed = discord.Embed(title=f"Información del servidor {server.name}", color=discord.Color.blue())
    embed.add_field(name="Dueño", value=server.owner, inline=False)
    embed.add_field(name="Miembros", value=server.member_count, inline=False)
    embed.add_field(name="Región", value=server.region, inline=False)
    embed.add_field(name="Creado el", value=server.created_at.strftime("%d/%m/%Y %H:%M:%S"), inline=False)
    await ctx.send(embed=embed)

# Utilidad: Trabajo y monedas
@bot.command()
async def trabajo(ctx):
    trabajos = [
        {"nombre": "informático", "monedas": random.randint(50, 100)},
        {"nombre": "diseñador", "monedas": random.randint(50, 100)},
        {"nombre": "músico", "monedas": random.randint(50, 100)},
        {"nombre": "chef", "monedas": random.randint(50, 100)},
        {"nombre": "escritor", "monedas": random.randint(50, 100)},
        {"nombre": "fotógrafo", "monedas": random.randint(50, 100)},
        {"nombre": "actor/actriz", "monedas": random.randint(50, 100)}
    ]
    
    trabajo_actual = random.choice(trabajos)
    await ctx.send(f"Has trabajado de {trabajo_actual['nombre']} y has obtenido {trabajo_actual['monedas']} coinson.")

# Sistema de cartera
@bot.command()
async def coinson(ctx):
    datos = cargar_datos()
    usuario_id = str(ctx.author.id)

    if usuario_id in datos:
        monedas_actuales = datos[usuario_id]["monedas"]
        await ctx.send(f"Tienes {monedas_actuales} coinson.")
    else:
        await ctx.send("Aún no tienes coinson. ¡Comienza a jugar para ganar monedas!")

# Sistema de XP

@bot.command()
async def xp(ctx):
    datos = cargar_datos()
    usuario_id = str(ctx.author.id)

    if usuario_id in datos:
        experiencia_actual = datos[usuario_id]["experiencia"]
        await ctx.send(f"Tienes {experiencia_actual} puntos de xp.")
    else:
        await ctx.send("Aún no tienes experiencia. ¡Sigue participando para ganar puntos de xp!")

# Sistema de niveles y experiencia
@bot.event
async def on_message(message):
    if not message.author.bot:
        datos = cargar_datos()
        usuario_id = str(message.author.id)

        if usuario_id not in datos:
            datos[usuario_id] = {"experiencia": 0, "nivel": 1, "monedas": 100}
        
        experiencia_actual = datos[usuario_id]["experiencia"]
        nivel_actual = datos[usuario_id]["nivel"]
        monedas_actuales = datos[usuario_id]["monedas"]
        experiencia_ganada = random.randint(15, 25)
        nueva_experiencia = experiencia_actual + experiencia_ganada

        # Subir de nivel si se alcanza la experiencia necesaria
        if nueva_experiencia >= nivel_actual * 100:
            datos[usuario_id]["nivel"] += 1
            nueva_experiencia -= nivel_actual * 100
            await message.channel.send(f"{message.author.mention} ¡Has subido al nivel {datos[usuario_id]['nivel']}!")

        datos[usuario_id]["experiencia"] = nueva_experiencia
        guardar_datos(datos)

    await bot.process_commands(message)

# Comando: Mostrar lista de niveles y experiencia
@bot.command()
async def niveles(ctx):
    datos = cargar_datos()

    def obtener_nivel_usuario(usuario_id):
        if usuario_id in datos:
            return datos[usuario_id]["nivel"]
        return 1

    def obtener_experiencia_usuario(usuario_id):
        if usuario_id in datos:
            return datos[usuario_id]["experiencia"]
        return 0

    lista_miembros = sorted(ctx.guild.members, key=lambda member: obtener_nivel_usuario(str(member.id)), reverse=True)
    embed = discord.Embed(title="Lista de niveles y experiencia", color=discord.Color.blue())
    
    for i, member in enumerate(lista_miembros):
        usuario_id = str(member.id)
        nivel = obtener_nivel_usuario(usuario_id)
        experiencia = obtener_experiencia_usuario(usuario_id)
        embed.add_field(name=f"{i+1}. {member.name}", value=f"Nivel: {nivel}\nExperiencia: {experiencia}", inline=False)

    await ctx.send(embed=embed)

# Comando: Mostrar información de un usuario específico
@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author

    embed = discord.Embed(title=f"Información de {member.name}", color=member.color)
    embed.add_field(name="ID", value=member.id, inline=False)
    embed.add_field(name="Apodo", value=member.nick, inline=False)
    embed.add_field(name="Creación de cuenta", value=member.created_at.strftime("%d/%m/%Y %H:%M:%S"), inline=False)
    embed.add_field(name="Fecha de ingreso", value=member.joined_at.strftime("%d/%m/%Y %H:%M:%S"), inline=False)

    roles = [role.name for role in member.roles]
    embed.add_field(name="Roles", value=", ".join(roles), inline=False)

    await ctx.send(embed=embed)

# Comando: Juego de Trivia mejorado
preguntas = [
    {
        "pregunta": "¿En qué año fue lanzado el primer iPhone?",
        "respuestas": ["2007", "2005", "2009", "2010"],
        "correcta": "2007"
    },
    {
        "pregunta": "¿Cuál es el planeta más grande del Sistema Solar?",
        "respuestas": ["Júpiter", "Saturno", "Urano", "Neptuno"],
        "correcta": "Júpiter"
    },
    {
        "pregunta": "¿Cuál es el río más largo del mundo?",
        "respuestas": ["Amazonas", "Nilo", "Misisipi", "Yangtsé"],
        "correcta": "Amazonas"
    }
]
@bot.command()
async def trivia(ctx):
    pregunta = random.choice(preguntas)
    respuestas = "\n".join([f"{i+1}. {respuesta}" for i, respuesta in enumerate(pregunta["respuestas"])])
    await ctx.send(f"{pregunta['pregunta']}\n{respuestas}")

    def check(m):
        return m.author == ctx.author and m.content.isdigit()

    try:
        mensaje = await bot.wait_for("message", check=check, timeout=15)
        respuesta = pregunta["respuestas"][int(mensaje.content)-1]
        if respuesta == pregunta["correcta"][0]:
            await ctx.send("¡Correcto! Ganaste 50 coinson.")
            agregar_monedas(ctx.author, 50)
        else:
            await ctx.send("Incorrecto. Inténtalo de nuevo más tarde.")
    except asyncio.TimeoutError:
        await ctx.send("Se acabó el tiempo. Inténtalo de nuevo más tarde.")

# Comando: Apostar monedas
@bot.group(invoke_without_command=True)
async def apostar(ctx, cantidad: int):
    datos = cargar_datos()
    usuario_id = str(ctx.author.id)

    if usuario_id not in datos:
        await ctx.send("No tienes monedas suficientes para apostar.")
        return

    monedas_actuales = datos[usuario_id]["monedas"]

    if cantidad <= 0 or cantidad > monedas_actuales:
        await ctx.send("Cantidad inválida. Asegúrate de tener suficientes monedas para apostar.")
        return

    opciones = ["cara", "cruz"]
    eleccion = random.choice(opciones)
    resultado = random.choice(opciones)

    if eleccion == resultado:
        monedas_ganadas = cantidad * 2
        await ctx.send(f"¡Ganaste! Apostaste {cantidad} coinson a {eleccion} y salió {resultado}. Ganaste {monedas_ganadas} coinson.")
        agregar_monedas(ctx.author, monedas_ganadas)
    else:
        await ctx.send(f"Perdiste. Apostaste {cantidad} coinson a {eleccion} y salió {resultado}.")
        restar_monedas(ctx.author, cantidad)

@apostar.command()
async def ayuda(ctx):
    embed = discord.Embed(title="Comando !apostar", color=discord.Color.blue())
    embed.add_field(name="Uso", value="!apostar <cantidad>", inline=False)
    embed.add_field(name="Descripción", value="Apostar una cantidad de monedas a cara o cruz.", inline=False)
    await ctx.send(embed=embed)

def agregar_monedas(usuario, cantidad):
    datos = cargar_datos()
    usuario_id = str(usuario.id)

    if usuario_id in datos:
        datos[usuario_id]["monedas"] += cantidad
    else:
        datos[usuario_id] = {"experiencia": 0, "nivel": 1, "monedas": cantidad}

    guardar_datos(datos)

def restar_monedas(usuario, cantidad):

    usuario_id = str(usuario.id)

    if usuario_id in datos:
        datos[usuario_id]["monedas"] -= cantidad
        guardar_datos(datos)

# Comando: Jugar al Blackjack
@bot.command()
async def blackjack(ctx):
    def check(m):
        return m.author == ctx.author and m.content.lower() in ["hit", "stand", "double"]

    async def mostrar_cartas(jugador, repartidor):
        jugador_mano = ", ".join([carta["nombre"] for carta in jugador])
        repartidor_mano = ", ".join([carta["nombre"] for carta in repartidor[1:]])

        embed = discord.Embed(title="Blackjack", color=discord.Color.blue())
        embed.add_field(name="Tus cartas:", value=jugador_mano, inline=False)
        embed.add_field(name="Carta del repartidor:", value=repartidor[1]["nombre"], inline=False)
        await ctx.send(embed=embed)

    cartas = [
        {"nombre": "As", "valor": 1},
        {"nombre": "2", "valor": 2},
        {"nombre": "3", "valor": 3},
        {"nombre": "4", "valor": 4},
        {"nombre": "5", "valor": 5},
        {"nombre": "6", "valor": 6},
        {"nombre": "7", "valor": 7},
        {"nombre": "8", "valor": 8},
        {"nombre": "9", "valor": 9},
        {"nombre": "10", "valor": 10},
        {"nombre": "J", "valor": 10},
        {"nombre": "Q", "valor": 10},
        {"nombre": "K", "valor": 10}
    ]

    jugador = [random.choice(cartas), random.choice(cartas)]
    repartidor = [random.choice(cartas), random.choice(cartas)]

    await mostrar_cartas(jugador, repartidor)

    while sum([carta["valor"] for carta in jugador]) < 21:
        await ctx.send("¿Quieres otra carta? (Escribe 'hit' o 'stand')")
        try:
            mensaje = await bot.wait_for("message", check=check, timeout=15)
            if mensaje.content.lower() == "hit":
                jugador.append(random.choice(cartas))
                await mostrar_cartas(jugador, repartidor)
            else:
                break
        except asyncio.TimeoutError:
            await ctx.send("Se acabó el tiempo. Te plantas.")
            break

    while sum([carta["valor"] for carta in repartidor]) < 17:
        repartidor.append(random.choice(cartas))

    if sum([carta["valor"] for carta in jugador]) > 21:
        await ctx.send("Te has pasado de 21. ¡Perdiste!")
        restar_monedas(ctx.author, 200)
    elif sum([carta["valor"] for carta in repartidor]) > 21 or sum([carta["valor"] for carta in jugador]) > sum([carta["valor"] for carta in repartidor]):
        await ctx.send("¡Ganaste! Tienes una mejor mano que el repartidor.")
        agregar_monedas(ctx.author, 400)
    elif sum([carta["valor"] for carta in jugador]) == sum([carta["valor"] for carta in repartidor]):
        await ctx.send("Empate. Nadie gana.")
    else:
        await ctx.send("Perdiste. El repartidor tiene una mejor mano.")
        restar_monedas(ctx.author, 200)
# Comando: Mostrar lista de comandos disponibles
@bot.command()
async def ayuda(ctx):
    descripcion_comandos = {
        "!saludar": "Saluda al bot.",
        "!kick (miembro)": "Expulsa a un miembro del servidor. (Requiere permiso 'kick_members')",
        "!ban (miembro)": "Banea a un miembro del servidor. (Requiere permiso 'ban_members')",
        "!clear (cantidad)": "Borra una cantidad especificada de mensajes en el canal. (Requiere permiso 'manage_messages')",
        "!adivina": "Juega al minijuego 'Adivina el número'.",
        "!ppt (elige: pidra, papel o tijeras)": "Juega al minijuego 'Piedra, Papel o Tijera'.",
        "!info": "Muestra información del servidor.",
        "!trabajo": "Realiza un trabajo y gana monedas.",
        "!niveles": "Muestra la lista de niveles y experiencia de los miembros del servidor.",
        "!userinfo (miembro)": "Muestra información de un usuario específico.",
        "!trivia": "Juega al minijuego 'Trivia'.",
        "!apostar (cantidad)": "Apostar monedas en un juego de cara o cruz.",
        "!blackjack": "Juega al minijuego 'Blackjack' contra el repartidor.",
        "!xp": "Muestra la experiencia del usuario.",
        "!coinson": "Muestra las monedas del usuario.",
        "!lvl": "Muestra el nivel del usuario."
    }

    embed = discord.Embed(title="Comandos disponibles", color=discord.Color.green())
    for comando, descripcion in descripcion_comandos.items():
        embed.add_field(name=comando, value=descripcion, inline=False)

    await ctx.send(embed=embed)

bot.run("MTExNDQ4MDEwODQwOTk3ODk1Mg.GSIerQ.d8DzLrzlNCdKYcqHAHygp5xWP6vg-y1jfSUKfE")
