import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Modal, TextInput, View, Button
import random
import datetime
import json
import asyncio
import os
from typing import Optional, Dict, Any
from itertools import cycle
from dotenv import load_dotenv
import io
import aiohttp
import re

load_dotenv()

# ------------------ CONFIG ------------------

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
intents.presences = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ------------------ DATOS ------------------

LOG_CHANNEL_ID = 1424514411682594946  # Cambia por tu canal real de logs
GUILD_ID = 1405199387642040321  # ID del servidor donde opera el bot
CANAL_MEMBRESIA_ID = 1406648572086059051  # ID del canal donde se envía el mensaje de membresía
ROLE_COMPETITIVO = 1406648557808648367
ROLE_FREESTYLER = 1406648556768596059
ROLE_MIEMBRO = 1406648558790250668
CANAL_BIENVENIDAS_ID = 1406648569271816192  # ID del canal de bienvenida
ROL_OBLIGATORIO_ID = 1424860513258701002 
MI_ID = 798937817869844541
DATOS_FILE = "datos.json"
TRIGGER_TEXT = "./start_globed$backup"

# ------------------ TICKETS CONFIG ------------------


TICKET_CATEGORY_NAME = "🎫 TICKETS DE SOPORTE"
TICKET_PANEL_CHANNEL_NAME = "🎫-crear-ticket"
TICKET_LOGS_CHANNEL_NAME = "📋-ticket-logs"

# ------------------ STREAMS CONFIG ------------------

STREAMS_CHANNEL_ID = None  # Se configurará automáticamente
STREAMS_CHANNEL_NAME = "🔴-streams-en-vivo"
STREAMS_LOOP_INTERVAL = 30  # 30 segundos entre verificaciones

# Almacenar streams activos para evitar duplicados
active_streams = {}
stream_notifications = {}

# Variables globales para almacenar los IDs creados
ticket_category_id = None
ticket_panel_channel_id = None
ticket_logs_channel_id = None




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
        await asyncio.sleep(0.5)  # Pequeño delay opcional, solo visual



