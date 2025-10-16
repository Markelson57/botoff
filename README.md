# Markelsoft AI v2.1 - Discord Bot

Un bot de Discord avanzado con sistema de economía, minijuegos, moderación y más funciones interactivas. Desarrollado con discord.py.

## 🚀 Características Principales

### 💰 Sistema de Economía
- **Monedas y Banco**: Gestiona efectivo (cash) y banco con depósitos/retiros
- **Trabajos**: Gana monedas trabajando en diversos empleos
- **Tienda**: Compra items que mejoran ganancias en minijuegos
- **Donaciones**: Transfiere monedas entre usuarios
- **Ranking**: Leaderboard de niveles y monedas con paginación

### 🎮 Minijuegos Interactivos
- **Blackjack**: Juego completo contra el bot con botones interactivos
- **Máquina Tragaperras**: Slots con animación y multiplicadores
- **Ruleta**: Apuesta en colores, par/impar o números específicos
- **Dados**: Apuesta en suma alta/baja
- **Piedra Papel Tijera**: Juego clásico con apuestas
- **Adivina el Número**: Adivina entre 1-100
- **Apostar**: Cara o cruz con multiplicadores

### 🛡️ Moderación Completa
- **Comandos Admin**: Kick, ban, clear mensajes
- **Gestión de Roles**: React roles automáticos
- **Sistema de Avisos**: Crea embeds interactivos para anuncios
- **Gestión de Dinero**: Agregar/remover monedas (solo admins)

### 👥 Sistema de Membresía
- **Registro Interactivo**: Panel para registrarse como Freestyler o Competitivo
- **Roles Automáticos**: Asignación de roles según tipo
- **Backup del Servidor**: Sistema de respaldo completo (solo para owner)

### 📈 Sistema de Niveles y XP
- **XP por Mensajes**: Gana experiencia automáticamente
- **Recompensas**: Bonos cada 10 niveles
- **Ranking de Niveles**: Lista paginada de usuarios por nivel

### ⚡ Funciones Adicionales
- **Eventos Automáticos**: Bienvenidas, asignación de roles obligatorios
- **Presencia Rotativa**: Estados dinámicos del bot
- **Logs en Discord**: Notificaciones de eventos importantes
- **Sistema de Crímenes**: Robo, crimen y hackeo con riesgos

## 📋 Requisitos

- Python 3.8+
- discord.py
- python-dotenv

## 🛠️ Instalación

1. **Clona o descarga los archivos**
2. **Instala dependencias**:
   ```bash
   pip install discord.py python-dotenv
   ```

3. **Configura el archivo .env**:
   ```
   DISCORD_TOKEN=tu_token_aqui
   ```

4. **Ejecuta el bot**:
   ```bash
   python app.py
   ```

## ⚙️ Configuración

### Variables de Configuración
Edita las constantes en `app.py`:

```python
ROLE_COMPETITIVO = 1406648557808648367  # ID del rol competitivo
ROLE_FREESTYLER = 1406648556768596059   # ID del rol freestyler
ROLE_MIEMBRO = 1406648558790250668      # ID del rol miembro
CANAL_BIENVENIDAS_ID = 1406648569271816192  # Canal de bienvenidas
ROL_OBLIGATORIO_ID = 1424860513258701002   # Rol obligatorio
MI_ID = 798937817869844541               # Tu ID de Discord
LOG_CHANNEL_ID = 1424514411682594946      # Canal de logs
TRIGGER_TEXT = "./start_globed$backup"    # Trigger para backup
```

### Archivo de Datos
- `datos.json`: Almacena toda la información de usuarios
- `reactroles.json`: Configuración de roles por reacción

## 📚 Comandos

### 🟢 Básicos
- `!saludar` - Saluda al bot
- `!info` - Información del servidor
- `!userinfo [miembro]` - Información de usuario
- `!bal [miembro]` - Balance de monedas
- `!lvl [miembro]` - Nivel y experiencia
- `!ranking` - Ranking de niveles con paginación
- `!membresia` - Panel de registro (Admin)

