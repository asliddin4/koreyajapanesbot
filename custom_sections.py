from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite
from config import ADMIN_ID

router = Router()

class CustomSectionStates(StatesGroup):
    waiting_for_section_name = State()
    waiting_for_section_description = State()
    waiting_for_subsection_name = State()
    waiting_for_subsection_description = State()

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

# Database functions for custom sections
async def create_custom_sections_table():
    """Create custom sections table if it doesn't exist"""
    async with aiosqlite.connect("language_bot.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                icon TEXT DEFAULT '📂',
                is_premium INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                order_index INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER
            )
        """)
        
        await db.execute("""
            CREATE TABLE IF NOT EXISTS custom_subsections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                icon TEXT DEFAULT '📄',
                is_premium INTEGER DEFAULT 0,
                order_index INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (section_id) REFERENCES custom_sections (id)
            )
        """)
        
        await db.commit()

async def add_custom_section(name: str, description=None, icon: str = "📂", is_premium: int = 0, created_by=None):
    """Add new custom section"""
    await create_custom_sections_table()
    async with aiosqlite.connect("language_bot.db") as db:
        cursor = await db.execute(
            "SELECT COALESCE(MAX(order_index), 0) + 1 FROM custom_sections"
        )
        order_index = (await cursor.fetchone())[0]
        
        await db.execute("""
            INSERT INTO custom_sections (name, description, icon, is_premium, order_index, created_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, description, icon, is_premium, order_index, created_by))
        await db.commit()
        return True

async def get_custom_sections():
    """Get all custom sections"""
    await create_custom_sections_table()
    async with aiosqlite.connect("language_bot.db") as db:
        cursor = await db.execute("""
            SELECT id, name, description, icon, is_premium, is_active, order_index, created_at
            FROM custom_sections 
            WHERE is_active = 1
            ORDER BY order_index ASC
        """)
        return await cursor.fetchall()

async def add_custom_subsection(section_id: int, name: str, description=None, icon: str = "📄", is_premium: int = 0):
    """Add subsection to custom section"""
    async with aiosqlite.connect("language_bot.db") as db:
        cursor = await db.execute(
            "SELECT COALESCE(MAX(order_index), 0) + 1 FROM custom_subsections WHERE section_id = ?",
            (section_id,)
        )
        order_index = (await cursor.fetchone())[0]
        
        await db.execute("""
            INSERT INTO custom_subsections (section_id, name, description, icon, is_premium, order_index)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (section_id, name, description, icon, is_premium, order_index))
        await db.commit()
        return True

async def get_custom_subsections(section_id: int):
    """Get subsections for a custom section"""
    async with aiosqlite.connect("language_bot.db") as db:
        cursor = await db.execute("""
            SELECT id, section_id, name, description, icon, is_premium, order_index, created_at
            FROM custom_subsections 
            WHERE section_id = ?
            ORDER BY order_index ASC
        """, (section_id,))
        return await cursor.fetchall()

# Keyboards for custom sections
def get_custom_sections_keyboard(sections):
    """Generate keyboard for custom sections"""
    buttons = []
    for section in sections:
        section_id, name, description, icon, is_premium, is_active, order_index, created_at = section
        premium_icon = "💎 " if is_premium else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{premium_icon}{icon} {name}",
                callback_data=f"custom_section_{section_id}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="🔙 Bosh menu", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_custom_subsections_keyboard(subsections, section_id):
    """Generate keyboard for custom subsections"""
    buttons = []
    for subsection in subsections:
        sub_id, sec_id, name, description, icon, is_premium, order_index, created_at = subsection
        premium_icon = "💎 " if is_premium else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{premium_icon}{icon} {name}",
                callback_data=f"custom_subsection_{sub_id}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="🔙 Bo'limlar", callback_data="view_custom_sections")
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_admin_custom_sections_keyboard():
    """Admin keyboard for managing custom sections"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="➕ Bo'lim yaratish", callback_data="create_custom_section"),
            InlineKeyboardButton(text="📋 Bo'limlarni ko'rish", callback_data="view_custom_sections")
        ],
        [
            InlineKeyboardButton(text="🗑️ Bo'limlarni o'chirish", callback_data="delete_custom_sections")
        ],
        [
            InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin_panel")
        ]
    ])

# Admin handlers
@router.callback_query(F.data == "admin_custom_sections")
@admin_only
async def admin_custom_sections_menu(callback: CallbackQuery):
    """Show custom sections admin menu"""
    await callback.message.edit_text(
        "🏗️ <b>Moslashtirilgan Bo'limlar Boshqaruvi</b>\n\n"
        "📝 Bu yerda bosh menyuga o'zingiz xohlagan bo'limlarni qo'shishingiz mumkin.\n\n"
        "🎯 Har bir bo'lim ichiga ham pastki bo'limlar yarata olasiz.\n\n"
        "⚙️ Quyidagi tugmalardan birini tanlang:",
        reply_markup=get_admin_custom_sections_keyboard()
    )

