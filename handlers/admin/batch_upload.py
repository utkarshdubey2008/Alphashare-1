from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from uuid import uuid4
import time
from datetime import datetime
from database import Database
from config import Messages, ADMIN_IDS, DB_CHANNEL_ID
from handlers.utils import get_size_formatted

# Store batch upload sessions
admin_batch_sessions = {}

class BatchUploadSession:
    def __init__(self, admin_id: int):
        self.admin_id = admin_id
        self.files = []
        self.batch_id = str(uuid4())[:8]
        self.start_time = time.time()
        self.created_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

def admin_check(func):
    """Decorator to check if user is an admin"""
    async def wrapper(client: Client, message: Message):
        if message.from_user.id not in ADMIN_IDS:
            await message.reply_text("⚠️ This command is only for admins!")
            return
        return await func(client, message)
    return wrapper

@Client.on_message(filters.command("batch_upload") & filters.private)
@admin_check
async def start_batch_upload(client: Client, message: Message):
    """Start a new batch upload session (Admin Only)"""
    admin_id = message.from_user.id
    
    # Check if admin already has an active session
    if admin_id in admin_batch_sessions:
        await message.reply_text(
            "You already have an active batch upload session. "
            "Please finish it with /done_batch or cancel it with /cancel_batch first."
        )
        return
    
    # Create new session
    admin_batch_sessions[admin_id] = BatchUploadSession(admin_id)
    
    await message.reply_text(
        "🔰 **Admin Batch Upload Mode Started!**\n\n"
        "Send me the files you want to include in this batch.\n\n"
        "Commands:\n"
        "• /done_batch - Finish and generate link\n"
        "• /cancel_batch - Cancel current session\n\n"
        "Note: Session will automatically expire in 30 minutes."
    )

@Client.on_message(filters.command("done_batch") & filters.private)
@admin_check
async def finish_batch_upload(client: Client, message: Message):
    """Finish batch upload and generate link (Admin Only)"""
    admin_id = message.from_user.id
    
    if admin_id not in admin_batch_sessions:
        await message.reply_text(
            "No active batch upload session. Start one with /batch_upload"
        )
        return
    
    session = admin_batch_sessions[admin_id]
    
    if not session.files:
        await message.reply_text(
            "No files in current batch. Send some files first or cancel with /cancel_batch"
        )
        return
    
    try:
        # Store batch information in database
        db = Database()
        batch_data = {
            "batch_id": session.batch_id,
            "admin_id": admin_id,
            "files": session.files,
            "created_at": session.created_at,
            "is_active": True
        }
        
        await db.add_batch(batch_data)
        
        # Get bot info
        bot = await client.get_me()
        bot_username = bot.username
        
        # Generate batch link
        batch_link = f"https://t.me/{bot_username}?start=batch_{session.batch_id}"
        
        # Calculate total size
        total_size = sum(file['size'] for file in session.files)
        total_size_formatted = get_size_formatted(total_size)
        
        # Create summary message
        summary = f"📦 **Admin Batch Upload Complete!**\n\n"
        summary += f"🆔 Batch ID: `{session.batch_id}`\n"
        summary += f"📄 Total Files: {len(session.files)}\n"
        summary += f"📊 Total Size: {total_size_formatted}\n"
        summary += f"👤 Uploaded by: {message.from_user.mention}\n"
        summary += f"⏰ Created at: {session.created_at} UTC\n\n"
        summary += "**Files in this batch:**\n"
        
        for idx, file in enumerate(session.files, 1):
            summary += f"{idx}. {file['name']} ({file['size_formatted']})\n"
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔗 Access Files", url=batch_link)],
            [InlineKeyboardButton("🗑 Delete Batch", callback_data=f"delete_batch_{session.batch_id}")]
        ])
        
        await message.reply_text(summary, reply_markup=keyboard)
        
        # Clear session
        del admin_batch_sessions[admin_id]
        
    except Exception as e:
        await message.reply_text(f"❌ Error occurred: {str(e)}")
        del admin_batch_sessions[admin_id]

@Client.on_message(filters.command("cancel_batch") & filters.private)
@admin_check
async def cancel_batch_upload(client: Client, message: Message):
    """Cancel current batch upload session (Admin Only)"""
    admin_id = message.from_user.id
    
    if admin_id in admin_batch_sessions:
        del admin_batch_sessions[admin_id]
        await message.reply_text("✅ Batch upload session cancelled.")
    else:
        await message.reply_text("No active batch upload session.")

@Client.on_message(filters.private & filters.media & ~filters.command(""))
async def handle_batch_file(client: Client, message: Message):
    """Handle incoming files during batch upload (Admin Only)"""
    user_id = message.from_user.id
    
    if user_id not in ADMIN_IDS:
        return
    
    if user_id not in admin_batch_sessions:
        return
    
    session = admin_batch_sessions[user_id]
    
    # Check session timeout (30 minutes)
    if time.time() - session.start_time > 1800:
        del admin_batch_sessions[user_id]
        await message.reply_text(
            "⏰ Batch upload session expired (30 minutes timeout).\n"
            "Start a new session with /batch_upload"
        )
        return
    
    try:
        # Forward file to database channel
        file_msg = await message.forward(DB_CHANNEL_ID)
        
        # Get file information
        file_info = {}
        
        if message.document:
            file_info = {
                "file_id": file_msg.id,
                "name": message.document.file_name,
                "size": message.document.file_size,
                "size_formatted": get_size_formatted(message.document.file_size),
                "mime_type": message.document.mime_type,
                "type": "document",
                "timestamp": time.time()
            }
        elif message.video:
            file_info = {
                "file_id": file_msg.id,
                "name": message.video.file_name or f"video_{file_msg.id}.mp4",
                "size": message.video.file_size,
                "size_formatted": get_size_formatted(message.video.file_size),
                "mime_type": message.video.mime_type,
                "type": "video",
                "timestamp": time.time()
            }
        elif message.audio:
            file_info = {
                "file_id": file_msg.id,
                "name": message.audio.file_name or f"audio_{file_msg.id}.mp3",
                "size": message.audio.file_size,
                "size_formatted": get_size_formatted(message.audio.file_size),
                "mime_type": message.audio.mime_type,
                "type": "audio",
                "timestamp": time.time()
            }
        elif message.photo:
            file_info = {
                "file_id": file_msg.id,
                "name": f"photo_{file_msg.id}.jpg",
                "size": message.photo.file_size,
                "size_formatted": get_size_formatted(message.photo.file_size),
                "mime_type": "image/jpeg",
                "type": "photo",
                "timestamp": time.time()
            }
        else:
            await message.reply_text(f"❌ Unsupported file type")
            return
        
        session.files.append(file_info)
        
        # Calculate total size
        total_size = sum(file['size'] for file in session.files)
        total_size_formatted = get_size_formatted(total_size)
        
        await message.reply_text(
            f"✅ File added to batch!\n\n"
            f"📄 Files in batch: {len(session.files)}\n"
            f"📊 Total size: {total_size_formatted}\n\n"
            f"Send more files or use:\n"
            f"• /done_batch - Finish and generate link\n"
            f"• /cancel_batch - Cancel current session"
        )
        
    except Exception as e:
        await message.reply_text(f"❌ Failed to process file: {str(e)}")
