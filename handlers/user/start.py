from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from database import Database
from utils import ButtonManager
import config
import asyncio
from ..utils.message_delete import schedule_message_deletion

db = Database()
button_manager = ButtonManager()

@Client.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    await db.add_user(message.from_user.id, message.from_user.username)
    
    if len(message.command) > 1:
        file_uuid = message.command[1]
        
        is_subscribed = await button_manager.check_force_sub(client, message.from_user.id)
        if not is_subscribed:
            await message.reply_text(
                config.Messages.FORCE_SUB_TEXT,
                reply_markup=button_manager.get_force_sub_buttons(),
                disable_web_page_preview=True
            )
            return
        
        file_data = await db.get_file(file_uuid)
        if not file_data:
            await message.reply_text("❌ File not found or has been deleted!", protect_content=config.PRIVACY_MODE)
            return
        
        try:
            msg = await client.copy_message(
                chat_id=message.chat.id,
                from_chat_id=config.DB_CHANNEL_ID,
                message_id=file_data["message_id"],
                protect_content=config.PRIVACY_MODE
            )
            await db.increment_downloads(file_uuid)
            await db.update_file_message_id(file_uuid, msg.id, message.chat.id)
            
            if file_data.get("auto_delete"):
                delete_time = file_data.get("auto_delete_time")
                if delete_time:
                    info_msg = await msg.reply_text(
                        f"⏳ **File Auto-Delete Information**\n\n"
                        f"This file will be automatically deleted in {delete_time} minutes\n"
                        f"• Delete Time: {delete_time} minutes\n"
                        f"• Time Left: {delete_time} minutes\n"
                        f"💡 **Save this file to your saved messages before it's deleted!**",
                        protect_content=config.PRIVACY_MODE
                    )
                    
                    asyncio.create_task(schedule_message_deletion(
                        client, file_uuid, message.chat.id, [msg.id, info_msg.id], delete_time
                    ))
        except Exception as e:
            await message.reply_text(f"❌ Error: {str(e)}", protect_content=config.PRIVACY_MODE)
        return
    
    # Check force subscription for start command
    is_subscribed = await button_manager.check_force_sub(client, message.from_user.id)
    if not is_subscribed:
        await message.reply_text(
            config.Messages.FORCE_SUB_TEXT,
            reply_markup=button_manager.get_force_sub_buttons(),
            disable_web_page_preview=True
        )
        return

    await message.reply_text(
        config.Messages.START_TEXT.format(
            bot_name=config.BOT_NAME,
            user_mention=message.from_user.mention
        ),
        reply_markup=button_manager.start_button(),
        protect_content=config.PRIVACY_MODE
    )

@Client.on_message(filters.command("upload") & filters.private & filters.reply)
async def upload_command(client: Client, message: Message):
    is_subscribed = await button_manager.check_force_sub(client, message.from_user.id)
    if not is_subscribed:
        await message.reply_text(
            config.Messages.FORCE_SUB_TEXT,
            reply_markup=button_manager.get_force_sub_buttons(),
            disable_web_page_preview=True
        )
        return

    file_message = message.reply_to_message
    if not file_message.document and not file_message.video and not file_message.audio and not file_message.photo:
        await message.reply_text("❌ Please reply to a valid file (document, video, audio, or photo).", protect_content=config.PRIVACY_MODE)
        return

    file_uuid = await db.save_file(file_message, message.from_user.id)
    
    await message.reply_text(
        f"✅ **File Successfully Uploaded!**\n\n"
        f"🔗 **Download Link:** `{config.BOT_USERNAME}?start={file_uuid}`\n\n"
        f"⚡ Share this link with others to let them download the file.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Download File", url=f"https://t.me/{config.BOT_USERNAME}?start={file_uuid}")]
        ]),
        protect_content=config.PRIVACY_MODE
    )

@Client.on_message(filters.command("batch_upload") & filters.private)
async def batch_upload_command(client: Client, message: Message):
    is_subscribed = await button_manager.check_force_sub(client, message.from_user.id)
    if not is_subscribed:
        await message.reply_text(
            config.Messages.FORCE_SUB_TEXT,
            reply_markup=button_manager.get_force_sub_buttons(),
            disable_web_page_preview=True
        )
        return

    if not message.reply_to_message or not message.reply_to_message.media_group_id:
        await message.reply_text("❌ Please reply to an album (grouped files) to upload as a batch.", protect_content=config.PRIVACY_MODE)
        return

    media_group_id = message.reply_to_message.media_group_id
    media_messages = await client.get_media_group(message.chat.id, media_group_id)

    if not media_messages:
        await message.reply_text("❌ No files found in the media group.", protect_content=config.PRIVACY_MODE)
        return

    batch_uuid = await db.save_batch(media_messages, message.from_user.id)

    await message.reply_text(
        f"✅ **Batch Successfully Uploaded!**\n\n"
        f"🔗 **Download Batch Link:** `{config.BOT_USERNAME}?start=batch_{batch_uuid}`\n\n"
        f"⚡ Share this link with others to let them download all files in this batch.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 Download Batch", url=f"https://t.me/{config.BOT_USERNAME}?start=batch_{batch_uuid}")]
        ]),
        protect_content=config.PRIVACY_MODE
    )

@Client.on_message(filters.command("batch_start") & filters.private)
async def batch_start_command(client: Client, message: Message):
    await db.add_user(message.from_user.id, message.from_user.username)

    if len(message.command) > 1 and message.command[1].startswith("batch_"):
        batch_uuid = message.command[1].split("_")[1]

        is_subscribed = await button_manager.check_force_sub(client, message.from_user.id)
        if not is_subscribed:
            await message.reply_text(
                config.Messages.FORCE_SUB_TEXT,
                reply_markup=button_manager.get_force_sub_buttons(),
                disable_web_page_preview=True
            )
            return

        batch_data = await db.get_batch(batch_uuid)
        if not batch_data:
            await message.reply_text("❌ Batch not found or has been deleted!", protect_content=config.PRIVACY_MODE)
            return

        for file_data in batch_data["files"]:
            try:
                msg = await client.copy_message(
                    chat_id=message.chat.id,
                    from_chat_id=config.DB_CHANNEL_ID,
                    message_id=file_data["message_id"],
                    protect_content=config.PRIVACY_MODE
                )
                await db.increment_downloads(file_data["file_uuid"])
                await db.update_file_message_id(file_data["file_uuid"], msg.id, message.chat.id)
            except Exception as e:
                await message.reply_text(f"❌ Error: {str(e)}", protect_content=config.PRIVACY_MODE)
        return

    await message.reply_text(
        config.Messages.START_TEXT.format(
            bot_name=config.BOT_NAME,
            user_mention=message.from_user.mention
        ),
        reply_markup=button_manager.start_button(),
        protect_content=config.PRIVACY_MODE
        )