# ---------- MODAL ----------
class MembresiaModal(Modal, title="Registro de Miembro"):
    nombre = TextInput(label="Nombre", placeholder="Tu nombre real", max_length=32)
    edad = TextInput(label="Edad", placeholder="Ej: 17", max_length=4)
    tipo = TextInput(label="Tipo (FREESTYLER o COMPETITIVO o LOS 2)", placeholder="Escribe uno de los tres", max_length=15)
    rango = TextInput(label="¿Qué rango eres?", placeholder="Ej: C1, GC2, SSL...", max_length=10)
    habilidades = TextInput(
        label="¿Qué sabes hacer?",
        style=discord.TextStyle.long,
        placeholder="Cuéntanos tus habilidades, experiencia, etc.",
        max_length=500,
    )

    async def on_submit(self, interaction: discord.Interaction):
        tipo_texto = self.tipo.value.strip().upper()
        if tipo_texto not in ["FREESTYLER", "COMPETITIVO", "LOS 2"]:
            await interaction.response.send_message(
                "⚠️ Debes escribir exactamente **FREESTYLER**, **COMPETITIVO** o **LOS 2**.", ephemeral=True
            )
            return

        color = discord.Color.blue() if tipo_texto == "FREESTYLER" else discord.Color.purple()
        embed = discord.Embed(
            title="📋 Solicitud de Membresía Pendiente",
            description="Tu solicitud ha sido enviada al propietario.\n\n"
                        "⏳ **Por favor, espera a que se revise y apruebe tu registro.**",
            color=color,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        # ====== Enviar al propietario (por MD) ======
        admin_user = await bot.fetch_user(MI_ID)  # Cambia MI_ID por tu ID real

        datos = discord.Embed(
            title="🔔 Nueva Solicitud de Membresía",
            description=f"Registro enviado por {interaction.user.mention} (`{interaction.user.id}`)",
            color=color
        )
        datos.add_field(name="👤 Nombre", value=self.nombre.value, inline=True)
        datos.add_field(name="🎂 Edad", value=self.edad.value, inline=True)
        datos.add_field(name="⚙️ Tipo", value=tipo_texto, inline=True)
        datos.add_field(name="🏆 Rango", value=self.rango.value, inline=True)
        datos.add_field(name="💬 Habilidades", value=self.habilidades.value, inline=False)
        datos.set_footer(text="Usa los botones de abajo para aceptar o rechazar.")

        view = AceptarMembresiaView(user_id=interaction.user.id, tipo=tipo_texto)
        await admin_user.send(embed=datos, view=view)


# ---------- VISTA DE ACEPTAR O RECHAZAR (PROPIETARIO) ----------
class AceptarMembresiaView(View):
    def __init__(self, user_id, tipo):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.tipo = tipo

    @discord.ui.button(label="✅ Aceptar", style=discord.ButtonStyle.success)
    async def aceptar(self, interaction: discord.Interaction, button: Button):
        guild = bot.get_guild(GUILD_ID)  # ← Cambia por el ID de tu servidor
        member = guild.get_member(self.user_id)

        if not member:
            await interaction.response.send_message("❌ El usuario ya no está en el servidor.", ephemeral=True)
            return

        # Roles
        roles = [guild.get_role(ROLE_MIEMBRO)]
        if self.tipo == "COMPETITIVO":
            roles.append(guild.get_role(ROLE_COMPETITIVO))
        elif self.tipo == "FREESTYLER":
            roles.append(guild.get_role(ROLE_FREESTYLER))
        elif self.tipo == "LOS 2":
            roles.append(guild.get_role(ROLE_COMPETITIVO))
            roles.append(guild.get_role(ROLE_FREESTYLER))

        for role in roles:
            if role:
                await member.add_roles(role, reason="Membresía aceptada por el propietario")

        # Avisar por DM al usuario
        try:
            await member.send("✅ Tu solicitud de membresía ha sido **aceptada**. ¡Bienvenido al servidor! 🎉")
        except:
            pass

        await interaction.response.send_message(
            content=f"✅ Has aceptado la solicitud de {member.mention}. Se le asignaron los roles.",
            embed=None,
            view=None
        )

    @discord.ui.button(label="❌ Rechazar", style=discord.ButtonStyle.danger)
    async def rechazar(self, interaction: discord.Interaction, button: Button):
        guild = bot.get_guild(GUILD_ID)
        member = guild.get_member(self.user_id)

        # Avisar por DM al usuario si sigue en el servidor
        if member:
            try:
                await member.send("❌ Tu solicitud de membresía ha sido **rechazada** por el propietario.")
            except:
                pass

        await interaction.response.send_message(
            content=f"🚫 Has rechazado la solicitud de {member.mention if member else 'ese usuario'}.",
            embed=None,
            view=None
        )


# ---------- BOTÓN PRINCIPAL “REGISTRARSE” ----------
class RegistroButton(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 Registrarse", style=discord.ButtonStyle.blurple)
    async def registrarse(self, interaction: discord.Interaction, button: Button):
        modal = MembresiaModal()
        await interaction.response.send_modal(modal)


# ---------- FUNCIÓN PARA ENVIAR EL MENSAJE DE MEMBRESÍA ----------
async def enviar_membresia(canal: discord.TextChannel):
    embed = discord.Embed(
        title="🎯 Registro de Miembro",
        description=(
            "👋 Bienvenido al servidor.\n\n"
            "Pulsa el botón de abajo para **registrarte como miembro**.\n"
            "Podrás elegir si eres **Freestyler** o **Competitivo** o **LOS 2**, poner tu rango y habilidades.\n\n"
            "📨 Una vez completes el formulario, **el propietario revisará tu solicitud** antes de darte acceso."
        ),
        color=discord.Color.green(),
    )
    embed.set_footer(text="Sistema de membresía con aprobación manual 🛡️")

    view = RegistroButton()
    await canal.send(embed=embed, view=view)



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


@bot.event
async def on_ready():
    try:
        synced = await bot.tree.sync()
        print(f"🌐 Se han sincronizado {len(synced)} comandos de barra (/) correctamente.")
    except Exception as e:
        print(f"❌ Error al sincronizar slash commands: {e}")

    print("\n" + "=" * 50)
    print("🧠  INICIANDO SISTEMA MARKELSOFT AI v2.1")
    print("🎫  SISTEMA DE TICKETS AUTO-CONFIGURABLE")
    print("=" * 50)

    steps = [
        "🔌 Conectando a Discord API...",
        "⚙️ Cargando comandos...",
        "🎨 Activando interfaz visual...",
        "🛰️ Sincronizando módulos de membresía...",
        "💾 Iniciando base de datos temporal...",
        "📺 Configurando sistema de streams...",
        "🔴 Iniciando monitoreo de streams...",
        "🚀 Lanzamiento completo."
    ]
    for step in steps:
        print(step)
        await asyncio.sleep(0.5)

    print(f"\n✅ Bot en línea como: {bot.user}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"🕒 Hora de inicio: {datetime.datetime.now().strftime('%H:%M:%S')}")
    print("=" * 50 + "\n")
    print(f"📺 Sistema de streams: ACTIVADO")
    print(f"🔴 Monitoreo cada: {STREAMS_LOOP_INTERVAL} segundos")
    print(f"🕒 Hora de inicio: {datetime.datetime.now().strftime('%H:%M:%S')}")
    print("=" * 50 + "\n")

    # Configurar sistema de streams automáticamente
    for guild in bot.guilds:
        success = await setup_streams_system(guild)
        if success:
            print(f"✅ Sistema de streams configurado en: {guild.name}")
        else:
            print(f"❌ Error configurando streams en: {guild.name}")

    # Iniciar el loop de verificación de streams
    if not check_streams_loop.is_running():
        check_streams_loop.start()
        print("🔴 Loop de verificación de streams iniciado")
    
    # Configurar sistema de tickets automáticamente
    for guild in bot.guilds:
        success = await setup_ticket_system(guild)
        if success:
            print(f"✅ Sistema de tickets configurado en: {guild.name}")
        else:
            print(f"❌ Error configurando tickets en: {guild.name}")

    # Presencia inicial
    await bot.change_presence(activity=discord.Game(name="Inicializando..."), status=discord.Status.idle)

    # Rotación de estados
    bot.loop.create_task(estado_rotativo())

    # Enviar log en Discord (opcional)
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

    # Inicializa base de datos
    datos = cargar_datos()
    for guild in bot.guilds:
        for member in guild.members:
            if not member.bot:
                asegurar_usuario(datos, str(member.id))
    guardar_datos(datos)

    # ---------- 🚀 AUTOMATIZACIÓN DEL MENSAJE DE MEMBRESÍA ----------
    canal_membresia = bot.get_channel(CANAL_MEMBRESIA_ID)
    if canal_membresia:
        try:
            # 🧹 Borra todos los mensajes del canal
            await canal_membresia.purge(limit=None)
            print(f"🧹 Canal '{canal_membresia.name}' limpiado correctamente.")

            # 📩 Envía el embed de membresía
            await enviar_membresia(canal_membresia)
            print("✅ Mensaje de membresía enviado automáticamente al iniciar el bot.")
        except Exception as e:
            print(f"⚠️ Error al limpiar o enviar mensaje de membresía: {e}")

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
async def addmoney(ctx, miembro: discord.Member, cantidad: int, tipo: str = "cash"):
    """Agrega dinero en efectivo (cash) o al banco (bank) a un usuario."""
    if tipo.lower() not in ["cash", "bank"]:
        await ctx.send("❌ Tipo inválido. Usa 'cash' o 'bank'.")
        return

    datos = cargar_datos()
    uid = str(miembro.id)
    asegurar_usuario(datos, uid)

    if cantidad <= 0:
        await ctx.send("❌ Ingresa una cantidad válida mayor que 0.")
        return

    if tipo.lower() == "bank":
        datos[uid]["bank"] = datos[uid].get("bank", 0) + cantidad
    else:
        agregar_a_cash(datos, uid, cantidad)
    guardar_datos(datos)

    await ctx.send(f"✅ Se añadieron {cantidad} <:amatista:1420736192269390006> a {miembro.mention} ({tipo.lower()}).")

# --- REMOVE MONEY ---
@bot.command()
@commands.has_permissions(administrator=True)
async def removemoney(ctx, miembro: discord.Member, cantidad: int, tipo: str = "cash"):
    """Resta dinero en efectivo (cash) o al banco (bank) a un usuario."""
    if tipo.lower() not in ["cash", "bank"]:
        await ctx.send("❌ Tipo inválido. Usa 'cash' o 'bank'.")
        return

    datos = cargar_datos()
    uid = str(miembro.id)
    asegurar_usuario(datos, uid)

    if cantidad <= 0:
        await ctx.send("❌ Ingresa una cantidad válida mayor que 0.")
        return

    if tipo.lower() == "bank":
        bank_actual = datos[uid].get("bank", 0)
        if cantidad > bank_actual:
            cantidad = bank_actual  # no dejes negativo
        datos[uid]["bank"] = bank_actual - cantidad
    else:
        efectivo_actual = datos[uid].get("cash", 0)
        if cantidad > efectivo_actual:
            cantidad = efectivo_actual  # no dejes negativo
        restar_de_cash(datos, uid, cantidad)
    guardar_datos(datos)

    await ctx.send(f"💸 Se removieron {cantidad} <:amatista:1420736192269390006> de {miembro.mention} ({tipo.lower()}).")


# ------------------ COMANDOS BÁSICOS / ADMIN ------------------

@bot.tree.command(name="ping", description="Verifica si el bot está vivo")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"Pong! 🏓 Latencia: {round(bot.latency * 1000)} ms")


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
        await ctx.send(f"{member.mention} ha sido baneado. Motivo: {reason if reason else 'No especificado'}.")
    except Exception as e:
        await ctx.send(f"No pude banear a {member.mention}. Error: {e}")

@bot.command()
@commands.has_permissions(manage_messages=True)
async def clear(ctx, amount: int = 5):
    deleted = await ctx.channel.purge(limit=amount+1)
    confirmation_message = await ctx.send(f"Se han borrado {len(deleted)-1} mensajes.")
    await asyncio.sleep(5)
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

@bot.command(aliases=["rank"])
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


# ------------------ SISTEMA DE STREAMS ------------------

async def setup_streams_system(guild):
    """Configura automáticamente el canal de streams"""
    global STREAMS_CHANNEL_ID
    
    print("📺 Configurando sistema de streams...")
    
    try:
        # Verificar si ya existe el canal
        existing_channel = discord.utils.get(guild.text_channels, name=STREAMS_CHANNEL_NAME)
        if existing_channel:
            STREAMS_CHANNEL_ID = existing_channel.id
            print(f"✅ Canal de streams ya existe: {existing_channel.name}")
        else:
            # Crear nuevo canal de streams
            streams_channel = await guild.create_text_channel(
                name=STREAMS_CHANNEL_NAME,
                reason="Canal para notificaciones de streams en vivo"
            )
            STREAMS_CHANNEL_ID = streams_channel.id
            
            # Configurar permisos del canal
            await streams_channel.set_permissions(guild.default_role, 
                view_channel=True,
                send_messages=False,
                read_message_history=True,
                add_reactions=True
            )
            
            # Embed de bienvenida
            embed = discord.Embed(
                title="📺 CANAL DE STREAMS EN VIVO",
                description=(
                    "**¡Bienvenido al canal de streams!** 🎮\n\n"
                    "🔴 **Aquí aparecerán automáticamente:**\n"
                    "• Streams de YouTube en vivo\n"
                    "• Directos de Twitch\n"
                    "• Lives de TikTok\n\n"
                    "**¿Eres miembro y quieres que aparezcan tus streams?**\n"
                    "Usa el comando `!addstream [plataforma] [URL/usuario]`\n\n"
                    "*Ejemplo:* `!addstream twitch tu_usuario`"
                ),
                color=discord.Color.purple()
            )
            embed.add_field(
                name="📋 Plataformas Soportadas",
                value="• **YouTube** - URLs de canal o video\n• **Twitch** - Nombre de usuario\n• **TikTok** - Nombre de usuario",
                inline=False
            )
            embed.add_field(
                name="🎮 Comandos Disponibles",
                value=(
                    "`!addstream` - Agregar tu stream\n"
                    "`!mystreams` - Ver tus streams registrados\n"
                    "`!delstream` - Eliminar un stream\n"
                    "`!streams` - Lista de todos los streams"
                ),
                inline=False
            )
            embed.set_footer(text="Sistema automático de notificaciones • Actualizado cada 5 minutos")
            
            await streams_channel.send(embed=embed)
            print(f"✅ Canal de streams creado: {streams_channel.name}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error configurando canal de streams: {e}")
        return False

def extract_platform_info(url):
    """Extrae información de la plataforma y usuario/ID del enlace"""
    url = url.lower().strip()
    
    # YouTube
    if 'youtube.com/' in url or 'youtu.be/' in url:
        platform = 'youtube'
        # Extraer channel ID o video ID
        if 'channel/' in url:
            channel_id = url.split('channel/')[-1].split('?')[0].split('/')[0]
            return platform, channel_id
        elif 'user/' in url:
            username = url.split('user/')[-1].split('?')[0].split('/')[0]
            return platform, username
        elif 'youtube.com/' in url:
            # Intentar extraer el handle (@usuario)
            if '@' in url:
                username = url.split('@')[-1].split('?')[0].split('/')[0]
                return platform, username
            else:
                # Usar el último segmento de la URL
                username = url.split('/')[-1].split('?')[0]
                return platform, username
        elif 'youtu.be/' in url:
            video_id = url.split('youtu.be/')[-1].split('?')[0]
            return platform, video_id
    
    # Twitch
    elif 'twitch.tv/' in url:
        platform = 'twitch'
        username = url.split('twitch.tv/')[-1].split('?')[0].split('/')[0]
        return platform, username
    
    # TikTok
    elif 'tiktok.com/' in url:
        platform = 'tiktok'
        if '@' in url:
            username = url.split('@')[-1].split('?')[0].split('/')[0]
        else:
            username = url.split('tiktok.com/')[-1].split('?')[0].split('/')[0]
        return platform, username
    
    # Si no es URL, asumir que es nombre de usuario
    else:
        # Intentar detectar plataforma por contexto
        if any(word in url for word in ['yt', 'youtube']):
            return 'youtube', url
        elif any(word in url for word in ['twitch', 'ttv']):
            return 'twitch', url
        elif any(word in url for word in ['tiktok', 'tt']):
            return 'tiktok', url
        else:
            return 'unknown', url

async def check_youtube_stream(session, identifier):
    """Verificar si hay stream en YouTube"""
    try:
        # API key de YouTube (necesitarías obtener una)
        # Por ahora usamos una verificación básica
        return {
            'live': False,
            'title': 'YouTube Stream',
            'url': f'https://youtube.com/{identifier}',
            'thumbnail': None
        }
    except:
        return {'live': False}

async def check_twitch_stream(session, username):
    """Verificar si hay stream en Twitch"""
    try:
        # Usar la API de Twitch (necesitarías client_id y client_secret)
        headers = {
            'Client-ID': 'tu_client_id',  # Necesitas registrar una app en Twitch
            'Authorization': 'Bearer tu_token'
        }
        
        async with session.get(f'https://api.twitch.tv/helix/streams?user_login={username}', headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                if data.get('data'):
                    stream_data = data['data'][0]
                    return {
                        'live': True,
                        'title': stream_data['title'],
                        'url': f'https://twitch.tv/{username}',
                        'thumbnail': stream_data['thumbnail_url'].format(width=1920, height=1080),
                        'viewers': stream_data['viewer_count'],
                        'game': stream_data['game_name']
                    }
        
        return {'live': False}
    except:
        return {'live': False}

async def check_tiktok_stream(session, username):
    """Verificar si hay stream en TikTok"""
    try:
        # TikTok no tiene API pública fácil, hacemos verificación básica
        return {
            'live': False,
            'title': 'TikTok Live',
            'url': f'https://tiktok.com/@{username}',
            'thumbnail': None
        }
    except:
        return {'live': False}

async def check_stream_status(platform, identifier):
    """Verificar el estado del stream"""
    async with aiohttp.ClientSession() as session:
        if platform == 'youtube':
            return await check_youtube_stream(session, identifier)
        elif platform == 'twitch':
            return await check_twitch_stream(session, identifier)
        elif platform == 'tiktok':
            return await check_tiktok_stream(session, identifier)
        else:
            return {'live': False}

def create_stream_embed(member, platform, stream_data):
    """Crear embed para notificación de stream"""
    
    colors = {
        'youtube': discord.Color.red(),
        'twitch': discord.Color.purple(),
        'tiktok': discord.Color.blue()
    }
    
    platform_emojis = {
        'youtube': '📺',
        'twitch': '🟣',
        'tiktok': '🎵'
    }
    
    embed = discord.Embed(
        title=f"{platform_emojis.get(platform, '🔴')} ¡{member.display_name} ESTÁ EN VIVO!",
        description=stream_data.get('title', 'Stream en vivo'),
        color=colors.get(platform, discord.Color.green()),
        url=stream_data.get('url', '#'),
        timestamp=discord.utils.utcnow()
    )
    
    embed.set_author(
        name=f"{member.display_name}",
        icon_url=member.display_avatar.url
    )
    
    # Agregar campos según la plataforma
    if platform == 'twitch' and stream_data.get('game'):
        embed.add_field(name="🎮 Juego", value=stream_data['game'], inline=True)
    
    if platform == 'twitch' and stream_data.get('viewers'):
        embed.add_field(name="👀 Espectadores", value=f"{stream_data['viewers']}", inline=True)
    
    embed.add_field(
        name="📡 Plataforma", 
        value=platform.upper(), 
        inline=True
    )
    
    # Thumbnail si está disponible
    if stream_data.get('thumbnail'):
        embed.set_image(url=stream_data['thumbnail'])
    
    embed.add_field(
        name="🔗 Enlace Directo",
        value=f"[Ver Stream]({stream_data.get('url', '#')})",
        inline=False
    )
    
    embed.set_footer(text=f"Haz clic en el título para ver el stream • {platform.upper()}")
    
    return embed

@tasks.loop(seconds=STREAMS_LOOP_INTERVAL)
async def check_streams_loop():
    """Loop principal para verificar streams"""
    if not STREAMS_CHANNEL_ID:
        return
    
    for guild in bot.guilds:
        streams_channel = guild.get_channel(STREAMS_CHANNEL_ID)
        if not streams_channel:
            continue
            
        # Cargar streams guardados
        streams_data = cargar_streams_data()
        
        for user_id, user_streams in streams_data.items():
            member = guild.get_member(int(user_id))
            if not member or not any(role.id == ROLE_MIEMBRO for role in member.roles):
                continue
                
            for stream_info in user_streams:
                platform = stream_info['platform']
                identifier = stream_info['identifier']
                custom_message = stream_info.get('message', '')
                
                # Verificar estado del stream
                stream_data = await check_stream_status(platform, identifier)
                
                stream_key = f"{user_id}_{platform}_{identifier}"
                
                if stream_data.get('live'):
                    # Stream está en vivo
                    if stream_key not in active_streams:
                        # Nuevo stream - enviar notificación
                        embed = create_stream_embed(member, platform, stream_data)
                        
                        # Agregar mensaje personalizado si existe
                        if custom_message:
                            embed.insert_field_at(
                                0,
                                name="💬 Mensaje del Streamer",
                                value=custom_message,
                                inline=False
                            )
                        
                        message = await streams_channel.send(
                            content=f"🎉 **¡NUEVO STREAM!** {member.mention} está en vivo!\n<@&{ROLE_MIEMBRO}>",
                            embed=embed
                        )
                        
                        active_streams[stream_key] = {
                            'message_id': message.id,
                            'start_time': discord.utils.utcnow()
                        }
                        
                        # Guardar notificación
                        stream_notifications[stream_key] = message.id
                        
                        print(f"🔴 Stream detectado: {member.display_name} en {platform}")
                        
                else:
                    # Stream terminó
                    if stream_key in active_streams:
                        # Eliminar de activos
                        del active_streams[stream_key]
                        
                        # Podrías enviar un mensaje de stream terminado si quieres
                        # await streams_channel.send(f"⏹️ {member.mention} ha terminado su stream.")
                        
                        print(f"⏹️ Stream terminado: {member.display_name} en {platform}")

def cargar_streams_data():
    """Cargar datos de streams desde archivo"""
    try:
        with open('streams_data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def guardar_streams_data(data):
    """Guardar datos de streams en archivo"""
    try:
        with open('streams_data.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Error guardando datos de streams: {e}")

# ------------------ COMANDOS DE STREAMS ------------------

@bot.command()
async def addstream(ctx, plataforma: str, *, enlace_o_usuario: str):
    """Agrega tu stream para recibir notificaciones automáticas"""
    
    # Verificar que el usuario tenga rol de miembro
    if not any(role.id == ROLE_MIEMBRO for role in ctx.author.roles):
        await ctx.send("❌ Solo los miembros pueden agregar sus streams.")
        return
    
    plataforma = plataforma.lower()
    plataformas_validas = ['youtube', 'twitch', 'tiktok', 'yt', 'ttv', 'tt']
    
    if plataforma not in plataformas_validas:
        await ctx.send(
            "❌ Plataforma no válida. Usa: `youtube`, `twitch` o `tiktok`\n\n"
            "**Ejemplos:**\n"
            "`!addstream twitch tu_usuario`\n"
            "`!addstream youtube https://youtube.com/tu_canal`\n"
            "`!addstream tiktok @tu_usuario`"
        )
        return
    
    # Mapear abreviaciones
    if plataforma in ['yt', 'youtube']:
        plataforma = 'youtube'
    elif plataforma in ['ttv', 'twitch']:
        plataforma = 'twitch'
    elif plataforma in ['tt', 'tiktok']:
        plataforma = 'tiktok'
    
    # Extraer información de la plataforma
    platform, identifier = extract_platform_info(enlace_o_usuario)
    
    if platform == 'unknown':
        # Usar la plataforma especificada por el usuario
        platform = plataforma
        identifier = enlace_o_usuario
    
    # Cargar datos existentes
    streams_data = cargar_streams_data()
    user_id = str(ctx.author.id)
    
    if user_id not in streams_data:
        streams_data[user_id] = []
    
    # Verificar si ya existe el stream
    for stream in streams_data[user_id]:
        if stream['platform'] == platform and stream['identifier'] == identifier:
            await ctx.send("❌ Ya tienes este stream registrado.")
            return
    
    # Preguntar por mensaje personalizado
    embed = discord.Embed(
        title="🎮 Configurar Stream",
        description=(
            f"**Plataforma:** {platform.upper()}\n"
            f"**Usuario/ID:** {identifier}\n\n"
            "¿Quieres agregar un mensaje personalizado para cuando estés en vivo?\n"
            "*Ejemplo: '¡Hola! Jugando Rocket League hoy'*"
        ),
        color=discord.Color.blue()
    )
    
    class StreamModal(Modal, title="Mensaje Personalizado para Stream"):
        message = TextInput(
            label="Mensaje (opcional)",
            placeholder="Ej: ¡Hola! Jugando Rocket League hoy...",
            max_length=200,
            required=False
        )
        
        async def on_submit(self, interaction: discord.Interaction):
            # Guardar stream
            stream_info = {
                'platform': platform,
                'identifier': identifier,
                'added_date': datetime.datetime.now().isoformat()
            }
            
            if self.message.value.strip():
                stream_info['message'] = self.message.value.strip()
            
            streams_data[user_id].append(stream_info)
            guardar_streams_data(streams_data)
            
            success_embed = discord.Embed(
                title="✅ Stream Agregado",
                description=(
                    f"**Plataforma:** {platform.upper()}\n"
                    f"**Usuario/ID:** `{identifier}`\n"
                    f"**Mensaje:** {stream_info.get('message', 'Ninguno')}\n\n"
                    "¡Ahora recibirás notificaciones automáticas cuando estés en vivo!"
                ),
                color=discord.Color.green()
            )
            
            await interaction.response.send_message(embed=success_embed, ephemeral=True)
    
    modal = StreamModal()
    await ctx.send(embed=embed, view=None)
    await ctx.send("💬 **Escribe tu mensaje personalizado (opcional):**", delete_after=10)
    await ctx.send("⏰ *Tienes 60 segundos para responder...*", delete_after=10)
    
    try:
        # Esperar respuesta de mensaje personalizado
        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel
        
        msg = await bot.wait_for('message', timeout=60.0, check=check)
        custom_message = msg.content.strip()
        
        # Guardar stream con mensaje
        stream_info = {
            'platform': platform,
            'identifier': identifier,
            'added_date': datetime.datetime.now().isoformat(),
            'message': custom_message if custom_message else None
        }
        
        streams_data[user_id].append(stream_info)
        guardar_streams_data(streams_data)
        
        success_embed = discord.Embed(
            title="✅ Stream Agregado",
            description=(
                f"**Plataforma:** {platform.upper()}\n"
                f"**Usuario/ID:** `{identifier}`\n"
                f"**Mensaje:** {custom_message if custom_message else 'Ninguno'}\n\n"
                "¡Ahora recibirás notificaciones automáticas cuando estés en vivo!"
            ),
            color=discord.Color.green()
        )
        
        await ctx.send(embed=success_embed)
        
        # Limpiar mensajes
        try:
            await msg.delete()
        except:
            pass
            
    except asyncio.TimeoutError:
        # Guardar sin mensaje personalizado
        stream_info = {
            'platform': platform,
            'identifier': identifier,
            'added_date': datetime.datetime.now().isoformat()
        }
        
        streams_data[user_id].append(stream_info)
        guardar_streams_data(streams_data)
        
        success_embed = discord.Embed(
            title="✅ Stream Agregado",
            description=(
                f"**Plataforma:** {platform.upper()}\n"
                f"**Usuario/ID:** `{identifier}`\n\n"
                "¡Ahora recibirás notificaciones automáticas cuando estés en vivo!"
            ),
            color=discord.Color.green()
        )
        
        await ctx.send(embed=success_embed)

@bot.command()
async def mystreams(ctx):
    """Muestra tus streams registrados"""
    
    streams_data = cargar_streams_data()
    user_id = str(ctx.author.id)
    
    if user_id not in streams_data or not streams_data[user_id]:
        embed = discord.Embed(
            title="📺 Tus Streams",
            description="No tienes streams registrados.\nUsa `!addstream` para agregar uno.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(
        title=f"📺 Streams de {ctx.author.display_name}",
        color=discord.Color.blue()
    )
    
    for i, stream in enumerate(streams_data[user_id], 1):
        platform_emoji = {
            'youtube': '📺',
            'twitch': '🟣', 
            'tiktok': '🎵'
        }.get(stream['platform'], '🔴')
        
        status = "🟢 Monitoreando" if f"{user_id}_{stream['platform']}_{stream['identifier']}" in active_streams else "⚪ Inactivo"
        
        value = f"**ID:** `{stream['identifier']}`\n**Estado:** {status}"
        
        if stream.get('message'):
            value += f"\n**Mensaje:** {stream['message']}"
        
        value += f"\n**Agregado:** <t:{int(datetime.datetime.fromisoformat(stream['added_date']).timestamp())}:R>"
        
        embed.add_field(
            name=f"{platform_emoji} {stream['platform'].upper()} [{i}]",
            value=value,
            inline=False
        )
    
    embed.set_footer(text=f"Total: {len(streams_data[user_id])} streams • Usa !delstream [número] para eliminar")
    await ctx.send(embed=embed)

@bot.command()
async def delstream(ctx, numero: int = None):
    """Elimina uno de tus streams registrados"""
    
    if numero is None:
        embed = discord.Embed(
            title="❌ Uso correcto",
            description="`!delstream [número]`\n\nUsa `!mystreams` para ver tus streams y sus números.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        return
    
    streams_data = cargar_streams_data()
    user_id = str(ctx.author.id)
    
    if user_id not in streams_data or not streams_data[user_id]:
        await ctx.send("❌ No tienes streams registrados.")
        return
    
    if numero < 1 or numero > len(streams_data[user_id]):
        await ctx.send(f"❌ Número inválido. Usa un número entre 1 y {len(streams_data[user_id])}.")
        return
    
    # Eliminar el stream
    stream_eliminado = streams_data[user_id].pop(numero - 1)
    
    # Si no quedan más streams, eliminar el usuario
    if not streams_data[user_id]:
        del streams_data[user_id]
    
    guardar_streams_data(streams_data)
    
    # Eliminar de activos si está
    stream_key = f"{user_id}_{stream_eliminado['platform']}_{stream_eliminado['identifier']}"
    if stream_key in active_streams:
        del active_streams[stream_key]
    
    embed = discord.Embed(
        title="✅ Stream Eliminado",
        description=(
            f"**Plataforma:** {stream_eliminado['platform'].upper()}\n"
            f"**Usuario/ID:** `{stream_eliminado['identifier']}`\n\n"
            "Este stream ya no será monitoreado."
        ),
        color=discord.Color.green()
    )
    
    await ctx.send(embed=embed)

@bot.command()
async def streams(ctx):
    """Muestra todos los streams registrados en el servidor"""
    
    streams_data = cargar_streams_data()
    
    if not streams_data:
        embed = discord.Embed(
            title="📺 Streams del Servidor",
            description="No hay streams registrados en el servidor.",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        return
    
    embed = discord.Embed(
        title="📺 Streams Registrados en el Servidor",
        color=discord.Color.purple()
    )
    
    total_streams = 0
    online_now = 0
    
    for user_id, user_streams in streams_data.items():
        member = ctx.guild.get_member(int(user_id))
        if member:
            stream_list = []
            for stream in user_streams:
                platform_emoji = {
                    'youtube': '📺',
                    'twitch': '🟣',
                    'tiktok': '🎵'
                }.get(stream['platform'], '🔴')
                
                status = "🟢 EN VIVO" if f"{user_id}_{stream['platform']}_{stream['identifier']}" in active_streams else "⚪"
                
                stream_list.append(f"{platform_emoji} {stream['platform'].upper()} - `{stream['identifier']}` {status}")
                total_streams += 1
                
                if status == "🟢 EN VIVO":
                    online_now += 1
            
            if stream_list:
                embed.add_field(
                    name=f"🎮 {member.display_name}",
                    value="\n".join(stream_list),
                    inline=False
                )
    
    embed.set_footer(text=f"Total: {total_streams} streams • En vivo: {online_now} • Miembros: {len(streams_data)}")
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def teststream(ctx, plataforma: str, usuario: str):
    """Comando de prueba para simular un stream (solo admin)"""
    
    platform, identifier = extract_platform_info(usuario)
    if platform == 'unknown':
        platform = plataforma
    
    # Simular datos de stream
    stream_data = {
        'live': True,
        'title': f'Stream de prueba de {ctx.author.display_name}',
        'url': f'https://{platform}.com/{usuario}',
        'viewers': 999,
        'game': 'Rocket League'
    }
    
    embed = create_stream_embed(ctx.author, platform, stream_data)
    
    await ctx.send(
        content=f"🎉 **¡PRUEBA DE STREAM!** {ctx.author.mention} está en vivo!\n<@&{ROLE_MIEMBRO}>",
        embed=embed
    )



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
        modal = HackearModal(self.ctx, self.member, self.datos, self.uid, self.target_uid, self.correct_code, self.sent_message)
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
            target_cash = self.datos[self.target_uid].get("cash", 0)
            upper = min(5000, target_cash)
            lower = min(1000, upper)
            cantidad = random.randint(lower, upper)
            # Robber gains in both monedas and cash
            self.datos[self.uid]["monedas"] = self.datos[self.uid].get("monedas", 0) + cantidad
            self.datos[self.uid]["cash"] = self.datos[self.uid].get("cash", 0) + cantidad
            # Victim loses only cash (not historical monedas)
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
            ganancia = random.randint(10000, 50000)
            agregar_a_cash_y_monedas(self.datos, self.uid, ganancia)
            guardar_datos(self.datos)
            await interaction.response.send_message(f"💥 **ÉXITO** — {self.ctx.author.mention} hackeó a {self.member.mention} y obtuvo **{ganancia} <:amatista:1420736192269390006>**!")
        else:
            multa = random.randint(13000, 15000)
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
@commands.cooldown(1, 30, commands.BucketType.user) 
async def robar(ctx, member: discord.Member):
    datos = cargar_datos()
    uid = str(ctx.author.id)
    target_uid = str(member.id)
    asegurar_usuario(datos, uid)
    asegurar_usuario(datos, target_uid)
    if datos[target_uid].get("cash", 0) <= 0:
        await ctx.send("❌ Este usuario no tiene efectivo para robar.")
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


# ------------------ SISTEMA DE TICKETS AUTO-CONFIGURABLE ------------------

async def setup_ticket_system(guild):
    """Crea automáticamente la categoría y canales para tickets"""
    global ticket_category_id, ticket_panel_channel_id, ticket_logs_channel_id
    
    print("🎫 Configurando sistema de tickets automáticamente...")
    
    # 1. Crear categoría de tickets
    try:
        # Verificar si ya existe la categoría
        existing_category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
        if existing_category:
            ticket_category_id = existing_category.id
            print(f"✅ Categoría de tickets ya existe: {existing_category.name}")
        else:
            # Crear nueva categoría
            ticket_category = await guild.create_category(
                name=TICKET_CATEGORY_NAME,
                reason="Configuración automática del sistema de tickets"
            )
            ticket_category_id = ticket_category.id
            print(f"✅ Categoría de tickets creada: {ticket_category.name}")
            
            # Configurar permisos de la categoría
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True,
                    manage_channels=True,
                    manage_messages=True
                )
            }
            await ticket_category.edit(overwrites=overwrites)
    except Exception as e:
        print(f"❌ Error creando categoría de tickets: {e}")
        return False

    # 2. Crear canal de logs de tickets
    try:
        existing_logs_channel = discord.utils.get(guild.text_channels, name=TICKET_LOGS_CHANNEL_NAME)
        if existing_logs_channel:
            ticket_logs_channel_id = existing_logs_channel.id
            print(f"✅ Canal de logs ya existe: {existing_logs_channel.name}")
        else:
            logs_channel = await guild.create_text_channel(
                name=TICKET_LOGS_CHANNEL_NAME,
                category=ticket_category,
                reason="Canal para logs del sistema de tickets"
            )
            ticket_logs_channel_id = logs_channel.id
            
            # Configurar permisos del canal de logs
            await logs_channel.set_permissions(guild.default_role, view_channel=False)
            await logs_channel.set_permissions(guild.me, view_channel=True, send_messages=True)
            
            # Mensaje de bienvenida en logs
            embed = discord.Embed(
                title="📋 SISTEMA DE TICKETS ACTIVADO",
                description=(
                    "**Este canal registrará toda la actividad del sistema de tickets:**\n\n"
                    "• 🎫 Creación de nuevos tickets\n"
                    "• 🔒 Cierre de tickets\n"
                    "• 🗑️ Eliminación de tickets\n"
                    "• 📊 Estadísticas y reportes"
                ),
                color=discord.Color.green(),
                timestamp=discord.utils.utcnow()
            )
            await logs_channel.send(embed=embed)
            print(f"✅ Canal de logs creado: {logs_channel.name}")
    except Exception as e:
        print(f"❌ Error creando canal de logs: {e}")
        return False

    # 3. Crear canal del panel de tickets (público)
    try:
        # Buscar canal existente
        existing_panel_channel = discord.utils.get(guild.text_channels, name=TICKET_PANEL_CHANNEL_NAME)
        if existing_panel_channel:
            ticket_panel_channel_id = existing_panel_channel.id
            print(f"✅ Canal del panel ya existe: {existing_panel_channel.name}")
            
            # Limpiar mensajes antiguos del bot
            async for message in existing_panel_channel.history(limit=20):
                if message.author == guild.me:
                    try:
                        await message.delete()
                    except:
                        pass
            await asyncio.sleep(1)
        else:
            # Crear nuevo canal público para el panel
            panel_channel = await guild.create_text_channel(
                name=TICKET_PANEL_CHANNEL_NAME,
                reason="Canal público para el panel de creación de tickets"
            )
            ticket_panel_channel_id = panel_channel.id
            
            # Configurar permisos públicos
            await panel_channel.set_permissions(guild.default_role, 
                view_channel=True,
                send_messages=False,
                read_message_history=True
            )
            print(f"✅ Canal del panel creado: {panel_channel.name}")

        # Crear/actualizar el panel de tickets
        panel_channel = guild.get_channel(ticket_panel_channel_id)
        if panel_channel:
            embed = discord.Embed(
                title="🎫 SISTEMA DE TICKETS DE SOPORTE",
                description=(
                    "**¿Necesitas ayuda? ¡Estamos aquí para ayudarte!**\n\n"
                    "🔹 **¿Qué son los tickets?**\n"
                    "• Canales privados para recibir soporte personalizado\n"
                    "• Solo tú y el equipo de staff pueden ver el contenido\n"
                    "• Respuesta rápida y organizada\n\n"
                    "🔹 **¿Cuándo crear un ticket?**\n"
                    "• Reportar problemas técnicos\n• Consultas sobre el servidor\n"
                    "• Reportar usuarios\n• Solicitar ayuda general\n\n"
                    "**👇 Haz clic en el botón de abajo para crear tu ticket**"
                ),
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📋 Instrucciones",
                value="1. Haz clic en **🎫 Crear Ticket**\n2. Describe tu problema en detalle\n3. Espera la respuesta del staff",
                inline=False
            )
            embed.set_footer(text="Sistema de Tickets • Soporte 24/7")
            
            view = TicketSetupView()
            await panel_channel.send(embed=embed, view=view)
            print("✅ Panel de tickets creado/actualizado exitosamente")
            
    except Exception as e:
        print(f"❌ Error creando/actualizando panel de tickets: {e}")
        return False

    print("🎫 Sistema de tickets configurado completamente!")
    return True

class TicketSetupView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Crear Ticket", style=discord.ButtonStyle.blurple, custom_id="create_ticket")
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket_channel(interaction)

    async def create_ticket_channel(self, interaction: discord.Interaction):
        global ticket_category_id
        
        guild = interaction.guild
        member = interaction.user
        
        # Verificar si el sistema está configurado
        if not ticket_category_id:
            await interaction.response.send_message(
                "❌ El sistema de tickets no está configurado. Contacta a un administrador.",
                ephemeral=True
            )
            return
        
        category = guild.get_channel(ticket_category_id)
        if not category:
            await interaction.response.send_message(
                "❌ No se encontró la categoría de tickets. Contacta a un administrador.",
                ephemeral=True
            )
            return
        
        # Verificar si ya tiene un ticket abierto
        for channel in category.channels:
            if isinstance(channel, discord.TextChannel) and channel.topic and f"ID: {member.id}" in channel.topic:
                await interaction.response.send_message(
                    "❌ Ya tienes un ticket abierto! Revisa la categoría de tickets.", 
                    ephemeral=True
                )
                return

        # Crear el canal de ticket
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            member: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True,
                embed_links=True
            ),
            guild.me: discord.PermissionOverwrite(
                view_channel=True,
                send_messages=True,
                manage_channels=True,
                manage_messages=True,
                read_message_history=True
            )
        }

        # Agregar permisos para roles de staff
        for role in guild.roles:
            if role.permissions.manage_messages or role.permissions.administrator:
                overwrites[role] = discord.PermissionOverwrite(
                    view_channel=True,
                    send_messages=True,
                    read_message_history=True,
                    manage_messages=True
                )

        try:
            ticket_channel = await category.create_text_channel(
                name=f"ticket-{member.name}-{random.randint(1000,9999)}",
                overwrites=overwrites,
                topic=f"Ticket de {member.display_name} | ID: {member.id} | Creado: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )
            
            # Embed del ticket
            embed = discord.Embed(
                title="🎫 Ticket de Soporte",
                description=(
                    f"Hola {member.mention}! 👋\n\n"
                    "**El equipo de soporte te atenderá pronto.**\n"
                    "Por favor, describe tu problema o consulta en detalle.\n\n"
                    "**Botones disponibles:**\n"
                    "• 🔒 **Cerrar Ticket** - Cierra este ticket\n"
                    "• ➕ **Agregar Usuario** - Añade alguien al ticket (Staff)\n"
                    "• 🗑️ **Eliminar Ticket** - Elimina inmediatamente (Admin)"
                ),
                color=discord.Color.blue()
            )
            embed.add_field(
                name="📋 Información",
                value=f"**Usuario:** {member.mention}\n**ID:** `{member.id}`\n**Fecha:** {discord.utils.utcnow().strftime('%d/%m/%Y %H:%M')}",
                inline=False
            )
            embed.set_footer(text="Sistema de Tickets • Responde lo antes posible")
            
            view = TicketManagementView()
            await ticket_channel.send(embed=embed, view=view)
            
            # Mensaje de confirmación
            await interaction.response.send_message(
                f"✅ **Ticket creado exitosamente!**\nVe a {ticket_channel.mention}", 
                ephemeral=True
            )
            
            # Mensaje de bienvenida en el ticket
            welcome_embed = discord.Embed(
                title="👋 ¡Bienvenido a tu ticket!",
                description="Por favor, describe tu problema o consulta y espera a que el staff te responda.",
                color=discord.Color.green()
            )
            await ticket_channel.send(embed=welcome_embed)
            
            # Log en el canal de logs
            if ticket_logs_channel_id:
                log_channel = guild.get_channel(ticket_logs_channel_id)
                if log_channel:
                    log_embed = discord.Embed(
                        title="🎫 NUEVO TICKET CREADO",
                        description=(
                            f"**Usuario:** {member.mention} (`{member.id}`)\n"
                            f"**Ticket:** {ticket_channel.mention}\n"
                            f"**Canal:** `{ticket_channel.name}`"
                        ),
                        color=discord.Color.green(),
                        timestamp=discord.utils.utcnow()
                    )
                    log_embed.set_author(name=str(member), icon_url=member.display_avatar.url)
                    await log_channel.send(embed=log_embed)
                
        except Exception as e:
            print(f"Error al crear ticket: {e}")
            await interaction.response.send_message(
                f"❌ **Error al crear el ticket:** {str(e)}", 
                ephemeral=True
            )

class TicketManagementView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Cerrar Ticket", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Verificar permisos - usuario del ticket o staff
        channel_topic = interaction.channel.topic or ""
        user_id_from_topic = None
        
        if "| ID: " in channel_topic:
            try:
                user_id_from_topic = int(channel_topic.split("| ID: ")[1].split(" |")[0])
            except:
                pass

        is_owner = interaction.user.id == user_id_from_topic
        is_staff = any(role.permissions.manage_messages for role in interaction.user.roles)
        
        if not (is_owner or is_staff):
            await interaction.response.send_message("❌ No tienes permisos para cerrar este ticket.", ephemeral=True)
            return

        # Embed de confirmación
        embed = discord.Embed(
            title="🔒 Cerrar Ticket",
            description=(
                "**¿Estás seguro de que quieres cerrar este ticket?**\n\n"
                "✅ **Sí, Cerrar** - El ticket se archivará y se enviará transcript\n"
                "❌ **Cancelar** - Mantener el ticket abierto"
            ),
            color=discord.Color.orange()
        )
        
        view = ConfirmCloseView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @discord.ui.button(label="➕ Agregar Usuario", style=discord.ButtonStyle.green, custom_id="add_user")
    async def add_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Solo staff puede agregar usuarios
        if not any(role.permissions.manage_messages for role in interaction.user.roles):
            await interaction.response.send_message("❌ Solo el staff puede agregar usuarios.", ephemeral=True)
            return

        modal = AddUserModal()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="🗑️ Eliminar", style=discord.ButtonStyle.danger, custom_id="delete_ticket")
    async def delete_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Solo administradores pueden eliminar directamente
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Solo los administradores pueden eliminar tickets directamente.", ephemeral=True)
            return

        embed = discord.Embed(
            title="🗑️ Eliminar Ticket",
            description="**¿Estás seguro de que quieres ELIMINAR este ticket?**\n\n⚠️ **Esta acción no se puede deshacer y no se guardará transcript.**",
            color=discord.Color.red()
        )
        
        view = ConfirmDeleteView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class ConfirmCloseView(View):
    def __init__(self):
        super().__init__(timeout=30)

    @discord.ui.button(label="✅ Sí, Cerrar", style=discord.ButtonStyle.red)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild
        
        # Obtener información del usuario del topic
        user_id = None
        user = None
        channel_topic = channel.topic or ""
        
        if "| ID: " in channel_topic:
            try:
                user_id = int(channel_topic.split("| ID: ")[1].split(" |")[0])
                user = await guild.fetch_member(user_id)
            except:
                pass

        # Crear transcript
        messages = []
        async for message in channel.history(limit=200, oldest_first=True):
            if not message.author.bot:  # Excluir mensajes de bots
                timestamp = message.created_at.strftime("%d/%m/%Y %H:%M")
                messages.append(f"[{timestamp}] {message.author.display_name}: {message.content}")
        
        transcript_text = "\n".join(messages) if messages else "No hay mensajes en este ticket."
        
        # Enviar transcript por DM si es posible
        if user:
            try:
                transcript_embed = discord.Embed(
                    title="📝 Transcript del Ticket Cerrado",
                    description=(
                        f"**Ticket:** `{channel.name}`\n"
                        f"**Cerrado por:** {interaction.user.mention}\n"
                        f"**Fecha:** {discord.utils.utcnow().strftime('%d/%m/%Y %H:%M')}\n\n"
                        f"**Cantidad de mensajes:** {len(messages)}"
                    ),
                    color=discord.Color.blue()
                )
                
                # Crear archivo de transcript
                transcript_file = discord.File(
                    io.BytesIO(transcript_text.encode('utf-8')), 
                    filename=f"transcript-{channel.name}.txt"
                )
                
                await user.send(embed=transcript_embed, file=transcript_file)
                transcript_sent = True
            except:
                transcript_sent = False
        else:
            transcript_sent = False

        # Log del cierre
        if ticket_logs_channel_id:
            log_channel = guild.get_channel(ticket_logs_channel_id)
            if log_channel:
                log_embed = discord.Embed(
                    title="🔒 TICKET CERRADO",
                    description=(
                        f"**Ticket:** `{channel.name}`\n"
                        f"**Usuario:** {user.mention if user else 'Desconocido'}\n"
                        f"**Cerrado por:** {interaction.user.mention}\n"
                        f"**Transcript enviado:** {'✅' if transcript_sent else '❌'}"
                    ),
                    color=discord.Color.orange(),
                    timestamp=discord.utils.utcnow()
                )
                await log_channel.send(embed=log_embed)

        # Cambiar permisos antes de eliminar (solo lectura)
        try:
            await channel.set_permissions(
                guild.default_role,
                view_channel=False
            )
            
            # Enviar mensaje final
            close_embed = discord.Embed(
                title="🔒 Ticket Cerrado",
                description=(
                    f"Este ticket ha sido cerrado por {interaction.user.mention}\n\n"
                    f"**Transcript:** {'✅ Enviado por DM' if transcript_sent else '❌ No se pudo enviar'}\n"
                    f"**El canal será eliminado en 10 segundos...**"
                ),
                color=discord.Color.red()
            )
            await channel.send(embed=close_embed)
            
            # Esperar y eliminar
            await asyncio.sleep(10)
            await channel.delete()
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error al cerrar el ticket: {e}", ephemeral=True)

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="✅ Operación cancelada.", embed=None, view=None)

class ConfirmDeleteView(View):
    def __init__(self):
        super().__init__(timeout=30)

    @discord.ui.button(label="🗑️ Sí, Eliminar", style=discord.ButtonStyle.danger)
    async def confirm_delete(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild
        
        # Log de eliminación
        if ticket_logs_channel_id:
            log_channel = guild.get_channel(ticket_logs_channel_id)
            if log_channel:
                log_embed = discord.Embed(
                    title="🗑️ TICKET ELIMINADO",
                    description=(
                        f"**Ticket:** `{channel.name}`\n"
                        f"**Eliminado por:** {interaction.user.mention}\n"
                        f"**Razón:** Eliminación directa (sin transcript)"
                    ),
                    color=discord.Color.red(),
                    timestamp=discord.utils.utcnow()
                )
                await log_channel.send(embed=log_embed)

        await interaction.response.edit_message(content="🗑️ Eliminando ticket...", embed=None, view=None)
        await asyncio.sleep(2)
        await channel.delete()

    @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.grey)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="✅ Eliminación cancelada.", embed=None, view=None)

class AddUserModal(Modal, title="Agregar Usuario al Ticket"):
    user_input = TextInput(
        label="ID o Mención del Usuario",
        placeholder="Ingresa el ID o menciona al usuario...",
        max_length=100
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Intentar obtener el usuario de diferentes formas
            user = None
            
            # Si es una mención
            if "<@" in self.user_input.value:
                user_id = int(self.user_input.value.replace('<@', '').replace('>', '').replace('!', ''))
                user = await interaction.guild.fetch_member(user_id)
            # Si es un ID numérico
            elif self.user_input.value.isdigit():
                user = await interaction.guild.fetch_member(int(self.user_input.value))
            # Si es un nombre
            else:
                # Buscar por nombre
                members = interaction.guild.members
                for member in members:
                    if self.user_input.value.lower() in member.name.lower() or self.user_input.value.lower() in member.display_name.lower():
                        user = member
                        break
            
            if not user:
                await interaction.response.send_message(
                    "❌ Usuario no encontrado. Asegúrate de usar ID, mención o nombre correcto.",
                    ephemeral=True
                )
                return
            
            # Agregar permisos al canal
            await interaction.channel.set_permissions(
                user,
                view_channel=True,
                send_messages=True,
                read_message_history=True,
                attach_files=True
            )
            
            success_embed = discord.Embed(
                title="✅ Usuario Agregado",
                description=f"{user.mention} ha sido agregado al ticket.",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=success_embed)
            
            # Anunciar en el ticket
            announce_embed = discord.Embed(
                title="👤 Usuario Agregado",
                description=f"{user.mention} fue agregado al ticket por {interaction.user.mention}",
                color=discord.Color.blue()
            )
            await interaction.channel.send(embed=announce_embed)
            
        except discord.NotFound:
            await interaction.response.send_message(
                "❌ Usuario no encontrado en el servidor.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Error: {str(e)}",
                ephemeral=True
            )

@bot.command()
@commands.has_permissions(administrator=True)
async def panelticket(ctx):
    """Crea el panel de tickets en el canal actual"""
    embed = discord.Embed(
        title="🎫 SISTEMA DE TICKETS DE SOPORTE",
        description=(
            "**¿Necesitas ayuda? ¡Estamos aquí para ayudarte!**\n\n"
            "🔹 **¿Qué son los tickets?**\n"
            "• Canales privados para recibir soporte personalizado\n"
            "• Solo tú y el equipo de staff pueden ver el contenido\n"
            "• Respuesta rápida y organizada\n\n"
            "**👇 Haz clic en el botón de abajo para crear tu ticket**"
        ),
        color=discord.Color.blue()
    )
    embed.add_field(
        name="📋 Instrucciones",
        value="1. Haz clic en **🎫 Crear Ticket**\n2. Describe tu problema en detalle\n3. Espera la respuesta del staff",
        inline=False
    )
    embed.set_footer(text="Sistema de Tickets • Soporte 24/7")
    
    view = TicketSetupView()
    await ctx.send(embed=embed, view=view)
    
    # Mensaje de confirmación
    confirm_embed = discord.Embed(
        description="✅ **Panel de tickets creado exitosamente!**",
        color=discord.Color.green()
    )
    await ctx.send(embed=confirm_embed, delete_after=10)
    
    try:
        await ctx.message.delete()
    except:
        pass

@bot.command()
@commands.has_permissions(manage_channels=True)
async def cerrarticket(ctx):
    """Cierra el ticket actual (solo staff)"""
    if not ctx.channel.name.startswith("ticket-"):
        await ctx.send("❌ Este comando solo funciona en canales de ticket.")
        return
    
    channel = ctx.channel
    guild = ctx.guild
    
    # Obtener información del usuario del topic
    user_id = None
    user = None
    channel_topic = channel.topic or ""
    
    if "| ID: " in channel_topic:
        try:
            user_id = int(channel_topic.split("| ID: ")[1].split(" |")[0])
            user = await guild.fetch_member(user_id)
        except:
            pass

    # Crear transcript
    messages = []
    async for message in channel.history(limit=200, oldest_first=True):
        if not message.author.bot:
            timestamp = message.created_at.strftime("%d/%m/%Y %H:%M")
            messages.append(f"[{timestamp}] {message.author.display_name}: {message.content}")
    
    transcript_text = "\n".join(messages) if messages else "No hay mensajes en este ticket."
    
    # Enviar transcript por DM si es posible
    if user:
        try:
            transcript_embed = discord.Embed(
                title="📝 Transcript del Ticket Cerrado",
                description=(
                    f"**Ticket:** `{channel.name}`\n"
                    f"**Cerrado por:** {ctx.author.mention}\n"
                    f"**Fecha:** {discord.utils.utcnow().strftime('%d/%m/%Y %H:%M')}"
                ),
                color=discord.Color.blue()
            )
            
            transcript_file = discord.File(
                io.BytesIO(transcript_text.encode('utf-8')), 
                filename=f"transcript-{channel.name}.txt"
            )
            
            await user.send(embed=transcript_embed, file=transcript_file)
            transcript_sent = True
        except:
            transcript_sent = False
    else:
        transcript_sent = False

    # Log del cierre
    if ticket_logs_channel_id:
        log_channel = guild.get_channel(ticket_logs_channel_id)
        if log_channel:
            log_embed = discord.Embed(
                title="🔒 TICKET CERRADO",
                description=(
                    f"**Ticket:** `{channel.name}`\n"
                    f"**Usuario:** {user.mention if user else 'Desconocido'}\n"
                    f"**Cerrado por:** {ctx.author.mention}\n"
                    f"**Transcript enviado:** {'✅' if transcript_sent else '❌'}"
                ),
                color=discord.Color.orange(),
                timestamp=discord.utils.utcnow()
            )
            await log_channel.send(embed=log_embed)

    # Mensaje final y eliminación
    close_embed = discord.Embed(
        title="🔒 Ticket Cerrado",
        description=(
            f"Este ticket ha sido cerrado por {ctx.author.mention}\n\n"
            f"**Transcript:** {'✅ Enviado por DM' if transcript_sent else '❌ No se pudo enviar'}\n"
            f"**El canal será eliminado en 5 segundos...**"
        ),
        color=discord.Color.red()
    )
    await ctx.send(embed=close_embed)
    
    await asyncio.sleep(5)
    await channel.delete()

@bot.command()
@commands.has_permissions(manage_channels=True)
async def agregarusuario(ctx, member: discord.Member):
    """Agrega un usuario al ticket actual"""
    if not ctx.channel.name.startswith("ticket-"):
        await ctx.send("❌ Este comando solo funciona en canales de ticket.")
        return
    
    await ctx.channel.set_permissions(
        member,
        view_channel=True,
        send_messages=True,
        read_message_history=True,
        attach_files=True
    )
    
    embed = discord.Embed(
        title="✅ Usuario Agregado",
        description=f"{member.mention} ha sido agregado al ticket por {ctx.author.mention}",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def ticketstats(ctx):
    """Muestra estadísticas de tickets"""
    if not ticket_category_id:
        await ctx.send("❌ El sistema de tickets no está configurado.")
        return
        
    category = ctx.guild.get_channel(ticket_category_id)
    if not category:
        await ctx.send("❌ No se encontró la categoría de tickets.")
        return
    
    active_tickets = len([ch for ch in category.channels if ch.name.startswith("ticket-")])
    
    embed = discord.Embed(
        title="📊 Estadísticas de Tickets",
        color=discord.Color.blue()
    )
    embed.add_field(name="🎫 Tickets Activos", value=f"**{active_tickets}** tickets abiertos", inline=True)
    embed.add_field(name="📁 Categoría", value=category.mention, inline=True)
    embed.add_field(name="👥 Capacidad", value=f"{active_tickets}/{50} canales", inline=True)
    
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(administrator=True)
async def resettickets(ctx):
    """Reinicia completamente el sistema de tickets (elimina todo)"""
    embed = discord.Embed(
        title="🔄 Reiniciar Sistema de Tickets",
        description=(
            "**¿Estás seguro de que quieres reiniciar el sistema de tickets?**\n\n"
            "⚠️ **Esto eliminará:**\n"
            "• Todos los tickets activos\n"
            "• La categoría de tickets\n"
            "• Los canales de panel y logs\n"
            "• Toda la configuración\n\n"
            "**Esta acción no se puede deshacer.**"
        ),
        color=discord.Color.red()
    )
    
    class ResetConfirmView(View):
        def __init__(self):
            super().__init__(timeout=30)
        
        @discord.ui.button(label="✅ Sí, Reiniciar", style=discord.ButtonStyle.danger)
        async def confirm_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
            global ticket_category_id, ticket_panel_channel_id, ticket_logs_channel_id
            
            if interaction.user != ctx.author:
                await interaction.response.send_message("❌ Solo quien ejecutó el comando puede confirmar.", ephemeral=True)
                return
                
            await interaction.response.edit_message(content="🔄 Reiniciando sistema de tickets...", embed=None, view=None)
            
            # Eliminar categoría y todos los canales
            try:
                if ticket_category_id:
                    category = ctx.guild.get_channel(ticket_category_id)
                    if category:
                        for channel in category.channels:
                            await channel.delete()
                        await category.delete()
                        
                # Resetear variables globales
                ticket_category_id = None
                ticket_panel_channel_id = None
                ticket_logs_channel_id = None
                
                success_embed = discord.Embed(
                    title="✅ Sistema de Tickets Reiniciado",
                    description="El sistema de tickets ha sido completamente reiniciado.\nUsa `!panelticket` para crear un nuevo panel.",
                    color=discord.Color.green()
                )
                await interaction.followup.send(embed=success_embed)
                
            except Exception as e:
                error_embed = discord.Embed(
                    title="❌ Error al Reiniciar",
                    description=f"No se pudo reiniciar el sistema: {str(e)}",
                    color=discord.Color.red()
                )
                await interaction.followup.send(embed=error_embed)
        
        @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.grey)
        async def cancel_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user != ctx.author:
                await interaction.response.send_message("❌ Solo quien ejecutó el comando puede cancelar.", ephemeral=True)
                return
            await interaction.response.edit_message(content="✅ Reinicio cancelado.", embed=None, view=None)
    
    await ctx.send(embed=embed, view=ResetConfirmView())

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

class SlotsRematchView(discord.ui.View):
    def __init__(self, ctx, cantidad, last_winnings, total_ganado=0):
        super().__init__(timeout=30)
        self.ctx = ctx
        self.cantidad = cantidad
        self.last_winnings = last_winnings
        self.total_ganado = total_ganado + last_winnings  # acumula el total
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

        for b in self.children:
            b.disabled = True
        await interaction.response.edit_message(content="🔄 Reiniciando partida...", view=self)
        try:
            # se pasa el total_ganado acumulado a la siguiente partida
            await self.ctx.invoke(bot.get_command("slots"), str(self.cantidad), self.total_ganado)
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
            await self.ctx.invoke(bot.get_command("slots"), nueva_apuesta, self.total_ganado)
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

    @discord.ui.button(label="Parar", style=discord.ButtonStyle.red)
    async def parar(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Solo quien jugó puede usar esto.", ephemeral=True)
            return

        self.terminado = True
        for b in self.children:
            b.disabled = True

        await interaction.response.edit_message(
            content=f"👋 ¡Gracias por jugar!\n💎 Total ganado en esta sesión: **{self.total_ganado}** <:amatista:1420736192269390006>",
            view=self
        )


@bot.command(aliases=["maquina"])
@commands.cooldown(1, 15, commands.BucketType.user)
async def slots(ctx, cantidad: str, total_ganado: int = 0):
    """!maquina <cantidad|all>"""
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

    # restar apuesta
    restar_de_cash(datos, uid, apuesta)
    guardar_datos(datos)

    simbolos = ["🍒", "🍋", "🍊", "🍇", "🔔", "⭐", "💎"]

    embed = discord.Embed(
        title="🎰 Slots",
        description=f"Bet: **{apuesta}** <:amatista:1420736192269390006>\n\nSpinning...\n\n🍒 | 🍋 | 🍊",
        color=discord.Color.gold()
    )
    message = await ctx.send(embed=embed)

    for i in range(10):
        reel1 = random.choice(simbolos)
        reel2 = random.choice(simbolos)
        reel3 = random.choice(simbolos)
        embed.description = f"Bet: **{apuesta}** <:amatista:1420736192269390006>\n\nSpinning...\n\n{reel1} | {reel2} | {reel3}"
        await message.edit(embed=embed)
        await asyncio.sleep(0.3 + i * 0.1)

    pesos = [30, 25, 20, 15, 6, 3, 1]
    reel1 = random.choices(simbolos, weights=pesos, k=1)[0]
    reel2 = random.choices(simbolos, weights=pesos, k=1)[0]
    reel3 = random.choices(simbolos, weights=pesos, k=1)[0]
        # Mostrar resultado final
    resultado = f"{reel1} | {reel2} | {reel3}"

    ganancia = 0
    if reel1 == reel2 == reel3:
        mults = {"🍒": 10, "🍋": 8, "🍊": 6, "🍇": 5, "🔔": 4, "⭐": 3, "💎": 2}
        ganancia = apuesta * mults.get(reel1, 2)
    elif reel1 == reel2 or reel2 == reel3 or reel1 == reel3:
        ganancia = apuesta * 2

    # Mostrar solo los símbolos por 1 segundo antes del resultado
    embed.description = f"Bet: **{apuesta}** <:amatista:1420736192269390006>\n\n🎰 Resultado:\n{resultado}"
    await message.edit(embed=embed)
    await asyncio.sleep(1)  # <- Espera 1 segundo antes de mostrar el resultado

    # Mostrar el resultado (ganado o perdido)
    if ganancia > 0:
        mult = obtener_multiplicador(datos, uid, "slots")
        ganancia = int(ganancia * mult)
        agregar_a_cash_y_monedas(datos, uid, ganancia)
        embed.description += f"\n\n**GANASTE!** 💎\nGanaste **{ganancia}** <:amatista:1420736192269390006>."
    else:
        embed.description += f"\n\n**PERDISTE.** 😢\nPerdiste **{apuesta}** <:amatista:1420736192269390006>."

    await message.edit(embed=embed, view=SlotsRematchView(ctx, cantidad, ganancia, total_ganado))
    guardar_datos(datos)



@bot.command()
@commands.cooldown(1, 20, commands.BucketType.user)
async def ruleta(ctx, cantidad: str, tipo: str, numero: str = None):
    import random, asyncio, discord

    datos = cargar_datos()
    uid = str(ctx.author.id)
    asegurar_usuario(datos, uid)

    # Procesar apuesta
    if cantidad.lower() == "all":
        apuesta = datos[uid].get("cash", 0)
    else:
        try:
            apuesta = int(cantidad)
        except:
            await ctx.send("❌ Cantidad inválida.")
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
            await ctx.send("❌ Debes poner el número (0–36).")
            return
        try:
            num_apostado = int(numero)
            if not 0 <= num_apostado <= 36:
                await ctx.send("❌ Número fuera de rango.")
                return
        except:
            await ctx.send("❌ Número inválido.")
            return

    # Configuración de colores
    rojos = [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]
    negros = [2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35]
    numeros = list(range(37))
    numero_ganador = random.randint(0, 36)
    color_ganador = (
        "rojo" if numero_ganador in rojos else
        "negro" if numero_ganador != 0 else
        "verde"
    )

    # Círculo de 12 posiciones (representación circular simple)
    posiciones = [
        (0, "🔴1"), (1, "⚫2"), (2, "🔴3"),
        (3, "⚫4"), (4, "🔴5"), (5, "⚫6"),
        (6, "🔴7"), (7, "⚫8"), (8, "🔴9"),
        (9, "⚫10"), (10, "🔴11"), (11, "🟩0")
    ]
    total_pos = len(posiciones)
    index_ganador = random.randint(0, total_pos - 1)
    index_actual = random.randint(0, total_pos - 1)

    # Embed inicial
    embed = discord.Embed(
        title="🎡 Ruleta girando...",
        description="",
        color=discord.Color.gold()
    )
    message = await ctx.send(embed=embed)

    def generar_ruleta(pos):
        """Devuelve un diseño circular en texto con la bola ⚪ en 'pos'."""
        circle = ["   "]*12
        for i, (_, emoji) in enumerate(posiciones):
            circle[i] = emoji
        circle[pos % total_pos] = "⚪"

        # Círculo de 3 filas
        return (
            f"   {circle[0]} {circle[1]} {circle[2]}\n"
            f" {circle[11]}       {circle[3]}\n"
            f"{circle[10]}         {circle[4]}\n"
            f" {circle[9]}       {circle[5]}\n"
            f"   {circle[8]} {circle[7]} {circle[6]}"
        )

    # Animación del giro (ralentizando)
    pasos = random.randint(35, 50)
    for i in range(pasos):
        embed.description = (
            f"Apuesta: **{apuesta}** <:amatista:1420736192269390006>\n\n"
            + generar_ruleta(index_actual)
        )
        await message.edit(embed=embed)
        index_actual = (index_actual + 1) % total_pos
        await asyncio.sleep(0.05 + (i / pasos) * 0.07)

    # Mostrar resultado
    resultado = posiciones[index_ganador][1]
    embed.title = "🎯 Ruleta detenida"
    embed.description = (
        f"Apuesta: **{apuesta}** <:amatista:1420736192269390006>\n\n"
        f"{generar_ruleta(index_ganador)}\n\n"
        f"➡️ **Número ganador:** {resultado}"
    )

    # Determinar si gana
    paridad = "par" if numero_ganador % 2 == 0 and numero_ganador != 0 else "impar"
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

    # Resultado final
    if gano:
        ganancia = int(apuesta * (35 if tipo == "numero" else 1.8))
        agregar_a_cash_y_monedas(datos, uid, ganancia)
        embed.description += f"\n\n✅ **¡GANASTE!** +{ganancia} <:amatista:1420736192269390006>"
        embed.color = discord.Color.green()
    else:
        restar_de_cash(datos, uid, apuesta)
        embed.description += f"\n\n❌ **Perdiste.** -{apuesta} <:amatista:1420736192269390006>"
        embed.color = discord.Color.red()

    await message.edit(embed=embed)
    guardar_datos(datos)


@bot.command()
@commands.cooldown(1, 10, commands.BucketType.user)
async def dado(ctx, cantidad: str, tipo: str):
    """
    !dado <cantidad|all> <tipo>
    Tipos: alto (suma > 7), bajo (suma < 7)
    """
    

    datos = cargar_datos()
    uid = str(ctx.author.id)
    asegurar_usuario(datos, uid)

    # --- Validación de apuesta ---
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
        await ctx.send("❌ Tipo inválido. Usa: `alto` o `bajo`.")
        return

    # --- Animación de lanzamiento ---
    embed = discord.Embed(
        title="🎲 Lanzando los dados...",
        description="Tirando 🎲🎲...",
        color=discord.Color.gold()
    )
    message = await ctx.send(embed=embed)
    
    dados_emojis = {
        1: "🎲💠1️⃣",
        2: "🎲💠2️⃣",
        3: "🎲💠3️⃣",
        4: "🎲💠4️⃣",
        5: "🎲💠5️⃣",
        6: "🎲💠6️⃣"
    }

    # Animación corta de “tirada”
    for _ in range(8):
        dado1 = random.randint(1, 6)
        dado2 = random.randint(1, 6)
        embed.description = f"🎲 {dados_emojis[dado1]}  {dados_emojis[dado2]}\n\nGirando..."
        await message.edit(embed=embed)
        await asyncio.sleep(0.25)

    # --- Resultado final ---
    dado1 = random.randint(1, 6)
    dado2 = random.randint(1, 6)
    suma = dado1 + dado2

    # Determinar si gana o pierde
    gano = (tipo == "alto" and suma > 7) or (tipo == "bajo" and suma < 7)

    # Mostrar resultado final
    embed.title = "🎲 Resultado final"
    embed.description = f"{dados_emojis[dado1]}  {dados_emojis[dado2]}  ➜ **Suma:** {suma}"

    if gano:
        ganancia_base = apuesta * 1.5
        mult = obtener_multiplicador(datos, uid, "dice")
        ganancia = int(ganancia_base * mult)
        agregar_a_cash_y_monedas(datos, uid, ganancia)
        embed.add_field(
            name="✅ ¡Has ganado!",
            value=f"Ganaste **{ganancia}** <:amatista:1420736192269390006>.",
            inline=False
        )
        embed.color = discord.Color.green()
    else:
        restar_de_cash(datos, uid, apuesta)
        embed.add_field(
            name="❌ Perdiste",
            value=f"Perdiste **{apuesta}** <:amatista:1420736192269390006>.",
            inline=False
        )
        embed.color = discord.Color.red()

    await message.edit(embed=embed)
    guardar_datos(datos)

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
    "tickets": {
        "!panelticket": "Crea el panel de tickets de soporte. (Admin)",
        "!cerrarticket": "Cierra el ticket actual. (Staff)",
        "!agregarusuario @usuario": "Agrega un usuario al ticket actual. (Staff)",
        "!ticketstats": "Muestra estadísticas de tickets. (Admin)",
        "!resettickets": "Reinicia completamente el sistema de tickets. (Admin)"
    },
    "streams": {
        "!addstream [plataforma] [usuario/URL]": "Registra tu stream para notificaciones automáticas. (Miembros)",
        "!mystreams": "Muestra tus streams registrados.",
        "!delstream [número]": "Elimina uno de tus streams registrados.",
        "!streams": "Muestra todos los streams registrados en el servidor.",
        "!teststream [plataforma] [usuario]": "Prueba una notificación de stream. (Admin)"
    },
    "otros": {
        "!ayuda (categoria)": "Muestra la lista de comandos o los de una categoría específica."
    },
    "funciones": {
        "Sistema de Economía": "Gestiona monedas, banco, trabajos, tienda con items para multiplicadores.",
        "Minijuegos Interactivos": "Juegos como blackjack, ppt, apostar, adivina con apuestas y rematch.",
        "Moderación Completa": "Comandos para admins: kick, ban, clear, avisos, reactroles, gestión de dinero.",
        "Sistema de Niveles y XP": "Gana XP por mensajes, sube niveles con recompensas cada 10 niveles.",
        "Registro de Miembros": "Panel interactivo para registrarse como freestyler o competitivo con roles automáticos.",
        "Sistema de Tickets": "Tickets de soporte privados con transcripts y gestión automática.",
        "Notificaciones de Streams": "Detección automática de streams en YouTube, Twitch y TikTok.",
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
    embed.add_field(
        name="Categorías", 
        value="• Básicos\n• Moderación\n• Economía\n• Minijuegos\n• Tickets\n• Streams\n• Otros\n• Funciones", 
        inline=False
    )
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

    @discord.ui.button(label="🎫 Tickets", style=discord.ButtonStyle.primary, row=2)
    async def tickets(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Solo el autor puede usar esto.", ephemeral=True)
            return
        embed = create_category_embed("tickets", self.ctx)
        view = CategoryHelpView(self.ctx)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="📺 Streams", style=discord.ButtonStyle.primary, row=2)
    async def streams(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Solo el autor puede usar esto.", ephemeral=True)
            return
        embed = create_category_embed("streams", self.ctx)
        view = CategoryHelpView(self.ctx)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="🔧 Otros", style=discord.ButtonStyle.primary, row=3)
    async def otros(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            await interaction.response.send_message("Solo el autor puede usar esto.", ephemeral=True)
            return
        embed = create_category_embed("otros", self.ctx)
        view = CategoryHelpView(self.ctx)
        await interaction.response.edit_message(embed=embed, view=view)

    @discord.ui.button(label="⚙️ Funciones", style=discord.ButtonStyle.primary, row=3)
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
            await ctx.send(
                "❌ Categoría no encontrada. Usa: "
                "`basicos`, `moderacion`, `economia`, `minijuegos`, `tickets`, `streams`, `otros`."
            )
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
    bot.run(os.getenv("TOKEN"))
