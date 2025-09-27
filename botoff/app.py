import discord
from discord.ext import commands
import random
import json
import asyncio
import os
from typing import Optional, Dict, Any

# ------------------ CONFIG ------------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------ DATOS ------------------

DATOS_FILE = "datos.json"

def cargar_datos() -> Dict[str, Any]:
    try:
        if not os.path.exists(DATOS_FILE):
            return {}
        with open(DATOS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def guardar_datos(datos: Dict[str, Any]):
    try:
        with open(DATOS_FILE, "w", encoding="utf-8") as f:
            json.dump(datos, f, ensure_ascii=False, indent=4)
    except PermissionError:
        print("No se tienen permisos para guardar datos en", DATOS_FILE)

def asegurar_usuario(datos: Dict[str, Any], uid: str):
    if uid not in datos:
        datos[uid] = {
            "cash": 0,
            "bank": 0,
            "nivel": 1,
            "experiencia": 0
        }
    else:
        for key in ["cash", "bank", "nivel", "experiencia"]:
            if key not in datos[uid]:
                datos[uid][key] = 1 if key == "nivel" else 0

def agregar_a_cash(datos: Dict[str, Any], uid: str, cantidad: int):
    asegurar_usuario(datos, uid)
    datos[uid]["cash"] = datos[uid].get("cash", 0) + cantidad

def obtener_monedas(datos: Dict[str, Any], uid: str) -> int:
    asegurar_usuario(datos, uid)
    return datos[uid].get("cash", 0) + datos[uid].get("bank", 0)

def restar_de_cash(datos: Dict[str, Any], uid: str, cantidad: int) -> bool:
    asegurar_usuario(datos, uid)
    if datos[uid].get("cash", 0) < cantidad:
        return False
    datos[uid]["cash"] = max(0, datos[uid]["cash"] - cantidad)
    # opcional: no modificamos monedas aquí, dejamos monedas = total histórico
    return True

# ------------------ UTILIDADES ------------------

def formato_tiempo(segundos: float) -> str:
    total = int(round(segundos))
    minutos = total // 60
    segundos_rest = total % 60
    if minutos > 0:
        return f"{minutos}m {segundos_rest}s"
    return f"{segundos_rest}s"

def obtener_rank_por_monedas(datos: Dict[str, Any], uid: str) -> Optional[int]:
    lista = sorted(
        [(u, info.get("monedas", 0)) for u, info in datos.items()],
        key=lambda x: x[1],
        reverse=True
    )
    for idx, (user_id, monedas) in enumerate(lista, start=1):
        if user_id == uid:
            return idx
    return None

# ------------------ XP / NIVELES ------------------

def recompensa_por_bloque(nivel: int) -> int:
    bloques = nivel // 10
    if bloques <= 0:
        return 0
    return 200 + (bloques - 1) * 100

# ------------------ EVENTOS ------------------

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="!ayuda"))
    print(f"Bot conectado como {bot.user} (ID: {bot.user.id})")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    datos = cargar_datos()
    uid = str(message.author.id)
    asegurar_usuario(datos, uid)

    experiencia_ganada = random.randint(15, 25)
    datos[uid]["experiencia"] += experiencia_ganada

    canal_niveles_id = 1412574049942503444  # cambia por tu ID si hace falta
    canal_niveles = message.guild.get_channel(canal_niveles_id) if message.guild else None

    while datos[uid]["experiencia"] >= datos[uid]["nivel"] * 100:
        datos[uid]["experiencia"] -= datos[uid]["nivel"] * 100
        datos[uid]["nivel"] += 1
        nuevo_nivel = datos[uid]["nivel"]
        if canal_niveles:
            try:
                if nuevo_nivel % 10 == 0:
                    recompensa = recompensa_por_bloque(nuevo_nivel)
                    datos[uid]["monedas"] += recompensa
                    datos[uid]["cash"] += recompensa
                    await canal_niveles.send(
                        f"🎉 {message.author.mention} ¡Has subido al nivel **{nuevo_nivel}** "
                        f"y has recibido **{recompensa} <:amatista:1420736192269390006>**!"
                    )
                else:
                    await canal_niveles.send(
                        f"🎉 {message.author.mention} ¡Has subido al nivel **{nuevo_nivel}**!"
                    )
            except Exception:
                pass

    guardar_datos(datos)
    await bot.process_commands(message)

