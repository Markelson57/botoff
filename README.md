# Markelsoft AI v2.1 - Discord Bot

Un bot de Discord avanzado con sistema de economía, minijuegos, moderación, tickets, streams y más funciones interactivas. Desarrollado con discord.py para servidores de gaming y comunidades.

![Discord](https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![License](https://img.shields.io/badge/Licencia-Open%20Source-green?style=for-the-badge)

## 🚀 Características Principales

### 💰 **Sistema de Economía Completo**
- **Monedas y Banco**: Gestiona efectivo (cash) y banco con depósitos/retiros
- **Trabajos Dinámicos**: +30 empleos diferentes con ganancias variables
- **Tienda Avanzada**: Items que mejoran ganancias en minijuegos
- **Donaciones**: Transfiere monedas entre usuarios de forma segura
- **Ranking Interactivo**: Leaderboard con paginación por botones

### 🎮 **Minijuegos Interactivos**
- **🎲 Blackjack**: Juego completo contra el bot con interfaz visual
- **🎰 Máquina Tragaperras**: Slots con animación y efectos visuales
- **🎡 Ruleta Europea**: Apuestas en colores, par/impar o números
- **🎯 Dados**: Sistema de apuestas alto/bajo con animaciones
- **✂️ Piedra Papel Tijera**: Clásico juego con sistema de apuestas
- **🔢 Adivina el Número**: Entre 1-100 con pistas inteligentes
- **🪙 Apostar**: Cara o cruz con multiplicadores por items

### 🛡️ **Sistema de Moderación Avanzado**
- **Comandos de Staff**: Kick, ban, clear con verificaciones de permisos
- **React Roles**: Sistema automático de asignación de roles por reacciones
- **Avisos Interactivos**: Crea embeds profesionales paso a paso
- **Gestión Económica**: Control total sobre la economía del servidor

### 🎫 **Sistema de Tickets de Soporte**
- **Panel Automático**: Se crea automáticamente al iniciar el bot
- **Tickets Privados**: Canales privados para soporte personalizado
- **Gestión de Staff**: Cerrar tickets y agregar usuarios
- **Transcripts**: Historial completo enviado por DM al cerrar
- **Sistema de Logs**: Registro completo de toda la actividad

### 📺 **Sistema de Notificaciones de Streams**
- **Multiplataforma**: YouTube, Twitch y TikTok
- **Detección Automática**: Verifica cada 5 minutos
- **Solo Miembros**: Exclusivo para usuarios con rol de miembro
- **Notificaciones Inteligentes**: Embeds profesionales con información del stream
- **Mensajes Personalizados**: Cada streamer puede agregar su mensaje

### 👥 **Sistema de Membresía Inteligente**
- **Registro Interactivo**: Panel con formulario modal profesional
- **Roles Automáticos**: Freestyler, Competitivo o ambos
- **Aprobación Manual**: El owner revisa y aprueba cada solicitud
- **Sistema de Backup**: Respaldo completo del servidor (solo owner)

### 📈 **Sistema de Niveles y XP**
- **XP por Mensajes**: Gana experiencia automáticamente
- **Recompensas por Nivel**: Bonos especiales cada 10 niveles
- **Ranking Visual**: Lista paginada con medallas para top 3
- **Progreso Visual**: Barra de progreso en mensajes de nivel

## 🎯 **Tabla de Comandos**

| Categoría | Comandos Principales | Permisos Requeridos |
|-----------|---------------------|-------------------|
| **🟢 Básicos** | `!saludar`, `!info`, `!userinfo`, `!bal`, `!lvl`, `!ranking` | Todos |
| **🛡️ Moderación** | `!kick`, `!ban`, `!clear`, `!aviso`, `!reactrole` | Capitán+ |
| **💰 Economía** | `!trabajar`, `!depositar`, `!retirar`, `!robar`, `!tienda` | Todos |
| **🎮 Minijuegos** | `!blackjack`, `!maquina`, `!ruleta`, `!ppt`, `!dado` | Todos |
| **🎫 Tickets** | `!cerrarticket`, `!agregarusuario`, `!ticketstats` | Capitán+ |
| **📺 Streams** | `!addstream`, `!mystreams`, `!delstream`, `!streams` | Miembros |

## ⚙️ **Instalación Rápida**

### 📋 Requisitos
- Python 3.8 o superior
- discord.py 2.3.0+
- python-dotenv

### 🚀 Instalación en 4 pasos:

1. **Instalar dependencias**:
```bash
pip install discord.py python-dotenv aiohttp
```

2. **Configurar variables de entorno**:
```env
DISCORD_TOKEN=tu_token_de_discord_aqui
```

3. **Configurar IDs del servidor** (en el código):
```python
GUILD_ID = 1405199387642040321
ROLE_MIEMBRO = 1406648558790250668
# ... otros IDs según tu servidor
```

4. **Ejecutar el bot**:
```bash
python bot.py
```

## 🎮 **Sistema de Items de la Tienda**

| Item | Precio | Multiplicador | Límite | Efecto |
|------|--------|---------------|--------|---------|
| 🃏 Blackjack | 5,000 | ×1.5 | 5 | Mejora ganancias en blackjack |
| 🎲 Apostar | 3,000 | ×1.2 | 3 | Mejora apuestas cara/cruz |
| ✂️ PPT | 10,000 | ×2.0 | 1 | Duplica ganancias en PPT |
| 🎰 Slots | 4,000 | ×1.3 | 4 | Mejora premios en tragaperras |
| 🎡 Ruleta | 6,000 | ×1.4 | 3 | Aumenta ganancias en ruleta |
| 🎯 Dados | 3,500 | ×1.25 | 5 | Mejora apuestas en dados |

## 🎫 **Sistema de Tickets**

### Características:
- ✅ **Creación automática** de categoría y canales
- ✅ **Tickets privados** solo visibles para usuario y staff
- ✅ **Prevención de múltiples tickets** por usuario
- ✅ **Transcripts automáticos** enviados por DM
- ✅ **Sistema de logs** completo
- ✅ **Interfaz visual** con botones

### Comandos para Staff:
```bash
!cerrarticket          # Cierra el ticket actual
!agregarusuario @user  # Agrega usuario al ticket
!ticketstats          # Estadísticas del sistema
```

## 📺 **Sistema de Streams**

### Plataformas soportadas:
- **YouTube** - URLs de canal o videos en vivo
- **Twitch** - Nombres de usuario
- **TikTok** - Usuarios de TikTok Live

### Comandos para Miembros:
```bash
!addstream twitch tu_usuario
!addstream youtube https://youtube.com/tu_canal  
!mystreams            # Ver streams registrados
!delstream 1          # Eliminar stream por número
```

## 🛡️ **Sistema de Permisos**

### Estructura de Staff:
- **🎯 Capitán**: Moderación básica + tickets
- **⚡ Co-Líder**: Todos los permisos + economía admin
- **👑 Líder**: Permisos completos de administrador

### Verificación automática:
```python
@commands.has_permissions(manage_channels=True)  # Para tickets
@commands.has_permissions(kick_members=True)     # Para moderación  
@commands.has_permissions(administrator=True)    # Para comandos admin
```

## 🔧 **Configuración Avanzada**

### Variables principales a modificar:
```python
# IDs esenciales
GUILD_ID = 1405199387642040321
ROLE_MIEMBRO = 1406648558790250668
ROLE_COMPETITIVO = 1406648557808648367
ROLE_FREESTYLER = 1406648556768596059

# Configuración económica
ALLOW_NEGATIVE_BALANCE = True
STREAMS_LOOP_INTERVAL = 30  # 30 segundos
```

### Estructura de archivos:
```
📁 Markelsoft-Bot/
├── 📄 bot.py                 # Código principal
├── 📄 datos.json            # Datos de usuarios
├── 📄 streams_data.json     # Streams registrados
├── 📄 reactroles.json       # Configuración de react roles
├── 📄 .env                  # Variables de entorno
└── 📁 backups/              # Backups del servidor
```

## 🎨 **Personalización**

### Estados dinámicos del bot:
El bot rota entre estos estados cada 30-60 segundos:
- 🎮 "Rocket League"
- 🎵 "los mejores freestylers"  
- 📹 "clips de Markelson"
- ❓ "usa !ayuda para comenzar"
- 🔄 "nuevas funciones del bot"
- 🧠 "el sistema Markelsoft"
- 🔥 "el servidor al máximo"

### Emojis personalizados:
- 💎 `<:amatista:1420736192269390006>` - Moneda del sistema
- 🚗 `<:octane:1424532429372129411>` - Emoji personalizado
- 👑 `<:dominus:1424532295594807296>` - Emoji personalizado

## 📊 **Eventos Automáticos**

| Evento | Descripción | Frecuencia |
|--------|-------------|------------|
| **Bienvenidas** | Mensaje embed en canal designado | Por cada nuevo miembro |
| **Niveles** | Notificación de subida de nivel | Por mensaje (15-25 XP) |
| **Streams** | Verificación de streams en vivo | Cada 5 minutos |
| **Logs** | Registro de eventos importantes | En tiempo real |
| **Backup** | Respaldo del servidor | Manual (solo owner) |

## 🔐 **Características de Seguridad**

- ✅ **Verificación de permisos** en todos los comandos
- ✅ **Cooldowns inteligentes** para prevenir spam
- ✅ **Validación de entradas** en todos los modales
- ✅ **Sistema de logs** para auditoría
- ✅ **Backup seguro** con envío por DM

## 🐛 **Solución de Problemas**

### Errores comunes:
1. **"Missing Permissions"**: Verificar roles del bot
2. **"Command Not Found"**: Revisar prefijo (!) 
3. **"JSON Decode Error"**: Eliminar archivos corruptos
4. **"Rate Limited"**: Esperar cooldown del comando

### Logs de diagnóstico:
El bot muestra información detallada en consola:
- ✅ Estado de conexión
- ✅ Comandos sincronizados  
- ✅ Sistemas inicializados
- ✅ Errores y advertencias

## 🤝 **Contribución**

¿Quieres mejorar el bot? ¡Tus contribuciones son bienvenidas!

1. **Fork** el proyecto
2. **Crea una rama** para tu feature (`git checkout -b feature/AmazingFeature`)
3. **Commit** tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. **Push** a la rama (`git push origin feature/AmazingFeature`)
5. **Abre un Pull Request**

## 📄 **Licencia**

Este proyecto es de **código abierto** bajo licencia MIT. Puedes:
- ✅ Usarlo en tu servidor
- ✅ Modificar el código
- ✅ Distribuir versiones modificadas
- ✅ Usar comercialmente

## 🆘 **Soporte y Contacto**

**Desarrollador Principal**: Markelson  
**Servidor de Soporte**: [AMETHYX CLAN](https://discord.gg/sQEsdrMrxN)

**Características del soporte**:
- 🐛 Reporte de bugs
- 💡 Sugerencias de features
- 🛠️ Ayuda con configuración
- 📚 Tutoriales y guías

---

### 🎉 **¡Todo listo para usar!**

El bot incluye **+50 comandos**, **8 sistemas principales** y **interfaz completamente en español**. ¡Disfruta de todas las funciones!

**Desarrollado con ❤️ por Markelson**  
*¿Preguntas? ¡No dudes en contactar!*