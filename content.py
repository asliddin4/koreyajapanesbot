from aiogram import Router, F
from aiogram.types import CallbackQuery, InputMediaPhoto, InputMediaVideo, InputMediaAudio, InputMediaDocument, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database import get_sections, is_premium_active
from keyboards import get_languages_keyboard, get_sections_keyboard, get_subsections_keyboard, get_content_keyboard
from utils.rating_system import update_user_rating
import aiosqlite
from config import DATABASE_PATH

router = Router()

@router.callback_query(F.data == "learn")
async def choose_language(callback: CallbackQuery):
    await callback.message.edit_text(
        "🌐 <b>Tilni tanlang:</b>\n\n"
        "Qaysi tilni o'rganmoqchisiz?",
        reply_markup=get_languages_keyboard()
    )

@router.callback_query(F.data.in_(["korean", "japanese"]))
async def show_sections(callback: CallbackQuery):
    language = callback.data
    user_id = callback.from_user.id
    
    # Update user rating for language selection
    await update_user_rating(user_id, 'content_access')
    
    sections = await get_sections(language=language)
    
    if not sections:
        await callback.message.edit_text(
            f"❌ {language.title()} tili uchun hozircha bo'limlar mavjud emas.\n\n"
            "Tez orada qo'shiladi! 🔜",
            reply_markup=get_languages_keyboard()
        )
        return
    
    language_name = "Koreys" if language == "korean" else "Yapon"
    await callback.message.edit_text(
        f"📚 <b>{language_name} tili bo'limlari:</b>\n\n"
        "Bo'limni tanlang:",
        reply_markup=get_sections_keyboard(sections, language)
    )

@router.callback_query(F.data.startswith("section_"))
async def show_subsections(callback: CallbackQuery):
    section_id = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    
    # Check if section requires premium
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT name, is_premium, language FROM sections WHERE id = ?", 
            (section_id,)
        )
        section = await cursor.fetchone()
    
    if not section:
        await callback.answer("❌ Bo'lim topilmadi!", show_alert=True)
        return
    
    section_name, is_premium_section, language = section
    
    # Check premium access
    if is_premium_section and not await is_premium_active(user_id):
        await callback.answer(
            "💎 Bu premium bo'lim! Premium obuna oling yoki do'stlaringizni taklif qiling.",
            show_alert=True
        )
        return
    
    # Get subsections
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT * FROM subsections WHERE section_id = ? ORDER BY id",
            (section_id,)
        )
        subsections = await cursor.fetchall()
    
    if not subsections:
        await callback.message.edit_text(
            f"📚 <b>{section_name}</b>\n\n"
            "❌ Bu bo'limda hozircha pastki bo'limlar mavjud emas.",
            reply_markup=get_sections_keyboard(await get_sections(language=language), language)
        )
        return
    
    await callback.message.edit_text(
        f"📚 <b>{section_name}</b>\n\n"
        "Pastki bo'limni tanlang:",
        reply_markup=get_subsections_keyboard(subsections, section_id, language)
    )