# ------------------ MANEJO DE ERRORES (Cooldowns) ------------------

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        tiempo = formato_tiempo(error.retry_after)
        await ctx.send(f"🕒 Este comando está en cooldown. Espera **{tiempo}** antes de volver a usarlo.")
    else:
        # si quieres evitar raise para todos, puedes comentar la siguiente línea
        raise error

# ------------------ COMANDOS BÁSICOS / ADMIN ------------------

@bot.command()
async def saludar(ctx):
    await ctx.send("¡Hola! ¡Estoy aquí para ayudar!")

@bot.command()
@commands.has_permissions(kick_members=True)
async def kick(ctx, member: discord.Member, *, reason=None):
    try:
        await member.kick(reason=reason)
        await ctx.send(f"{member.mention} ha sido expulsado.")
    except Exception as e:
        await ctx.send(f"No pude expulsar a {member.mention}. Error: {e}")

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, member: discord.Member, *, reason=None):
    try:
        await member.ban(reason=reason)
        await ctx.send(f"{member.mention} ha sido baneado.")
    except Exception as e:
        await ctx.send(f"No pude banear a {member.mention}. Error: {e}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    deleted = await ctx.channel.purge(limit=amount+1)
    confirmation_message = await ctx.send(f"Se han borrado {len(deleted)-1} mensajes.")
    await asyncio.sleep(10)
    try:
        await confirmation_message.delete()
    except:
        pass

# ------------------ INFO / USUARIO ------------------

@bot.command()
async def userinfo(ctx, member: discord.Member = None):
    if member is None:
        member = ctx.author
    embed = discord.Embed(title=f"👤 Información de {member}", color=discord.Color.blue())
    embed.add_field(name="ID", value=member.id, inline=False)
    embed.add_field(name="Cuenta creada el", value=member.created_at.strftime("%d/%m/%Y %H:%M:%S"), inline=False)
    embed.add_field(name="Se unió al servidor", value=member.joined_at.strftime("%d/%m/%Y %H:%M:%S"), inline=False)
    if member.avatar:
        embed.set_thumbnail(url=member.avatar.url)
    await ctx.send(embed=embed)

@bot.command()
async def lvl(ctx, member: discord.Member = None):
    datos = cargar_datos()
    if member is None:
        member = ctx.author
    uid = str(member.id)
    asegurar_usuario(datos, uid)
    nivel = datos[uid]["nivel"]
    xp = datos[uid]["experiencia"]
    embed = discord.Embed(title=f"📈 Nivel de {member.name}", color=discord.Color.green())
    embed.add_field(name="Nivel", value=nivel, inline=True)
    embed.add_field(name="Experiencia", value=xp, inline=True)
    await ctx.send(embed=embed)

@bot.command()
async def ranking(ctx):
    datos = cargar_datos()
    miembros = []
    for uid, info in datos.items():
        user = bot.get_user(int(uid))
        miembros.append((user, info.get("nivel", 0), info.get("experiencia", 0)))
    miembros.sort(key=lambda x: (x[1], x[2]), reverse=True)
    desc = ""
    for i, (usuario, nivel, xp) in enumerate(miembros[:10], 1):
        if usuario:
            desc += f"**{i}. {usuario.name}** - Nivel {nivel} | XP {xp}\n"
    embed = discord.Embed(title="🏆 Ranking de Niveles", description=desc if desc else "No hay datos.", color=discord.Color.gold())
    await ctx.send(embed=embed)

# ------------------ ROBOS / CRIMEN ------------------

@bot.command()
async def robar(ctx, member: discord.Member):
    datos = cargar_datos()
    uid = str(ctx.author.id)
    target_uid = str(member.id)
    asegurar_usuario(datos, uid)
    asegurar_usuario(datos, target_uid)
    if datos[target_uid].get("monedas", 0) <= 0:
        await ctx.send("❌ Este usuario no tiene monedas para robar.")
        return
    exito = random.choice([True, False])
    if exito:
        cantidad = random.randint(10, min(50, datos[target_uid].get("monedas", 0)))
        datos[uid]["monedas"] = datos[uid].get("monedas", 0) + cantidad
        datos[target_uid]["monedas"] = max(0, datos[target_uid].get("monedas", 0) - cantidad)
        datos[uid]["cash"] = datos[uid].get("cash", 0) + cantidad
        datos[target_uid]["cash"] = max(0, datos[target_uid].get("cash", 0) - cantidad)
        await ctx.send(f"🎉 Has robado {cantidad} <:amatista:1420736192269390006> a {member.mention}!")
    else:
        await ctx.send(f"❌ Fallaste al intentar robar a {member.mention} y no obtuviste nada.")
    guardar_datos(datos)

@bot.command()
async def crimen(ctx):
    datos = cargar_datos()
    uid = str(ctx.author.id)
    asegurar_usuario(datos, uid)
    riesgo = random.randint(0, 100)
    if riesgo < 50:
        ganancia = random.randint(50, 100)
        datos[uid]["monedas"] = datos[uid].get("monedas", 0) + ganancia
        datos[uid]["cash"] = datos[uid].get("cash", 0) + ganancia
        await ctx.send(f"🎉 Crimen exitoso! Ganaste {ganancia} <:amatista:1420736192269390006>.")
    else:
        perdida = random.randint(20, 50)
        datos[uid]["monedas"] = max(0, datos[uid].get("monedas", 0) - perdida)
        datos[uid]["cash"] = max(0, datos[uid].get("cash", 0) - perdida)
        await ctx.send(f"❌ Crimen fallido! Perdiste {perdida} <:amatista:1420736192269390006>.")
    guardar_datos(datos)

# ------------------ MINIJUEGOS ADICIONALES ------------------

@bot.command()
async def apostar(ctx, cantidad: str, opcion: str):
    """
    !apostar <cantidad|all> <cara/cruz>
    apuesta usando valor de cash (no bank). Si pones 'all' apuesta todo el cash.
    """
    datos = cargar_datos()
    uid = str(ctx.author.id)
    asegurar_usuario(datos, uid)

    # determinar cantidad real
    if cantidad.lower() == "all":
        cantidad_real = datos[uid].get("cash", 0)
    else:
        try:
            cantidad_real = int(cantidad)
        except:
            await ctx.send("Cantidad inválida. Usa un número o 'all'.")
            return

    if cantidad_real <= 0 or datos[uid].get("cash", 0) < cantidad_real:
        await ctx.send("❌ No tienes suficiente efectivo (cash) para esa apuesta.")
        return

    opcion = opcion.lower()
    if opcion not in ("cara", "cruz"):
        await ctx.send("Opción inválida. Usa 'cara' o 'cruz'.")
        return

    resultado = random.choice(["cara", "cruz"])
    if opcion == resultado:
        ganancia = cantidad_real * 2
        # restamos la apuesta y añadimos la ganancia neta
        restar_de_cash(datos, uid, cantidad_real)
        agregar_a_cash_y_monedas(datos, uid, ganancia)
        await ctx.send(f"🎉 Ganaste! Salió {resultado}. Ganaste {ganancia} <:amatista:1420736192269390006>.")
    else:
        # pierdes la cantidad apostada (de cash)
        restar_de_cash(datos, uid, cantidad_real)
        guardar_datos(datos)
        await ctx.send(f"❌ Perdiste! Salió {resultado}. Perdiste {cantidad_real} <:amatista:1420736192269390006>.")
    guardar_datos(datos)

@bot.command()
async def blackjack(ctx, cantidad: str):
    """
    Blackjack interactivo:
    - Usa tu cash como apuesta (o 'all').
    - Puedes pedir carta (hit) o plantarte (stand).
    - El bot juega como la banca: saca hasta 17+.
    - Si empatas, recuperas la apuesta.
    """
    datos = cargar_datos()
    uid = str(ctx.author.id)
    asegurar_usuario(datos, uid)

    # definir apuesta
    if cantidad.lower() == "all":
        apuesta = datos[uid].get("cash", 0)
    else:
        try:
            apuesta = int(cantidad)
        except:
            await ctx.send("❌ Cantidad inválida. Usa un número o 'all'.")
            return

    if apuesta <= 0 or datos[uid].get("cash", 0) < apuesta:
        await ctx.send("❌ No tienes suficiente cash para esa apuesta.")
        return

    # mazo simplificado
    cartas = [2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10, 11] * 4
    random.shuffle(cartas)

    def valor(mano):
        total = sum(mano)
        ases = mano.count(11)
        while total > 21 and ases:
            total -= 10
            ases -= 1
        return total

    # inicializar manos
    mano_jugador = [cartas.pop(), cartas.pop()]
    mano_bot = [cartas.pop(), cartas.pop()]

    restar_de_cash(datos, uid, apuesta)

    # función para mostrar mano
    def mostrar_mano_final():
        return f"🃏 Tu mano: {mano_jugador} = {valor(mano_jugador)}\n🤖 Mano del bot: {mano_bot} = {valor(mano_bot)}"

    # mostrar inicio
    await ctx.send(
        f"🎲 Apostaste {apuesta} <:amatista:1420736192269390006>\n"
        f"🃏 Tu mano: {mano_jugador} = {valor(mano_jugador)}\n"
        f"🤖 Mano del bot: [{mano_bot[0]}, ?]"
    )

    # turno del jugador
    while valor(mano_jugador) < 21:
        await ctx.send("👉 Escribe `hit` para pedir carta o `stand` para plantarte.")

        try:
            msg = await bot.wait_for(
                "message",
                timeout=30.0,
                check=lambda m: m.author == ctx.author and m.channel == ctx.channel
            )
        except asyncio.TimeoutError:
            await ctx.send("⌛ Tiempo agotado, te plantas automáticamente.")
            break

        if msg.content.lower() == "hit":
            carta = cartas.pop()
            mano_jugador.append(carta)
            await ctx.send(f"🃏 Nueva carta: {carta} | Tu mano ahora: {mano_jugador} = {valor(mano_jugador)}")
            if valor(mano_jugador) > 21:
                await ctx.send(f"💥 Te pasaste! Pierdes {apuesta} <:amatista:1420736192269390006>.")
                guardar_datos(datos)
                return
        elif msg.content.lower() == "stand":
            break
        else:
            await ctx.send("Escribe solo `hit` o `stand`.")

    # turno del bot
    while valor(mano_bot) < 17:
        mano_bot.append(cartas.pop())

    total_jugador = valor(mano_jugador)
    total_bot = valor(mano_bot)

    # resultado final
    if total_bot > 21 or total_jugador > total_bot:
        ganancia = apuesta * 2
        agregar_a_cash(datos, uid, ganancia)
        await ctx.send(mostrar_mano_final() + f"\n🎉 Ganaste {ganancia} <:amatista:1420736192269390006>!")
    elif total_jugador == total_bot:
        agregar_a_cash(datos, uid, apuesta)
        await ctx.send(mostrar_mano_final() + f"\n🤝 Empate. Recuperas tu apuesta de {apuesta}.")
    else:
        await ctx.send(mostrar_mano_final() + f"\n❌ Pierdes {apuesta} <:amatista:1420736192269390006>.")

    guardar_datos(datos)

# ------------------ TICKETS ------------------

@bot.command()
async def panelticket(ctx):
    await ctx.send("🎫 Panel de tickets: (Próximamente funcional)")

# ------------------ MINIJUEGOS ------------------

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

# ------------------ PIEDRA PAPEL TIJERA ------------------

@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def ppt(ctx, apuesta: str, choice: str):
    datos = cargar_datos()
    usuario_id = str(ctx.author.id)
    asegurar_usuario(datos, usuario_id)

    if apuesta.lower() == "all":
        apuesta_real = datos[usuario_id].get("cash", 0)
    else:
        try:
            apuesta_real = int(apuesta)
        except:
            await ctx.send("Cantidad inválida. Usa un número o 'all'.")
            return

    if apuesta_real <= 0 or datos[usuario_id].get("cash", 0) < apuesta_real:
        await ctx.send("❌ No tienes suficientes monedas (cash) para esa apuesta.")
        return

    choices = ["piedra", "papel", "tijera"]
    choice = choice.lower()
    if choice not in choices:
        await ctx.send("Opción inválida. Las opciones son: piedra, papel o tijera.")
        return

    bot_choice = random.choice(choices)
    if choice == bot_choice:
        await ctx.send(f"🤝 Empate. Ambos eligieron {choice}.")
    elif ((choice == "piedra" and bot_choice == "tijera") or
          (choice == "papel" and bot_choice == "piedra") or
          (choice == "tijera" and bot_choice == "papel")):
        ganancia = apuesta_real * 2
        # restamos apuesta y sumamos ganancia
        restar_de_cash(datos, usuario_id, apuesta_real)
        agregar_a_cash_y_monedas(datos, usuario_id, ganancia)
        await ctx.send(f"🎉 Ganaste. Elegiste {choice} y yo elegí {bot_choice}. Ganaste {ganancia} <:amatista:1420736192269390006>.")
    else:
        restar_de_cash(datos, usuario_id, apuesta_real)
        await ctx.send(f"😢 Perdiste. Elegiste {choice} y yo elegí {bot_choice}. Perdiste {apuesta_real} monedas.")

    guardar_datos(datos)

@ppt.error
async def ppt_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"🕒 Debes esperar {formato_tiempo(error.retry_after)} antes de volver a jugar PPT.")
    else:
        raise error

