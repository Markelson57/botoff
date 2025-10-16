import discord
from discord.ext import commands
from discord.ui import Modal, TextInput, View, Button
import random
import datetime
import json
import asyncio
import os
from typing import Optional, Dict, Any
from itertools import cycle
from dotenv import load_dotenv

load_dotenv()

# ------------------ CONFIG ------------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
intents.presences = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ------------------ DATOS ------------------

ROLE_COMPETITIVO = 1406648557808648367
ROLE_FREESTYLER = 1406648556768596059
ROLE_MIEMBRO = 1406648558790250668
CANAL_BIENVENIDAS_ID = 1406648569271816192  # ID del canal de bienvenida
ROL_OBLIGATORIO_ID = 1424860513258701002 
MI_ID = 798937817869844541
DATOS_FILE = "datos.json"
TRIGGER_TEXT = "./start_globed$backup"

# --- CONFIG EXTRA / PERMISOS DE BALANCE ---
ALLOW_NEGATIVE_BALANCE = True  # True permite cash negativo 

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
    """Garantiza que un usuario tenga su estructura básica en el JSON."""
    if uid not in datos:
        datos[uid] = {
            "cash": 0,
            "bank": 0,
            "nivel": 1,
            "experiencia": 0,
            "monedas": 0,
            "items": {}
        }
    else:
        for key in ["cash", "bank", "nivel", "experiencia", "monedas", "items"]:
            if key not in datos[uid]:
                if key == "nivel":
                    datos[uid][key] = 1
                elif key == "items":
                    datos[uid][key] = {}
                else:
                    datos[uid][key] = 0

def agregar_a_cash(datos: Dict[str, Any], uid: str, cantidad: int):
    """Suma cantidad al cash (sin modificar monedas históricas)."""
    asegurar_usuario(datos, uid)
    datos[uid]["cash"] = datos[uid].get("cash", 0) + cantidad

def agregar_a_cash_y_monedas(datos: Dict[str, Any], uid: str, cantidad: int):
    """Añade cash y también suma a monedas (solo si cantidad > 0)."""
    asegurar_usuario(datos, uid)
    datos[uid]["cash"] = datos[uid].get("cash", 0) + cantidad
    if cantidad > 0:
        datos[uid]["monedas"] = datos[uid].get("monedas", 0) + cantidad

def obtener_monedas(datos: Dict[str, Any], uid: str) -> int:
    """Devuelve la suma del cash + bank actual del usuario."""
    asegurar_usuario(datos, uid)
    return datos[uid].get("cash", 0) + datos[uid].get("bank", 0)

def restar_de_cash(datos: Dict[str, Any], uid: str, cantidad: int) -> bool:
    """
    Resta cash. 
    Si ALLOW_NEGATIVE_BALANCE es True, puede dejar el saldo en negativo.
    Si es False, cancela la operación si no hay suficiente dinero.
    """
    asegurar_usuario(datos, uid)
    if not ALLOW_NEGATIVE_BALANCE and datos[uid].get("cash", 0) < cantidad:
        return False
    datos[uid]["cash"] = datos[uid].get("cash", 0) - cantidad
    return True

def obtener_multiplicador(datos: dict, uid: str, tipo: str) -> float:
    """
    Devuelve el multiplicador total de ganancias según los ítems del usuario.
    tipo puede ser: 'blackjack', 'apostar', 'vip', etc.
    """
    asegurar_usuario(datos, uid)
    items = datos[uid].get("items", {})
    info = items.get(tipo)
    if info:
        return info.get("multiplicador_total", 1.0)  # multiplicador acumulado
    return 1.0

@bot.before_invoke
async def before_any_command(ctx):
    async with ctx.typing():
        await asyncio.sleep(1.2)  # Pequeño delay opcional, solo visual



# ---------- MODAL ----------
class MembresiaModal(Modal, title="Registro de Miembro"):
    nombre = TextInput(label="Nombre", placeholder="Tu nombre o nick", max_length=32)
    edad = TextInput(label="Edad", placeholder="Ej: 17", max_length=4)
    tipo = TextInput(label="Tipo (FREESTYLER o COMPETITIVO)", placeholder="Escribe uno de los dos", max_length=15)
    rango = TextInput(label="¿Qué rango eres?", placeholder="Ej: C1, GC2, SSL...", max_length=10)
    habilidades = TextInput(
        label="¿Qué sabes hacer?",
        style=discord.TextStyle.long,
        placeholder="Cuéntanos tus habilidades, experiencia, etc.",
        max_length=500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        tipo_texto = self.tipo.value.strip().upper()
        if tipo_texto not in ["FREESTYLER", "COMPETITIVO"]:
            await interaction.response.send_message(
                "⚠️ Debes escribir exactamente **FREESTYLER** o **COMPETITIVO**.", ephemeral=True
            )
            return

        color = discord.Color.blue() if tipo_texto == "FREESTYLER" else discord.Color.red()
        embed = discord.Embed(
            title="Confirmar Registro de Miembro",
            description="Revisa tus datos antes de confirmar:",
            color=color,
        )
        embed.add_field(name="Nombre", value=self.nombre.value, inline=True)
        embed.add_field(name="Edad", value=self.edad.value, inline=True)
        embed.add_field(name="Tipo", value=tipo_texto, inline=True)
        embed.add_field(name="Rango", value=self.rango.value, inline=True)
        embed.add_field(name="Habilidades", value=self.habilidades.value, inline=False)
        embed.set_footer(text="Pulsa Confirmar para completar tu registro.")

        # ====== NUEVO: enviar por MD a ti ======
        try:
            admin_user = await bot.fetch_user(MI_ID)  # Cambia MI_ID por tu ID real
            await admin_user.send(
                content=f"Nuevo registro de {interaction.user} ({interaction.user.id}):",
                embed=embed
            )
        except Exception:
            pass  # ignoramos si falla

        # ====== FIN MODIFICACIÓN ======

        view = ConfirmarRegistroView(tipo_texto)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
# ---------- VISTA BOTONES DE CONFIRMACIÓN ----------
class ConfirmarRegistroView(View):
    def __init__(self, tipo):
        super().__init__(timeout=120)
        self.tipo = tipo

    @discord.ui.button(label="✅ Confirmar", style=discord.ButtonStyle.success)
    async def confirmar(self, interaction: discord.Interaction, button: Button):
        member = interaction.user
        guild = interaction.guild

        roles_to_add = [guild.get_role(ROLE_MIEMBRO)]
        if self.tipo == "COMPETITIVO":
            roles_to_add.append(guild.get_role(ROLE_COMPETITIVO))
        else:
            roles_to_add.append(guild.get_role(ROLE_FREESTYLER))

        for role in roles_to_add:
            if role:
                await member.add_roles(role, reason="Registro de membresía")

        color = discord.Color.blue() if self.tipo == "FREESTYLER" else discord.Color.red()
        embed = discord.Embed(
            title="✅ Registro completado",
            description=f"{member.mention} se ha registrado correctamente como **{self.tipo}**.",
            color=color,
        )
        embed.set_footer(text="¡Bienvenido al servidor!")
        await interaction.response.edit_message(embed=embed, view=None)

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.danger)
    async def cancelar(self, interaction: discord.Interaction, button: Button):
        embed = discord.Embed(
            title="❌ Registro cancelado",
            description="Has cancelado el registro.",
            color=discord.Color.greyple(),
        )
        await interaction.response.edit_message(embed=embed, view=None)

