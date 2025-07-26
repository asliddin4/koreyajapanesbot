from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite
from config import ADMIN_ID

router = Router()

class CustomContentStates(StatesGroup):
    waiting_for_content_title = State()
    waiting_for_content_description = State()
    waiting_for_content_file = State()
    waiting_for_content_text = State()

def admin_only(func):
    """Decorator to restrict access to admin only"""
    from functools import wraps
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        message_or_callback = args[0] if args else None
        if not message_or_callback:
            return
            
        user_id = message_or_callback.from_user.id
        if user_id != ADMIN_ID:
            if isinstance(message_or_callback, Message):
                await message_or_callback.answer("❌ Bu buyruq faqat admin uchun!")
            else:
                await message_or_callback.answer("❌ Bu buyruq faqat admin uchun!", show_alert=True)
            return
        return await func(*args, **kwargs)
    return wrapper

# Database functions
async def create_custom_content_table():
    """Create custom content table if it doesn't exist"""
    async with aiosqlite.connect("language_bot.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER,
                subsection_id INTEGER,
                title TEXT NOT NULL,
                description TEXT,
                content_type TEXT NOT NULL,
                file_id TEXT,
                file_unique_id TEXT,
                content_text TEXT,
                thumbnail_file_id TEXT,
                file_size INTEGER,
                duration INTEGER,
                is_premium INTEGER DEFAULT 0,
                order_index INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                FOREIGN KEY (section_id) REFERENCES custom_sections (id),
                FOREIGN KEY (subsection_id) REFERENCES custom_subsections (id)
            )
        """)
        await db.commit()

async def add_custom_content(section_id=None, subsection_id=None, title="", description=None, 
                           content_type="", file_id="", file_unique_id="", content_text="",
                           thumbnail_file_id="", file_size=0, duration=0, is_premium=0, created_by=None):
    """Add content to custom section or subsection"""
    await create_custom_content_table()
    async with aiosqlite.connect("language_bot.db") as db:
        # Get next order index
        if subsection_id:
            cursor = await db.execute(
                "SELECT COALESCE(MAX(order_index), 0) + 1 FROM custom_content WHERE subsection_id = ?",
                (subsection_id,)
            )
        else:
            cursor = await db.execute(
                "SELECT COALESCE(MAX(order_index), 0) + 1 FROM custom_content WHERE section_id = ? AND subsection_id IS NULL",
                (section_id,)
            )
        order_index = (await cursor.fetchone())[0]
        
        await db.execute("""
            INSERT INTO custom_content 
            (section_id, subsection_id, title, description, content_type, file_id, file_unique_id, 
             content_text, thumbnail_file_id, file_size, duration, is_premium, order_index, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (section_id, subsection_id, title, description, content_type, file_id, file_unique_id,
              content_text, thumbnail_file_id, file_size, duration, is_premium, order_index, created_by))
        await db.commit()
        return True

async def get_custom_content(section_id=None, subsection_id=None):
    """Get content for section or subsection"""
    await create_custom_content_table()
    async with aiosqlite.connect("language_bot.db") as db:
        if subsection_id:
            cursor = await db.execute("""
                SELECT id, section_id, subsection_id, title, description, content_type, 
                       file_id, file_unique_id, content_text, thumbnail_file_id, 
                       file_size, duration, is_premium, order_index, created_at
                FROM custom_content 
                WHERE subsection_id = ?
                ORDER BY order_index ASC
            """, (subsection_id,))
        else:
            cursor = await db.execute("""
                SELECT id, section_id, subsection_id, title, description, content_type, 
                       file_id, file_unique_id, content_text, thumbnail_file_id, 
                       file_size, duration, is_premium, order_index, created_at
                FROM custom_content 
                WHERE section_id = ? AND subsection_id IS NULL
                ORDER BY order_index ASC
            """, (section_id,))
        return await cursor.fetchall()

async def delete_custom_content(content_id):
    """Delete specific content"""
    async with aiosqlite.connect("language_bot.db") as db:
        await db.execute("DELETE FROM custom_content WHERE id = ?", (content_id,))
        await db.commit()
        return True