# ------------------ INFO / TRABAJO / ECONOMÍA ------------------

@bot.command()
async def info(ctx):
    server = ctx.guild
    embed = discord.Embed(title=f"Información del servidor {server.name}", color=discord.Color.blue())
    embed.add_field(name="Dueño", value=server.owner, inline=False)
    embed.add_field(name="Miembros", value=server.member_count, inline=False)
    try:
        embed.add_field(name="Región", value=str(server.region), inline=False)
    except:
        pass
    embed.add_field(name="Creado el", value=server.created_at.strftime("%d/%m/%Y %H:%M:%S"), inline=False)
    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 60, commands.BucketType.user)
async def trabajar(ctx):
    datos = cargar_datos()
    uid = str(ctx.author.id)
    asegurar_usuario(datos, uid)

    trabajos = [
        {"nombre": "informático", "min": 50, "max": 120},
        {"nombre": "diseñador", "min": 50, "max": 120},
        {"nombre": "músico", "min": 50, "max": 120},
        {"nombre": "chef", "min": 50, "max": 120},
        {"nombre": "fotógrafo", "min": 50, "max": 120},
    ]

    trabajo_actual = random.choice(trabajos)
    ganancia = random.randint(trabajo_actual["min"], trabajo_actual["max"])
    datos[uid]["monedas"] = datos[uid].get("monedas", 0) + ganancia
    datos[uid]["cash"] = datos[uid].get("cash", 0) + ganancia
    guardar_datos(datos)
    await ctx.send(f"💼 {ctx.author.mention} trabajó como {trabajo_actual['nombre']} y ganó {ganancia} <:amatista:1420736192269390006>.")

