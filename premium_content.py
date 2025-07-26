from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite

from config import ADMIN_ID, DATABASE_PATH

router = Router()

class PremiumContentStates(StatesGroup):
    premium_content_title = State()
    premium_content_description = State()
    premium_content_type = State()
    premium_content_upload = State()

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

@router.callback_query(F.data == "admin_premium_content")
@admin_only
async def admin_premium_content_menu(callback: CallbackQuery):
    """Premium content management menu"""
    await callback.message.edit_text(
        """📱 <b>Premium Content Boshqaruvi</b>
        
Premium bo'limlarga kontent qo'shishingiz mumkin:

📝 <b>Topik 1 Premium</b> - Koreys tili Topik 1 darslari
📝 <b>Topik 2 Premium</b> - Koreys tili Topik 2 darslari  
🇯🇵 <b>JLPT Premium</b> - Yapon tili JLPT darslari

Qaysi bo'limga kontent qo'shmoqchisiz?""",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Topik 1 Premium", callback_data="premium_content_topik1"),
                InlineKeyboardButton(text="📝 Topik 2 Premium", callback_data="premium_content_topik2")
            ],
            [
                InlineKeyboardButton(text="🇯🇵 JLPT Premium", callback_data="premium_content_jlpt")
            ],
            [
                InlineKeyboardButton(text="📋 Barcha kontent", callback_data="view_all_premium_content")
            ],
            [
                InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin_panel")
            ]
        ])
    )

@router.callback_query(F.data.startswith("premium_content_"))
@admin_only
async def premium_content_section(callback: CallbackQuery):
    """Show premium content for specific section"""
    section_type = callback.data.replace("premium_content_", "")
    
    # Skip if it's view_all_premium_content
    if section_type == "view_all_premium_content":
        return
    
    section_names = {
        "topik1": "📝 Topik 1 Premium",
        "topik2": "📝 Topik 2 Premium", 
        "jlpt": "🇯🇵 JLPT Premium"
    }
    
    section_name = section_names.get(section_type, "Premium Bo'lim")
    
    from database import get_premium_content
    content_list = await get_premium_content(section_type)
    
    text = f"📱 <b>{section_name}</b>\n\n"
    
    if content_list:
        text += "📚 <b>Mavjud kontent:</b>\n\n"
        for i, content in enumerate(content_list, 1):
            content_id, title, description, file_id, file_type, content_text, order_index = content
            text += f"{i}. 📖 {title}\n"
            if description:
                text += f"   📝 {description}\n"
            text += f"   📁 Tur: {file_type or 'matn'}\n\n"
    else:
        text += "❌ Hozircha kontent yo'q.\n\n"
    
    buttons = [
        [
            InlineKeyboardButton(text="➕ Kontent qo'shish", callback_data=f"add_premium_content_{section_type}")
        ]
    ]
    
    if content_list:
        buttons.append([
            InlineKeyboardButton(text="🗑️ Kontent o'chirish", callback_data=f"delete_premium_content_{section_type}")
        ])
    
    buttons.append([
        InlineKeyboardButton(text="🔙 Premium kontent", callback_data="admin_premium_content")
    ])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data.startswith("add_premium_content_"))
@admin_only
async def add_premium_content_start(callback: CallbackQuery, state: FSMContext):
    """Start adding premium content"""
    section_type = callback.data.replace("add_premium_content_", "")
    
    section_names = {
        "topik1": "📝 Topik 1 Premium",
        "topik2": "📝 Topik 2 Premium", 
        "jlpt": "🇯🇵 JLPT Premium"
    }
    
    section_name = section_names.get(section_type, "Premium Bo'lim")
    
    await state.update_data(premium_section_type=section_type)
    
    await callback.message.edit_text(
        f"➕ <b>{section_name} ga kontent qo'shish</b>\n\n"
        "📝 Kontent sarlavhasini kiriting:",
        reply_markup=None
    )
    
    await state.set_state(PremiumContentStates.premium_content_title)

@router.message(PremiumContentStates.premium_content_title)
@admin_only
async def premium_content_title(message: Message, state: FSMContext):
    """Get premium content title"""
    title = message.text.strip()
    
    if not title:
        await message.answer("❌ Sarlavha bo'sh bo'lishi mumkin emas!")
        return
    
    await state.update_data(premium_content_title=title)
    await message.answer(
        "📝 Kontent tavsifini kiriting (ixtiyoriy):\n\n"
        "Agar tavsif kerak bo'lmasa, 'yo'q' deb yozing."
    )
    await state.set_state(PremiumContentStates.premium_content_description)