# Keyboards
def get_content_type_keyboard():
    """Keyboard for selecting content type"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📝 Matn", callback_data="content_type_text"),
            InlineKeyboardButton(text="🖼️ Rasm", callback_data="content_type_photo")
        ],
        [
            InlineKeyboardButton(text="🎥 Video", callback_data="content_type_video"),
            InlineKeyboardButton(text="🎵 Musiqa", callback_data="content_type_audio")
        ],
        [
            InlineKeyboardButton(text="🎤 Audio", callback_data="content_type_voice"),
            InlineKeyboardButton(text="📄 Hujjat", callback_data="content_type_document")
        ],
        [
            InlineKeyboardButton(text="🔙 Orqaga", callback_data="cancel_content_creation")
        ]
    ])

def get_custom_content_keyboard(contents, section_id=None, subsection_id=None, is_admin=False):
    """Generate keyboard for custom content"""
    buttons = []
    
    for content in contents:
        content_id, sec_id, sub_id, title, description, content_type, file_id, file_unique_id, content_text, thumbnail_file_id, file_size, duration, is_premium, order_index, created_at = content
        
        # Content type icons
        type_icons = {
            'text': '📝',
            'photo': '🖼️',
            'video': '🎥', 
            'audio': '🎵',
            'voice': '🎤',
            'document': '📄'
        }
        
        icon = type_icons.get(content_type, '📂')
        premium_icon = "💎 " if is_premium else ""
        
        buttons.append([
            InlineKeyboardButton(
                text=f"{premium_icon}{icon} {title}",
                callback_data=f"view_custom_content_{content_id}"
            )
        ])
    
    # Add admin buttons
    if is_admin:
        if subsection_id:
            buttons.append([
                InlineKeyboardButton(text="➕ Kontent qo'shish", callback_data=f"add_content_subsection_{subsection_id}")
            ])
            buttons.append([
                InlineKeyboardButton(text="🔙 Bo'limga qaytish", callback_data=f"custom_section_{section_id}")
            ])
        else:
            buttons.append([
                InlineKeyboardButton(text="➕ Kontent qo'shish", callback_data=f"add_content_section_{section_id}")
            ])
            buttons.append([
                InlineKeyboardButton(text="🔙 Bo'limlar", callback_data="view_custom_sections")
            ])
    else:
        if subsection_id:
            buttons.append([
                InlineKeyboardButton(text="🔙 Bo'limga qaytish", callback_data=f"custom_section_{section_id}")
            ])
        else:
            buttons.append([
                InlineKeyboardButton(text="🔙 Bo'limlar", callback_data="view_custom_sections")
            ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# Duplicate function removed - using the one above

# Content Management Handlers
@router.callback_query(F.data.startswith("add_content_section_"))
@admin_only
async def add_content_to_section(callback: CallbackQuery, state: FSMContext):
    """Start adding content to section"""
    try:
        callback_data = callback.data
        print(f"DEBUG: Full callback data: {callback_data}")
        section_id = int(callback.data.replace("add_content_section_", ""))
        print(f"DEBUG: Parsed section_id: {section_id}")
    except ValueError as e:
        print(f"DEBUG: ValueError in section parsing: {e}")
        await callback.answer(f"❌ Noto'g'ri ma'lumot: {callback.data}")
        return
    except Exception as e:
        print(f"DEBUG: Other error in section parsing: {e}")
        await callback.answer(f"❌ Xatolik: {str(e)}")
        return
    
    # Get section name
    async with aiosqlite.connect("language_bot.db") as db:
        cursor = await db.execute("SELECT name FROM custom_sections WHERE id = ?", (section_id,))
        section = await cursor.fetchone()
    
    if not section:
        await callback.answer("❌ Bo'lim topilmadi!", show_alert=True)
        return
    
    section_name = section[0]
    await state.update_data(section_id=section_id, section_name=section_name, subsection_id=None)
    
    await callback.message.edit_text(
        f"➕ <b>Kontent Qo'shish</b>\n\n"
        f"📂 Bo'lim: {section_name}\n\n"
        f"🎯 Qanday turdagi kontent qo'shmoqchisiz?",
        reply_markup=get_content_type_keyboard()
    )

@router.callback_query(F.data.startswith("add_content_subsection_"))
@admin_only
async def add_content_to_subsection(callback: CallbackQuery, state: FSMContext):
    """Start adding content to subsection"""
    try:
        callback_data = callback.data
        print(f"DEBUG: Full callback data: {callback_data}")
        subsection_id = int(callback.data.replace("add_content_subsection_", ""))
        print(f"DEBUG: Parsed subsection_id: {subsection_id}")
    except ValueError as e:
        print(f"DEBUG: ValueError in subsection parsing: {e}")
        await callback.answer(f"❌ Noto'g'ri ma'lumot: {callback.data}")
        return
    except Exception as e:
        print(f"DEBUG: Other error in subsection parsing: {e}")
        await callback.answer(f"❌ Xatolik: {str(e)}")
        return
    
    # Get subsection and section info
    async with aiosqlite.connect("language_bot.db") as db:
        cursor = await db.execute("""
            SELECT cs.name, s.id, s.name 
            FROM custom_subsections cs
            JOIN custom_sections s ON cs.section_id = s.id
            WHERE cs.id = ?
        """, (subsection_id,))
        result = await cursor.fetchone()
    
    if not result:
        await callback.answer("❌ Pastki bo'lim topilmadi!", show_alert=True)
        return
    
    subsection_name, section_id, section_name = result
    await state.update_data(
        section_id=section_id, 
        section_name=section_name, 
        subsection_id=subsection_id, 
        subsection_name=subsection_name
    )
    
    await callback.message.edit_text(
        f"➕ <b>Kontent Qo'shish</b>\n\n"
        f"📂 Bo'lim: {section_name}\n"
        f"📄 Pastki bo'lim: {subsection_name}\n\n"
        f"🎯 Qanday turdagi kontent qo'shmoqchisiz?",
        reply_markup=get_content_type_keyboard()
    )

# Content type selection handlers
@router.callback_query(F.data.startswith("content_type_"))
async def select_content_type(callback: CallbackQuery, state: FSMContext):
    """Handle content type selection"""
    # Check admin access
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Bu buyruq faqat admin uchun!", show_alert=True)
        return
        
    try:
        content_type = callback.data.replace("content_type_", "")
        await callback.answer()
        print(f"DEBUG: Content type selected: {content_type}")
    except Exception as e:
        await callback.answer(f"❌ Xatolik: {str(e)}")
        return
    data = await state.get_data()
    
    await state.update_data(content_type=content_type)
    
    type_names = {
        'text': 'Matn',
        'photo': 'Rasm', 
        'video': 'Video',
        'audio': 'Musiqa',
        'voice': 'Audio',
        'document': 'Hujjat'
    }
    
    type_name = type_names.get(content_type, content_type)
    section_name = data.get('section_name', '')
    subsection_name = data.get('subsection_name', '')
    
    location_text = f"📂 Bo'lim: {section_name}"
    if subsection_name:
        location_text += f"\n📄 Pastki bo'lim: {subsection_name}"
    
    await callback.message.edit_text(
        f"📝 <b>Kontent Sarlavhasi</b>\n\n"
        f"{location_text}\n"
        f"📋 Turi: {type_name}\n\n"
        f"✏️ Kontent sarlavhasini kiriting:\n\n"
        f"💡 Masalan: 'Dars 1', 'Grammatika qoidalari', 'Amaliyot' va h.k.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="cancel_content_creation")]
        ])
    )
    
    await state.set_state(CustomContentStates.waiting_for_content_title)

@router.message(CustomContentStates.waiting_for_content_title)
@admin_only
async def process_content_title(message: Message, state: FSMContext):
    """Process content title"""
    if not message.text:
        await message.answer("❌ Iltimos, matn kiriting!")
        return
        
    title = message.text.strip()
    
    if len(title) < 2:
        await message.answer("❌ Sarlavha kamida 2 ta belgi bo'lishi kerak!")
        return
    
    await state.update_data(title=title)
    
    await message.answer(
        f"📄 <b>Kontent Tavsifi</b>\n\n"
        f"📋 Sarlavha: {title}\n\n"
        f"💬 Kontent haqida qisqacha tavsif kiriting "
        f"(yoki /skip yozing tavsif qo'shmaslik uchun):"
    )
    await state.set_state(CustomContentStates.waiting_for_content_description)

@router.message(CustomContentStates.waiting_for_content_description)
@admin_only
async def process_content_description(message: Message, state: FSMContext):
    """Process content description"""
    if not message.text:
        await message.answer("❌ Iltimos, matn kiriting yoki /skip yozing!")
        return
        
    description = None if message.text == "/skip" else message.text.strip()
    data = await state.get_data()
    content_type = data.get('content_type')
    
    await state.update_data(description=description)
    
    if content_type == 'text':
        await message.answer(
            f"📝 <b>Matn Kontenti</b>\n\n"
            f"✏️ Kontent matninini kiriting:\n\n"
            f"💡 Bu yerda dars matnini, tushuntirishlarni, "
            f"yoki boshqa matn ma'lumotlarini kiritishingiz mumkin."
        )
        await state.set_state(CustomContentStates.waiting_for_content_text)
    else:
        type_instructions = {
            'photo': "🖼️ Rasmni yuklang",
            'video': "🎥 Video faylni yuklang", 
            'audio': "🎵 Musiqa faylini yuklang",
            'voice': "🎤 Audio yoki ovozli xabar yuklang",
            'document': "📄 Hujjat faylini yuklang"
        }
        
        instruction = type_instructions.get(content_type, "Faylni yuklang")
        
        await message.answer(
            f"📁 <b>Fayl Yuklash</b>\n\n"
            f"📋 Sarlavha: {data.get('title')}\n"
            f"📄 Tavsif: {description or 'Kiritilmagan'}\n\n"
            f"📤 {instruction}:"
        )
        await state.set_state(CustomContentStates.waiting_for_content_file)

@router.message(CustomContentStates.waiting_for_content_text)
@admin_only
async def process_content_text(message: Message, state: FSMContext):
    """Process text content"""
    if not message.text:
        await message.answer("❌ Iltimos, matn kiriting!")
        return
        
    content_text = message.text.strip()
    data = await state.get_data()
    
    try:
        await add_custom_content(
            section_id=data.get('section_id'),
            subsection_id=data.get('subsection_id'),
            title=data.get('title', ""),
            description=data.get('description', ""),
            content_type='text',
            content_text=content_text,
            created_by=message.from_user.id
        )
        
        location = f"Bo'lim: {data.get('section_name')}"
        if data.get('subsection_name'):
            location += f" → {data.get('subsection_name')}"
        
        await message.answer(
            f"✅ <b>Matn kontent muvaffaqiyatli qo'shildi!</b>\n\n"
            f"📍 {location}\n"
            f"📋 Sarlavha: {data.get('title')}\n"
            f"📄 Tavsif: {data.get('description') or 'Kiritilmagan'}\n"
            f"📝 Matn uzunligi: {len(content_text)} belgi"
        )
        
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    
    await state.clear()

@router.message(CustomContentStates.waiting_for_content_file)
@admin_only
async def process_content_file(message: Message, state: FSMContext):
    """Process content file"""
    data = await state.get_data()
    content_type = data.get('content_type')
    
    file_id = None
    file_unique_id = None
    file_size = 0
    duration = 0
    thumbnail_file_id = None
    
    # Process different file types
    if content_type == 'photo' and message.photo:
        file_id = message.photo[-1].file_id
        file_unique_id = message.photo[-1].file_unique_id
        file_size = message.photo[-1].file_size or 0
        
    elif content_type == 'video' and message.video:
        file_id = message.video.file_id
        file_unique_id = message.video.file_unique_id
        file_size = message.video.file_size or 0
        duration = message.video.duration or 0
        if message.video.thumbnail:
            thumbnail_file_id = message.video.thumbnail.file_id
            
    elif content_type == 'audio' and message.audio:
        file_id = message.audio.file_id
        file_unique_id = message.audio.file_unique_id
        file_size = message.audio.file_size or 0
        duration = message.audio.duration or 0
        if message.audio.thumbnail:
            thumbnail_file_id = message.audio.thumbnail.file_id
            
    elif content_type == 'voice' and (message.voice or message.video_note):
        if message.voice:
            file_id = message.voice.file_id
            file_unique_id = message.voice.file_unique_id
            file_size = message.voice.file_size or 0
            duration = message.voice.duration or 0
        elif message.video_note:
            file_id = message.video_note.file_id
            file_unique_id = message.video_note.file_unique_id
            file_size = message.video_note.file_size or 0
            duration = message.video_note.duration or 0
            if message.video_note.thumbnail:
                thumbnail_file_id = message.video_note.thumbnail.file_id
                
    elif content_type == 'document' and message.document:
        file_id = message.document.file_id
        file_unique_id = message.document.file_unique_id
        file_size = message.document.file_size or 0
        if message.document.thumbnail:
            thumbnail_file_id = message.document.thumbnail.file_id
    
    if not file_id:
        await message.answer(
            f"❌ Noto'g'ri fayl turi!\n\n"
            f"📋 Kutilayotgan tur: {content_type}\n"
            f"💡 Iltimos, to'g'ri fayl turini yuklang."
        )
        return
    
    try:
        await add_custom_content(
            section_id=data.get('section_id'),
            subsection_id=data.get('subsection_id'),
            title=data.get('title', ""),
            description=data.get('description', ""),
            content_type=content_type,
            file_id=file_id,
            file_unique_id=file_unique_id,
            thumbnail_file_id=thumbnail_file_id or "",
            file_size=file_size,
            duration=duration,
            created_by=message.from_user.id
        )
        
        location = f"Bo'lim: {data.get('section_name')}"
        if data.get('subsection_name'):
            location += f" → {data.get('subsection_name')}"
        
        size_text = f"{file_size // 1024} KB" if file_size < 1024*1024 else f"{file_size // (1024*1024)} MB"
        duration_text = f"{duration // 60}:{duration % 60:02d}" if duration > 0 else ""
        
        info_text = f"📍 {location}\n"
        info_text += f"📋 Sarlavha: {data.get('title')}\n"
        info_text += f"📄 Tavsif: {data.get('description') or 'Kiritilmagan'}\n"
        info_text += f"📁 Fayl hajmi: {size_text}\n"
        if duration_text:
            info_text += f"⏱️ Davomiyligi: {duration_text}\n"
        
        await message.answer(
            f"✅ <b>Kontent muvaffaqiyatli qo'shildi!</b>\n\n{info_text}"
        )
        
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    
    await state.clear()

# View content handlers  
@router.callback_query(F.data.startswith("view_custom_content_"))
async def view_custom_content(callback: CallbackQuery):
    """View specific custom content"""
    try:
        content_id = int(callback.data.replace("view_custom_content_", ""))
    except ValueError:
        await callback.answer("❌ Noto'g'ri ma'lumot")
        return
    
    # Check if user is premium for premium content
    user_id = callback.from_user.id
    async with aiosqlite.connect("language_bot.db") as db:
        cursor = await db.execute("SELECT is_premium FROM users WHERE user_id = ?", (user_id,))
        user_result = await cursor.fetchone()
        is_premium = user_result[0] if user_result else 0
        
        # Get content
        cursor = await db.execute("""
            SELECT id, section_id, subsection_id, title, description, content_type, 
                   file_id, file_unique_id, content_text, thumbnail_file_id, 
                   file_size, duration, is_premium, order_index, created_at
            FROM custom_content WHERE id = ?
        """, (content_id,))
        content = await cursor.fetchone()
    
    if not content:
        await callback.answer("❌ Kontent topilmadi!", show_alert=True)
        return
    
    content_id, section_id, subsection_id, title, description, content_type, file_id, file_unique_id, content_text, thumbnail_file_id, file_size, duration, content_is_premium, order_index, created_at = content
    
    # Check premium access
    if content_is_premium and not is_premium and user_id != ADMIN_ID:
        await callback.message.edit_text(
            f"💎 <b>Premium Kontent</b>\n\n"
            f"📋 {title}\n\n"
            f"🔒 Bu kontent premium foydalanuvchilar uchun!\n\n"
            f"✨ Premium a'zolik uchun:\n"
            f"💰 /premium - To'lov qilish\n"
            f"👥 /referral - Do'stlarni taklif qilish",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💎 Premium", callback_data="premium_menu")],
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"custom_section_{section_id}" if not subsection_id else f"custom_subsection_{subsection_id}")]
            ])
        )
        return
    
    # Send content based on type
    caption = f"📋 <b>{title}</b>\n\n"
    if description:
        caption += f"📄 {description}\n\n"
    
    back_callback = f"custom_section_{section_id}" if not subsection_id else f"custom_subsection_{subsection_id}"
    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=back_callback)]
    ])
    
    try:
        if content_type == 'text':
            full_text = caption + f"📝 <b>Matn:</b>\n{content_text}"
            await callback.message.edit_text(full_text, reply_markup=back_keyboard)
            
        elif content_type == 'photo':
            await callback.message.delete()
            await callback.bot.send_photo(
                chat_id=callback.message.chat.id,
                photo=file_id,
                caption=caption,
                reply_markup=back_keyboard
            )
            
        elif content_type == 'video':
            await callback.message.delete()
            await callback.bot.send_video(
                chat_id=callback.message.chat.id,
                video=file_id,
                caption=caption,
                reply_markup=back_keyboard
            )
            
        elif content_type == 'audio':
            await callback.message.delete()
            await callback.bot.send_audio(
                chat_id=callback.message.chat.id,
                audio=file_id,
                caption=caption,
                reply_markup=back_keyboard
            )
            
        elif content_type == 'voice':
            await callback.message.delete()
            await callback.bot.send_voice(
                chat_id=callback.message.chat.id,
                voice=file_id,
                caption=caption,
                reply_markup=back_keyboard
            )
            
        elif content_type == 'document':
            await callback.message.delete()
            await callback.bot.send_document(
                chat_id=callback.message.chat.id,
                document=file_id,
                caption=caption,
                reply_markup=back_keyboard
            )
            
    except Exception as e:
        await callback.answer(f"❌ Kontent ko'rsatishda xatolik: {str(e)}", show_alert=True)

@router.callback_query(F.data == "cancel_content_creation")
async def cancel_content_creation(callback: CallbackQuery, state: FSMContext):
    """Cancel content creation"""
    await state.clear()
    await callback.message.edit_text(
        "❌ <b>Kontent yaratish bekor qilindi</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin_panel")]
        ])
    )