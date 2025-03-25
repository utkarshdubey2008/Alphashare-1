from typing import List, Union
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import config
import logging
from pyrogram.errors import UserNotParticipant, BadRequest
from pyrogram.enums import ChatMemberStatus

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

    async def check_force_sub(self, client, user_id: int) -> bool:
        """Check user's subscription status in all required channels"""
        if not self.channel_configs:
            return True

        for channel_id, _, name in self.channel_configs:
            try:
                member = await client.get_chat_member(int(channel_id), user_id)
                if member.status not in ["member", "administrator", "creator"]:
                    return False
            except UserNotParticipant:
                return False
            except BadRequest as e:
                error_msg = str(e).lower()
                if "chat not found" in error_msg:
                    logging.error(f"Channel {name} ({channel_id}) not found or bot not admin")
                    continue
                elif "user not found" in error_msg:
                    return False
                continue
            except Exception as e:
                logging.error(f"Unexpected error checking {name} channel ({channel_id}): {str(e)}")
                continue
        return True

    def force_sub_button(self) -> InlineKeyboardMarkup:
        """Generate force subscription buttons without refresh button"""
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

    async def show_start(self, client, callback_query: CallbackQuery):
        """Show start message after checking subscription"""
        try:
            is_subbed = await self.check_force_sub(client, callback_query.from_user.id)
            if is_subbed:
                await callback_query.message.edit_text(
                    config.Messages.START_TEXT.format(
                        bot_name=config.BOT_NAME,
                        user_mention=callback_query.from_user.mention
                    ),
                    reply_markup=self.start_button(),
                    disable_web_page_preview=True
                )
            else:
                await callback_query.message.edit_text(
                    config.Messages.FORCE_SUB_TEXT,
                    reply_markup=self.force_sub_button(),
                    disable_web_page_preview=True
                )
        except Exception as e:
            logging.error(f"Error in show_start: {str(e)}")

    async def show_help(self, client, callback_query: CallbackQuery):
        """Show help message after checking subscription"""
        try:
            is_subbed = await self.check_force_sub(client, callback_query.from_user.id)
            if is_subbed:
                await callback_query.message.edit_text(
                    config.Messages.HELP_TEXT,
                    reply_markup=self.help_button(),
                    disable_web_page_preview=True
                )
            else:
                await callback_query.message.edit_text(
                    config.Messages.FORCE_SUB_TEXT,
                    reply_markup=self.force_sub_button(),
                    disable_web_page_preview=True
                )
        except Exception as e:
            logging.error(f"Error in show_help: {str(e)}")

    async def show_about(self, client, callback_query: CallbackQuery):
        """Show about message after checking subscription"""
        try:
            is_subbed = await self.check_force_sub(client, callback_query.from_user.id)
            if is_subbed:
                await callback_query.message.edit_text(
                    config.Messages.ABOUT_TEXT.format(
                        bot_name=config.BOT_NAME,
                        version=config.BOT_VERSION
                    ),
                    reply_markup=self.about_button(),
                    disable_web_page_preview=True
                )
            else:
                await callback_query.message.edit_text(
                    config.Messages.FORCE_SUB_TEXT,
                    reply_markup=self.force_sub_button(),
                    disable_web_page_preview=True
                )
        except Exception as e:
            logging.error(f"Error in show_about: {str(e)}")

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
