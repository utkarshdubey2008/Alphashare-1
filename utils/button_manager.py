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
        self.force_sub_channels = config.FORCE_SUB_CHANNELS
        self.force_sub_links = config.FORCE_SUB_LINKS

    async def check_force_sub(self, client: Client, user_id: int) -> bool:
        """Check user's subscription status in configured channels"""
        if not self.force_sub_channels:
            return True

        for channel_id in self.force_sub_channels:
            try:
                member = await client.get_chat_member(chat_id=channel_id, user_id=user_id)
                if member.status in [ChatMemberStatus.BANNED, ChatMemberStatus.LEFT, ChatMemberStatus.RESTRICTED]:
                    return False
                if member.status not in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]:
                    return False
            except UserNotParticipant:
                return False
            except BadRequest as e:
                logging.error(f"Error checking subscription for channel {channel_id}: {str(e)}")
                continue
            except Exception as e:
                logging.error(f"Unexpected error for channel {channel_id}: {str(e)}")
                continue
        return True

    def get_force_sub_buttons(self) -> InlineKeyboardMarkup:
        """Generate force subscription buttons for configured channels"""
        buttons = []
        
        for channel_id in self.force_sub_channels:
            if channel_id in self.force_sub_links:
                channel_link = self.force_sub_links[channel_id]
                if channel_link and channel_link.startswith(("https://t.me/", "t.me/")):
                    # Ensure the link is properly formatted
                    if not channel_link.startswith("https://"):
                        channel_link = "https://" + channel_link
                    buttons.append([
                        InlineKeyboardButton(
                            text=f"📢 Join Channel",
                            url=channel_link
                        )
                    ])
        
        # Add support channel button if available
        if config.SUPPORT_LINK:
            buttons.append([
                InlineKeyboardButton(
                    text="📞 Support",
                    url=config.SUPPORT_LINK
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
        return is_subscribed, self.start_button() if is_subscribed else self.get_force_sub_buttons()

    async def show_start(self, client: Client, callback_query: CallbackQuery):
        """Show start message with subscription check"""
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
        """Show help message with subscription check"""
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
        """Show about message with subscription check"""
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
