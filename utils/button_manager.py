from typing import List, Union
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import config
import logging
from pyrogram.errors import UserNotParticipant, BadRequest
from pyrogram.enums import ChatMemberStatus
from pyrogram import Client

class ButtonManager:
    def __init__(self):
        self.db_channel = config.DB_CHANNEL_ID
        self._init_channels()

    def _init_channels(self):
        """Initialize force subscription channels"""
        self.channel_configs = []
        # Only initialize the first two channels as per requirement
        channels = [
            (config.FSUB_CHNL_ID, config.FSUB_CHNL_LINK, "Main"),
            (config.FSUB_CHNL_2_ID, config.FSUB_CHNL_2_LINK, "Second")
        ]
        
        for channel_id, link, name in channels:
            if channel_id and link:
                try:
                    # Handle channel ID with or without -100 prefix
                    clean_id = str(channel_id).replace("-100", "")
                    int_id = int(clean_id)
                    final_id = f"-100{int_id}" if not str(int_id).startswith("-100") else str(int_id)
                    self.channel_configs.append((final_id, link, name))
                except (ValueError, TypeError):
                    logging.error(f"Invalid channel ID format for {name} channel: {channel_id}")

    async def check_force_sub(self, client: Client, user_id: int) -> bool:
        """Check user's subscription status in all required channels"""
        if not self.channel_configs:
            return True

        for channel_id, channel_link, name in self.channel_configs:
            try:
                # Try to get chat member info
                member = await client.get_chat_member(chat_id=int(channel_id), user_id=user_id)
                
                # Check if user is banned/kicked first
                if member.status in [ChatMemberStatus.BANNED, ChatMemberStatus.LEFT, ChatMemberStatus.RESTRICTED]:
                    return False
                    
                # Check for valid member status
                if member.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                    return False
                    
            except UserNotParticipant:
                return False
            except BadRequest as e:
                logging.error(f"Bot is not admin in channel {name} ({channel_id}) or channel is invalid: {str(e)}")
                continue
            except Exception as e:
                logging.error(f"Error checking subscription in {name} ({channel_id}): {str(e)}")
                continue
                
        return True

    def get_force_sub_buttons(self) -> InlineKeyboardMarkup:
        """Generate force subscription buttons without check button"""
        buttons = []
        
        for channel_id, channel_link, name in self.channel_configs:
            if channel_id and channel_link:
                buttons.append([
                    InlineKeyboardButton(
                        text=f"📢 Join {name} Channel",
                        url=channel_link
                    )
                ])
        
        return InlineKeyboardMarkup(buttons)

    def start_button(self) -> InlineKeyboardMarkup:
        """Create start menu buttons"""
        buttons = [
            [
                InlineKeyboardButton("Help 📜", callback_data="help"),
                InlineKeyboardButton("About ℹ️", callback_data="about")
            ],
            [
                InlineKeyboardButton("Channel 📢", url=config.CHANNEL_LINK),
                InlineKeyboardButton("Developer 👨‍💻", url=config.DEVELOPER_LINK)
            ]
        ]
        return InlineKeyboardMarkup(buttons)

    def help_button(self) -> InlineKeyboardMarkup:
        """Create help menu buttons"""
        buttons = [
            [
                InlineKeyboardButton("Home 🏠", callback_data="home"),
                InlineKeyboardButton("About ℹ️", callback_data="about")
            ],
            [
                InlineKeyboardButton("Channel 📢", url=config.CHANNEL_LINK)
            ]
        ]
        return InlineKeyboardMarkup(buttons)

    def about_button(self) -> InlineKeyboardMarkup:
        """Create about menu buttons"""
        buttons = [
            [
                InlineKeyboardButton("Home 🏠", callback_data="home"),
                InlineKeyboardButton("Help 📜", callback_data="help")
            ],
            [
                InlineKeyboardButton("Channel 📢", url=config.CHANNEL_LINK)
            ]
        ]
        return InlineKeyboardMarkup(buttons)

    def file_button(self, file_uuid: str) -> InlineKeyboardMarkup:
        """Create file action buttons"""
        buttons = [
            [
                InlineKeyboardButton("Download 📥", callback_data=f"download_{file_uuid}"),
                InlineKeyboardButton("Share Link 🔗", callback_data=f"share_{file_uuid}")
            ],
            [
                InlineKeyboardButton("Channel 📢", url=config.CHANNEL_LINK)
            ]
        ]
        return InlineKeyboardMarkup(buttons)

    async def handle_subscription_check(self, client: Client, user_id: int) -> tuple[bool, InlineKeyboardMarkup]:
        """Handle subscription check and return appropriate buttons"""
        is_subscribed = await self.check_force_sub(client, user_id)
        if is_subscribed:
            return True, self.start_button()
        else:
            return False, self.get_force_sub_buttons()

    async def show_start(self, client: Client, callback_query: CallbackQuery):
        """Show start message with automatic subscription check"""
        try:
            is_subbed, markup = await self.handle_subscription_check(client, callback_query.from_user.id)
            await callback_query.message.edit_text(
                config.Messages.START_TEXT.format(
                    bot_name=config.BOT_NAME,
                    user_mention=callback_query.from_user.mention
                ) if is_subbed else config.Messages.FORCE_SUB_TEXT,
                reply_markup=markup,
                disable_web_page_preview=True
            )
        except Exception as e:
            logging.error(f"Error in show_start: {str(e)}")

    async def show_help(self, client: Client, callback_query: CallbackQuery):
        """Show help message with automatic subscription check"""
        try:
            is_subbed, markup = await self.handle_subscription_check(client, callback_query.from_user.id)
            await callback_query.message.edit_text(
                config.Messages.HELP_TEXT if is_subbed else config.Messages.FORCE_SUB_TEXT,
                reply_markup=markup,
                disable_web_page_preview=True
            )
        except Exception as e:
            logging.error(f"Error in show_help: {str(e)}")

    async def show_about(self, client: Client, callback_query: CallbackQuery):
        """Show about message with automatic subscription check"""
        try:
            is_subbed, markup = await self.handle_subscription_check(client, callback_query.from_user.id)
            await callback_query.message.edit_text(
                config.Messages.ABOUT_TEXT.format(
                    bot_name=config.BOT_NAME,
                    version=config.BOT_VERSION
                ) if is_subbed else config.Messages.FORCE_SUB_TEXT,
                reply_markup=markup,
                disable_web_page_preview=True
            )
        except Exception as e:
            logging.error(f"Error in show_about: {str(e)}")