# ------------------ BALANCE ------------------

@bot.command()
async def bal(ctx, member: discord.Member = None):
    datos = cargar_datos()
    if member is None:
        member = ctx.author
    uid = str(member.id)
    asegurar_usuario(datos, uid)
    cash = datos[uid]["cash"]
    bank = datos[uid]["bank"]
    total = obtener_monedas(datos, uid)
    posicion = obtener_rank_por_monedas(datos, uid)

    embed = discord.Embed(title=f"💰 Balance de {member.name}", color=discord.Color.gold())
    embed.add_field(name="Efectivo (cash)", value=f"{cash} <:amatista:1420736192269390006>", inline=True)
    embed.add_field(name="Banco", value=f"{bank} <:amatista:1420736192269390006>", inline=True)
    embed.add_field(name="Total", value=f"{total} <:amatista:1420736192269390006>", inline=False)
    embed.set_footer(text=f"Posición en leaderboard: #{posicion if posicion else '—'}")
    await ctx.send(embed=embed)


# ------------------ BANCOS ------------------

@bot.command()
async def depositar(ctx, cantidad: str):
    datos = cargar_datos()
    uid = str(ctx.author.id)
    asegurar_usuario(datos, uid)

    if cantidad.lower() == "all":
        cantidad_real = datos[uid].get("cash", 0)
    else:
        try:
            cantidad_real = int(cantidad)
        except:
            await ctx.send("Cantidad inválida. Usa un número o 'all'.")
            return

    if cantidad_real <= 0 or cantidad_real > datos[uid].get("cash", 0):
        await ctx.send("Cantidad inválida o no tienes suficiente cash.")
        return

    datos[uid]["cash"] = datos[uid].get("cash", 0) - cantidad_real
    datos[uid]["bank"] = datos[uid].get("bank", 0) + cantidad_real
    guardar_datos(datos)
    await ctx.send(f"💳 Has depositado {cantidad_real} <:amatista:1420736192269390006> en tu banco.")