@router.callback_query(F.data == "create_custom_section")
@admin_only
async def create_custom_section_start(callback: CallbackQuery, state: FSMContext):
    """Start creating new custom section"""
    await callback.message.edit_text(
        "➕ <b>Yangi Bo'lim Yaratish</b>\n\n"
        "📝 Bo'lim nomini kiriting:\n\n"
        "💡 Masalan: 'Grammatika', 'Lug'at', 'Amaliyot' va h.k.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_custom_sections")]
        ])
    )
    await state.set_state(CustomSectionStates.waiting_for_section_name)

@router.message(CustomSectionStates.waiting_for_section_name)
@admin_only
async def process_section_name(message: Message, state: FSMContext):
    """Process section name"""
    section_name = message.text.strip()
    
    if len(section_name) < 2:
        await message.answer("❌ Bo'lim nomi kamida 2 ta belgi bo'lishi kerak!")
        return
    
    await state.update_data(section_name=section_name)
    
    await message.answer(
        f"📝 <b>Bo'lim tavsifi</b>\n\n"
        f"📌 Nom: {section_name}\n\n"
        f"💬 Bo'lim haqida qisqacha tavsif kiriting "
        f"(yoki /skip yozing tavsif qo'shmaslik uchun):"
    )
    await state.set_state(CustomSectionStates.waiting_for_section_description)

@router.message(CustomSectionStates.waiting_for_section_description)
@admin_only
async def process_section_description(message: Message, state: FSMContext):
    """Process section description"""
    data = await state.get_data()
    section_name = data['section_name']
    description = None if message.text == "/skip" else message.text.strip()
    
    try:
        await add_custom_section(
            name=section_name,
            description=description,
            created_by=message.from_user.id
        )
        
        await message.answer(
            f"✅ <b>Bo'lim muvaffaqiyatli yaratildi!</b>\n\n"
            f"📂 Nom: {section_name}\n"
            f"📄 Tavsif: {description or 'Kiritilmagan'}\n\n"
            f"🎯 Bo'lim bosh menyuga qo'shildi.\n"
            f"💡 Endi bu bo'limga pastki bo'limlar qo'shishingiz mumkin.",
            reply_markup=get_admin_custom_sections_keyboard()
        )
        
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    
    await state.clear()

# View custom sections
@router.callback_query(F.data == "view_custom_sections")
async def view_custom_sections(callback: CallbackQuery):
    """Show all custom sections"""
    sections = await get_custom_sections()
    
    if not sections:
        await callback.message.edit_text(
            "📭 <b>Hech qanday bo'lim topilmadi</b>\n\n"
            "💡 Admin panel orqali yangi bo'limlar yarating.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Bosh menu", callback_data="main_menu")]
            ])
        )
        return
    
    await callback.message.edit_text(
        f"📂 <b>Barcha Bo'limlar</b>\n\n"
        f"📊 Jami: {len(sections)} ta bo'lim\n\n"
        f"👆 Bo'limni tanlang:",
        reply_markup=get_custom_sections_keyboard(sections)
    )