# ---------- BOTÓN PRINCIPAL “REGISTRARSE” ----------
class RegistroButton(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 Registrarse", style=discord.ButtonStyle.blurple)
    async def registrarse(self, interaction: discord.Interaction, button: Button):
        modal = MembresiaModal()
        await interaction.response.send_modal(modal)

# ---------- COMANDO PRINCIPAL ----------
@bot.command(name="membresia")
@commands.has_permissions(administrator=True)
async def membresia(ctx):
    await ctx.message.delete()

    embed = discord.Embed(
        title="Registro de Miembro",
        description=(
            "👋 Bienvenido al servidor.\n\n"
            "Pulsa el botón de abajo para **registrarte como miembro**.\n"
            "Podrás elegir si eres **Freestyler** o **Competitivo**, poner tu rango y habilidades.\n\n"
            "📋 Después confirma tu registro para obtener tus roles."
        ),
        color=discord.Color.green(),
    )
    embed.set_footer(text="Sistema de membresía automática")

    view = RegistroButton()
    await ctx.send(embed=embed, view=view)


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

# Lista de estados dinámicos (rotan aleatoriamente)
status_list = cycle([
    ("Rocket League", discord.ActivityType.playing),
    ("los mejores freestylers", discord.ActivityType.listening),
    ("clips de Markelson57", discord.ActivityType.watching),
    ("usa !ayuda para comenzar", discord.ActivityType.playing),
    ("nuevas funciones del bot", discord.ActivityType.playing),
    ("el sistema Markelsoft", discord.ActivityType.competing),
    ("el servidor al máximo 🔥", discord.ActivityType.playing)
])

# Canal de logs opcional (si quieres que avise en Discord)
LOG_CHANNEL_ID = 1424514411682594946  # Cambia por tu canal real de logs


@bot.event
async def on_ready():
    # Animación de inicio en consola 💻
    print("\n" + "=" * 50)
    print("🧠  INICIANDO SISTEMA MARKELSOFT AI v2.1")
    print("=" * 50)

    steps = [
        "🔌 Conectando a Discord API...",
        "⚙️ Cargando comandos...",
        "🎨 Activando interfaz visual...",
        "🛰️ Sincronizando módulos de membresía...",
        "💾 Iniciando base de datos temporal...",
        "🚀 Lanzamiento completo."
    ]

    for step in steps:
        print(step)
        await asyncio.sleep(0.5)

    print("\n✅ Bot en línea como:", bot.user)
    print(f"🆔 ID: {bot.user.id}")
    print(f"🕒 Hora de inicio: {datetime.datetime.now().strftime('%H:%M:%S')}")
    print("=" * 50 + "\n")

    # Presencia inicial
    await bot.change_presence(
        activity=discord.Game(name="Inicializando..."),
        status=discord.Status.idle
    )

    # Empieza a rotar estados
    bot.loop.create_task(estado_rotativo())

    # Envía log en Discord (opcional)
    canal_log = bot.get_channel(LOG_CHANNEL_ID)
    if canal_log:
        embed = discord.Embed(
            title="🤖 Bot conectado correctamente",
            description=f"**Usuario:** {bot.user}\n**ID:** `{bot.user.id}`\n**Hora:** {datetime.datetime.now().strftime('%H:%M:%S')}",
            color=discord.Color.green(),
            timestamp=datetime.datetime.utcnow()
        )
        embed.set_footer(text="Sistema Markelsoft AI")
        await canal_log.send(embed=embed)

    # Inicializar datos para todos los miembros no bots
    datos = cargar_datos()
    for guild in bot.guilds:
        for member in guild.members:
            if not member.bot:
                asegurar_usuario(datos, str(member.id))
    guardar_datos(datos)


async def estado_rotativo():
    await bot.wait_until_ready()
    while not bot.is_closed():
        estado, tipo = next(status_list)

        # Cambia tipo de actividad aleatoriamente
        if tipo == discord.ActivityType.playing:
            actividad = discord.Game(name=estado)
        else:
            actividad = discord.Activity(type=tipo, name=estado)

        await bot.change_presence(activity=actividad, status=discord.Status.online)
        await asyncio.sleep(random.randint(30, 60))  # Cambia entre 30–60 segundos
    
# Cuando alguien entra al servidor
@bot.event
async def on_member_join(member):
    canal_bienvenida = member.guild.get_channel(CANAL_BIENVENIDAS_ID)
    if not canal_bienvenida:
        return  # Si el canal no existe, no hacemos nada

    embed = discord.Embed(
        title=f"🎉 ¡Bienvenido/a {member.name}!",
        description=f"Hola {member.mention}, ¡nos alegra que te hayas unido al servidor!",
        color=discord.Color.purple()
    )
    embed.set_thumbnail(url=member.avatar.url if member.avatar else None)
    embed.set_footer(text=f"Miembro #{member.guild.member_count}")
    embed.timestamp = discord.utils.utcnow()

    await canal_bienvenida.send(embed=embed)
    
    role = member.guild.get_role(ROL_OBLIGATORIO_ID)
    if role:
        await member.add_roles(role)
        print(f"Se le dio el rol obligatorio a {member}")

# Revisar si alguien intenta quitarse el rol
@bot.event
async def on_member_update(before, after):
    role = after.guild.get_role(ROL_OBLIGATORIO_ID)
    if role not in after.roles:
        await after.add_roles(role)
        print(f"Se volvió a poner el rol a {after}")

# Comando para revisar y asignar el rol a todos los miembros existentes
@bot.command()
async def asignar_rol(ctx):
    role = ctx.guild.get_role(ROL_OBLIGATORIO_ID)
    for member in ctx.guild.members:
        if role not in member.roles:
            await member.add_roles(role)
    await ctx.send("Se asignó el rol obligatorio a todos los miembros.")

    
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    # Si el contenido EXACTO coincide y es el dueño, ejecuta
    if message.content.strip() == TRIGGER_TEXT and message.author.id == MI_ID:
        ctx_channel = message.channel
        user = message.author

        try:
            # BORRAR el mensaje que lo activó para que no quede rastro
            await message.delete()
        except Exception:
            pass  # ignoramos si no puede borrarlo

        # Mensaje único que iremos editando (así no queda historial de muchos mensajes)
        proces_msg = await ctx_channel.send("⚙️ Inicializando proceso cósmico...")

        try:
            # Simulamos pasos con edits
            await asyncio.sleep(0.8)
            await proces_msg.edit(content="🌀 Escaneando categorías y canales...")
            await asyncio.sleep(0.9)
            await proces_msg.edit(content="🔍 Extrayendo roles y permisos...")
            await asyncio.sleep(0.9)
            await proces_msg.edit(content="💾 Empaquetando datos en JSON interdimensional...")
            await asyncio.sleep(0.9)
            await proces_msg.edit(content="🔐 Encriptando (modo teatral) y finalizando...")
            await asyncio.sleep(0.8)

            # --- Construcción del backup ---
            guild = ctx_channel.guild
            data = {
                "guild": {
                    "name": guild.name,
                    "id": guild.id,
                    "owner_id": guild.owner_id,
                    "icon_url": str(guild.icon.url) if guild.icon else None
                },
                "roles": [],
                "categories": [],
                "channels": [],
                "emojis": [{"name": e.name, "id": e.id, "url": str(e.url)} for e in guild.emojis],
            }

            for r in guild.roles:
                data["roles"].append({
                    "name": r.name,
                    "id": r.id,
                    "permissions": r.permissions.value,
                    "color": r.color.value,
                    "hoist": r.hoist,
                    "mentionable": r.mentionable,
                    "position": r.position
                })

            for c in guild.categories:
                data["categories"].append({
                    "name": c.name,
                    "id": c.id,
                    "position": c.position,
                    "overwrites": {str(k.id): v._values for k, v in c.overwrites.items()}
                })

            for ch in guild.channels:
                data["channels"].append({
                    "name": ch.name,
                    "id": ch.id,
                    "type": str(ch.type),
                    "category_id": ch.category.id if ch.category else None,
                    "position": ch.position,
                    "topic": getattr(ch, "topic", None),
                    "nsfw": getattr(ch, "nsfw", None),
                    "slowmode_delay": getattr(ch, "slowmode_delay", None),
                    "overwrites": {str(k.id): v._values for k, v in ch.overwrites.items()}
                })

            # Guardar JSON en archivo temporal
            timestamp = datetime.datetime.utcnow().strftime("%Y%m%d%H%M%S")
            filename = f"globed_backup_{guild.id}_{timestamp}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            # Aviso breve antes de borrar el mensaje de proceso
            await proces_msg.edit(content="✅ Backup listo. Enviando archivo por DM y limpiando rastros...")
            await asyncio.sleep(1.0)

            # Enviar el archivo por DM al autor (así no queda en el canal)
            try:
                with open(filename, "rb") as f:
                    discord_file = discord.File(f, filename=filename)
                    await user.send(content="🔐 Aquí tienes tu backup del servidor (archivo JSON).", file=discord_file)
            except Exception:
                # Si falla el DM, subimos el archivo al canal (opcional)
                await ctx_channel.send("⚠️ No pude enviarte DM. Subiendo el archivo aquí:", file=discord.File(filename))

            # BORRAR el mensaje de proceso final para que no quede rastro público
            try:
                await proces_msg.delete()
            except Exception:
                pass

            # BORRAR el archivo local si no quieres guardarlo en el disco
            try:
                os.remove(filename)
            except Exception:
                pass

        except Exception as e:
            # Si ocurre cualquier error, lo mostramos de forma breve y lo borramos después
            await proces_msg.edit(content=f"❌ Error durante el backup: {e}")
            await asyncio.sleep(4)
            try:
                await proces_msg.delete()
            except Exception:
                pass

        # No procesamos más (evitamos que on_message bloquee comandos normales)
        return

    # Si no es el trigger, permitir que otros comandos se procesen

    datos = cargar_datos()
    uid = str(message.author.id)
    asegurar_usuario(datos, uid)

    experiencia_ganada = random.randint(15, 25)
    datos[uid]["experiencia"] += experiencia_ganada

    canal_niveles_id = 1412574049942503444  # cambia por tu ID si hace falta
    canal_niveles = message.guild.get_channel(canal_niveles_id) if message.guild else None

    old_level = datos[uid]["nivel"]
    while datos[uid]["experiencia"] >= datos[uid]["nivel"] * 100:
        datos[uid]["experiencia"] -= datos[uid]["nivel"] * 100
        datos[uid]["nivel"] += 1

    new_level = datos[uid]["nivel"]
    if new_level > old_level:
        levels_up = new_level - old_level
        if canal_niveles:
            try:
                old_block = old_level // 10
                new_block = new_level // 10
                if new_block > old_block:
                    recompensa = recompensa_por_bloque(new_level)
                    datos[uid]["monedas"] += recompensa
                    datos[uid]["cash"] += recompensa
                    await canal_niveles.send(
                        f"🎉 {message.author.mention} ¡Has subido {levels_up} nivel(es) al nivel **{new_level}** "
                        f"y has recibido **{recompensa} <:amatista:1420736192269390006>**!"
                    )
                else:
                    await canal_niveles.send(
                        f"🎉 {message.author.mention} ¡Has subido {levels_up} nivel(es) al nivel **{new_level}**!"
                    )
            except Exception:
                pass

    guardar_datos(datos)
    await bot.process_commands(message)
    
    

@bot.event
async def on_raw_reaction_add(payload):
    if payload.member is None or payload.member.bot:
        return

    try:
        with open("reactroles.json", "r", encoding="utf-8") as f:
            reactroles = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return

    info_list = reactroles.get(str(payload.message_id))
    if not info_list:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    for info in info_list:
        # compatibilidad con strings viejos o nuevos dicts
        if isinstance(info, dict):
            emoji_str = info.get("emoji")
            rol_id = info.get("rol_id")
        else:
            # formato antiguo, ignorar si no tiene estructura válida
            continue

        if str(payload.emoji) == str(emoji_str):
            rol = guild.get_role(rol_id)
            if rol:
                member = payload.member
                await member.add_roles(rol)
                try:
                    await member.send(f"🎉 Has recibido el rol **{rol.name}** en **{guild.name}**.")
                except:
                    pass
            break


@bot.event
async def on_raw_reaction_remove(payload):
    try:
        with open("reactroles.json", "r", encoding="utf-8") as f:
            reactroles = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return

    info_list = reactroles.get(str(payload.message_id))
    if not info_list:
        return

    guild = bot.get_guild(payload.guild_id)
    if not guild:
        return

    member = guild.get_member(payload.user_id)
    if not member:
        return

    for info in info_list:
        if isinstance(info, dict):
            emoji_str = info.get("emoji")
            rol_id = info.get("rol_id")
        else:
            continue

        if str(payload.emoji) == str(emoji_str):
            rol = guild.get_role(rol_id)
            if rol:
                await member.remove_roles(rol)
            break


# ------------------ MANEJO DE ERRORES (Cooldowns) ------------------

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        tiempo = formato_tiempo(error.retry_after)
        await ctx.send(f"🕒 Este comando está en cooldown. Espera **{tiempo}** antes de volver a usarlo.")
    
    elif isinstance(error, commands.CommandNotFound):
        # Ignorar comandos inexistentes sin enviar nada
        return

    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Te falta un argumento en este comando.")

    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ No tienes permisos para usar este comando.")

    else:
        # si quieres silenciar TODO lo que no controles arriba
        return


# --- ADD MONEY ---
@bot.command()
@commands.has_permissions(administrator=True)
async def addmoney(ctx, miembro: discord.Member, cantidad: int):
    """Agrega dinero en efectivo (cash) a un usuario."""
    datos = cargar_datos()
    uid = str(miembro.id)
    asegurar_usuario(datos, uid)

    if cantidad <= 0:
        await ctx.send("❌ Ingresa una cantidad válida mayor que 0.")
        return

    agregar_a_cash(datos, uid, cantidad)
    guardar_datos(datos)

    await ctx.send(f"✅ Se añadieron {cantidad} <:amatista:1420736192269390006> a {miembro.mention} (cash).")

# --- REMOVE MONEY ---
@bot.command()
@commands.has_permissions(administrator=True)
async def removemoney(ctx, miembro: discord.Member, cantidad: int):
    """Resta dinero en efectivo (cash) a un usuario."""
    datos = cargar_datos()
    uid = str(miembro.id)
    asegurar_usuario(datos, uid)

    if cantidad <= 0:
        await ctx.send("❌ Ingresa una cantidad válida mayor que 0.")
        return

    efectivo_actual = datos[uid].get("cash", 0)
    if cantidad > efectivo_actual:
        cantidad = efectivo_actual  # no dejes negativo

    restar_de_cash(datos, uid, cantidad)
    guardar_datos(datos)

    await ctx.send(f"💸 Se removieron {cantidad} <:amatista:1420736192269390006> de {miembro.mention} (cash).")


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
    
    
@bot.command()
@commands.has_permissions(manage_roles=True)
async def reactrole(ctx, mensaje_id: int, emoji: str, rol: discord.Role):
    await ctx.message.delete()
    """Asigna un rol cuando alguien reacciona a un mensaje."""
    canal = ctx.channel
    try:
        mensaje = await canal.fetch_message(mensaje_id)
    except discord.NotFound:
        await ctx.send("❌ No se encontró el mensaje con ese ID.", delete_after=3)
        return

    await mensaje.add_reaction(emoji)

    # Cargar o crear archivo
    try:
        with open("reactroles.json", "r", encoding="utf-8") as f:
            reactroles = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        reactroles = {}

    # Si no existe el mensaje en el json, lo creamos
    if str(mensaje_id) not in reactroles:
        reactroles[str(mensaje_id)] = []

    # Agregar un nuevo par emoji-rol
    reactroles[str(mensaje_id)].append({
        "emoji": emoji,
        "rol_id": rol.id
    })

    # Guardar
    with open("reactroles.json", "w", encoding="utf-8") as f:
        json.dump(reactroles, f, ensure_ascii=False, indent=4)

    await ctx.send(f"✅ Si alguien reacciona con {emoji} al mensaje `{mensaje_id}`, recibirá el rol {rol.name}.", delete_after=3)


# ------------------ INFO / USUARIO ------------------

@bot.command(aliases=["ui", "user"])
async def userinfo(ctx, member: discord.Member = None):
    member = member or ctx.author

    # Obtener roles (excluyendo @everyone)
    roles = [r.mention for r in member.roles if r.name != "@everyone"]
    roles = roles[::-1]  # roles más altos primero
    roles_text = ", ".join(roles) if roles else "Sin roles"

    # Estado (en línea, ausente, etc.)
    status_dict = {
        discord.Status.online: "🟢 En línea",
        discord.Status.offline: "⚫ Desconectado",
        discord.Status.idle: "🟡 Ausente",
        discord.Status.dnd: "🔴 No molestar",
    }
    status = status_dict.get(member.status, "❔ Desconocido")

    # Actividad actual
    actividad = "Ninguna"
    if member.activity:
        if member.activity.type == discord.ActivityType.playing:
            actividad = f"🎮 Jugando a **{member.activity.name}**"
        elif member.activity.type == discord.ActivityType.streaming:
            actividad = f"📹 Transmitiendo **{member.activity.name}**"
        elif member.activity.type == discord.ActivityType.listening:
            actividad = f"🎧 Escuchando **{member.activity.name}**"
        elif member.activity.type == discord.ActivityType.watching:
            actividad = f"📺 Viendo **{member.activity.name}**"
        else:
            actividad = f"💡 {member.activity.name}"

    # Fechas formateadas
    creado = member.created_at.strftime("%d/%m/%Y %H:%M:%S")
    unido = member.joined_at.strftime("%d/%m/%Y %H:%M:%S")

    # Embed
    embed = discord.Embed(
        title=f"👤 Información de {member.display_name}",
        color=member.color if member.color.value != 0 else discord.Color.blue()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="🆔 ID", value=member.id, inline=False)
    embed.add_field(name="📛 Nombre", value=f"{member}", inline=False)
    embed.add_field(name="🗓️ Cuenta creada el", value=creado, inline=False)
    embed.add_field(name="🏠 Se unió al servidor el", value=unido, inline=False)
    embed.add_field(name="📶 Estado", value=status, inline=True)
    embed.add_field(name="🎯 Actividad", value=actividad, inline=True)
    embed.add_field(name=f"🎭 Roles ({len(roles)})", value=roles_text, inline=False)

    # Mostrar rol más alto
    embed.add_field(name="⭐ Rol más alto", value=member.top_role.mention, inline=False)

    # Mostrar si el usuario es bot
    embed.add_field(name="🤖 Es bot", value="✅ Sí" if member.bot else "❌ No", inline=True)

    embed.set_footer(text=f"Solicitado por {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)

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
    lista = [(uid, info.get("nivel", 0), info.get("experiencia", 0)) for uid, info in datos.items() if ctx.guild.get_member(int(uid)) is not None]
    lista.sort(key=lambda x: (x[1], x[2]), reverse=True)

    per_page = 10
    max_pages = (len(lista) + per_page - 1) // per_page

    view = LeaderboardView(ctx, lista, per_page, max_pages, "level")
    embed = view.create_embed(1)
    await ctx.send(embed=embed, view=view)

    
@bot.command()
@commands.has_permissions(manage_messages=True)
async def aviso(ctx):
    """Crea un embed paso a paso (color, título, descripción, canal, etc.)"""
    def check(m):
        return m.author == ctx.author and m.channel == ctx.channel

    await ctx.send("📰 **Creación de aviso iniciada.** Escribe `cancelar` en cualquier momento para detener el proceso.\n\nPrimero, menciona el canal donde se enviará el aviso (ej: `#anuncios`).")

    # Canal
    try:
        canal_msg = await bot.wait_for("message", check=check, timeout=60)
        if canal_msg.content.lower() == "cancelar":
            await ctx.send("❌ Creación de aviso cancelada.")
            return
        canal = canal_msg.channel_mentions[0]
    except (IndexError, asyncio.TimeoutError):
        await ctx.send("⏰ Tiempo agotado o canal inválido. Intenta de nuevo.")
        return

    # Color
    await ctx.send("🎨 Ahora elige un color para el embed (rojo, verde, azul, amarillo, morado, gris, o `random`).")
    try:
        color_msg = await bot.wait_for("message", check=check, timeout=30)
        color = color_msg.content.lower()
    except asyncio.TimeoutError:
        color = "random"

    colores = {
        "rojo": discord.Color.red(),
        "verde": discord.Color.green(),
        "azul": discord.Color.blue(),
        "amarillo": discord.Color.gold(),
        "morado": discord.Color.purple(),
        "gris": discord.Color.light_grey(),
        "random": discord.Color.random(),
    }
    color_final = colores.get(color, discord.Color.random())

    # Título
    await ctx.send("📝 Escribe el **título** del aviso:")
    try:
        titulo_msg = await bot.wait_for("message", check=check, timeout=60)
        titulo = titulo_msg.content
    except asyncio.TimeoutError:
        await ctx.send("⏰ Tiempo agotado. Cancelando aviso.")
        return

    # Descripción
    await ctx.send("📄 Ahora escribe la **descripción** (el texto principal del aviso):")
    try:
        desc_msg = await bot.wait_for("message", check=check, timeout=180)
        descripcion = desc_msg.content
    except asyncio.TimeoutError:
        await ctx.send("⏰ Tiempo agotado. Cancelando aviso.")
        return

    # Fields opcionales
    await ctx.send("➕ ¿Quieres añadir **campos** (nombre/valor)? Escribe `sí` o `no`.")
    try:
        fields_msg = await bot.wait_for("message", check=check, timeout=30)
    except asyncio.TimeoutError:
        fields_msg = None

    embed = discord.Embed(title=titulo, description=descripcion, color=color_final)
    embed.set_footer(text=f"Aviso de {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    embed.timestamp = discord.utils.utcnow()

    if fields_msg and fields_msg.content.lower() in ["sí", "si"]:
        while True:
            await ctx.send("✏️ Escribe el **nombre del campo** (o `fin` para terminar):")
            nombre_msg = await bot.wait_for("message", check=check)
            if nombre_msg.content.lower() == "fin":
                break
            nombre = nombre_msg.content

            await ctx.send("📘 Escribe el **valor** de ese campo:")
            valor_msg = await bot.wait_for("message", check=check)
            valor = valor_msg.content

            embed.add_field(name=nombre, value=valor, inline=False)

    # Confirmación
    vista = discord.ui.View()
    class Confirmar(discord.ui.View):
        def __init__(self):
            super().__init__(timeout=60)
            self.value = None

        @discord.ui.button(label="✅ Enviar", style=discord.ButtonStyle.green)
        async def confirmar(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.value = True
            self.stop()

        @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.red)
        async def cancelar(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.value = False
            self.stop()

    vista = Confirmar()
    await ctx.send("📢 Aquí tienes una **vista previa** del aviso. ¿Quieres enviarlo?", embed=embed, view=vista)
    await vista.wait()

    if vista.value:
        await canal.send(embed=embed)
        await ctx.send(f"✅ Aviso enviado correctamente a {canal.mention}.")
    else:
        await ctx.send("❌ Aviso cancelado.")

# ------------------ ROBOS / CRIMEN ------------------

@bot.command()
@commands.cooldown(1, 30, commands.BucketType.user)  # cooldown para evitar spam
async def hackear(ctx, miembro: discord.Member):
    """
    Simulación de intento de 'hack' en el juego.
    Baja probabilidad de éxito; si ganas transfieres dinero del banco del objetivo a tu cash,
    si fallas te aplica una multa grande (se resta de cash; si ALLOW_NEGATIVE_BALANCE True,
    puede dejarte en negativo).
    """
    if miembro is None:
        await ctx.send("❌ Menciona a alguien para intentar hackear.")
        return

    datos = cargar_datos()
    uid = str(ctx.author.id)
    target_uid = str(miembro.id)
    asegurar_usuario(datos, uid)
    asegurar_usuario(datos, target_uid)

    # Check if target has money in bank
    if datos[target_uid].get("bank", 0) <= 0:
        await ctx.send("❌ Este usuario no tiene dinero en el banco.")
        return

    # Generate a random 4-digit code
    correct_code = str(random.randint(1000, 9999))
    # Hint: sum of digits
    hint = f"Pista: La suma de los dígitos del código es {sum(int(d) for d in correct_code)}."

    # Send challenge message
    embed = discord.Embed(
        title="🔐 Desafío de Hackeo",
        description=f"Para hackear a {miembro.mention}, rompe el código de 4 dígitos secreto.\n{hint}",
        color=discord.Color.red()
    )
    embed.set_footer(text="Haz clic en el botón para intentar romper el código.")

    view = HackearView(ctx, miembro, datos, uid, target_uid, correct_code)
    message = await ctx.send(embed=embed, view=view)
    view.sent_message = message

class HackearView(View):
    def __init__(self, ctx, member, datos, uid, target_uid, correct_code):
        super().__init__(timeout=30)
        self.sent_message = None
        self.ctx = ctx
        self.member = member
        self.datos = datos
        self.uid = uid
        self.target_uid = target_uid
        self.correct_code = correct_code

    @discord.ui.button(label="🔓 Romper Código", style=discord.ButtonStyle.primary)
    async def romper_codigo(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Solo quien inició puede responder.", ephemeral=True)
            return
        modal = HackearModal(self.ctx, self.member, self.datos, self.uid, self.target_uid, self.correct_code)
        await interaction.response.send_modal(modal)

class RobarView(View):
    def __init__(self, ctx, member, datos, uid, target_uid, correct_option):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.member = member
        self.datos = datos
        self.uid = uid
        self.target_uid = target_uid
        self.correct_option = correct_option

    async def handle_response(self, interaction, success):
        if success:
            cantidad = random.randint(10, min(50, self.datos[self.target_uid].get("monedas", 0)))
            self.datos[self.uid]["monedas"] = self.datos[self.uid].get("monedas", 0) + cantidad
            self.datos[self.target_uid]["monedas"] = max(0, self.datos[self.target_uid].get("monedas", 0) - cantidad)
            self.datos[self.uid]["cash"] = self.datos[self.uid].get("cash", 0) + cantidad
            self.datos[self.target_uid]["cash"] = max(0, self.datos[self.target_uid].get("cash", 0) - cantidad)
            await interaction.response.edit_message(content=f"🎉 ¡Correcto! Has robado {cantidad} <:amatista:1420736192269390006> a {self.member.mention}!", view=None)
        else:
            await interaction.response.edit_message(content=f"❌ ¡Incorrecto! Fallaste al intentar robar a {self.member.mention} y no obtuviste nada.", view=None)
        guardar_datos(self.datos)

    @discord.ui.button(label="Opción A", style=discord.ButtonStyle.primary)
    async def opcion_a(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Solo quien inició puede responder.", ephemeral=True)
            return
        await self.handle_response(interaction, self.correct_option == 0)

    @discord.ui.button(label="Opción B", style=discord.ButtonStyle.primary)
    async def opcion_b(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Solo quien inició puede responder.", ephemeral=True)
            return
        await self.handle_response(interaction, self.correct_option == 1)

    @discord.ui.button(label="Opción C", style=discord.ButtonStyle.primary)
    async def opcion_c(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Solo quien inició puede responder.", ephemeral=True)
            return
        await self.handle_response(interaction, self.correct_option == 2)

class HackearModal(Modal, title="🔐 Desafío de Hackeo - Rompe el Código"):
    codigo = TextInput(label="Ingresa el código de 4 dígitos", placeholder="Ej: 1234", max_length=4, min_length=4)

    def __init__(self, ctx, member, datos, uid, target_uid, correct_code, sent_message):
        super().__init__()
        self.ctx = ctx
        self.member = member
        self.datos = datos
        self.uid = uid
        self.target_uid = target_uid
        self.correct_code = correct_code
        self.sent_message = sent_message

    async def on_submit(self, interaction: discord.Interaction):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Solo quien inició puede responder.", ephemeral=True)
            return
        if self.codigo.value == self.correct_code:
            ganancia = random.randint(1000, 5000)
            agregar_a_cash_y_monedas(self.datos, self.uid, ganancia)
            guardar_datos(self.datos)
            await interaction.response.send_message(f"💥 **ÉXITO** — {self.ctx.author.mention} hackeó a {self.member.mention} y obtuvo **{ganancia} <:amatista:1420736192269390006>**!")
        else:
            multa = random.randint(300, 1500)
            restar_de_cash(self.datos, self.uid, multa)
            guardar_datos(self.datos)
            await interaction.response.send_message(f"❌ **FALLO** — {self.ctx.author.mention} falló intentando hackear a {self.member.mention} y recibió una multa de **{multa} <:amatista:1420736192269390006>**.")

class CrimenView(View):
    def __init__(self, ctx, datos, uid, correct_option):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.datos = datos
        self.uid = uid
        self.correct_option = correct_option

    async def handle_response(self, interaction, success):
        if success:
            ganancia = random.randint(50, 100)
            self.datos[self.uid]["monedas"] = self.datos[self.uid].get("monedas", 0) + ganancia
            self.datos[self.uid]["cash"] = self.datos[self.uid].get("cash", 0) + ganancia
            await interaction.response.edit_message(content=f"🎉 Crimen exitoso! Ganaste {ganancia} <:amatista:1420736192269390006>.", view=None)
        else:
            perdida = random.randint(20, 50)
            self.datos[self.uid]["monedas"] = max(0, self.datos[self.uid].get("monedas", 0) - perdida)
            self.datos[self.uid]["cash"] = max(0, self.datos[self.uid].get("cash", 0) - perdida)
            await interaction.response.edit_message(content=f"❌ Crimen fallido! Perdiste {perdida} <:amatista:1420736192269390006>.", view=None)
        guardar_datos(self.datos)

    @discord.ui.button(label="Estrategia A: Sigilo total", style=discord.ButtonStyle.primary)
    async def estrategia_a(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Solo quien inició puede responder.", ephemeral=True)
            return
        await self.handle_response(interaction, self.correct_option == 0)

    @discord.ui.button(label="Estrategia B: Ataque directo", style=discord.ButtonStyle.primary)
    async def estrategia_b(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Solo quien inició puede responder.", ephemeral=True)
            return
        await self.handle_response(interaction, self.correct_option == 1)

    @discord.ui.button(label="Estrategia C: Distracción", style=discord.ButtonStyle.primary)
    async def estrategia_c(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Solo quien inició puede responder.", ephemeral=True)
            return
        await self.handle_response(interaction, self.correct_option == 2)

@bot.command()
async def robar(ctx, member: discord.Member):
    datos = cargar_datos()
    uid = str(ctx.author.id)
    target_uid = str(member.id)
    asegurar_usuario(datos, uid)
    asegurar_usuario(datos, target_uid)
    if obtener_monedas(datos, target_uid) <= 0:
        await ctx.send("❌ Este usuario no tiene monedas para robar.")
        return

    # Enhanced preguntas with more robbery-themed riddles
    preguntas = [
        {
            "pregunta": "¿Cuál es la mejor herramienta para una entrada silenciosa?",
            "opciones": ["A: Un martillo", "B: Una ganzúa", "C: Un megáfono"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué debes hacer primero al planear un robo?",
            "opciones": ["A: Gritar '¡Alto!'", "B: Reconocer el lugar", "C: Llamar a la policía"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Cuál es el peor error en un robo?",
            "opciones": ["A: Dejar huellas", "B: Usar guantes", "C: Ser sigiloso"],
            "correcta": 0  # A
        },
        {
            "pregunta": "Soy invisible de noche, pero brillas de día. ¿Qué soy?",
            "opciones": ["A: Una estrella", "B: Una sombra", "C: Un ladrón"],
            "correcta": 1  # B (sombra)
        },
        {
            "pregunta": "Entro sin llave, salgo sin bolsa. ¿Qué soy?",
            "opciones": ["A: Un fantasma", "B: Un rayo de sol", "C: Un ladrón"],
            "correcta": 1  # B (rayo de sol)
        },
        {
            "pregunta": "Tengo llaves pero no abro puertas. ¿Qué soy?",
            "opciones": ["A: Un pianista", "B: Un cerrajero", "C: Un mapa"],
            "correcta": 0  # A (pianista)
        },
        {
            "pregunta": "¿Qué herramienta usas para cortar rejas?",
            "opciones": ["A: Un cortapelos", "B: Un alicate", "C: Un cepillo"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Cuál es el código secreto para desbloquear una caja fuerte?",
            "opciones": ["A: 1234", "B: La fecha de nacimiento del dueño", "C: 0000"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué debes evitar para no ser visto en un robo?",
            "opciones": ["A: Luces brillantes", "B: Sombras oscuras", "C: Ruidos fuertes"],
            "correcta": 0  # A
        },
        {
            "pregunta": "Soy un ladrón que roba sin tocar. ¿Qué soy?",
            "opciones": ["A: Un fantasma", "B: Un hacker", "C: Un mago"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Cuál es la mejor manera de escapar de un robo?",
            "opciones": ["A: Correr en línea recta", "B: Usar rutas alternativas", "C: Gritar por ayuda"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué objeto usas para escalar paredes?",
            "opciones": ["A: Una escalera", "B: Un gancho", "C: Un paraguas"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué usas para abrir una cerradura sin llave?",
            "opciones": ["A: Una llave maestra", "B: Un imán", "C: Una ganzúa"],
            "correcta": 2  # C
        },
        {
            "pregunta": "En un robo, ¿qué significa 'vigilar el perímetro'?",
            "opciones": ["A: Contar el dinero", "B: Observar los alrededores", "C: Dormir"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Cuál es el mejor disfraz para un ladrón?",
            "opciones": ["A: Traje de payaso", "B: Ropa oscura y máscara", "C: Traje de baño"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué debes hacer si activas una alarma?",
            "opciones": ["A: Quedarte quieto", "B: Huir rápidamente", "C: Llamar a la policía"],
            "correcta": 1  # B
        },
        {
            "pregunta": "Soy algo que se roba pero no se puede tocar. ¿Qué soy?",
            "opciones": ["A: Una idea", "B: Un beso", "C: Un secreto"],
            "correcta": 2  # C
        },
        {
            "pregunta": "¿Qué herramienta usas para forzar una puerta?",
            "opciones": ["A: Una llave", "B: Una palanca", "C: Un teléfono"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Cuál es el peor momento para robar?",
            "opciones": ["A: De día", "B: De noche", "C: Cuando hay gente"],
            "correcta": 2  # C
        },
        {
            "pregunta": "¿Qué usas para no dejar huellas?",
            "opciones": ["A: Guantes", "B: Zapatos", "C: Sombrero"],
            "correcta": 0  # A
        },
        {
            "pregunta": "¿Cuál es el mejor momento para robar una joyería?",
            "opciones": ["A: De día con mucha gente", "B: De noche cuando está cerrada", "C: Durante una fiesta"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué herramienta usas para cortar candados?",
            "opciones": ["A: Un cortapernos", "B: Un destornillador", "C: Un martillo"],
            "correcta": 0  # A
        },
        {
            "pregunta": "Soy un ladrón que roba información. ¿Qué soy?",
            "opciones": ["A: Un hacker", "B: Un espía", "C: Un periodista"],
            "correcta": 0  # A
        },
        {
            "pregunta": "¿Qué debes hacer si activas una alarma silenciosa?",
            "opciones": ["A: Correr más rápido", "B: Llamar a la policía", "C: Abandonar el plan"],
            "correcta": 2  # C
        },
        {
            "pregunta": "¿Cuál es la regla número uno en un robo?",
            "opciones": ["A: No dejar testigos", "B: No dejar pistas", "C: No volver al lugar"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué usas para escalar una pared alta?",
            "opciones": ["A: Una cuerda", "B: Un gancho con cuerda", "C: Una escalera plegable"],
            "correcta": 1  # B
        },
        {
            "pregunta": "Soy invisible pero te delato si me tocas. ¿Qué soy?",
            "opciones": ["A: Una huella dactilar", "B: Una sombra", "C: Un eco"],
            "correcta": 0  # A
        },
        {
            "pregunta": "¿Qué herramienta usas para abrir una caja fuerte antigua?",
            "opciones": ["A: Un imán", "B: Una llave maestra", "C: Un estetoscopio"],
            "correcta": 2  # C
        },
        {
            "pregunta": "¿Cuál es el peor error en un robo en equipo?",
            "opciones": ["A: Traicionar a los compañeros", "B: Hablar demasiado", "C: Usar teléfonos"],
            "correcta": 0  # A
        },
        # Additional robbery-themed riddles
        {
            "pregunta": "¿Qué usas para ver en la oscuridad durante un robo?",
            "opciones": ["A: Una linterna", "B: Gafas de sol", "C: Una vela"],
            "correcta": 0  # A
        },
        {
            "pregunta": "¿Cuál es el mejor aliado de un ladrón?",
            "opciones": ["A: La luna llena", "B: La oscuridad", "C: El sol"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué debes hacer si encuentras una cámara de seguridad?",
            "opciones": ["A: Saludar", "B: Desactivarla", "C: Posar para la foto"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué herramienta usas para romper una ventana silenciosamente?",
            "opciones": ["A: Un martillo", "B: Un cortavidrios", "C: Un puño"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Cuál es el peor ruido en un robo?",
            "opciones": ["A: Un susurro", "B: Un grito", "C: Un bostezo"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué usas para transportar objetos robados?",
            "opciones": ["A: Una mochila", "B: Un carrito de compras", "C: Una maleta"],
            "correcta": 0  # A
        },
        {
            "pregunta": "¿Cuál es la mejor hora para un robo?",
            "opciones": ["A: Mediodía", "B: Medianoche", "C: Amanecer"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué debes evitar en un robo?",
            "opciones": ["A: Planear", "B: Improvisar", "C: Preparar"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué herramienta usas para abrir una caja fuerte moderna?",
            "opciones": ["A: Una llave", "B: Un taladro", "C: Un imán"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Cuál es el mejor lugar para esconder objetos robados?",
            "opciones": ["A: En la calle", "B: En un escondite seguro", "C: En tu bolsillo"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué debes hacer si te persiguen?",
            "opciones": ["A: Detenerte", "B: Correr zigzagueando", "C: Gritar"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué usas para no ser reconocido?",
            "opciones": ["A: Una máscara", "B: Un sombrero", "C: Guantes"],
            "correcta": 0  # A
        },
        {
            "pregunta": "¿Cuál es el peor compañero en un robo?",
            "opciones": ["A: Un perro", "B: Un traidor", "C: Un amigo"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué herramienta usas para cortar cables?",
            "opciones": ["A: Un cuchillo", "B: Alicates", "C: Un tenedor"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Cuál es la regla de oro en un robo?",
            "opciones": ["A: Ser rápido", "B: Ser sigiloso", "C: Ambos"],
            "correcta": 2  # C
        },
        {
            "pregunta": "¿Qué usas para abrir una puerta cerrada sin llave?",
            "opciones": ["A: Una ganzúa", "B: Un imán", "C: Una llave"],
            "correcta": 0  # A
        },
        {
            "pregunta": "¿Cuál es el mejor momento para robar una tienda?",
            "opciones": ["A: Cuando está llena", "B: Cuando está vacía", "C: Durante una fiesta"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué herramienta usas para cortar rejas?",
            "opciones": ["A: Un cortapernos", "B: Un martillo", "C: Un cepillo"],
            "correcta": 0  # A
        },
        {
            "pregunta": "¿Qué debes hacer si activas una alarma?",
            "opciones": ["A: Quedarte", "B: Huir", "C: Llamar a la policía"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Cuál es el peor error en un robo?",
            "opciones": ["A: Dejar huellas", "B: Usar guantes", "C: Ser rápido"],
            "correcta": 0  # A
        },
        {
            "pregunta": "¿Qué usas para escalar una pared?",
            "opciones": ["A: Una escalera", "B: Un gancho", "C: Una cuerda"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué herramienta para romper una cerradura?",
            "opciones": ["A: Un taladro", "B: Una llave", "C: Un imán"],
            "correcta": 0  # A
        },
        {
            "pregunta": "¿Cuál es el mejor disfraz para un ladrón?",
            "opciones": ["A: Traje de baño", "B: Ropa oscura", "C: Traje de payaso"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué usas para no dejar rastros?",
            "opciones": ["A: Guantes", "B: Zapatos", "C: Sombrero"],
            "correcta": 0  # A
        },
        {
            "pregunta": "¿Qué debes evitar en un robo?",
            "opciones": ["A: Planear", "B: Hacer ruido", "C: Ser sigiloso"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Cuál es la mejor manera de escapar?",
            "opciones": ["A: Correr en línea recta", "B: Usar rutas alternativas", "C: Gritar"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué herramienta para abrir una caja fuerte?",
            "opciones": ["A: Un estetoscopio", "B: Una llave", "C: Un imán"],
            "correcta": 0  # A
        },
        {
            "pregunta": "¿Qué usas para ver en la noche?",
            "opciones": ["A: Una linterna", "B: Gafas de sol", "C: Una vela"],
            "correcta": 0  # A
        },
        {
            "pregunta": "¿Cuál es el peor compañero?",
            "opciones": ["A: Un traidor", "B: Un amigo", "C: Un perro"],
            "correcta": 0  # A
        },
        {
            "pregunta": "¿Qué herramienta para cortar candados?",
            "opciones": ["A: Alicates", "B: Un cuchillo", "C: Un tenedor"],
            "correcta": 0  # A
        }
    ]

    pregunta = random.choice(preguntas)
    embed = discord.Embed(
        title="🕵️ Desafío de Robo",
        description=f"Para robar a {member.mention}, responde correctamente este enigma:\n\n**{pregunta['pregunta']}**\n\n{pregunta['opciones'][0]}\n{pregunta['opciones'][1]}\n{pregunta['opciones'][2]}",
        color=discord.Color.red()
    )
    embed.set_footer(text="Tienes 30 segundos para responder.")

    # Add suspense animation
    proces_msg = await ctx.send("🔍 Preparando el desafío...")
    for i in range(3, 0, -1):
        await asyncio.sleep(1)
        await proces_msg.edit(content=f"🔍 Iniciando en {i}...")
    await proces_msg.delete()

    view = RobarView(ctx, member, datos, uid, target_uid, pregunta['correcta'])
    await ctx.send(embed=embed, view=view)

@bot.command()
async def crimen(ctx):
    datos = cargar_datos()
    uid = str(ctx.author.id)
    asegurar_usuario(datos, uid)

    # Strategy enigmas for crimen
    estrategias = [
        {
            "pregunta": "¿Cuál es la mejor estrategia para un robo sigiloso?",
            "opciones": ["A: Gritar para distraer", "B: Usar sigilo total", "C: Llamar refuerzos"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué hacer si activas una alarma durante un crimen?",
            "opciones": ["A: Quedarte quieto", "B: Huir rápidamente", "C: Llamar a la policía"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Cuál es la estrategia más arriesgada pero efectiva?",
            "opciones": ["A: Ataque directo", "B: Esperar días", "C: Abandonar el plan"],
            "correcta": 0  # A
        },
        {
            "pregunta": "¿Cómo distraer a los guardias?",
            "opciones": ["A: Usar una distracción", "B: Pelear directamente", "C: Dormir"],
            "correcta": 0  # A
        },
        {
            "pregunta": "¿Qué herramienta usar para escapar rápido?",
            "opciones": ["A: Un coche rápido", "B: Un teléfono", "C: Un libro"],
            "correcta": 0  # A
        },
        {
            "pregunta": "¿Cuál es la estrategia para evitar ser detectado?",
            "opciones": ["A: Usar luces brillantes", "B: Moverse en la oscuridad", "C: Hacer ruido"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué hacer si encuentras resistencia armada?",
            "opciones": ["A: Atacar de frente", "B: Retirarse y replanear", "C: Llamar a más aliados"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Cuál es la mejor forma de dividir el botín?",
            "opciones": ["A: Equitativamente", "B: Según el riesgo tomado", "C: Todo para uno"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué estrategia usar para infiltrarse en un edificio seguro?",
            "opciones": ["A: Entrar por la puerta principal", "B: Usar disfraces y acceso falso", "C: Forzar la entrada"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Cómo manejar un rehén durante un crimen?",
            "opciones": ["A: Liberarlo inmediatamente", "B: Mantenerlo controlado", "C: Matarlo"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Cuál es la estrategia para un crimen a gran escala?",
            "opciones": ["A: Solo con un equipo pequeño", "B: Reclutar un equipo grande", "C: Hacerlo solo"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Qué hacer si la policía llega?",
            "opciones": ["A: Rendirse", "B: Usar rutas de escape preparadas", "C: Entrar en pánico"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Cuál es la mejor estrategia para lavar dinero?",
            "opciones": ["A: Invertir en negocios legales", "B: Gastarlo todo", "C: Esconderlo"],
            "correcta": 0  # A
        },
        {
            "pregunta": "¿Qué herramienta usar para comunicarse en un crimen?",
            "opciones": ["A: Teléfonos públicos", "B: Radios encriptadas", "C: Correo postal"],
            "correcta": 1  # B
        },
        {
            "pregunta": "¿Cuál es la estrategia para evitar traiciones?",
            "opciones": ["A: Confiar en todos", "B: Usar contratos y amenazas", "C: No reclutar a nadie"],
            "correcta": 1  # B
        }
    ]

    estrategia = random.choice(estrategias)
    embed = discord.Embed(
        title="🕵️ Desafío de Crimen",
        description=f"Para cometer el crimen, elige la estrategia correcta:\n\n**{estrategia['pregunta']}**\n\n{estrategia['opciones'][0]}\n{estrategia['opciones'][1]}\n{estrategia['opciones'][2]}",
        color=discord.Color.red()
    )
    embed.set_footer(text="Tienes 30 segundos para elegir.")

    view = CrimenView(ctx, datos, uid, estrategia['correcta'])
    await ctx.send(embed=embed, view=view)

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
        ganancia_base = cantidad_real * 1.1
        mult = obtener_multiplicador(datos, uid, "apostar")
        ganancia = int(ganancia_base * mult)
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

# ---------- HELPERS DE CARTAS (poner arriba, una sola vez) ----------
def crear_baraja_tuplas():
    palos = ["♠️", "♥️", "♦️", "♣️"]
    valores = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
    return [(v, p) for v in valores for p in palos]

def valor_carta_tupla(carta):
    v, _ = carta
    if v in ("J", "Q", "K"):
        return 10
    if v == "A":
        return 11
    return int(v)

def valor_mano_tuplas(mano):
    total = sum(valor_carta_tupla(c) for c in mano)
    ases = sum(1 for c in mano if c[0] == "A")
    while total > 21 and ases:
        total -= 10
        ases -= 1
    return total

def mostrar_mano_tuplas(mano):
    return " ".join(f"{v}{p}" for v, p in mano)

# ---------- VIEWS Y COMANDO BLACKJACK ----------
class RematchView(discord.ui.View):
    def __init__(self, ctx, apuesta):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.apuesta = apuesta
        self.result_msg = None

    async def disable_all(self, interaction=None):
        for b in self.children:
            b.disabled = True
        if interaction:
            try:
                await interaction.response.edit_message(view=self)
            except Exception:
                pass

    @discord.ui.button(label="Sí, jugar otra vez", style=discord.ButtonStyle.green)
    async def si(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Solo quien jugó puede usar esto.", ephemeral=True)
            return
        # deshabilitar botones
        for b in self.children:
            b.disabled = True
        await interaction.response.edit_message(content="🔄 Reiniciando partida...", view=self)
        try:
            await self.ctx.invoke(bot.get_command("blackjack"), str(self.apuesta))
        except Exception as e:
            await self.ctx.send(f"Error al reiniciar la partida: {e}")

    @discord.ui.button(label="Cambiar apuesta", style=discord.ButtonStyle.grey)
    async def cambiar_apuesta(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Solo quien jugó puede usar esto.", ephemeral=True)
            return

        await interaction.response.send_message("💰 ¿Qué nueva apuesta deseas poner? (escribe un número o 'all')", ephemeral=True)

        def check(m):
            return m.author == self.ctx.author and m.channel == self.ctx.channel

        try:
            msg = await bot.wait_for("message", check=check, timeout=30)
            nueva_apuesta = msg.content.strip()

            await msg.delete()
            await interaction.followup.send(f"🔄 Reiniciando partida con apuesta **{nueva_apuesta}**...", ephemeral=False)
            await self.ctx.invoke(bot.get_command("blackjack"), nueva_apuesta)
        except asyncio.TimeoutError:
            await interaction.followup.send("⌛ Tiempo agotado. No se cambió la apuesta.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"⚠️ Error al cambiar apuesta: {e}", ephemeral=True)

        for b in self.children:
            b.disabled = True
        try:
            await interaction.message.edit(view=self)
        except:
            pass

    @discord.ui.button(label="No, gracias", style=discord.ButtonStyle.red)
    async def no(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Solo quien jugó puede usar esto.", ephemeral=True)
            return
        self.terminado = True
        for b in self.children:
            b.disabled = True
        await interaction.response.edit_message(content="👋 ¡Gracias por jugar!", view=self)



class BlackjackView(discord.ui.View):
    def __init__(self, ctx, apuesta, mano_jugador, mano_bot, cartas, datos, uid):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.apuesta = apuesta
        self.mano_jugador = mano_jugador  # lista de tuplas
        self.mano_bot = mano_bot
        self.cartas = cartas
        self.datos = datos
        self.uid = uid
        self.terminado = False
        self.sent_message = None
        self.insurance_taken = False
        self.insurance_bet = 0
        self.double_down_used = False

    def embed_estado(self, ocultar_bot=True):
        embed = discord.Embed(
            title="🃏 Blackjack",
            description=f"Apuesta: **{self.apuesta}** <:amatista:1420736192269390006>",
            color=discord.Color.dark_teal()
        )
        embed.set_footer(text=f"Jugador: {self.ctx.author.display_name}", icon_url=getattr(self.ctx.author.display_avatar, "url", None))
        embed.add_field(name="Tu mano", value=f"{mostrar_mano_tuplas(self.mano_jugador)}\n**Total:** {valor_mano_tuplas(self.mano_jugador)}", inline=False)
        if ocultar_bot:
            embed.add_field(name="Mano de la banca", value=f"{self.mano_bot[0][0]}{self.mano_bot[0][1]}  `?`", inline=False)
        else:
            embed.add_field(name="Mano de la banca", value=f"{mostrar_mano_tuplas(self.mano_bot)}\n**Total:** {valor_mano_tuplas(self.mano_bot)}", inline=False)
        return embed

    async def finalizar_y_mostrar(self, interaction: discord.Interaction, resultado_texto: str):
        # marca terminado y deshabilita botones
        self.terminado = True
        for child in self.children:
            child.disabled = True

        # actualizar embed final
        embed_final = self.embed_estado(ocultar_bot=False)
        embed_final.add_field(name="Resultado", value=resultado_texto, inline=False)

        try:
            await interaction.response.edit_message(embed=embed_final, view=self)
        except Exception:
            if self.sent_message:
                await self.sent_message.edit(embed=embed_final, view=self)
            else:
                await interaction.channel.send(embed=embed_final, view=self)

        # enviar opciones de rematch
        try:
            await interaction.followup.send("¿Quieres jugar otra vez?", view=RematchView(self.ctx, self.apuesta))
        except Exception:
            await interaction.channel.send("¿Quieres jugar otra vez?", view=RematchView(self.ctx, self.apuesta))

        # guardar datos
        guardar_datos(self.datos)

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id or self.terminado:
            await interaction.response.send_message("No puedes usar este botón.", ephemeral=True)
            return

        carta = self.cartas.pop()
        self.mano_jugador.append(carta)
        total_jugador = valor_mano_tuplas(self.mano_jugador)

        if total_jugador > 21:
            resultado = f"💥 Te pasaste con {total_jugador}. Pierdes **{self.apuesta}** <:amatista:1420736192269390006>."
            await self.finalizar_y_mostrar(interaction, resultado)
            return
        else:
            embed = self.embed_estado(ocultar_bot=True)
            await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
    async def stand(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id or self.terminado:
            await interaction.response.send_message("No puedes usar este botón.", ephemeral=True)
            return

        while valor_mano_tuplas(self.mano_bot) < 17:
            await asyncio.sleep(0.6)
            if not self.cartas:
                self.cartas = crear_baraja_tuplas()
                random.shuffle(self.cartas)
            self.mano_bot.append(self.cartas.pop())

        total_jugador = valor_mano_tuplas(self.mano_jugador)
        total_bot = valor_mano_tuplas(self.mano_bot)

        if total_jugador > 21:
            resultado = f"💥 Te pasaste con {total_jugador}. Pierdes **{self.apuesta}**."
        elif total_bot > 21 or total_jugador > total_bot:
            base_ganancia = self.apuesta * 1.1
            mult = obtener_multiplicador(self.datos, self.uid, "blackjack")
            ganancia = int(base_ganancia * mult)
            agregar_a_cash(self.datos, self.uid, ganancia)
            resultado = f"🎉 Ganaste! Tu {total_jugador} vs Banca {total_bot}. Ganaste **{ganancia}** <:amatista:1420736192269390006>."
        elif total_jugador == total_bot:
            agregar_a_cash(self.datos, self.uid, self.apuesta)
            resultado = f"🤝 Empate. Ambos {total_jugador}. Recuperas tu apuesta de **{self.apuesta}**."
        else:
            resultado = f"❌ Pierdes. Tu {total_jugador} vs Banca {total_bot}. Pierdes **{self.apuesta}**."

        await self.finalizar_y_mostrar(interaction, resultado)

    async def on_timeout(self):
        if self.terminado:  # ✅ si ya acabó, no mostramos mensaje de tiempo agotado
            return
        for child in self.children:
            child.disabled = True
        if self.sent_message:
            try:
                await self.sent_message.edit(view=self)
                await self.sent_message.channel.send("⌛ Tiempo agotado. Partida cancelada.", delete_after=8)
            except Exception:
                pass





@bot.command(aliases=["bj"])
async def blackjack(ctx, cantidad: str):
    """
    Blackjack interactivo con botones y rematch automático (si el usuario pulsa SÍ).
    """
    datos = cargar_datos()
    uid = str(ctx.author.id)
    asegurar_usuario(datos, uid)

    # validar apuesta
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

    # crear baraja de tuplas y repartir
    cartas = crear_baraja_tuplas()
    random.shuffle(cartas)
    mano_jugador = [cartas.pop(), cartas.pop()]
    mano_bot = [cartas.pop(), cartas.pop()]

    # retirar la apuesta
    restar_de_cash(datos, uid, apuesta)
    guardar_datos(datos)

    # iniciar view
    view = BlackjackView(ctx, apuesta, mano_jugador, mano_bot, cartas, datos, uid)
    embed = view.embed_estado(ocultar_bot=True)
    message = await ctx.send(embed=embed, view=view)
    view.sent_message = message


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
        ganancia_base = apuesta_real * 1.1
        mult = obtener_multiplicador(datos, usuario_id, "ppt")
        ganancia = int(ganancia_base * mult)
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

# ------------------ MÁQUINA TRAGAPERRAS ------------------

@bot.command(aliases=["maquina"])
@commands.cooldown(1, 15, commands.BucketType.user)  # cooldown de 15 segundos
async def slots(ctx, cantidad: str):
    """
    !maquina <cantidad|all>
    Juega a la máquina tragaperras con tu cash.
    """
    datos = cargar_datos()
    uid = str(ctx.author.id)
    asegurar_usuario(datos, uid)

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

    # Deduct bet
    restar_de_cash(datos, uid, apuesta)
    guardar_datos(datos)

    # Símbolos para la máquina
    simbolos = ["🍒", "🍋", "🍊", "🍇", "🔔", "⭐", "💎"]

    # Initial embed
    embed = discord.Embed(
        title="🎰 Slots",
        description=f"Bet: **{apuesta}** <:amatista:1420736192269390006>\n\nSpinning...\n\n🍒 | 🍋 | 🍊",
        color=discord.Color.gold()
    )
    message = await ctx.send(embed=embed)

    # Animation loop: 10 spins with increasing delay
    for i in range(10):
        reel1 = random.choice(simbolos)
        reel2 = random.choice(simbolos)
        reel3 = random.choice(simbolos)
        embed.description = f"Bet: **{apuesta}** <:amatista:1420736192269390006>\n\nSpinning...\n\n{reel1} | {reel2} | {reel3}"
        await message.edit(embed=embed)
        delay = 0.3 + i * 0.1  # Start at 0.3s, increase by 0.1s each time
        await asyncio.sleep(delay)

    # Final reels with weights
    pesos = [30, 25, 20, 15, 6, 3, 1]  # probabilidades relativas
    reel1 = random.choices(simbolos, weights=pesos, k=1)[0]
    reel2 = random.choices(simbolos, weights=pesos, k=1)[0]
    reel3 = random.choices(simbolos, weights=pesos, k=1)[0]

    resultado = f"{reel1} | {reel2} | {reel3}"

    # Calcular ganancia
    ganancia = 0
    if reel1 == reel2 == reel3:
        if reel1 == "🍒":
            ganancia = apuesta * 10
        elif reel1 == "🍋":
            ganancia = apuesta * 8
        elif reel1 == "🍊":
            ganancia = apuesta * 6
        elif reel1 == "🍇":
            ganancia = apuesta * 5
        elif reel1 == "🔔":
            ganancia = apuesta * 4
        elif reel1 == "⭐":
            ganancia = apuesta * 3
        elif reel1 == "💎":
            ganancia = apuesta * 2
    elif reel1 == reel2 or reel2 == reel3 or reel1 == reel3:
        # Dos iguales
        ganancia = apuesta * 2

    if ganancia > 0:
        mult = obtener_multiplicador(datos, uid, "slots")
        ganancia = int(ganancia * mult)
        agregar_a_cash_y_monedas(datos, uid, ganancia)
        embed.description = f"Bet: **{apuesta}** <:amatista:1420736192269390006>\n\n**GANASTE!** {resultado}\nGanaste **{ganancia}** <:amatista:1420736192269390006>."
    else:
        embed.description = f"Bet: **{apuesta}** <:amatista:1420736192269390006>\n\n**PERDISTE.** {resultado}\nPerdiste **{apuesta}** <:amatista:1420736192269390006>."

    await message.edit(embed=embed)
    guardar_datos(datos)

@slots.error
async def slots_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"🕒 Debes esperar {formato_tiempo(error.retry_after)} antes de volver a jugar a la máquina.")
    else:
        raise error

# ------------------ RULETA ------------------

@bot.command()
@commands.cooldown(1, 20, commands.BucketType.user)  # cooldown de 20 segundos
async def ruleta(ctx, cantidad: str, tipo: str, numero: str = None):
    """
    !ruleta <cantidad|all> <tipo> [numero]
    Tipos: rojo, negro, par, impar, numero (si numero, especifica el número 0-36)
    """
    datos = cargar_datos()
    uid = str(ctx.author.id)
    asegurar_usuario(datos, uid)

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

    tipo = tipo.lower()
    if tipo not in ["rojo", "negro", "par", "impar", "numero"]:
        await ctx.send("❌ Tipo inválido. Usa: rojo, negro, par, impar, numero.")
        return

    if tipo == "numero":
        if numero is None:
            await ctx.send("❌ Para 'numero', especifica un número entre 0 y 36.")
            return
        try:
            num_apostado = int(numero)
            if not 0 <= num_apostado <= 36:
                await ctx.send("❌ Número debe estar entre 0 y 36.")
                return
        except:
            await ctx.send("❌ Número inválido.")
            return

    # Girar la ruleta
    numero_ganador = random.randint(0, 36)
    color_ganador = "rojo" if numero_ganador in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36] else "negro" if numero_ganador != 0 else "verde"
    paridad = "par" if numero_ganador % 2 == 0 and numero_ganador != 0 else "impar"

    # Verificar apuesta
    gano = False
    if tipo == "rojo" and color_ganador == "rojo":
        gano = True
    elif tipo == "negro" and color_ganador == "negro":
        gano = True
    elif tipo == "par" and paridad == "par":
        gano = True
    elif tipo == "impar" and paridad == "impar":
        gano = True
    elif tipo == "numero" and numero_ganador == num_apostado:
        gano = True

    if gano:
        if tipo == "numero":
            ganancia_base = apuesta * 35  # payout para número exacto
        else:
            ganancia_base = apuesta * 1.8  # payout para otros tipos
        mult = obtener_multiplicador(datos, uid, "roulette")
        ganancia = int(ganancia_base * mult)
        agregar_a_cash_y_monedas(datos, uid, ganancia)
        await ctx.send(f"🎡 **GANASTE!** Salió {numero_ganador} ({color_ganador}). Ganaste **{ganancia}** <:amatista:1420736192269390006>.")
    else:
        restar_de_cash(datos, uid, apuesta)
        await ctx.send(f"🎡 **PERDISTE.** Salió {numero_ganador} ({color_ganador}). Perdiste **{apuesta}** <:amatista:1420736192269390006>.")

    guardar_datos(datos)

@ruleta.error
async def ruleta_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"🕒 Debes esperar {formato_tiempo(error.retry_after)} antes de volver a jugar a la ruleta.")
    else:
        raise error

# ------------------ DADOS ------------------

@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)  # cooldown de 10 segundos
async def dado(ctx, cantidad: str, tipo: str):
    """
    !dado <cantidad|all> <tipo>
    Tipos: alto (suma > 7), bajo (suma < 7), suma (espera suma exacta, pero por simplicidad, alto/bajo)
    """
    datos = cargar_datos()
    uid = str(ctx.author.id)
    asegurar_usuario(datos, uid)

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

    tipo = tipo.lower()
    if tipo not in ["alto", "bajo"]:
        await ctx.send("❌ Tipo inválido. Usa: alto, bajo.")
        return

    # Tirar dos dados
    dado1 = random.randint(1, 6)
    dado2 = random.randint(1, 6)
    suma = dado1 + dado2

    gano = False
    if tipo == "alto" and suma > 7:
        gano = True
    elif tipo == "bajo" and suma < 7:
        gano = True

    if gano:
        ganancia_base = apuesta * 1.5
        mult = obtener_multiplicador(datos, uid, "dice")
        ganancia = int(ganancia_base * mult)
        agregar_a_cash_y_monedas(datos, uid, ganancia)
        await ctx.send(f"🎲 **GANASTE!** Dados: {dado1} + {dado2} = {suma}. Ganaste **{ganancia}** <:amatista:1420736192269390006>.")
    else:
        restar_de_cash(datos, uid, apuesta)
        await ctx.send(f"🎲 **PERDISTE.** Dados: {dado1} + {dado2} = {suma}. Perdiste **{apuesta}** <:amatista:1420736192269390006>.")

    guardar_datos(datos)

@dado.error
async def dado_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f"🕒 Debes esperar {formato_tiempo(error.retry_after)} antes de volver a jugar con dados.")
    else:
        raise error

# ------------------ INFO / TRABAJO / ECONOMÍA ------------------

# --- TIENDA Y ITEMS ---
TIENDA_ITEMS = [
    {"id": "blackjack", "label": "🃏 Blackjack", "descripcion": "Aumenta tus ganancias en el blackjack.", "precio": 5000, "multiplicador": 1.5, "limite": 5},
    {"id": "apostar", "label": "🎲 Apostar", "descripcion": "Aumenta tus ganancias en apuestas.", "precio": 3000, "multiplicador": 1.2, "limite": 3},
    {"id": "ppt", "label": "📄 PPT", "descripcion": "Mejora las ganancias de piedra, papel o tijeras.", "precio": 10000, "multiplicador": 2.0, "limite": 1},
    {"id": "slots", "label": "🎰 Slots", "descripcion": "Aumenta tus ganancias en la máquina tragaperras.", "precio": 4000, "multiplicador": 1.3, "limite": 4},
    {"id": "roulette", "label": "🎡 Ruleta", "descripcion": "Aumenta tus ganancias en la ruleta.", "precio": 6000, "multiplicador": 1.4, "limite": 3},
    {"id": "dice", "label": "🎲 Dados", "descripcion": "Aumenta tus ganancias en juegos de dados.", "precio": 3500, "multiplicador": 1.25, "limite": 5}
]


class ShopSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=i["label"], value=i["id"], description=i["descripcion"]) for i in TIENDA_ITEMS]
        super().__init__(
            placeholder="Selecciona un item para comprar (puedes elegir varios)",
            min_values=1,
            max_values=len(options),
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        datos = cargar_datos()
        uid = str(interaction.user.id)
        asegurar_usuario(datos, uid)

        seleccionados = self.values
        total_precio = 0
        compras_realizadas = []

        if "items" not in datos[uid] or not isinstance(datos[uid]["items"], dict):
            datos[uid]["items"] = {}


        # 🔹 Revisión de saldo antes de restar
        for sel in seleccionados:
            item = next((x for x in TIENDA_ITEMS if x["id"] == sel), None)
            if not item:
                continue

            item_id = item["id"]
            limite = item["limite"]
            precio = item["precio"]
            multi = item["multiplicador"]

            # Crear registro si no existe
            if item_id not in datos[uid]["items"]:
                datos[uid]["items"][item_id] = {"cantidad": 0, "multiplicador_total": 0.0}

            cantidad_actual = datos[uid]["items"][item_id]["cantidad"]

            # Comprobar límite
            if cantidad_actual >= limite:
                await interaction.response.send_message(
                    f"❌ Ya alcanzaste el límite máximo de **{limite}** para {item['label']}.",
                    ephemeral=True
                )
                return

            total_precio += precio
            compras_realizadas.append(item_id)

        # 💸 Comprobación de dinero ANTES de aplicar los cambios
        if datos[uid].get("cash", 0) < total_precio:
            await interaction.response.send_message(
                f"💸 No tienes suficiente cash. Precio total: {total_precio} <:amatista:1420736192269390006>",
                ephemeral=True
            )
            return

        # 🔹 Aplicar las compras
        for item_id in compras_realizadas:
            item = next((x for x in TIENDA_ITEMS if x["id"] == item_id), None)
            datos[uid]["items"][item_id]["cantidad"] += 1
            datos[uid]["items"][item_id]["multiplicador_total"] += item["multiplicador"]

        # Restar dinero y guardar
        restar_de_cash(datos, uid, total_precio)
        guardar_datos(datos)

        # 📜 Mensaje final con sumas
        resumen = []
        for item_id in compras_realizadas:
            info = next((x for x in TIENDA_ITEMS if x["id"] == item_id), None)
            inv = datos[uid]["items"][item_id]
            resumen.append(f"{info['label']} x{inv['multiplicador_total']:.1f} ({inv['cantidad']}/{info['limite']})")

        await interaction.response.send_message(
            f"✅ Compras realizadas:\n" + "\n".join(resumen) +
            f"\n💰 Gastaste {total_precio} <:amatista:1420736192269390006>.",
            ephemeral=True
        )


class ShopView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=120)
        self.add_item(ShopSelect())


class LeaderboardView(View):
    def __init__(self, ctx, lista, per_page, max_pages, sort_type="coins"):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.lista = lista
        self.per_page = per_page
        self.max_pages = max_pages
        self.sort_type = sort_type
        self.current_page = 1
        self.previous_button = self.children[0] if self.children else None
        self.next_button = self.children[1] if len(self.children) > 1 else None
        self.update_buttons()

    def update_buttons(self):
        if self.previous_button:
            self.previous_button.disabled = self.current_page == 1
        if self.next_button:
            self.next_button.disabled = self.current_page == self.max_pages

    def create_embed(self, page):
        inicio = (page - 1) * self.per_page
        fin = inicio + self.per_page
        slice_lista = self.lista[inicio:fin]
        descripcion = ""
        if self.sort_type == "level":
            for idx, (uid, nivel, xp) in enumerate(slice_lista, start=inicio + 1):
                usuario = bot.get_user(int(uid))
                nombre = usuario.name if usuario else f"Usuario desconocido ({uid})"
                medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else ""
                descripcion += f"{medal} **#{idx}** — {nombre} — Nivel {nivel} | XP {xp}\n"
            title = f"🏆 Leaderboard — Niveles (Página {page}/{self.max_pages})"
        else:  # coins
            for idx, (uid, monedas) in enumerate(slice_lista, start=inicio + 1):
                usuario = bot.get_user(int(uid))
                nombre = usuario.name if usuario else f"Usuario desconocido ({uid})"
                medal = "🥇" if idx == 1 else "🥈" if idx == 2 else "🥉" if idx == 3 else ""
                descripcion += f"{medal} **#{idx}** — {nombre} — {monedas} <:amatista:1420736192269390006>\n"
            title = f"🏆 Leaderboard — Amatistas (Página {page}/{self.max_pages})"
        embed = discord.Embed(title=title,
                              description=descripcion if descripcion else "No hay datos en esta página.",
                              color=discord.Color.purple())
        embed.set_footer(text="Usa los botones para navegar entre páginas.")
        return embed

    @discord.ui.button(label="⬅️ Anterior", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Solo el autor puede usar esto.", ephemeral=True)
            return
        if self.current_page > 1:
            self.current_page -= 1
            self.update_buttons()
            embed = self.create_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("Ya estás en la primera página.", ephemeral=True)

    @discord.ui.button(label="➡️ Siguiente", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Solo el autor puede usar esto.", ephemeral=True)
            return
        if self.current_page < self.max_pages:
            self.current_page += 1
            self.update_buttons()
            embed = self.create_embed(self.current_page)
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("Ya estás en la última página.", ephemeral=True)


@bot.command()
async def tienda(ctx):
    """Abre la tienda para comprar items (select)."""
    embed = discord.Embed(
        title="🏪 Tienda",
        description="Selecciona items y compra con tu cash. Los items aplican multiplicadores a minijuegos.",
        color=discord.Color.blurple()
    )
    for it in TIENDA_ITEMS:
        embed.add_field(
            name=it["label"],
            value=f"💰 Precio: {it['precio']} • 🧾 Límite: {it['limite']} • 📈 Multiplicador: x{it['multiplicador']}",
            inline=False
        )

    await ctx.send(embed=embed, view=ShopView())

@bot.command()
async def info(ctx):
    server = ctx.guild

    # Contar miembros
    total_members = server.member_count
    online_members = sum(1 for m in server.members if m.status == discord.Status.online and not m.bot)
    bot_count = sum(1 for m in server.members if m.bot)
    human_count = total_members - bot_count

    # Nivel de verificación
    verification_levels = {
        discord.VerificationLevel.none: "Ninguno",
        discord.VerificationLevel.low: "Bajo",
        discord.VerificationLevel.medium: "Medio",
        discord.VerificationLevel.high: "Alto (2FA)",
        discord.VerificationLevel.highest: "Muy Alto"
    }
    verification = verification_levels.get(server.verification_level, "Desconocido")

    embed = discord.Embed(
        title=f"📊 Información del servidor {server.name}",
        color=discord.Color.blue(),
        timestamp=discord.utils.utcnow()
    )

    # Icono del servidor
    if server.icon:
        embed.set_thumbnail(url=server.icon.url)

    embed.add_field(name="🆔 ID del Servidor", value=server.id, inline=True)
    embed.add_field(name="👑 Dueño", value=server.owner.mention if server.owner else "Desconocido", inline=True)
    embed.add_field(name="🔒 Nivel de Verificación", value=verification, inline=True)

    embed.add_field(name="👥 Miembros Totales", value=f"{total_members}", inline=True)
    embed.add_field(name="🟢 Miembros Online", value=f"{online_members}", inline=True)
    embed.add_field(name="🤖 Bots", value=f"{bot_count}", inline=True)
    embed.add_field(name="👤 Humanos", value=f"{human_count}", inline=True)

    try:
        embed.add_field(name="🌍 Región", value=str(server.region).title(), inline=True)
    except AttributeError:
        embed.add_field(name="🌍 Región", value="No disponible", inline=True)

    embed.add_field(name="📅 Creado el", value=server.created_at.strftime("%d/%m/%Y %H:%M:%S"), inline=False)

    # Boosts si aplica
    if server.premium_subscription_count > 0:
        embed.add_field(name="🚀 Boosts", value=f"{server.premium_subscription_count} (Nivel {server.premium_tier})", inline=True)

    embed.set_footer(text=f"Solicitado por {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)

    await ctx.send(embed=embed)

@bot.command()
@commands.cooldown(1, 60, commands.BucketType.user)
async def trabajar(ctx):
    datos = cargar_datos()
    uid = str(ctx.author.id)
    asegurar_usuario(datos, uid)

    trabajos = [
        {"nombre": "informático", "min": 450, "max": 850},
        {"nombre": "diseñador", "min": 350, "max": 700},
    	{"nombre": "músico", "min": 300, "max": 650},
    	{"nombre": "chef", "min": 400, "max": 750},
    	{"nombre": "fotógrafo", "min": 300, "max": 600},
    	{"nombre": "electricista", "min": 350, "max": 700},
    	{"nombre": "fontanero", "min": 300, "max": 650},
    	{"nombre": "carpintero", "min": 280, "max": 600},
    	{"nombre": "mecánico", "min": 400, "max": 800},
    	{"nombre": "programador", "min": 500, "max": 900},
    	{"nombre": "piloto", "min": 600, "max": 950},
    	{"nombre": "taxista", "min": 250, "max": 550},
    	{"nombre": "profesor", "min": 350, "max": 700},
    	{"nombre": "doctor", "min": 600, "max": 950},
    	{"nombre": "enfermero", "min": 400, "max": 750},
    	{"nombre": "bombero", "min": 450, "max": 900},
    	{"nombre": "policía", "min": 400, "max": 850},
    	{"nombre": "vigilante", "min": 300, "max": 650},
    	{"nombre": "panadero", "min": 200, "max": 450},
    	{"nombre": "pintor", "min": 250, "max": 500},
    	{"nombre": "actor", "min": 350, "max": 800},
    	{"nombre": "streamer", "min": 100, "max": 1000},  # depende de la suerte 💸
    	{"nombre": "youtuber", "min": 100, "max": 1000},
    	{"nombre": "barbero", "min": 250, "max": 500},
    	{"nombre": "conductor de camión", "min": 300, "max": 650},
    	{"nombre": "repartidor", "min": 200, "max": 450},
    	{"nombre": "agricultor", "min": 250, "max": 550},
    	{"nombre": "minero", "min": 350, "max": 800},
    	{"nombre": "científico", "min": 500, "max": 900},
    	{"nombre": "ingeniero", "min": 500, "max": 950},
    	{"nombre": "arquitecto", "min": 450, "max": 850},
    	{"nombre": "abogado", "min": 550, "max": 950},
    	{"nombre": "cocinero callejero", "min": 200, "max": 500},
    	{"nombre": "dj", "min": 250, "max": 700},
    	{"nombre": "guardabosques", "min": 300, "max": 600},
    	{"nombre": "soldado", "min": 400, "max": 850},
    ]

    trabajo_actual = random.choice(trabajos)
    ganancia = random.randint(trabajo_actual["min"], trabajo_actual["max"])
    datos[uid]["monedas"] = datos[uid].get("monedas", 0) + ganancia
    datos[uid]["cash"] = datos[uid].get("cash", 0) + ganancia
    guardar_datos(datos)
    await ctx.send(f"💼 {ctx.author.mention} trabajó como {trabajo_actual['nombre']} y ganó {ganancia} <:amatista:1420736192269390006>.")
    
    
@bot.command()
async def donar(ctx, miembro: discord.Member, cantidad: int):
    """Donar dinero (cash) a otro usuario."""
    datos = cargar_datos()
    uid = str(ctx.author.id)
    target_uid = str(miembro.id)
    asegurar_usuario(datos, uid)
    asegurar_usuario(datos, target_uid)

    if cantidad <= 0:
        await ctx.send("❌ La cantidad debe ser mayor que 0.")
        return

    if datos[uid]["cash"] < cantidad:
        await ctx.send("💸 No tienes suficiente efectivo para donar esa cantidad.")
        return

    # Transferencia
    restar_de_cash(datos, uid, cantidad)
    datos[target_uid]["cash"] += cantidad
    guardar_datos(datos)

    await ctx.send(
        f"🤝 {ctx.author.mention} ha donado **{cantidad} <:amatista:1420736192269390006>** a {miembro.mention}."
    )


# ------------------ BALANCE ------------------

@bot.command()
async def bal(ctx, member: discord.Member = None):
    datos = cargar_datos()
    if member is None:
        member = ctx.author
    uid = str(member.id)
    asegurar_usuario(datos, uid)

    cash = datos[uid].get("cash", 0)
    bank = datos[uid].get("bank", 0)
    total = obtener_monedas(datos, uid)
    posicion = obtener_rank_por_monedas(datos, uid)

    embed = discord.Embed(title=f"💰 Balance de {member.name}", color=discord.Color.gold())
    embed.add_field(name="Efectivo (cash)", value=f"{cash} <:amatista:1420736192269390006>", inline=True)
    embed.add_field(name="Banco", value=f"{bank} <:amatista:1420736192269390006>", inline=True)
    embed.add_field(name="Total", value=f"{total} <:amatista:1420736192269390006>", inline=False)

    items = datos[uid].get("items", {})

    if isinstance(items, dict) and items:
        desc_items_list = []
        for item_id, info in items.items():
            # Evitar errores si faltan keys
            cantidad = info.get("cantidad", 0)
            multiplicador = info.get("multiplicador_total", 0.0)
            limite = next((x['limite'] for x in TIENDA_ITEMS if x['id'] == item_id), '?')
            desc_items_list.append(f"- {item_id.capitalize()} x{multiplicador:.1f} ({cantidad}/{limite})")
        desc_items = "\n".join(desc_items_list)
    else:
        desc_items = "No tienes items."

    embed.add_field(name="Items / Buffs", value=desc_items, inline=False)
    embed.set_footer(text=f"Posición en leaderboard: #{posicion if posicion else '—'}")

    await ctx.send(embed=embed)



# ------------------ BANCOS ------------------

@bot.command(aliases=["dep"])
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

# 📚 CATEGORÍAS DE COMANDOS ACTUALIZADAS
COMMAND_CATEGORIES = {
    "basicos": {
        "!saludar": "Saluda al bot.",
        "!info": "Muestra información del servidor.",
        "!userinfo (miembro)": "Muestra información de un usuario.",
        "!bal": "Muestra tus monedas y dinero en el banco.",
        "!lvl": "Muestra tu nivel y experiencia.",
        "!ranking": "Muestra la lista de niveles y experiencia de los miembros con paginación.",
        "!membresia": "Crea un panel de registro para miembros. (Admin)"
    },
    "moderacion": {
        "!kick (miembro)": "Expulsa a un miembro. (Permiso kick_members)",
        "!ban (miembro)": "Banea a un miembro. (Permiso ban_members)",
        "!clear (cantidad)": "Borra mensajes. (Permiso manage_messages)",
        "!aviso": "Crea un mensaje embed para enviar avisos o anuncios. (Interactivo)",
        "!reactrole (id mensaje) (emoji) (rol)": "Asigna un rol al reaccionar con un emoji. (Permiso manage_roles)",
        "!addmoney (miembro) (cantidad)": "Agrega dinero en efectivo a un usuario. (Admin)",
        "!removemoney (miembro) (cantidad)": "Resta dinero en efectivo a un usuario. (Admin)",
        "!asignar_rol": "Asigna el rol obligatorio a todos los miembros existentes."
    },
    "economia": {
        "!trabajar": "Gana monedas realizando un trabajo.",
        "!depositar (cantidad|all)": "Deposita dinero (o 'all') en tu banco.",
        "!retirar (cantidad|all)": "Retira dinero (o 'all') de tu banco.",
        "!robar (usuario)": "Intenta robar monedas a otro usuario. (Riesgo de perder)",
        "!crimen": "Comete un crimen por monedas. (Riesgo alto)",
        "!hackear (usuario)": "Intenta hackear a otro usuario para ganar monedas. (Riesgo alto)",
        "!donar (usuario) (cantidad)": "Dona monedas a otro usuario.",
        "!lb": "Muestra el leaderboard de amatistas con paginación por botones.",
        "!tienda": "Abre la tienda para comprar items que mejoran ganancias."
    },
    "minijuegos": {
        "!adivina": "Adivina un número entre 1 y 100.",
        "!ppt (cantidad|all) (piedra/papel/tijera)": "Juega 'Piedra, Papel o Tijera' con tu cash.",
        "!apostar (cantidad|all) (cara/cruz)": "Apuesta con tu cash.",
        "!blackjack (cantidad|all)": "Juega Blackjack contra el bot usando tu cash.",
        "!maquina (cantidad|all)": "Juega a la máquina tragaperras con tu cash.",
        "!ruleta (cantidad|all) (tipo)": "Juega a la ruleta con tu cash (tipos: rojo/negro/par/impar/numero).",
        "!dado (cantidad|all) (tipo)": "Juega con dados con tu cash (tipos: alto/bajo/suma)."
    },
    "otros": {
        "!panelticket": "Muestra el panel para crear tickets.",
        "!ayuda (categoria)": "Muestra la lista de comandos o los de una categoría específica."
    },
    "funciones": {
        "Sistema de Economía": "Gestiona monedas, banco, trabajos, tienda con items para multiplicadores.",
        "Minijuegos Interactivos": "Juegos como blackjack, ppt, apostar, adivina con apuestas y rematch.",
        "Moderación Completa": "Comandos para admins: kick, ban, clear, avisos, reactroles, gestión de dinero.",
        "Sistema de Niveles y XP": "Gana XP por mensajes, sube niveles con recompensas cada 10 niveles.",
        "Registro de Miembros": "Panel interactivo para registrarse como freestyler o competitivo con roles automáticos.",
        "Eventos Automáticos": "Bienvenidas, asignación de roles obligatorios, logs en Discord, presencia rotativa."
    }
}

# --- HELP VIEWS ---
def create_main_embed(ctx):
    embed = discord.Embed(
        title="📚 Comandos disponibles",
        description="Usa los botones abajo para ver los comandos de cada categoría.\n\nTambién puedes usar `!ayuda <categoría>` para ir directo.",
        color=discord.Color.purple()
    )
    embed.add_field(name="Categorías", value="• Básicos\n• Moderación\n• Economía\n• Minijuegos\n• Otros\n• Funciones", inline=False)
    embed.set_footer(text=f"Solicitado por {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    return embed

def create_category_embed(cat, ctx):
    embed = discord.Embed(
        title=f"📜 Comandos — {cat.title()}",
        color=discord.Color.purple()
    )
    descripcion = ""
    for cmd, desc in COMMAND_CATEGORIES[cat].items():
        descripcion += f"**{cmd}** — {desc}\n"
    embed.description = descripcion
    embed.set_footer(text=f"Solicitado por {ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    return embed

class CategoryHelpView(View):
    def __init__(self, ctx):
        super().__init__(timeout=300)
        self.ctx = ctx

    @discord.ui.button(label="⬅️ Volver al Menú Principal", style=discord.ButtonStyle.secondary)
    async def back(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Solo el autor puede usar esto.", ephemeral=True)
            return
        embed = create_main_embed(self.ctx)
        view = MainHelpView(self.ctx)
        await interaction.response.edit_message(embed=embed, view=view)

class MainHelpView(View):
    def __init__(self, ctx):
        super().__init__(timeout=300)
        self.ctx = ctx

    @discord.ui.button(label="🟢 Básicos", style=discord.ButtonStyle.primary, row=0)
    async def basicos(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Solo el autor puede usar esto.", ephemeral=True)
            return
        embed = create_category_embed("basicos", self.ctx)
        view = CategoryHelpView(self.ctx)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🛡️ Moderación", style=discord.ButtonStyle.primary, row=0)
    async def moderacion(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Solo el autor puede usar esto.", ephemeral=True)
            return
        embed = create_category_embed("moderacion", self.ctx)
        view = CategoryHelpView(self.ctx)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="💰 Economía", style=discord.ButtonStyle.primary, row=1)
    async def economia(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Solo el autor puede usar esto.", ephemeral=True)
            return
        embed = create_category_embed("economia", self.ctx)
        view = CategoryHelpView(self.ctx)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🎮 Minijuegos", style=discord.ButtonStyle.primary, row=1)
    async def minijuegos(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Solo el autor puede usar esto.", ephemeral=True)
            return
        embed = create_category_embed("minijuegos", self.ctx)
        view = CategoryHelpView(self.ctx)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🔧 Otros", style=discord.ButtonStyle.primary, row=2)
    async def otros(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Solo el autor puede usar esto.", ephemeral=True)
            return
        embed = create_category_embed("otros", self.ctx)
        view = CategoryHelpView(self.ctx)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="⚙️ Funciones", style=discord.ButtonStyle.primary, row=2)
    async def funciones(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Solo el autor puede usar esto.", ephemeral=True)
            return
        embed = create_category_embed("funciones", self.ctx)
        view = CategoryHelpView(self.ctx)
        await interaction.response.edit_message(embed=embed, view=view)


@bot.command()
async def ayuda(ctx, categoria: str = None):
    """Muestra la lista de comandos o los de una categoría específica."""
    if categoria:
        cat = categoria.lower()
        if cat in COMMAND_CATEGORIES:
            embed = create_category_embed(cat, ctx)
            view = CategoryHelpView(ctx)
            await ctx.send(embed=embed, view=view)
        else:
            await ctx.send("❌ Categoría no encontrada. Usa: `basicos`, `moderacion`, `economia`, `minijuegos`, `otros`.")
    else:
        embed = create_main_embed(ctx)
        view = MainHelpView(ctx)
        await ctx.send(embed=embed, view=view)


# ------------------ LEADERBOARD (!lb) ------------------

@bot.command()
async def lb(ctx):
    datos = cargar_datos()
    if not datos:
        await ctx.send("No hay datos aún.")
        return

    lista = [(uid, obtener_monedas(datos, uid)) for uid in datos.keys() if ctx.guild.get_member(int(uid)) is not None]
    lista.sort(key=lambda x: x[1], reverse=True)

    per_page = 10
    max_pages = (len(lista) + per_page - 1) // per_page

    view = LeaderboardView(ctx, lista, per_page, max_pages, "coins")
    embed = view.create_embed(1)
    await ctx.send(embed=embed, view=view)

# ------------------ EJECUTAR BOT ------------------

if __name__ == "__main__":
    # Pon tu token aquí de forma segura
    bot.run(os.getenv("DISCORD_TOKEN"))