@bot.command()
async def retirar(ctx, cantidad: str):
    datos = cargar_datos()
    uid = str(ctx.author.id)
    asegurar_usuario(datos, uid)

    if cantidad.lower() == "all":
        cantidad_real = datos[uid].get("bank", 0)
    else:
        try:
            cantidad_real = int(cantidad)
        except:
            await ctx.send("Cantidad inválida. Usa un número o 'all'.")
            return

    if cantidad_real <= 0 or cantidad_real > datos[uid].get("bank", 0):
        await ctx.send("Cantidad inválida o no tienes suficiente en el banco.")
        return

    datos[uid]["bank"] = datos[uid].get("bank", 0) - cantidad_real
    datos[uid]["cash"] = datos[uid].get("cash", 0) + cantidad_real
    guardar_datos(datos)
    await ctx.send(f"💵 Has retirado {cantidad_real} <:amatista:1420736192269390006> de tu banco.")

# ------------------ AYUDA / LISTA DE COMANDOS ------------------

COMMAND_CATEGORIES = {
    "basicos": {
        "!saludar": "Saluda al bot.",
        "!info": "Muestra información del servidor.",
        "!userinfo (miembro)": "Muestra información de un usuario.",
        "!bal": "Muestra tus monedas y dinero en el banco.",
        "!lvl": "Muestra tu nivel y experiencia.",
        "!ranking": "Muestra la lista de niveles y experiencia de los miembros."
    },
    "moderacion": {
        "!kick (miembro)": "Expulsa a un miembro. (Permiso kick_members)",
        "!ban (miembro)": "Banea a un miembro. (Permiso ban_members)",
        "!clear (cantidad)": "Borra mensajes. (Permiso manage_messages)"
    },
    "economia": {
        "!trabajar": "Gana monedas realizando un trabajo.",
        "!depositar (cantidad|all)": "Deposita dinero (o 'all') en tu banco.",
        "!retirar (cantidad|all)": "Retira dinero (o 'all') de tu banco.",
        "!robar (usuario)": "Intenta robar monedas a otro usuario. (Riesgo de perder)",
        "!crimen": "Comete un crimen por monedas. (Riesgo alto)",
        "!lb": "Muestra el leaderboard de amatistas (top)."
    },
    "minijuegos": {
        "!adivina": "Adivina un número entre 1 y 100.",
        "!ppt (cantidad|all) (piedra/papel/tijera)": "Juega 'Piedra, Papel o Tijera' con tu cash.",
        "!apostar (cantidad|all) (cara/cruz)": "Apuesta con tu cash.",
        "!blackjack (cantidad|all)": "Juega Blackjack contra el bot usando tu cash."
    },
    "otros": {
        "!panelticket": "Muestra el panel para crear tickets."
    }
}

