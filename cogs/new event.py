# Módulos de discord
from discord import Color
from discord.ext import commands
import discord

# Módulos extra
from time import time
from typing import Optional, Dict, Any
import logging

# Módulos de bot
from func.terminal import printr
from func.botconfig import configJson, DefaultServerConfig, GetPrefix
from func.database import DatabaseConnect
from templates.views import VerificationView, VeriConfiView, ClosedTicketToolView
from templates.embeds import SimpleEmbed

# Configurar logging
logger = logging.getLogger(__name__)

class Event(commands.Cog):
    #
    # Cog para manejar eventos de Discord como mensajes, voice chat y creación de canales.
    #
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.voice_sessions: Dict[int, float] = {}
    
    @commands.Cog.listener()
    async def on_ready(self) -> None:
        """Evento ejecutado cuando el bot está listo."""
        try:
            # Recargar las views de mensajes ya enviados
            self.bot.add_view(VerificationView())
            self.bot.add_view(VeriConfiView())
            self.bot.add_view(ClosedTicketToolView())
            printr("Views de event.py cargadas correctamente.", 1)
            logger.info("Event cog cargado exitosamente")
        except Exception as e:
            logger.error(f"Error al cargar views: {e}")
            printr(f"Error al cargar views: {e}", 3)
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """
        Maneja los mensajes enviados y actualiza las estadísticas del usuario.
        """
        # Validaciones iniciales
        if not self._should_process_message(message):
            return
        
        try:
            # Obtener datos del mensaje
            user_id = str(message.author.id)
            guild_id = str(message.guild.id)
            username = str(message.author)
            
            # Crear configuración del servidor si no existe
            await self._ensure_server_config(message.guild, guild_id)
            
            # Actualizar estadísticas del usuario
            await self._update_user_message_stats(user_id, username, message, guild_id)
            
        except Exception as e:
            logger.error(f"Error en on_message: {e}")
            printr(f"Error procesando mensaje: {e}", 3)
        
        # Procesar comandos
        await self.bot.process_commands(message)
    
    @commands.Cog.listener()
    async def on_voice_state_update(
        self, 
        member: discord.Member, 
        before: discord.VoiceState, 
        after: discord.VoiceState
    ) -> None:
        """
        Maneja los cambios de estado de voz y registra el tiempo en voice chat.
        """
        user_id = member.id
        guild_id = str(member.guild.id)
        
        try:
            # Usuario se une a un canal de voz
            if before.channel is None and after.channel is not None:
                self.voice_sessions[user_id] = time()
                logger.debug(f"Usuario {member.display_name} se unió a voice chat")
            
            # Usuario sale de un canal de voz
            elif before.channel is not None and after.channel is None:
                await self._handle_voice_session_end(member, user_id, guild_id)
                
        except Exception as e:
            logger.error(f"Error en on_voice_state_update: {e}")
            printr(f"Error procesando voice state: {e}", 3)
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        """
        Maneja la creación de nuevos canales, especialmente tickets de verificación.
        """
        try:
            guild_id = str(channel.guild.id)
            
            # Verificar si el servidor tiene configuración
            if guild_id not in configJson:
                return
            
            ticket_config = configJson[guild_id].get("ticket")
            if not ticket_config:
                return
            
            # Verificar si es un canal de ticket de verificación
            if await self._is_verification_ticket(channel, ticket_config):
                await self._setup_verification_ticket(channel)
                
        except Exception as e:
            logger.error(f"Error en on_guild_channel_create: {e}")
            printr(f"Error creando canal: {e}", 3)
    
    def _should_process_message(self, message: discord.Message) -> bool:
        """
        Determina si un mensaje debe ser procesado.
        """
        # Saltar si es un bot
        if message.author.bot:
            return False
        
        # Saltar si no es en un servidor
        if not message.guild:
            return False
        
        # Saltar si es un comando (para evitar doble ejecución)
        prefix = GetPrefix(self.bot, message)
        if message.content.startswith(prefix):
            return False
        
        return True
    
    async def _ensure_server_config(self, guild: discord.Guild, guild_id: str) -> None:
        """
        Asegura que el servidor tenga configuración.
        """
        if guild_id not in configJson:
            printr(f"El servidor {guild.name} no tiene configuración JSON.", 2)
            DefaultServerConfig(guild_id)
    
    async def _update_user_message_stats(
        self, 
        user_id: str, 
        username: str, 
        message: discord.Message, 
        guild_id: str
    ) -> None:
        """
        Actualiza las estadísticas de mensajes del usuario.
        """
        conn = None
        try:
            conn = DatabaseConnect(guild_id)
            cursor = conn.cursor()
            
            # Buscar datos existentes del usuario
            cursor.execute("SELECT messages FROM data WHERE id = ?", (user_id,))
            data = cursor.fetchone()
            
            if data:
                # Actualizar contador existente
                new_count = data[0] + 1
                cursor.execute("UPDATE data SET messages = ? WHERE id = ?", (new_count, user_id))
            else:
                # Crear nuevo registro
                join_date = message.author.joined_at.strftime("%d/%m/%Y") if message.author.joined_at else "N/A"
                cursor.execute(
                    "INSERT INTO data (id, username, date, messages, voicechat) VALUES (?, ?, ?, ?, ?)",
                    (user_id, username, join_date, 1, 0)
                )
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error actualizando estadísticas de mensaje: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    async def _handle_voice_session_end(self, member: discord.Member, user_id: int, guild_id: str) -> None:
        """
        Maneja el final de una sesión de voice chat.
        """
        if user_id not in self.voice_sessions:
            return
        
        conn = None
        try:
            start_time = self.voice_sessions.pop(user_id)
            # Corregir el cálculo: dividir por 3600 para obtener horas
            session_hours = (time() - start_time) / 3600
            
            conn = DatabaseConnect(guild_id)
            cursor = conn.cursor()
            
            # Buscar datos existentes del usuario
            cursor.execute("SELECT voicechat FROM data WHERE id = ?", (str(user_id),))
            data = cursor.fetchone()
            
            if data:
                # Sumar al tiempo existente
                total_hours = data[0] + session_hours
                cursor.execute("UPDATE data SET voicechat = ? WHERE id = ?", (total_hours, str(user_id)))
            else:
                # Crear nuevo registro
                join_date = member.joined_at.strftime("%d/%m/%Y") if member.joined_at else "N/A"
                cursor.execute(
                    "INSERT INTO data (id, username, date, messages, voicechat) VALUES (?, ?, ?, ?, ?)",
                    (str(user_id), member.display_name, join_date, 0, session_hours)
                )
            
            conn.commit()
            logger.debug(f"Sesión de voice chat registrada: {session_hours:.2f} horas para {member.display_name}")
            
        except Exception as e:
            logger.error(f"Error manejando fin de sesión de voz: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    async def _is_verification_ticket(self, channel: discord.abc.GuildChannel, ticket_config: Dict[str, Any]) -> bool:
        """
        Verifica si un canal es un ticket de verificación.
        """
        try:
            # Verificar si está en la categoría correcta
            if channel.category_id != ticket_config.get("category"):
                return False
            
            # Verificar si el nombre coincide con el patrón
            verification_config = ticket_config.get("panels", {}).get("verification", {})
            expected_name = verification_config.get("name", "")
            
            if not expected_name:
                return False
            
            channel_name_parts = str(channel.name).split("-")
            return len(channel_name_parts) > 0 and channel_name_parts[0] == expected_name
            
        except Exception as e:
            logger.error(f"Error verificando si es ticket de verificación: {e}")
            return False
    
    async def _setup_verification_ticket(self, channel: discord.TextChannel) -> None:
        """
        Configura un ticket de verificación recién creado.
        """
        try:
            embed = SimpleEmbed(
                "Verificación", 
                "Inicia el proceso para obtener la información necesaria para completar la verificación.", 
                Color.blurple()
            )
            
            # Verificar si el topic contiene un ID de usuario válido
            user_mention = f"<@{channel.topic}>" if channel.topic and channel.topic.isdigit() else ""
            
            await channel.send(user_mention, embed=embed, view=VerificationView())
            logger.info(f"Ticket de verificación configurado en {channel.name}")
            
        except Exception as e:
            logger.error(f"Error configurando ticket de verificación: {e}")
            raise

# Función de configuración
async def setup(bot: commands.Bot) -> None:
    """
    Función para configurar el cog.
    """
    await bot.add_cog(Event(bot))