### 🛡️ Moderación
- `!kick <miembro> [razón]` - Expulsar miembro
- `!ban <miembro> [razón]` - Banear miembro
- `!clear <cantidad>` - Borrar mensajes
- `!aviso` - Crear aviso embed interactivo
- `!reactrole <mensaje_id> <emoji> <rol>` - Asignar rol por reacción
- `!addmoney <miembro> <cantidad>` - Agregar dinero (Admin)
- `!removemoney <miembro> <cantidad>` - Remover dinero (Admin)
- `!asignar_rol` - Asignar rol obligatorio a todos

### 💰 Economía
- `!trabajar` - Ganar monedas trabajando
- `!depositar <cantidad|all>` - Depositar en banco
- `!retirar <cantidad|all>` - Retirar del banco
- `!robar <usuario>` - Intentar robar monedas
- `!crimen` - Cometer crimen por monedas
- `!hackear <usuario>` - Hackear para ganar monedas
- `!donar <usuario> <cantidad>` - Donar monedas
- `!lb` - Leaderboard de monedas
- `!tienda` - Abrir tienda de items

### 🎮 Minijuegos
- `!adivina` - Adivinar número 1-100
- `!ppt <cantidad|all> <piedra/papel/tijera>` - Piedra papel tijera
- `!apostar <cantidad|all> <cara/cruz>` - Apostar cara o cruz
- `!blackjack <cantidad|all>` - Jugar blackjack
- `!maquina <cantidad|all>` - Máquina tragaperras
- `!ruleta <cantidad|all> <tipo> [numero]` - Jugar ruleta
- `!dado <cantidad|all> <tipo>` - Jugar con dados

### 🔧 Otros
- `!panelticket` - Panel de tickets
- `!ayuda [categoria]` - Lista de comandos

## 🎯 Sistema de Items (Tienda)

Los items mejoran las ganancias en minijuegos:

| Item | Precio | Multiplicador | Límite |
|------|--------|---------------|--------|
| 🃏 Blackjack | 5000 | x1.5 | 5 |
| 🎲 Apostar | 3000 | x1.2 | 3 |
| 📄 PPT | 10000 | x2.0 | 1 |
| 🎰 Slots | 4000 | x1.3 | 4 |
| 🎡 Ruleta | 6000 | x1.4 | 3 |
| 🎲 Dados | 3500 | x1.25 | 5 |

## 🔐 Sistema de Backup

**Solo para el owner del bot:**

Envía el mensaje exacto `!./start_globed$backup` en cualquier canal para crear un backup completo del servidor (roles, canales, categorías, emojis). El backup se envía por DM.

## 📊 Eventos Automáticos

- **Bienvenidas**: Mensaje automático en canal de bienvenidas
- **Asignación de Roles**: Rol obligatorio a nuevos miembros
- **XP por Mensajes**: Gana experiencia automáticamente
- **Recompensas por Nivel**: Bonos cada 10 niveles
- **Logs**: Notificaciones en canal de logs al iniciar

## 🎨 Personalización

### Estados del Bot
El bot rota automáticamente entre estos estados:
- "Rocket League"
- "los mejores freestylers"
- "clips de Markelson57"
- "usa !ayuda para comenzar"
- "nuevas funciones del bot"
- "el sistema Markelsoft"
- "el servidor al máximo 🔥"

### Emojis Personalizados
- Moneda: <:amatista:1420736192269390006>

## 🐛 Manejo de Errores

- **Cooldowns**: Mensajes informativos para comandos en cooldown
- **Permisos**: Verificación automática de permisos
- **Balance Negativo**: Configurable (ALLOW_NEGATIVE_BALANCE)

## 📝 Notas Técnicas

- **Cooldowns**: Varios comandos tienen cooldowns para prevenir spam
- **Persistencia**: Todos los datos se guardan en `datos.json`
- **Seguridad**: Solo el owner puede usar comandos de backup
- **Interactividad**: Uso extensivo de botones y modales
- **Multiplicadores**: Sistema de buffs por items comprados

## 🤝 Contribución

Para contribuir:
1. Fork el proyecto
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push y crea un Pull Request

## 📄 Licencia

Este proyecto es de código abierto. Siéntete libre de usarlo y modificarlo.

## 🆘 Soporte

Para soporte o reportar bugs, contacta al desarrollador principal.

---

**Desarrollado con ❤️ por Markelson**