@bot.command()
async def ayuda(ctx, categoria: str = None):
    if categoria:
        cat = categoria.lower()
        if cat in COMMAND_CATEGORIES:
            embed = discord.Embed(title=f"📜 Comandos — {cat.title()}", color=discord.Color.green())
            descripcion = ""
            for cmd, desc in COMMAND_CATEGORIES[cat].items():
                descripcion += f"**{cmd}** — {desc}\n"
            embed.description = descripcion
            await ctx.send(embed=embed)
            return
        else:
            await ctx.send("Categoría no encontrada. Usa: basicos, moderacion, economia, minijuegos, otros")
            return

    # ayuda general
    embed = discord.Embed(title="📜 Comandos disponibles", color=discord.Color.green())
    for cat_name, cmds in COMMAND_CATEGORIES.items():
        descripcion = ""
        for cmd, desc in cmds.items():
            descripcion += f"**{cmd}** — {desc}\n"
        embed.add_field(name=cat_name.title(), value=descripcion, inline=False)
    embed.set_footer(text="Usa `!ayuda <categoria>` para ver comandos de esa categoría. Ej: !ayuda minijuegos")
    await ctx.send(embed=embed)

# ------------------ LEADERBOARD (!lb) ------------------

@bot.command()
async def lb(ctx, pagina: int = 1):
    datos = cargar_datos()
    if not datos:
        await ctx.send("No hay datos aún.")
        return

    lista = [(uid, obtener_monedas(datos, uid)) for uid in datos.keys()]
    lista.sort(key=lambda x: x[1], reverse=True)

    per_page = 10
    max_pages = (len(lista) + per_page - 1) // per_page
    pagina = max(1, min(pagina, max_pages))

    inicio = (pagina - 1) * per_page
    fin = inicio + per_page
    slice_lista = lista[inicio:fin]

    descripcion = ""
    for idx, (uid, monedas) in enumerate(slice_lista, start=inicio + 1):
        usuario = bot.get_user(int(uid))
        nombre = usuario.name if usuario else f"Usuario desconocido ({uid})"
        medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else ""
        descripcion += f"{medal} **#{idx}** — {nombre} — {monedas} <:amatista:1420736192269390006>\n"

    embed = discord.Embed(title=f"🏆 Leaderboard — Amatistas (Página {pagina}/{max_pages})",
                          description=descripcion if descripcion else "No hay datos en esta página.",
                          color=discord.Color.purple())
    embed.set_footer(text="Usa !lb <número_de_página> para ver otras páginas.")
    await ctx.send(embed=embed)

# ------------------ EJECUTAR BOT ------------------

if __name__ == "__main__":
    # Pon tu token aquí de forma segura
    bot.run("MTExNDQ4MDEwODQwOTk3ODk1Mg.GSIerQ.d8DzLrzlNCdKYcqHAHygp5xWP6vg-y1jfSUKfE")