@router.callback_query(F.data.startswith("subsection_") & ~F.data.startswith("subsection_topik") & ~F.data.startswith("subsection_jlpt"))
async def show_content(callback: CallbackQuery):
    parts = callback.data.split("_")
    try:
        subsection_id = int(parts[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Noto'g'ri ma'lumot")
        return
    user_id = callback.from_user.id
    
    # Check if subsection requires premium
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT s.name, s.is_premium, sec.name, sec.language, sec.id
            FROM subsections s
            JOIN sections sec ON s.section_id = sec.id
            WHERE s.id = ?
        """, (subsection_id,))
        subsection_info = await cursor.fetchone()
    
    if not subsection_info:
        await callback.answer("❌ Pastki bo'lim topilmadi!", show_alert=True)
        return
    
    subsection_name, is_premium_subsection, section_name, language, section_id = subsection_info
    
    # Check premium access
    if is_premium_subsection and not await is_premium_active(user_id):
        await callback.answer(
            "💎 Bu premium pastki bo'lim! Premium obuna oling yoki do'stlaringizni taklif qiling.",
            show_alert=True
        )
        return
    
    # Get content
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT id, subsection_id, title, file_id, file_type, caption, is_premium, created_at FROM content WHERE subsection_id = ? ORDER BY created_at",
            (subsection_id,)
        )
        content_items = await cursor.fetchall()
    
    if not content_items:
        await callback.message.edit_text(
            f"📚 <b>{section_name} > {subsection_name}</b>\n\n"
            "❌ Bu pastki bo'limda hozircha kontent mavjud emas.",
            reply_markup=get_content_keyboard(subsection_id, section_id, language, [])
        )
        return
    
    # Update user rating for accessing content
    await update_user_rating(user_id, 'content_view')
    
    await callback.message.edit_text(
        f"📚 <b>{section_name} > {subsection_name}</b>\n\n"
        f"📁 Mavjud kontentlar: {len(content_items)} ta\n\n"
        "Kontentni tanlang:",
        reply_markup=get_content_keyboard(subsection_id, section_id, language, content_items)
    )

@router.callback_query(F.data.startswith("content_") & ~F.data.startswith("content_text_") & ~F.data.startswith("content_photo_") & ~F.data.startswith("content_video_") & ~F.data.startswith("content_audio_") & ~F.data.startswith("content_document_") & ~F.data.startswith("content_music_"))
async def show_content_item(callback: CallbackQuery):
    try:
        content_id = int(callback.data.split("_")[1])
    except (ValueError, IndexError):
        await callback.answer("❌ Noto'g'ri ma'lumot")
        return
    user_id = callback.from_user.id
    
    # Get content details
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT c.*, s.name as subsection_name, sec.name as section_name, 
                   sec.language, s.section_id, c.subsection_id
            FROM content c
            JOIN subsections s ON c.subsection_id = s.id
            JOIN sections sec ON s.section_id = sec.id
            WHERE c.id = ?
        """, (content_id,))
        content_info = await cursor.fetchone()
    
    if not content_info:
        await callback.answer("❌ Kontent topilmadi!", show_alert=True)
        return
    
    # Check premium access for content  
    # content_info structure: id, subsection_id, title, file_id, file_type, caption, is_premium, created_at, content_text, subsection_name, section_name, language, section_id, subsection_id
    is_premium_content = content_info[6] if len(content_info) > 6 else False
    if is_premium_content and not await is_premium_active(user_id):
        await callback.answer(
            "💎 Bu premium kontent! Premium obuna oling yoki do'stlaringizni taklif qiling.",
            show_alert=True
        )
        return
    
    # Update user progress and rating
    await update_user_rating(user_id, 'content_complete')
    
    # Mark content as viewed
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT OR REPLACE INTO user_progress (user_id, content_id, completed, completed_at)
            VALUES (?, ?, 1, CURRENT_TIMESTAMP)
        """, (user_id, content_id))
        await db.commit()
    
    # Send content based on type
    file_id = content_info[3]
    file_type = content_info[4] 
    title = content_info[2]
    caption = content_info[5]
    content_text_data = content_info[8] if len(content_info) > 8 else None
    
    content_text = f"📚 <b>{title}</b>\n"
    if caption:
        content_text += f"\n{caption}"
    
    try:
        if file_type == 'text':
            # For text content, use content_text if available, otherwise file_id
            text_content = content_text_data if content_text_data else file_id
            full_text = f"{content_text}\n\n📄 <b>Matn:</b>\n{text_content}"
            
            # Send text message with navigation - get subsection_id, section_id, language from content_info
            subsection_id = content_info[1]
            section_id = content_info[12] if len(content_info) > 12 else None
            language = content_info[11] if len(content_info) > 11 else 'korean'
            
            from keyboards import get_content_navigation_keyboard
            await callback.message.edit_text(
                full_text,
                reply_markup=get_content_navigation_keyboard(subsection_id, section_id, language)
            )
            return
            
        elif file_type == 'photo':
            await callback.bot.send_photo(
                chat_id=callback.from_user.id,
                photo=file_id,
                caption=content_text
            )
        elif file_type == 'video':
            await callback.bot.send_video(
                chat_id=callback.from_user.id,
                video=file_id,
                caption=content_text
            )
        elif file_type == 'audio':
            await callback.bot.send_audio(
                chat_id=callback.from_user.id,
                audio=file_id,
                caption=content_text
            )
        elif file_type == 'document':
            await callback.bot.send_document(
                chat_id=callback.from_user.id,
                document=file_id,
                caption=content_text
            )
        
        # Get navigation keyboard
        from keyboards import get_content_navigation_keyboard
        
        await callback.message.edit_text(
            f"✅ <b>Kontent yuborildi!</b>\n\n"
            f"📚 {content_info[9]} > {content_info[8]}\n"
            f"📄 {title}",
            reply_markup=get_content_navigation_keyboard(
                content_info[12],  # subsection_id
                content_info[11],  # section_id
                content_info[10]   # language
            )
        )
        
    except TelegramBadRequest as e:
        await callback.answer(f"❌ Kontent yuborishda xatolik: {str(e)}", show_alert=True)

@router.callback_query(F.data.startswith("back_to_"))
async def handle_back_navigation(callback: CallbackQuery):
    parts = callback.data.split("_")
    destination = parts[2]
    
    if destination == "languages":
        await choose_language(callback)
    elif destination == "sections":
        if len(parts) > 3:
            language = parts[3]
            # Bo'limlarni tilga qarab ko'rsatish
            await show_sections_for_language(callback, language)
        else:
            await choose_language(callback)
    elif destination.startswith("subsections"):
        if len(parts) > 3:
            section_id = int(parts[3])
            # Pastki bo'limlarni ko'rsatish
            await show_subsections_for_section(callback, section_id)
        else:
            await choose_language(callback)
    elif destination.startswith("content"):
        if len(parts) > 3:
            subsection_id = int(parts[3])
            # Kontentni ko'rsatish
            await show_content_for_subsection(callback, subsection_id)
        else:
            await choose_language(callback)

# Yordamchi funksiyalar orqaga qaytish uchun
async def show_sections_for_language(callback: CallbackQuery, language: str):
    """Tilga qarab bo'limlarni ko'rsatish"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT id, name, description, is_premium 
            FROM sections 
            WHERE language = ? 
            ORDER BY created_at
        """, (language,))
        sections = await cursor.fetchall()
    
    if not sections:
        await callback.message.edit_text(
            f"❌ {language.title()} tili uchun bo'limlar topilmadi.",
            reply_markup=get_back_to_languages_keyboard()
        )
        return
    
    sections_text = f"📚 <b>{language.title()} tili bo'limlari:</b>\n\n"
    
    keyboard = InlineKeyboardBuilder()
    for section in sections:
        premium_icon = "💎" if section[3] else ""
        sections_text += f"{premium_icon} {section[1]}\n"
        if section[2]:
            sections_text += f"   <i>{section[2]}</i>\n"
        sections_text += "\n"
        
        keyboard.add(InlineKeyboardButton(
            text=f"{premium_icon} {section[1]}",
            callback_data=f"section_{section[0]}"
        ))
    
    keyboard.add(InlineKeyboardButton(text="🔙 Tillarga qaytish", callback_data="back_to_languages"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(sections_text, reply_markup=keyboard.as_markup())

async def show_subsections_for_section(callback: CallbackQuery, section_id: int):
    """Bo'limga qarab pastki bo'limlarni ko'rsatish"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Bo'lim ma'lumotlarini olish
        cursor = await db.execute("SELECT name, language FROM sections WHERE id = ?", (section_id,))
        section = await cursor.fetchone()
        
        if not section:
            await callback.answer("❌ Bo'lim topilmadi!", show_alert=True)
            return
        
        # Pastki bo'limlarni olish
        cursor = await db.execute("""
            SELECT id, name, description, is_premium 
            FROM subsections 
            WHERE section_id = ? 
            ORDER BY id
        """, (section_id,))
        subsections = await cursor.fetchall()
    
    if not subsections:
        await callback.message.edit_text(
            f"❌ {section[0]} bo'limida pastki bo'limlar topilmadi.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔙 Bo'limlarga qaytish", callback_data=f"back_to_sections_{section[1]}")
            ]])
        )
        return
    
    subsections_text = f"📖 <b>{section[0]}</b>\n\n"
    
    keyboard = InlineKeyboardBuilder()
    for subsection in subsections:
        premium_icon = "💎" if subsection[3] else ""
        subsections_text += f"{premium_icon} {subsection[1]}\n"
        if subsection[2]:
            subsections_text += f"   <i>{subsection[2]}</i>\n"
        subsections_text += "\n"
        
        keyboard.add(InlineKeyboardButton(
            text=f"{premium_icon} {subsection[1]}",
            callback_data=f"subsection_{subsection[0]}"
        ))
    
    keyboard.add(InlineKeyboardButton(text="🔙 Bo'limlarga qaytish", callback_data=f"back_to_sections_{section[1]}"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(subsections_text, reply_markup=keyboard.as_markup())

async def show_content_for_subsection(callback: CallbackQuery, subsection_id: int):
    """Pastki bo'limga qarab kontentlarni ko'rsatish"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Pastki bo'lim va bo'lim ma'lumotlarini olish
        cursor = await db.execute("""
            SELECT s.name, s.section_id, sec.name, sec.language 
            FROM subsections s
            JOIN sections sec ON s.section_id = sec.id
            WHERE s.id = ?
        """, (subsection_id,))
        subsection_info = await cursor.fetchone()
        
        if not subsection_info:
            await callback.answer("❌ Pastki bo'lim topilmadi!", show_alert=True)
            return
        
        # Kontentlarni olish
        cursor = await db.execute("""
            SELECT id, title, file_type, is_premium
            FROM content 
            WHERE subsection_id = ? 
            ORDER BY id
        """, (subsection_id,))
        contents = await cursor.fetchall()
    
    if not contents:
        await callback.message.edit_text(
            f"❌ {subsection_info[0]} bo'limida kontent topilmadi.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"back_to_subsections_{subsection_info[1]}")
            ]])
        )
        return
    
    content_text = f"📖 <b>{subsection_info[2]} > {subsection_info[0]}</b>\n\n"
    
    keyboard = InlineKeyboardBuilder()
    for content in contents:
        premium_icon = "💎" if content[3] else ""
        type_icon = "📄" if content[2] == "text" else "🖼️" if content[2] == "photo" else "🎥" if content[2] == "video" else "🎵"
        content_text += f"{premium_icon}{type_icon} {content[1]}\n"
        
        keyboard.add(InlineKeyboardButton(
            text=f"{premium_icon}{type_icon} {content[1]}",
            callback_data=f"content_{content[0]}"
        ))
    
    keyboard.add(InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"back_to_subsections_{subsection_info[1]}"))
    keyboard.adjust(1)
    
    await callback.message.edit_text(content_text, reply_markup=keyboard.as_markup())

@router.callback_query(F.data == "my_progress")
async def show_user_progress(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Get completed content count by language
        cursor = await db.execute("""
            SELECT sec.language, COUNT(up.id) as completed_count
            FROM user_progress up
            JOIN content c ON up.content_id = c.id
            JOIN subsections s ON c.subsection_id = s.id
            JOIN sections sec ON s.section_id = sec.id
            WHERE up.user_id = ? AND up.completed = 1
            GROUP BY sec.language
        """, (user_id,))
        progress_by_language = await cursor.fetchall()
        
        # Get total content count by language
        cursor = await db.execute("""
            SELECT sec.language, COUNT(c.id) as total_count
            FROM content c
            JOIN subsections s ON c.subsection_id = s.id
            JOIN sections sec ON s.section_id = sec.id
            GROUP BY sec.language
        """, ())
        total_by_language = await cursor.fetchall()
        
        # Get recent progress
        cursor = await db.execute("""
            SELECT c.title, sec.language, up.completed_at
            FROM user_progress up
            JOIN content c ON up.content_id = c.id
            JOIN subsections s ON c.subsection_id = s.id
            JOIN sections sec ON s.section_id = sec.id
            WHERE up.user_id = ? AND up.completed = 1
            ORDER BY up.completed_at DESC
            LIMIT 5
        """, (user_id,))
        recent_progress = await cursor.fetchall()
    
    progress_text = "📊 <b>Sizning o'rganish jarayoningiz</b>\n\n"
    
    # Create dictionaries for easier lookup
    progress_dict = {lang: count for lang, count in progress_by_language}
    total_dict = {lang: count for lang, count in total_by_language}
    
    # Show progress by language
    for language in ['korean', 'japanese']:
        lang_name = "Koreys" if language == "korean" else "Yapon"
        completed = progress_dict.get(language, 0)
        total = total_dict.get(language, 0)
        
        if total > 0:
            percentage = (completed / total) * 100
            progress_bar = "█" * int(percentage // 10) + "░" * (10 - int(percentage // 10))
            progress_text += f"🇰🇷 <b>{lang_name}:</b> {completed}/{total} ({percentage:.1f}%)\n"
            progress_text += f"   {progress_bar}\n\n"
    
    # Show recent activity
    if recent_progress:
        progress_text += "📚 <b>So'nggi faoliyat:</b>\n"
        for content_title, language, completed_at in recent_progress:
            lang_flag = "🇰🇷" if language == "korean" else "🇯🇵"
            date = completed_at[:10]
            progress_text += f"{lang_flag} {content_title} - {date}\n"
    else:
        progress_text += "📚 <b>Hozircha faoliyat yo'q</b>\n"
        progress_text += "O'rganishni boshlash uchun 'O'rganish' tugmasini bosing!"
    
    from keyboards import get_main_menu
    from config import ADMIN_ID
    
    await callback.message.edit_text(
        progress_text,
        reply_markup=get_main_menu(user_id == ADMIN_ID)
    )