@router.message(PremiumContentStates.premium_content_description)
@admin_only
async def premium_content_description(message: Message, state: FSMContext):
    """Get premium content description"""
    description = None if message.text.lower() in ['yo\'q', 'no', '-'] else message.text
    await state.update_data(premium_content_description=description)
    
    await message.answer(
        "📁 Kontent turini tanlang:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📄 Matn", callback_data="premium_content_type_text"),
                InlineKeyboardButton(text="🖼️ Rasm", callback_data="premium_content_type_photo")
            ],
            [
                InlineKeyboardButton(text="🎥 Video", callback_data="premium_content_type_video"),
                InlineKeyboardButton(text="🎵 Audio", callback_data="premium_content_type_audio")
            ],
            [
                InlineKeyboardButton(text="📁 Hujjat", callback_data="premium_content_type_document")
            ]
        ])
    )
    await state.set_state(PremiumContentStates.premium_content_type)

@router.callback_query(F.data == "premium_content_type_text")
@admin_only
async def premium_content_text_type(callback: CallbackQuery, state: FSMContext):
    """Handle text content type"""
    await callback.message.edit_text(
        "📄 <b>Matn kontent</b>\n\n"
        "Matn kontentni kiriting:"
    )
    await state.set_state(PremiumContentStates.premium_content_upload)

@router.callback_query(F.data.startswith("premium_content_type_"))
@admin_only
async def premium_content_file_type(callback: CallbackQuery, state: FSMContext):
    """Handle file content types"""
    content_type = callback.data.replace("premium_content_type_", "")
    
    # Skip text type as it's handled separately
    if content_type == "text":
        return
        
    await state.update_data(premium_content_file_type=content_type)
    
    type_names = {
        "photo": "🖼️ Rasm",
        "video": "🎥 Video", 
        "audio": "🎵 Audio",
        "document": "📁 Hujjat"
    }
    
    type_name = type_names.get(content_type, "Fayl")
    
    await callback.message.edit_text(
        f"📁 <b>{type_name} yuklash</b>\n\n"
        f"{type_name} faylni yuboring:"
    )
    await state.set_state(PremiumContentStates.premium_content_upload)

@router.message(PremiumContentStates.premium_content_upload)
@admin_only
async def premium_content_upload(message: Message, state: FSMContext):
    """Handle premium content upload"""
    try:
        data = await state.get_data()
        section_type = data['premium_section_type']
        title = data['premium_content_title']
        description = data.get('premium_content_description')
        
        file_id = None
        file_type = None
        content_text = None
        
        # Handle text content
        if message.content_type == "text":
            content_text = message.text
            file_type = "text"
        # Handle file content
        elif message.content_type == "photo":
            file_id = message.photo[-1].file_id
            file_type = "photo"
        elif message.content_type == "video":
            file_id = message.video.file_id
            file_type = "video"
        elif message.content_type == "audio":
            file_id = message.audio.file_id
            file_type = "audio"
        elif message.content_type == "document":
            file_id = message.document.file_id
            file_type = "document"
        else:
            await message.answer("❌ Noto'g'ri fayl turi!")
            return
        
        # Save to database
        from database import add_premium_content
        await add_premium_content(
            section_type=section_type,
            title=title,
            description=description,
            file_id=file_id,
            file_type=file_type,
            content_text=content_text
        )
        
        section_names = {
            "topik1": "📝 Topik 1 Premium",
            "topik2": "📝 Topik 2 Premium", 
            "jlpt": "🇯🇵 JLPT Premium"
        }
        
        section_name = section_names.get(section_type, "Premium Bo'lim")
        
        description_text = description or "Yo'q"
        await message.answer(
            f"✅ <b>Kontent muvaffaqiyatli qo'shildi!</b>\n\n"
            f"📱 Bo'lim: {section_name}\n"
            f"📖 Sarlavha: {title}\n"
            f"📝 Tavsif: {description_text}\n"
            f"📁 Tur: {file_type}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Premium kontent", callback_data="admin_premium_content")]
            ])
        )
        
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
        await state.clear()