# View specific custom section
@router.callback_query(F.data.startswith("custom_section_"))
async def view_custom_section(callback: CallbackQuery):
    """View specific custom section and its subsections/content"""
    try:
        section_id = int(callback.data.replace("custom_section_", ""))
    except ValueError:
        await callback.answer("❌ Noto'g'ri ma'lumot")
        return
    
    # Get section info
    async with aiosqlite.connect("language_bot.db") as db:
        cursor = await db.execute("""
            SELECT id, name, description, icon, is_premium
            FROM custom_sections WHERE id = ?
        """, (section_id,))
        section = await cursor.fetchone()
    
    if not section:
        await callback.answer("❌ Bo'lim topilmadi!", show_alert=True)
        return
    
    section_id, name, description, icon, is_premium = section
    subsections = await get_custom_subsections(section_id)
    
    # Get content for this section (direct content, not in subsections)
    from handlers.custom_content import get_custom_content
    content = await get_custom_content(section_id=section_id)
    
    # Check if admin
    is_admin = callback.from_user.id == ADMIN_ID
    
    section_text = f"{icon} <b>{name}</b>\n\n"
    if description:
        section_text += f"📄 {description}\n\n"
    
    buttons = []
    
    # Add subsections
    for subsection in subsections:
        sub_id, sec_id, sub_name, sub_description, sub_icon, sub_is_premium, order_index, created_at = subsection
        premium_icon = "💎 " if sub_is_premium else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{premium_icon}{sub_icon} {sub_name}",
                callback_data=f"custom_subsection_{sub_id}"
            )
        ])
    
    # Add direct content
    for content_item in content:
        content_id, sec_id, sub_id, title, desc, content_type, file_id, file_unique_id, content_text, thumbnail_file_id, file_size, duration, content_is_premium, order_index, created_at = content_item
        
        type_icons = {
            'text': '📝',
            'photo': '🖼️',
            'video': '🎥', 
            'audio': '🎵',
            'voice': '🎤',
            'document': '📄'
        }
        
        icon = type_icons.get(content_type, '📂')
        premium_icon = "💎 " if content_is_premium else ""
        
        buttons.append([
            InlineKeyboardButton(
                text=f"{premium_icon}{icon} {title}",
                callback_data=f"view_custom_content_{content_id}"
            )
        ])
    
    # Statistics
    total_items = len(subsections) + len(content)
    if total_items > 0:
        section_text += f"📊 Jami: {len(subsections)} pastki bo'lim, {len(content)} kontent\n\n"
        section_text += "👆 Elementni tanlang:"
    else:
        section_text += "📭 Hech qanday kontent yoki pastki bo'lim yo'q.\n\n"
    
    # Add admin buttons
    if is_admin:
        admin_buttons = [
            [InlineKeyboardButton(text="➕ Pastki bo'lim qo'shish", callback_data=f"add_subsection_{section_id}")],
            [InlineKeyboardButton(text="📁 Kontent qo'shish", callback_data=f"add_content_section_{section_id}")],
            [InlineKeyboardButton(text="🗑️ Bo'limni o'chirish", callback_data=f"delete_section_{section_id}")]
        ]
        buttons = admin_buttons + buttons
    
    # Add back button
    buttons.append([InlineKeyboardButton(text="🔙 Bo'limlar", callback_data="view_custom_sections")])
    
    await callback.message.edit_text(
        section_text, 
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

# Add subsection to custom section
@router.callback_query(F.data.startswith("add_subsection_"))
@admin_only
async def add_subsection_start(callback: CallbackQuery, state: FSMContext):
    """Start adding subsection to custom section"""
    try:
        section_id = int(callback.data.replace("add_subsection_", ""))
    except ValueError:
        await callback.answer("❌ Noto'g'ri ma'lumot")
        return
    
    # Get section name
    async with aiosqlite.connect("language_bot.db") as db:
        cursor = await db.execute("SELECT name FROM custom_sections WHERE id = ?", (section_id,))
        section = await cursor.fetchone()
    
    if not section:
        await callback.answer("❌ Bo'lim topilmadi!", show_alert=True)
        return
    
    section_name = section[0]
    
    await state.update_data(section_id=section_id, section_name=section_name)
    
    await callback.message.edit_text(
        f"➕ <b>Pastki Bo'lim Qo'shish</b>\n\n"
        f"📂 Bo'lim: {section_name}\n\n"
        f"📝 Pastki bo'lim nomini kiriting:\n\n"
        f"💡 Masalan: 'Dars 1', 'Amaliyot 1', 'Test' va h.k.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"custom_section_{section_id}")]
        ])
    )
    await state.set_state(CustomSectionStates.waiting_for_subsection_name)

@router.message(CustomSectionStates.waiting_for_subsection_name)
@admin_only
async def process_subsection_name(message: Message, state: FSMContext):
    """Process subsection name"""
    data = await state.get_data()
    section_id = data['section_id']
    section_name = data['section_name']
    subsection_name = message.text.strip()
    
    if len(subsection_name) < 2:
        await message.answer("❌ Pastki bo'lim nomi kamida 2 ta belgi bo'lishi kerak!")
        return
    
    await state.update_data(subsection_name=subsection_name)
    
    await message.answer(
        f"📝 <b>Pastki bo'lim tavsifi</b>\n\n"
        f"📂 Bo'lim: {section_name}\n"
        f"📌 Pastki bo'lim: {subsection_name}\n\n"
        f"💬 Pastki bo'lim haqida qisqacha tavsif kiriting "
        f"(yoki /skip yozing tavsif qo'shmaslik uchun):"
    )
    await state.set_state(CustomSectionStates.waiting_for_subsection_description)

@router.message(CustomSectionStates.waiting_for_subsection_description)
@admin_only
async def process_subsection_description(message: Message, state: FSMContext):
    """Process subsection description"""
    data = await state.get_data()
    section_id = data['section_id']
    section_name = data['section_name']
    subsection_name = data['subsection_name']
    description = None if message.text == "/skip" else message.text.strip()
    
    try:
        await add_custom_subsection(
            section_id=section_id,
            name=subsection_name,
            description=description
        )
        
        await message.answer(
            f"✅ <b>Pastki bo'lim muvaffaqiyatli qo'shildi!</b>\n\n"
            f"📂 Bo'lim: {section_name}\n"
            f"📌 Pastki bo'lim: {subsection_name}\n"
            f"📄 Tavsif: {description or 'Kiritilmagan'}\n\n"
            f"🎯 Pastki bo'lim bo'limga qo'shildi.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Bo'limga qaytish", callback_data=f"custom_section_{section_id}")]
            ])
        )
        
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")
    
    await state.clear()