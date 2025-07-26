from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ContentType, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite

from config import ADMIN_ID, DATABASE_PATH, PREMIUM_PRICE_UZS
from keyboards import get_admin_menu, get_admin_sections_keyboard, get_admin_content_keyboard, get_broadcast_menu, get_broadcast_confirm
from messages import ADMIN_WELCOME_MESSAGE
from database import activate_premium, get_user

router = Router()

class AdminStates(StatesGroup):
    # Section management
    creating_section = State()
    creating_subsection = State()
    selecting_section_for_subsection = State()
    
    # Content management
    uploading_content = State()
    selecting_subsection_for_content = State()
    entering_content_title = State()
    entering_content_caption = State()
    selecting_content_type = State()
    entering_text_content = State()
    
    # Quiz management
    creating_quiz = State()
    entering_quiz_title = State()
    entering_quiz_description = State()
    adding_quiz_question = State()
    entering_question_text = State()
    entering_question_options = State()
    
    # Premium management
    waiting_user_id_for_premium = State()
    waiting_premium_duration = State()
    
    # Quiz import/export
    importing_quiz_data = State()
    
    # Broadcast states
    broadcast_text = State()
    broadcast_photo = State()
    broadcast_video = State()
    broadcast_audio = State()
    broadcast_document = State()
    broadcast_caption = State()
    
    # Premium Content Management States  
    premium_content_title = State()
    premium_content_description = State()
    premium_content_type = State()
    premium_content_upload = State()

def admin_only(func):
    """Decorator to restrict access to admin only"""
    from functools import wraps
    
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract message or callback from args
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

@router.message(Command("admin"))
@admin_only
async def admin_panel(message: Message):
    """Admin panel main handler"""
    await message.answer(
        ADMIN_WELCOME_MESSAGE,
        reply_markup=get_admin_menu()
    )

@router.callback_query(F.data == "admin_sections")
@admin_only
async def admin_sections(callback: CallbackQuery):
    if callback.message:
        await callback.message.edit_text(
            "📚 <b>Bo'limlar boshqaruvi</b>\n\nNima qilmoqchisiz?",
            reply_markup=get_admin_sections_keyboard()
        )

@router.callback_query(F.data == "create_section")
@admin_only
async def create_section_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📝 <b>Yangi bo'lim yaratish</b>\n\n"
        "Bo'lim nomini kiriting:\n"
        "Format: Nom|Til|Premium(ha/yo'q)\n"
        "Misol: Koreys alfaviti|korean|yo'q"
    )
    await state.set_state(AdminStates.creating_section)

@router.message(AdminStates.creating_section)
@admin_only
async def create_section_process(message: Message, state: FSMContext):
    try:
        text = message.text.strip()
        
        # Bo'sh xabar tekshirish
        if not text:
            await message.answer("❌ Bo'sh xabar! Iltimos qaytadan kiriting.")
            return
        
        # Cancel command tekshirish
        if text.lower() in ['/cancel', 'bekor qilish', 'cancel']:
            await state.clear()
            await message.answer("❌ Bo'lim yaratish bekor qilindi.", reply_markup=get_admin_menu())
            return
        
        # Format tekshirish
        parts = text.split('|')
        if len(parts) < 3:
            await message.answer(
                "❌ Noto'g'ri format!\n\n"
                "To'g'ri format: Nom|Til|Premium\n"
                "Misol: Koreys alfaviti|korean|yo'q\n\n"
                "Til: korean yoki japanese\n"
                "Premium: ha yoki yo'q"
            )
            return
        
        name = parts[0].strip()
        language = parts[1].strip().lower()
        premium_text = parts[2].strip().lower()
        
        # Bo'sh maydon tekshirish
        if not name or not language:
            await message.answer("❌ Nom va til bo'sh bo'lishi mumkin emas!")
            return
        
        # Til tekshirish
        if language not in ['korean', 'japanese']:
            await message.answer("❌ Til faqat 'korean' yoki 'japanese' bo'lishi kerak!")
            return
        
        # Premium tekshirish
        is_premium = premium_text in ['ha', 'yes', 'true', '1']
        
        # Database ga saqlash
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("""
                INSERT INTO sections (name, language, is_premium, created_by)
                VALUES (?, ?, ?, ?)
            """, (name, language, is_premium, ADMIN_ID))
            await db.commit()
            
            # Yaratilgan bo'limni olish
            cursor = await db.execute("SELECT id FROM sections WHERE name = ? AND created_by = ? ORDER BY id DESC LIMIT 1", (name, ADMIN_ID))
            result = await cursor.fetchone()
            section_id = result[0] if result else "N/A"
        
        premium_display = 'Ha' if is_premium else "Yo'q"
        language_display = 'Koreys' if language == 'korean' else 'Yapon'
        
        await message.answer(
            f"✅ <b>Bo'lim muvaffaqiyatli yaratildi!</b>\n\n"
            f"🆔 ID: {section_id}\n"
            f"📚 Nom: <b>{name}</b>\n"
            f"🌐 Til: <b>{language_display}</b>\n"
            f"💎 Premium: <b>{premium_display}</b>",
            reply_markup=get_admin_menu()
        )
        await state.clear()
        
    except Exception as e:
        print(f"Bo'lim yaratishda xatolik: {str(e)}")
        await message.answer(
            f"❌ Xatolik yuz berdi: {str(e)}\n\n"
            "Iltimos qaytadan urinib ko'ring yoki /admin orqali bosh menyuga qayting."
        )
        await state.clear()

@router.callback_query(F.data == "create_subsection")
@admin_only
async def create_subsection_start(callback: CallbackQuery, state: FSMContext):
    # Get all sections
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT id, name, language FROM sections ORDER BY created_at")
        sections = await cursor.fetchall()
    
    if not sections:
        await callback.answer("❌ Avval bo'lim yarating!", show_alert=True)
        return
    
    sections_text = "📚 <b>Mavjud bo'limlar:</b>\n\n"
    for section in sections:
        sections_text += f"ID: {section[0]} - {section[1]} ({section[2]})\n"
    
    sections_text += "\n📝 Pastki bo'lim yaratish uchun bo'lim ID sini kiriting:"
    
    await callback.message.edit_text(sections_text)
    await state.set_state(AdminStates.selecting_section_for_subsection)

@router.message(AdminStates.selecting_section_for_subsection)
@admin_only
async def select_section_for_subsection(message: Message, state: FSMContext):
    try:
        section_id = int(message.text)
        
        # Verify section exists
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("SELECT name FROM sections WHERE id = ?", (section_id,))
            section = await cursor.fetchone()
        
        if not section:
            await message.answer("❌ Bo'lim topilmadi!")
            return
            
        await state.update_data(section_id=section_id)
        await message.answer(
            "📝 Pastki bo'lim ma'lumotlarini kiriting:\n"
            "Format: Nom|Premium(ha/yo'q)\n"
            "Misol: 1-dars|yo'q"
        )
        await state.set_state(AdminStates.creating_subsection)
        
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")

@router.message(AdminStates.creating_subsection)
@admin_only
async def create_subsection_process(message: Message, state: FSMContext):
    try:
        text = message.text.strip()
        
        # Bo'sh xabar tekshirish
        if not text:
            await message.answer("❌ Bo'sh xabar! Iltimos qaytadan kiriting.")
            return
        
        # Cancel command tekshirish
        if text.lower() in ['/cancel', 'bekor qilish', 'cancel']:
            await state.clear()
            await message.answer("❌ Pastki bo'lim yaratish bekor qilindi.", reply_markup=get_admin_menu())
            return
        
        data = await state.get_data()
        section_id = data.get('section_id')
        
        if not section_id:
            await message.answer("❌ Bo'lim ID topilmadi! Qaytadan boshlang.")
            await state.clear()
            return
        
        # Format tekshirish
        parts = text.split('|')
        if len(parts) < 2:
            await message.answer(
                "❌ Noto'g'ri format!\n\n"
                "To'g'ri format: Nom|Premium\n"
                "Misol: 1-dars|yo'q\n\n"
                "Premium: ha yoki yo'q"
            )
            return
        
        name = parts[0].strip()
        premium_text = parts[1].strip().lower()
        
        # Bo'sh nom tekshirish
        if not name:
            await message.answer("❌ Dars nomi bo'sh bo'lishi mumkin emas!")
            return
        
        # Premium tekshirish
        is_premium = premium_text in ['ha', 'yes', 'true', '1']
        
        # Database ga saqlash
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Bo'lim mavjudligini tekshirish
            cursor = await db.execute("SELECT name FROM sections WHERE id = ?", (section_id,))
            section = await cursor.fetchone()
            
            if not section:
                await message.answer("❌ Bo'lim topilmadi!")
                await state.clear()
                return
            
            # Pastki bo'lim yaratish
            await db.execute("""
                INSERT INTO subsections (section_id, name, is_premium)
                VALUES (?, ?, ?)
            """, (section_id, name, is_premium))
            await db.commit()
            
            # Yaratilgan pastki bo'limni olish
            cursor = await db.execute(
                "SELECT id FROM subsections WHERE section_id = ? AND name = ? ORDER BY id DESC LIMIT 1", 
                (section_id, name)
            )
            result = await cursor.fetchone()
            subsection_id = result[0] if result else "N/A"
        
        premium_display = 'Ha' if is_premium else "Yo'q"
        
        await message.answer(
            f"✅ <b>Pastki bo'lim muvaffaqiyatli yaratildi!</b>\n\n"
            f"🆔 ID: {subsection_id}\n"
            f"📚 Bo'lim: <b>{section[0]}</b>\n"
            f"📖 Dars: <b>{name}</b>\n"
            f"💎 Premium: <b>{premium_display}</b>",
            reply_markup=get_admin_menu()
        )
        await state.clear()
        
    except Exception as e:
        print(f"Pastki bo'lim yaratishda xatolik: {str(e)}")
        await message.answer(
            f"❌ Xatolik yuz berdi: {str(e)}\n\n"
            "Iltimos qaytadan urinib ko'ring yoki /admin orqali bosh menyuga qayting."
        )
        await state.clear()

@router.callback_query(F.data == "admin_content")
@admin_only
async def admin_content(callback: CallbackQuery):
    await callback.message.edit_text(
        "📁 <b>Kontent boshqaruvi</b>\n\nNima qilmoqchisiz?",
        reply_markup=get_admin_content_keyboard()
    )

@router.callback_query(F.data == "upload_content")
@admin_only
async def upload_content_start(callback: CallbackQuery, state: FSMContext):
    # Get all subsections with their sections
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT s.id, s.name, sec.name 
            FROM subsections s
            JOIN sections sec ON s.section_id = sec.id
            ORDER BY sec.created_at, s.id
        """)
        subsections = await cursor.fetchall()
    
    if not subsections:
        await callback.answer("❌ Avval bo'lim va pastki bo'lim yarating!", show_alert=True)
        return
    
    subsections_text = "📚 <b>Mavjud pastki bo'limlar:</b>\n\n"
    for subsection in subsections:
        subsections_text += f"ID: {subsection[0]} - {subsection[1]} ({subsection[2]})\n"
    
    subsections_text += "\n📝 Kontent yuklash uchun pastki bo'lim ID sini kiriting:"
    
    await callback.message.edit_text(subsections_text)
    await state.set_state(AdminStates.selecting_subsection_for_content)

@router.message(AdminStates.selecting_subsection_for_content)
@admin_only
async def select_subsection_for_content(message: Message, state: FSMContext):
    try:
        subsection_id = int(message.text)
        
        # Verify subsection exists
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("""
                SELECT s.name, sec.name 
                FROM subsections s
                JOIN sections sec ON s.section_id = sec.id
                WHERE s.id = ?
            """, (subsection_id,))
            subsection = await cursor.fetchone()
        
        if not subsection:
            await message.answer("❌ Pastki bo'lim topilmadi! Qaytadan kiriting.")
            return
        
        await state.update_data(subsection_id=subsection_id)
        await message.answer(
            f"📚 Tanlangan pastki bo'lim: {subsection[0]} ({subsection[1]})\n\n"
            "📝 Kontent sarlavhasini kiriting:"
        )
        await state.set_state(AdminStates.entering_content_title)
        
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")

@router.message(AdminStates.entering_content_title)
@admin_only
async def enter_content_title(message: Message, state: FSMContext):
    title = message.text
    # Limit title length to prevent keyboard issues
    if len(title) > 100:
        title = title[:100]
        await message.answer(
            f"⚠️ Sarlavha juda uzun edi, 100 belgigacha qisqartirildi:\n\n"
            f"📝 Sarlavha: {title}"
        )
    
    await state.update_data(content_title=title)
    await message.answer(
        "📝 Kontent izohini kiriting (ixtiyoriy):\n"
        "Agar izoh kerak bo'lmasa, 'yo'q' deb yozing."
    )
    await state.set_state(AdminStates.entering_content_caption)

@router.message(AdminStates.entering_content_caption)
@admin_only
async def enter_content_caption(message: Message, state: FSMContext):
    caption = None if message.text.lower() in ['yo\'q', 'no', '-'] else message.text
    await state.update_data(content_caption=caption)
    
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    content_type_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📄 Matn", callback_data="content_type_text"),
            InlineKeyboardButton(text="🖼️ Rasm", callback_data="content_type_file")
        ],
        [
            InlineKeyboardButton(text="🎥 Video", callback_data="content_type_file"),
            InlineKeyboardButton(text="🎵 Audio", callback_data="content_type_file")
        ],
        [
            InlineKeyboardButton(text="📁 Hujjat", callback_data="content_type_file")
        ]
    ])
    
    await message.answer(
        "📁 Kontent turini tanlang:",
        reply_markup=content_type_keyboard
    )
    await state.set_state(AdminStates.selecting_content_type)

@router.callback_query(F.data == "content_type_text")
@admin_only
async def select_text_content(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📄 <b>Matn kontent</b>\n\n"
        "Matn kontentni kiriting:"
    )
    await state.set_state(AdminStates.entering_text_content)

@router.callback_query(F.data == "content_type_file")
@admin_only
async def select_file_content(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📁 Endi kontentni yuboring:\n"
        "• Video\n"
        "• Audio\n"
        "• Rasm\n"
        "• Hujjat (PDF)"
    )
    await state.set_state(AdminStates.uploading_content)

@router.message(AdminStates.entering_text_content)
@admin_only
async def enter_text_content(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        subsection_id = data['subsection_id']
        title = data['content_title']
        caption = data.get('content_caption')
        content_text = message.text
        
        # Save text content to database
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("""
                INSERT INTO content (subsection_id, title, file_id, file_type, caption)
                VALUES (?, ?, ?, ?, ?)
            """, (subsection_id, title, content_text, 'text', caption))
            await db.commit()
        
        caption_text = caption or "Yo'q"
        await message.answer(
            f"✅ Matn kontent muvaffaqiyatli yuklandi!\n\n"
            f"📚 Sarlavha: {title}\n"
            f"📄 Tur: Matn\n"
            f"📝 Izoh: {caption_text}",
            reply_markup=get_admin_menu()
        )
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")

@router.message(AdminStates.uploading_content)
@admin_only
async def upload_content_process(message: Message, state: FSMContext):
    if not message.content_type in [ContentType.VIDEO, ContentType.AUDIO, ContentType.PHOTO, ContentType.DOCUMENT]:
        await message.answer("❌ Faqat video, audio, rasm yoki hujjat yuboring!")
        return
    
    try:
        data = await state.get_data()
        subsection_id = data['subsection_id']
        title = data['content_title']
        caption = data.get('content_caption')
        
        # Get file_id based on content type
        file_id = None
        file_type = None
        
        if message.content_type == ContentType.VIDEO and message.video:
            file_id = message.video.file_id
            file_type = 'video'
        elif message.content_type == ContentType.AUDIO and message.audio:
            file_id = message.audio.file_id
            file_type = 'audio'
        elif message.content_type == ContentType.PHOTO and message.photo:
            file_id = message.photo[-1].file_id  # Get highest resolution
            file_type = 'photo'
        elif message.content_type == ContentType.DOCUMENT and message.document:
            file_id = message.document.file_id
            file_type = 'document'
        else:
            await message.answer("❌ Fayl ma'lumotlari topilmadi!")
            return
        
        # Save to database
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("""
                INSERT INTO content (subsection_id, title, file_id, file_type, caption)
                VALUES (?, ?, ?, ?, ?)
            """, (subsection_id, title, file_id, file_type, caption))
            await db.commit()
        
        caption_text = caption or "Yo'q"
        await message.answer(
            f"✅ Kontent muvaffaqiyatli yuklandi!\n\n"
            f"📚 Sarlavha: {title}\n"
            f"📁 Tur: {file_type.capitalize()}\n"
            f"📝 Izoh: {caption_text}",
            reply_markup=get_admin_menu()
        )
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")

@router.callback_query(F.data == "admin_quiz")
@admin_only
async def admin_quiz(callback: CallbackQuery):
    from keyboards import get_admin_quiz_keyboard
    await callback.message.edit_text(
        "🧠 <b>Test boshqaruvi</b>\n\nNima qilmoqchisiz?",
        reply_markup=get_admin_quiz_keyboard()
    )

@router.callback_query(F.data == "create_quiz")
@admin_only
async def create_quiz_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🧠 <b>Yangi test yaratish</b>\n\n"
        "Test sarlavhasini kiriting:"
    )
    await state.set_state(AdminStates.entering_quiz_title)

@router.message(AdminStates.entering_quiz_title)
@admin_only
async def enter_quiz_title(message: Message, state: FSMContext):
    await state.update_data(quiz_title=message.text)
    await message.answer("📝 Test tavsifini kiriting:")
    await state.set_state(AdminStates.entering_quiz_description)

@router.message(AdminStates.entering_quiz_description)
@admin_only
async def enter_quiz_description(message: Message, state: FSMContext):
    await state.update_data(quiz_description=message.text)
    await message.answer(
        "🌐 Test tilini kiriting (korean/japanese):"
    )
    await state.set_state(AdminStates.creating_quiz)

@router.message(AdminStates.creating_quiz)
@admin_only
async def create_quiz_process(message: Message, state: FSMContext):
    language = message.text.lower()
    if language not in ['korean', 'japanese']:
        await message.answer("❌ Faqat 'korean' yoki 'japanese' kiriting!")
        return
    
    try:
        data = await state.get_data()
        title = data['quiz_title']
        description = data['quiz_description']
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("""
                INSERT INTO quizzes (title, description, language, created_by)
                VALUES (?, ?, ?, ?)
            """, (title, description, language, ADMIN_ID))
            quiz_id = cursor.lastrowid
            await db.commit()
        
        await state.update_data(quiz_id=quiz_id)
        await message.answer(
            f"✅ Test yaratildi!\n\n"
            f"📚 Sarlavha: {title}\n"
            f"📝 Tavsif: {description}\n"
            f"🌐 Til: {language.title()}\n\n"
            "Endi savollar qo'shing. Savol matnini kiriting:"
        )
        await state.set_state(AdminStates.entering_question_text)
        
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")

@router.message(AdminStates.entering_question_text)
@admin_only
async def enter_question_text(message: Message, state: FSMContext):
    await state.update_data(question_text=message.text)
    await message.answer(
        "📝 Javob variantlarini kiriting:\n"
        "Format: A|B|C|D|To'g'ri_javob\n"
        "Misol: Annyeonghaseyo|Konnichiwa|Hello|Bonjour|A\n\n"
        "Agar 2 ta variant bo'lsa: A|B||To'g'ri_javob"
    )
    await state.set_state(AdminStates.entering_question_options)

@router.message(AdminStates.entering_question_options)
@admin_only
async def enter_question_options(message: Message, state: FSMContext):
    parts = message.text.split('|')
    if len(parts) < 4:
        await message.answer("❌ Noto'g'ri format! Qaytadan kiriting.")
        return
    
    try:
        data = await state.get_data()
        quiz_id = data['quiz_id']
        question_text = data['question_text']
        
        option_a = parts[0].strip()
        option_b = parts[1].strip()
        option_c = parts[2].strip() if parts[2].strip() else None
        option_d = parts[3].strip() if parts[3].strip() else None
        correct_answer = parts[4].strip().upper()
        
        if correct_answer not in ['A', 'B', 'C', 'D']:
            await message.answer("❌ To'g'ri javob A, B, C yoki D bo'lishi kerak!")
            return
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("""
                INSERT INTO quiz_questions 
                (quiz_id, question, option_a, option_b, option_c, option_d, correct_answer)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (quiz_id, question_text, option_a, option_b, option_c, option_d, correct_answer))
            await db.commit()
        
        from keyboards import get_quiz_continue_keyboard
        await message.answer(
            f"✅ Savol qo'shildi!\n\n"
            f"❓ Savol: {question_text}\n"
            f"A) {option_a}\n"
            f"B) {option_b}\n"
            + (f"C) {option_c}\n" if option_c else "") +
            + (f"D) {option_d}\n" if option_d else "") +
            f"✅ To'g'ri javob: {correct_answer}",
            reply_markup=get_quiz_continue_keyboard()
        )
        
    except Exception as e:
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)}")

@router.callback_query(F.data == "add_more_questions")
@admin_only
async def add_more_questions(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "❓ Keyingi savol matnini kiriting:"
    )
    await state.set_state(AdminStates.entering_question_text)

@router.callback_query(F.data == "finish_quiz")
@admin_only
async def finish_quiz(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "✅ Test muvaffaqiyatli yaratildi va saqlandi!",
        reply_markup=get_admin_menu()
    )
    await state.clear()

@router.callback_query(F.data == "import_quizzes")
@admin_only
async def import_quizzes_start(callback: CallbackQuery, state: FSMContext):
    import_text = """📥 <b>Testlarni import qilish</b>

Siz QuizBot dan testlaringizni import qilishingiz mumkin. Quyidagi formatda yuboring:

<b>Format:</b>
```
QUIZ_TITLE: Test nomi
QUIZ_DESCRIPTION: Test haqida
QUIZ_LANGUAGE: korean/japanese  
QUIZ_PREMIUM: true/false

Q: Savol matni?
A: Variant A
B: Variant B  
C: Variant C
D: Variant D
CORRECT: A

Q: Ikkinchi savol?
A: Variant A
B: Variant B
CORRECT: A
```

Yoki JSON formatda:
```json
{
  "title": "Test nomi",
  "description": "Test haqida", 
  "language": "korean",
  "is_premium": false,
  "questions": [
    {
      "question": "Savol matni?",
      "options": {
        "A": "Variant A",
        "B": "Variant B", 
        "C": "Variant C",
        "D": "Variant D"
      },
      "correct": "A"
    }
  ]
}
```

Testlaringizni yuklang:"""
    
    await callback.message.edit_text(import_text)
    await state.set_state(AdminStates.importing_quiz_data)

@router.message(AdminStates.importing_quiz_data)
@admin_only
async def process_quiz_import(message: Message, state: FSMContext):
    try:
        import json
        import re
        
        text = message.text.strip()
        
        # Try JSON format first
        if text.startswith('{'):
            data = json.loads(text)
            await import_json_quiz(data, message)
        else:
            # Try text format
            await import_text_quiz(text, message)
            
        await state.clear()
        
    except Exception as e:
        await message.answer(f"❌ Import xatoligi: {str(e)}\n\nFormatni tekshiring va qaytadan urinib ko'ring.")

async def import_json_quiz(data, message):
    """Import quiz from JSON format"""
    try:
        title = data['title']
        description = data.get('description', '')
        language = data.get('language', 'korean')
        is_premium = data.get('is_premium', False)
        questions = data['questions']
        
        # Create quiz
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("""
                INSERT INTO quizzes (title, description, language, is_premium, created_by)
                VALUES (?, ?, ?, ?, ?)
            """, (title, description, language, is_premium, ADMIN_ID))
            quiz_id = cursor.lastrowid
            
            # Add questions
            question_count = 0
            for q in questions:
                question_text = q['question']
                options = q['options']
                correct = q['correct']
                
                await db.execute("""
                    INSERT INTO quiz_questions 
                    (quiz_id, question, option_a, option_b, option_c, option_d, correct_answer)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    quiz_id, question_text,
                    options.get('A', ''), options.get('B', ''),
                    options.get('C'), options.get('D'),
                    correct
                ))
                question_count += 1
            
            await db.commit()
        
        premium_status = "Ha" if is_premium else "Yoq"
        await message.answer(
            f"✅ <b>Import muvaffaqiyatli!</b>\n\n"
            f"📚 Test: {title}\n"
            f"🌐 Til: {language}\n"
            f"❓ Savollar: {question_count} ta\n"
            f"💎 Premium: {premium_status}",
            reply_markup=get_admin_menu()
        )
        
    except Exception as e:
        await message.answer(f"❌ JSON import xatoligi: {str(e)}")

async def import_text_quiz(text, message):
    """Import quiz from text format"""
    try:
        lines = text.split('\n')
        
        # Parse header
        title = ""
        description = "" 
        language = "korean"
        is_premium = False
        
        questions = []
        current_question = {}
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if line.startswith('QUIZ_TITLE:'):
                title = line.replace('QUIZ_TITLE:', '').strip()
            elif line.startswith('QUIZ_DESCRIPTION:'):
                description = line.replace('QUIZ_DESCRIPTION:', '').strip()
            elif line.startswith('QUIZ_LANGUAGE:'):
                language = line.replace('QUIZ_LANGUAGE:', '').strip()
            elif line.startswith('QUIZ_PREMIUM:'):
                is_premium = line.replace('QUIZ_PREMIUM:', '').strip().lower() == 'true'
            elif line.startswith('Q:'):
                if current_question:
                    questions.append(current_question)
                current_question = {'question': line.replace('Q:', '').strip(), 'options': {}}
            elif line.startswith(('A:', 'B:', 'C:', 'D:')):
                letter = line[0]
                text_part = line[2:].strip()
                current_question['options'][letter] = text_part
            elif line.startswith('CORRECT:'):
                current_question['correct'] = line.replace('CORRECT:', '').strip()
        
        if current_question:
            questions.append(current_question)
        
        if not title or not questions:
            await message.answer("❌ Test sarlavhasi yoki savollar topilmadi!")
            return
        
        # Save to database
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("""
                INSERT INTO quizzes (title, description, language, is_premium, created_by)
                VALUES (?, ?, ?, ?, ?)
            """, (title, description, language, is_premium, ADMIN_ID))
            quiz_id = cursor.lastrowid
            
            for q in questions:
                await db.execute("""
                    INSERT INTO quiz_questions 
                    (quiz_id, question, option_a, option_b, option_c, option_d, correct_answer)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    quiz_id, q['question'],
                    q['options'].get('A', ''), q['options'].get('B', ''),
                    q['options'].get('C'), q['options'].get('D'),
                    q['correct']
                ))
            
            await db.commit()
        
        premium_status = "Ha" if is_premium else "Yoq"
        await message.answer(
            f"✅ <b>Import muvaffaqiyatli!</b>\n\n"
            f"📚 Test: {title}\n"
            f"🌐 Til: {language}\n"
            f"❓ Savollar: {len(questions)} ta\n"
            f"💎 Premium: {premium_status}",
            reply_markup=get_admin_menu()
        )
        
    except Exception as e:
        await message.answer(f"❌ Text import xatoligi: {str(e)}")

@router.callback_query(F.data == "export_quizzes")
@admin_only
async def export_quizzes(callback: CallbackQuery):
    try:
        import json
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Get all quizzes
            cursor = await db.execute("SELECT * FROM quizzes ORDER BY language, title")
            quizzes = await cursor.fetchall()
            
            if not quizzes:
                await callback.message.edit_text(
                    "❌ Export qilinadigan testlar yo'q.",
                    reply_markup=get_admin_menu()
                )
                return
            
            export_data = []
            
            for quiz in quizzes:
                quiz_id, title, description, language, is_premium, created_by, created_at = quiz
                
                # Get questions
                cursor = await db.execute("""
                    SELECT question, option_a, option_b, option_c, option_d, correct_answer
                    FROM quiz_questions WHERE quiz_id = ?
                """, (quiz_id,))
                questions = await cursor.fetchall()
                
                quiz_data = {
                    "title": title,
                    "description": description,
                    "language": language,
                    "is_premium": bool(is_premium),
                    "questions": []
                }
                
                for q in questions:
                    question, opt_a, opt_b, opt_c, opt_d, correct = q
                    
                    options = {"A": opt_a, "B": opt_b}
                    if opt_c:
                        options["C"] = opt_c
                    if opt_d:
                        options["D"] = opt_d
                    
                    quiz_data["questions"].append({
                        "question": question,
                        "options": options,
                        "correct": correct
                    })
                
                export_data.append(quiz_data)
        
        # Send as file
        export_json = json.dumps(export_data, ensure_ascii=False, indent=2)
        
        await callback.message.edit_text(
            f"📤 <b>Export tayyor!</b>\n\n"
            f"📊 Jami testlar: {len(export_data)} ta\n\n"
            f"JSON format:\n<code>{export_json[:500]}...</code>",
            reply_markup=get_admin_menu()
        )
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Export xatoligi: {str(e)}",
            reply_markup=get_admin_menu()
        )

@router.callback_query(F.data == "admin_stats")
@admin_only
async def admin_stats(callback: CallbackQuery):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Get user statistics
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1")
        premium_users = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COUNT(*) FROM sections")
        total_sections = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COUNT(*) FROM content")
        total_content = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COUNT(*) FROM quizzes")
        total_quizzes = (await cursor.fetchone())[0]
    
    stats_text = f"""
📊 <b>Bot statistikasi</b>

👥 <b>Foydalanuvchilar:</b>
• Jami: {total_users} ta
• Premium: {premium_users} ta
• Oddiy: {total_users - premium_users} ta

📚 <b>Kontent:</b>
• Bo'limlar: {total_sections} ta  
• Kontentlar: {total_content} ta
• Testlar: {total_quizzes} ta

📈 <b>Faollik:</b>
• Bugun faol: {total_users // 4} ta (taxminiy)
• Haftalik faol: {total_users // 2} ta (taxminiy)
    """
    
    await callback.message.edit_text(
        stats_text,
        reply_markup=get_admin_menu()
    )

# Premium management handlers
@router.callback_query(F.data == "admin_premium")
@admin_only
async def admin_premium_menu(callback: CallbackQuery):
    premium_text = """
💎 <b>Premium boshqaruv paneli</b>

Admin sifatida quyidagi amallarni bajarishingiz mumkin:

🎁 <b>Premium berish:</b> Foydalanuvchiga manual premium faollashtirish
👥 <b>Premium foydalanuvchilar:</b> Premium foydalanuvchilar ro'yxati
📊 <b>To'lovlar tarixi:</b> Premium faollashtirishlar tarixi

Nima qilmoqchisiz?
    """
    

    
    buttons = [
        [
            InlineKeyboardButton(text="🎁 Premium berish", callback_data="give_premium"),
        ],
        [
            InlineKeyboardButton(text="👥 Premium foydalanuvchilar", callback_data="premium_users_list"),
        ],
        [
            InlineKeyboardButton(text="🗑️ Content o'chirish", callback_data="content_delete_menu"),
        ],
        [
            InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin_panel")
        ]
    ]
    
    await callback.message.edit_text(
        premium_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data == "give_premium")
@admin_only
async def give_premium_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.waiting_user_id_for_premium)
    
    await callback.message.edit_text(
        """
🎁 <b>Premium berish</b>

Premium berishingiz kerak bo'lgan foydalanuvchining <b>User ID</b> raqamini yuboring.

<b>User ID ni qanday topish mumkin:</b>
1. Foydalanuvchi botga yozganda loglardan ko'rish
2. Foydalanuvchi @userinfobot ga /start yuborsin
3. Foydalanuvchi sizga o'z ID sini yuborsin

<b>Misol:</b> 123456789

Bekor qilish uchun /cancel yuboring.
        """,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_premium")]
        ])
    )

@router.message(AdminStates.waiting_user_id_for_premium)
@admin_only
async def process_user_id_for_premium(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        
        # Check if user exists
        user = await get_user(user_id)
        if not user:
            await message.answer(
                "❌ Bunday ID li foydalanuvchi topilmadi!\n\n"
                "Iltimos, to'g'ri User ID kiriting yoki /cancel yuboring.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_premium")]
                ])
            )
            return
        
        # Save user_id and ask for duration
        await state.update_data(target_user_id=user_id)
        await state.set_state(AdminStates.waiting_premium_duration)
        
        user_name = user[2] or "Noma'lum"  # first_name
        username = f"@{user[1]}" if user[1] else "Username yo'q"
        
        await message.answer(
            f"""
✅ <b>Foydalanuvchi topildi!</b>

👤 <b>Foydalanuvchi:</b> {user_name}
🆔 <b>Username:</b> {username}
🆔 <b>ID:</b> {user_id}

💎 <b>Necha oylik premium berasiz?</b>

Kun sonini kiriting (1-365):
• 30 = 1 oy
• 90 = 3 oy  
• 365 = 1 yil

<b>Misol:</b> 30
            """,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_premium")]
            ])
        )
        
    except ValueError:
        await message.answer(
            "❌ Noto'g'ri format! \n\n"
            "Iltimos, faqat raqam kiriting.\n"
            "Misol: 123456789",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_premium")]
            ])
        )

@router.message(AdminStates.waiting_premium_duration)
@admin_only
async def process_premium_duration(message: Message, state: FSMContext):
    try:
        duration_days = int(message.text.strip())
        
        if duration_days < 1 or duration_days > 365:
            await message.answer(
                "❌ Kun soni 1 dan 365 gacha bo'lishi kerak!\n\n"
                "Iltimos, to'g'ri son kiriting.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_premium")]
                ])
            )
            return
        
        # Get saved user_id
        data = await state.get_data()
        target_user_id = data.get('target_user_id')
        
        if not target_user_id:
            await message.answer("❌ Xatolik! Qaytadan boshlang.")
            await state.clear()
            return
        
        # Activate premium
        await activate_premium(target_user_id, duration_days)
        
        # Get user info for confirmation
        user = await get_user(target_user_id)
        user_name = user[2] if user else "Noma'lum"
        
        # Send success message
        await message.answer(
            f"""
🎉 <b>Premium muvaffaqiyatli faollashtirildi!</b>

👤 <b>Foydalanuvchi:</b> {user_name}
🆔 <b>ID:</b> {target_user_id}
💎 <b>Muddat:</b> {duration_days} kun
📅 <b>Faollashtirildi:</b> Hozir

✅ Foydalanuvchi endi premium imkoniyatlardan foydalanishi mumkin!
            """,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎁 Yana premium berish", callback_data="give_premium")],
                [InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin_panel")]
            ])
        )
        
        # Send notification to user using the message's bot instance
        print(f"DEBUG: Attempting to send notification to user_id: {target_user_id}")
        try:
            result = await message.bot.send_message(
                int(target_user_id),
                f"""🎉 <b>Tabriklaymiz! Premium obuna faollashtirildi!</b>

💎 Sizga <b>{duration_days} kunlik</b> premium obuna berildi!

✨ <b>Endi sizda mavjud:</b>
• Barcha premium kontentlarga kirish
• Maxsus testlar va materiallar  
• Kengaytirilgan statistika
• Reklama yo'q
• Birinchi bo'lib yangi kontentlarni ko'rish

📚 Premium obunangizdan foydalanishni boshlash uchun /premium buyrug'ini yuboring!

🙏 Premium obunangizni bergan admin: @chang_chi_won""",
                parse_mode="HTML"
            )
            
            print(f"DEBUG: Message sent successfully: {result}")
            
            # Notify admin that notification was sent successfully
            await message.answer(
                f"✅ Foydalanuvchiga premium notification yuborildi!\n"
                f"🆔 User ID: {target_user_id}\n"
                f"📱 Message ID: {result.message_id}"
            )
            
        except Exception as e:
            print(f"DEBUG: Failed to send notification: {str(e)}")
            # User might have blocked the bot - notify admin
            await message.answer(
                f"⚠️ Premium faollashtirildi, lekin foydalanuvchiga habar yuborib bo'lmadi.\n"
                f"🆔 Foydalanuvchi ID: {target_user_id}\n"
                f"🔥 Xatolik: {str(e)}\n"
                f"💡 Sabab: Foydalanuvchi botni bloklagan yoki ID noto'g'ri."
            )
        
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ Noto'g'ri format!\n\n"
            "Iltimos, faqat raqam kiriting.\n"
            "Misol: 30",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="admin_premium")]
            ])
        )

# Content deletion handlers
@router.callback_query(F.data == "content_delete_menu")
@admin_only
async def content_delete_menu(callback: CallbackQuery):
    await callback.message.edit_text(
        """
🗑️ <b>Content o'chirish paneli</b>

⚠️ <b>Diqqat!</b> O'chirilgan content qaytarilmaydi!

Nima o'chirmoqchisiz:
        """,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📚 Bo'limlarni o'chirish", callback_data="delete_sections"),
                InlineKeyboardButton(text="📖 Darslarni o'chirish", callback_data="delete_content")
            ],
            [
                InlineKeyboardButton(text="🧠 Testlarni o'chirish", callback_data="delete_quizzes"),
                InlineKeyboardButton(text="📁 Fayllarni o'chirish", callback_data="delete_files")
            ],
            [
                InlineKeyboardButton(text="👥 Foydalanuvchilarni o'chirish", callback_data="delete_users")
            ],
            [
                InlineKeyboardButton(text="🗑️ Hammani tozalash", callback_data="delete_all_confirmation")
            ],
            [
                InlineKeyboardButton(text="🔙 Premium panel", callback_data="admin_premium")
            ]
        ])
    )

@router.callback_query(F.data == "delete_sections")
@admin_only
async def delete_sections_list(callback: CallbackQuery):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT id, name as title, language, is_premium 
            FROM sections 
            ORDER BY language, name
        """)
        sections = await cursor.fetchall()
    
    if not sections:
        await callback.message.edit_text(
            "❌ O'chiriladigan bo'limlar yo'q.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="content_delete_menu")]
            ])
        )
        return
    
    text = "📚 <b>Bo'limlarni o'chirish</b>\n\n⚠️ Bo'limni o'chirganda uning barcha darslari ham o'chadi!\n\n"
    buttons = []
    
    for section_id, title, language, is_premium in sections:
        premium_icon = "💎" if is_premium else "📖"
        lang_icon = "🇰🇷" if language == "korean" else "🇯🇵"
        
        buttons.append([
            InlineKeyboardButton(
                text=f"{premium_icon}{lang_icon} {title}",
                callback_data=f"confirm_delete_section_{section_id}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="content_delete_menu")
    ])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data.startswith("confirm_delete_section_"))
@admin_only
async def confirm_delete_section(callback: CallbackQuery):
    section_id = int(callback.data.split("_")[-1])
    
    # Get section info
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT name as title, language FROM sections WHERE id = ?
        """, (section_id,))
        section = await cursor.fetchone()
        
        # Count subsections and content
        cursor = await db.execute("""
            SELECT COUNT(*) FROM subsections WHERE section_id = ?
        """, (section_id,))
        subsection_count = (await cursor.fetchone())[0]
        
        cursor = await db.execute("""
            SELECT COUNT(*) FROM content WHERE subsection_id IN (
                SELECT id FROM subsections WHERE section_id = ?
            )
        """, (section_id,))
        content_count = (await cursor.fetchone())[0]
    
    if not section:
        await callback.answer("❌ Bo'lim topilmadi!", show_alert=True)
        return
    
    title, language = section
    lang_name = "Koreys tili" if language == "korean" else "Yapon tili"
    
    await callback.message.edit_text(
        f"""
⚠️ <b>Bo'limni o'chirishni tasdiqlang!</b>

📚 <b>Bo'lim:</b> {title}
🌐 <b>Til:</b> {lang_name}
📂 <b>Subsections:</b> {subsection_count} ta
📖 <b>Darslar:</b> {content_count} ta

❌ <b>DIQQAT!</b> Bu amal qaytarilmaydi!
        """,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"execute_delete_section_{section_id}"),
                InlineKeyboardButton(text="❌ Yo'q, bekor qilish", callback_data="delete_sections")
            ]
        ])
    )

@router.callback_query(F.data.startswith("execute_delete_section_"))
@admin_only
async def execute_delete_section(callback: CallbackQuery):
    section_id = int(callback.data.split("_")[-1])
    
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Get section title for confirmation
            cursor = await db.execute("SELECT name as title FROM sections WHERE id = ?", (section_id,))
            section = await cursor.fetchone()
            title = section[0] if section else "Noma'lum"
            
            # Delete content first (from subsections of this section)
            await db.execute("""
                DELETE FROM content WHERE subsection_id IN (
                    SELECT id FROM subsections WHERE section_id = ?
                )
            """, (section_id,))
            
            # Delete subsections
            await db.execute("DELETE FROM subsections WHERE section_id = ?", (section_id,))
            
            # Delete section
            await db.execute("DELETE FROM sections WHERE id = ?", (section_id,))
            
            await db.commit()
        
        await callback.message.edit_text(
            f"✅ <b>Bo'lim muvaffaqiyatli o'chirildi!</b>\n\n📚 O'chirilgan: {title}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🗑️ Yana o'chirish", callback_data="delete_sections")],
                [InlineKeyboardButton(text="🔙 Content panel", callback_data="content_delete_menu")]
            ])
        )
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Xatolik yuz berdi: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="delete_sections")]
            ])
        )

@router.callback_query(F.data == "delete_content")
@admin_only
async def delete_content_list(callback: CallbackQuery):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT c.id, c.title, s.name as section_title, c.is_premium
            FROM content c
            JOIN subsections sub ON c.subsection_id = sub.id
            JOIN sections s ON sub.section_id = s.id
            ORDER BY s.name, c.title
            LIMIT 20
        """)
        contents = await cursor.fetchall()
    
    if not contents:
        await callback.message.edit_text(
            "❌ O'chiriladigan darslar yo'q.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="content_delete_menu")]
            ])
        )
        return
    
    text = "📖 <b>Darslarni o'chirish</b>\n\n"
    buttons = []
    
    for content_id, title, section_title, is_premium in contents:
        premium_icon = "💎" if is_premium else "📖"
        
        buttons.append([
            InlineKeyboardButton(
                text=f"{premium_icon} {title} ({section_title})",
                callback_data=f"confirm_delete_content_{content_id}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="content_delete_menu")
    ])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data.startswith("confirm_delete_content_"))
@admin_only
async def confirm_delete_content(callback: CallbackQuery):
    content_id = int(callback.data.split("_")[-1])
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT c.title, s.name as section_title
            FROM content c
            JOIN subsections sub ON c.subsection_id = sub.id
            JOIN sections s ON sub.section_id = s.id
            WHERE c.id = ?
        """, (content_id,))
        content = await cursor.fetchone()
    
    if not content:
        await callback.answer("❌ Dars topilmadi!", show_alert=True)
        return
    
    content_title, section_title = content
    
    await callback.message.edit_text(
        f"""
⚠️ <b>Darsni o'chirishni tasdiqlang!</b>

📖 <b>Dars:</b> {content_title}
📚 <b>Bo'lim:</b> {section_title}

❌ <b>DIQQAT!</b> Bu amal qaytarilmaydi!
        """,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"execute_delete_content_{content_id}"),
                InlineKeyboardButton(text="❌ Yo'q, bekor qilish", callback_data="delete_content")
            ]
        ])
    )

@router.callback_query(F.data.startswith("execute_delete_content_"))
@admin_only
async def execute_delete_content(callback: CallbackQuery):
    content_id = int(callback.data.split("_")[-1])
    
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Get content title for confirmation
            cursor = await db.execute("SELECT title FROM content WHERE id = ?", (content_id,))
            content = await cursor.fetchone()
            title = content[0] if content else "Noma'lum"
            
            # Delete content
            await db.execute("DELETE FROM content WHERE id = ?", (content_id,))
            await db.commit()
        
        await callback.message.edit_text(
            f"✅ <b>Dars muvaffaqiyatli o'chirildi!</b>\n\n📖 O'chirilgan: {title}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🗑️ Yana o'chirish", callback_data="delete_content")],
                [InlineKeyboardButton(text="🔙 Content panel", callback_data="content_delete_menu")]
            ])
        )
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Xatolik yuz berdi: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="delete_content")]
            ])
        )

@router.callback_query(F.data == "delete_quizzes")
@admin_only
async def delete_quizzes_list(callback: CallbackQuery):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT id, title, language, is_premium
            FROM quizzes
            ORDER BY language, title
        """)
        quizzes = await cursor.fetchall()
    
    if not quizzes:
        await callback.message.edit_text(
            "❌ O'chiriladigan testlar yo'q.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="content_delete_menu")]
            ])
        )
        return
    
    text = "🧠 <b>Testlarni o'chirish</b>\n\n"
    buttons = []
    
    for quiz_id, title, language, is_premium in quizzes:
        premium_icon = "💎" if is_premium else "🧠"
        lang_icon = "🇰🇷" if language == "korean" else "🇯🇵"
        
        buttons.append([
            InlineKeyboardButton(
                text=f"{premium_icon}{lang_icon} {title}",
                callback_data=f"confirm_delete_quiz_{quiz_id}"
            )
        ])
    
    buttons.append([
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="content_delete_menu")
    ])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data.startswith("confirm_delete_quiz_"))
@admin_only
async def confirm_delete_quiz(callback: CallbackQuery):
    quiz_id = int(callback.data.split("_")[-1])
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT title, language FROM quizzes WHERE id = ?
        """, (quiz_id,))
        quiz = await cursor.fetchone()
        
        # Count questions
        cursor = await db.execute("""
            SELECT COUNT(*) FROM quiz_questions WHERE quiz_id = ?
        """, (quiz_id,))
        question_count = (await cursor.fetchone())[0]
    
    if not quiz:
        await callback.answer("❌ Test topilmadi!", show_alert=True)
        return
    
    title, language = quiz
    lang_name = "Koreys tili" if language == "korean" else "Yapon tili"
    
    await callback.message.edit_text(
        f"""
⚠️ <b>Testni o'chirishni tasdiqlang!</b>

🧠 <b>Test:</b> {title}
🌐 <b>Til:</b> {lang_name}
❓ <b>Savollar:</b> {question_count} ta

❌ <b>DIQQAT!</b> Bu amal qaytarilmaydi!
        """,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"execute_delete_quiz_{quiz_id}"),
                InlineKeyboardButton(text="❌ Yo'q, bekor qilish", callback_data="delete_quizzes")
            ]
        ])
    )

@router.callback_query(F.data.startswith("execute_delete_quiz_"))
@admin_only
async def execute_delete_quiz(callback: CallbackQuery):
    quiz_id = int(callback.data.split("_")[-1])
    
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Get quiz title for confirmation
            cursor = await db.execute("SELECT title FROM quizzes WHERE id = ?", (quiz_id,))
            quiz = await cursor.fetchone()
            title = quiz[0] if quiz else "Noma'lum"
            
            # Delete quiz questions first
            await db.execute("DELETE FROM quiz_questions WHERE quiz_id = ?", (quiz_id,))
            
            # Delete quiz
            await db.execute("DELETE FROM quizzes WHERE id = ?", (quiz_id,))
            
            await db.commit()
        
        await callback.message.edit_text(
            f"✅ <b>Test muvaffaqiyatli o'chirildi!</b>\n\n🧠 O'chirilgan: {title}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🗑️ Yana o'chirish", callback_data="delete_quizzes")],
                [InlineKeyboardButton(text="🔙 Content panel", callback_data="content_delete_menu")]
            ])
        )
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Xatolik yuz berdi: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="delete_quizzes")]
            ])
        )

@router.callback_query(F.data == "delete_files")
@admin_only
async def delete_files_menu(callback: CallbackQuery):
    # Count different types of media in content
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Count content with files/media (using caption field instead of content_text)
        cursor = await db.execute("""
            SELECT COUNT(*) FROM content 
            WHERE caption LIKE '%http%' OR caption LIKE '%@%' OR caption LIKE '%.jpg%' 
            OR caption LIKE '%.png%' OR caption LIKE '%.mp4%' OR caption LIKE '%.pdf%'
            OR file_id IS NOT NULL
        """)
        media_content_count = (await cursor.fetchone())[0]
        
        # Get sample of content with potential files
        cursor = await db.execute("""
            SELECT c.id, c.title, s.name as section_title, c.caption
            FROM content c
            JOIN subsections sub ON c.subsection_id = sub.id
            JOIN sections s ON sub.section_id = s.id
            WHERE c.caption LIKE '%http%' OR c.caption LIKE '%@%' 
            OR c.caption LIKE '%.jpg%' OR c.caption LIKE '%.png%' 
            OR c.caption LIKE '%.mp4%' OR c.caption LIKE '%.pdf%'
            OR c.file_id IS NOT NULL
            LIMIT 10
        """)
        media_contents = await cursor.fetchall()
    
    if media_content_count == 0:
        await callback.message.edit_text(
            "❌ Fayl yoki media bo'lgan darslar topilmadi.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="content_delete_menu")]
            ])
        )
        return
    
    text = f"📁 <b>Fayllar va media o'chirish</b>\n\n📊 Jami: {media_content_count} ta darsda fayl/media bor\n\n"
    buttons = []
    
    for content_id, title, section_title, caption in media_contents:
        # Determine media type
        if caption and 'http' in caption:
            media_icon = "🔗"
        elif caption and any(ext in caption.lower() for ext in ['.jpg', '.png', '.gif']):
            media_icon = "🖼️"
        elif caption and any(ext in caption.lower() for ext in ['.mp4', '.avi', '.mov']):
            media_icon = "🎥"
        elif caption and any(ext in caption.lower() for ext in ['.pdf', '.doc']):
            media_icon = "📄"
        else:
            media_icon = "📁"
        
        buttons.append([
            InlineKeyboardButton(
                text=f"{media_icon} {title[:30]}... ({section_title})",
                callback_data=f"confirm_delete_content_{content_id}"
            )
        ])
    
    if media_content_count > 10:
        buttons.append([
            InlineKeyboardButton(text="📄 Ko'proq ko'rsatish", callback_data="show_more_files")
        ])
    
    buttons.extend([
        [InlineKeyboardButton(text="🗑️ Barcha fayllarni o'chirish", callback_data="delete_all_files_confirm")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="content_delete_menu")]
    ])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data == "delete_all_files_confirm")
@admin_only
async def delete_all_files_confirm(callback: CallbackQuery):
    await callback.message.edit_text(
        """
⚠️ <b>BARCHA FAYLLARNI O'CHIRISHNI TASDIQLANG!</b>

Bu amal:
• Barcha darslardan fayl va media linklerini o'chiradi
• Content matnini tozalaydi
• Qaytarib bo'lmaydi!

❌ <b>JIDDIY DIQQAT!</b> Bu amal qaytarilmaydi!
        """,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, barcha fayllarni o'chirish", callback_data="execute_delete_all_files"),
                InlineKeyboardButton(text="❌ Yo'q, bekor qilish", callback_data="delete_files")
            ]
        ])
    )

@router.callback_query(F.data == "execute_delete_all_files")
@admin_only
async def execute_delete_all_files(callback: CallbackQuery):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Update content to remove file references
            await db.execute("""
                UPDATE content 
                SET caption = 'Content o''chirildi (fayl/media bo''lgan)', file_id = NULL
                WHERE caption LIKE '%http%' OR caption LIKE '%@%' 
                OR caption LIKE '%.jpg%' OR caption LIKE '%.png%' 
                OR caption LIKE '%.mp4%' OR caption LIKE '%.pdf%'
                OR file_id IS NOT NULL
            """)
            
            affected_rows = db.total_changes
            await db.commit()
        
        await callback.message.edit_text(
            f"✅ <b>Barcha fayllar muvaffaqiyatli o'chirildi!</b>\n\n📊 O'zgartirilgan darslar: {affected_rows} ta",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Content panel", callback_data="content_delete_menu")]
            ])
        )
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Xatolik yuz berdi: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="delete_files")]
            ])
        )

@router.callback_query(F.data == "delete_users")
@admin_only
async def delete_users_menu(callback: CallbackQuery):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1")
        premium_users = (await cursor.fetchone())[0]
        
        # Get recent users
        cursor = await db.execute("""
            SELECT user_id, first_name, username, created_at, is_premium
            FROM users 
            ORDER BY created_at DESC
            LIMIT 10
        """)
        recent_users = await cursor.fetchall()
    
    text = f"""
👥 <b>Foydalanuvchilarni o'chirish</b>

📊 <b>Statistika:</b>
• Jami foydalanuvchilar: {total_users} ta
• Premium foydalanuvchilar: {premium_users} ta
• Oddiy foydalanuvchilar: {total_users - premium_users} ta

👤 <b>So'nggi foydalanuvchilar:</b>
"""
    
    buttons = []
    for user_id, first_name, username, created_at, is_premium in recent_users:
        name = first_name or "Noma'lum"
        username_text = f"@{username}" if username else "Username yo'q"
        premium_icon = "💎" if is_premium else "👤"
        
        buttons.append([
            InlineKeyboardButton(
                text=f"{premium_icon} {name} ({username_text})",
                callback_data=f"confirm_delete_user_{user_id}"
            )
        ])
    
    buttons.extend([
        [InlineKeyboardButton(text="🗑️ Oddiy foydalanuvchilarni o'chirish", callback_data="delete_regular_users")],
        [InlineKeyboardButton(text="⚠️ Hamma foydalanuvchini o'chirish", callback_data="delete_all_users_confirm")],
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="content_delete_menu")]
    ])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data.startswith("confirm_delete_user_"))
@admin_only
async def confirm_delete_user(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    
    # Don't allow admin to delete themselves
    if user_id == ADMIN_ID:
        await callback.answer("❌ O'zingizni o'chira olmaysiz!", show_alert=True)
        return
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT first_name, username, is_premium FROM users WHERE user_id = ?
        """, (user_id,))
        user = await cursor.fetchone()
    
    if not user:
        await callback.answer("❌ Foydalanuvchi topilmadi!", show_alert=True)
        return
    
    first_name, username, is_premium = user
    name = first_name or "Noma'lum"
    username_text = f"@{username}" if username else "Username yo'q"
    premium_status = "Premium" if is_premium else "Oddiy"
    
    await callback.message.edit_text(
        f"""
⚠️ <b>Foydalanuvchini o'chirishni tasdiqlang!</b>

👤 <b>Ism:</b> {name}
🆔 <b>Username:</b> {username_text}
💎 <b>Status:</b> {premium_status}
🔢 <b>ID:</b> {user_id}

❌ <b>DIQQAT!</b> Bu amal qaytarilmaydi!
        """,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"execute_delete_user_{user_id}"),
                InlineKeyboardButton(text="❌ Yo'q, bekor qilish", callback_data="delete_users")
            ]
        ])
    )

@router.callback_query(F.data.startswith("execute_delete_user_"))
@admin_only
async def execute_delete_user(callback: CallbackQuery):
    user_id = int(callback.data.split("_")[-1])
    
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Get user name for confirmation
            cursor = await db.execute("SELECT first_name FROM users WHERE user_id = ?", (user_id,))
            user = await cursor.fetchone()
            name = user[0] if user and user[0] else "Noma'lum"
            
            # Delete user
            await db.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            await db.commit()
        
        await callback.message.edit_text(
            f"✅ <b>Foydalanuvchi muvaffaqiyatli o'chirildi!</b>\n\n👤 O'chirilgan: {name}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🗑️ Yana o'chirish", callback_data="delete_users")],
                [InlineKeyboardButton(text="🔙 Content panel", callback_data="content_delete_menu")]
            ])
        )
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Xatolik yuz berdi: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="delete_users")]
            ])
        )

@router.callback_query(F.data == "delete_all_confirmation")
@admin_only
async def delete_all_confirmation(callback: CallbackQuery):
    await callback.message.edit_text(
        """
🚨 <b>BUTUN BOTNI TOZALASH!</b>

Bu amal quyidagilarni o'chiradi:
• 📚 Barcha bo'limlar va darslar
• 🧠 Barcha testlar va savollar  
• 👥 Barcha foydalanuvchilar (admindan tashqari)
• 📁 Barcha fayllar va media
• 📊 Barcha statistikalar

❌ <b>JIDDIY OGOHLANTIRISH!</b>
Bu amalni qaytarib bo'lmaydi!
Butun bot ma'lumotlari yo'qoladi!

Davom etishga ishonchingiz komilmi?
        """,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔥 Ha, hammani o'chirish", callback_data="execute_delete_all"),
                InlineKeyboardButton(text="❌ Yo'q, bekor qilish", callback_data="content_delete_menu")
            ]
        ])
    )

@router.callback_query(F.data == "execute_delete_all")
@admin_only
async def execute_delete_all(callback: CallbackQuery):
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Delete everything except admin user
            await db.execute("DELETE FROM content")
            await db.execute("DELETE FROM subsections") 
            await db.execute("DELETE FROM sections")
            await db.execute("DELETE FROM quiz_questions")
            await db.execute("DELETE FROM quizzes")
            await db.execute(f"DELETE FROM users WHERE user_id != {ADMIN_ID}")
            
            await db.commit()
        
        await callback.message.edit_text(
            """
✅ <b>Butun bot muvaffaqiyatli tozalandi!</b>

🗑️ <b>O'chirilganlar:</b>
• Barcha bo'limlar va darslar
• Barcha testlar va savollar
• Barcha foydalanuvchilar (admindan tashqari)
• Barcha fayllar va media

🎯 Bot endi tozalar holatda!
Yangi contentlar qo'shishingiz mumkin.
            """,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin_panel")]
            ])
        )
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Xatolik yuz berdi: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Orqaga", callback_data="content_delete_menu")]
            ])
        )

@router.callback_query(F.data == "premium_users_list") 
@admin_only
async def show_premium_users(callback: CallbackQuery):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT user_id, first_name, username, premium_expires_at, created_at
            FROM users 
            WHERE is_premium = 1 AND premium_expires_at > datetime('now')
            ORDER BY premium_expires_at DESC
            LIMIT 20
        """)
        premium_users = await cursor.fetchall()
    
    if not premium_users:
        text = "👥 <b>Premium foydalanuvchilar</b>\n\n❌ Hozirda faol premium foydalanuvchi yo'q."
    else:
        text = f"👥 <b>Premium foydalanuvchilar</b>\n\n📊 Jami: {len(premium_users)} ta\n\n"
        
        for user_id, name, username, expires_at, created_at in premium_users:
            username_text = f"@{username}" if username else "Username yo'q"
            expires_date = expires_at.split()[0] if expires_at else "Noma'lum"
            
            text += f"👤 <b>{name}</b>\n"
            text += f"🆔 {username_text} (ID: {user_id})\n"
            text += f"⏰ Tugaydi: {expires_date}\n\n"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Premium boshqaruv", callback_data="admin_premium")]
        ])
    )

@router.callback_query(F.data == "admin_payments")
@admin_only  
async def admin_payments_menu(callback: CallbackQuery):
    text = f"""
💳 <b>To'lov ma'lumotlari</b>

<b>Joriy to'lov kartasi:</b>
🏦 Bank: KAPITALBANK
💳 Turi: VISA  
💳 Raqam: <code>4278 3100 2775 4068</code>
👤 Egasi: <b>HOSHIMJON MAMADIYEV</b>

<b>Premium narx:</b> {PREMIUM_PRICE_UZS:,} so'm/oy

<b>To'lov tasdiqlash:</b>
• Foydalanuvchi to'lov chekini yuborsa
• /premium_activate [user_id] buyrug'ini ishlating
• Masalan: /premium_activate 123456789

<b>To'lov bekor qilish:</b>
• /premium_deactivate [user_id] buyrug'i

⚠️ Barcha to'lovlarni diqqat bilan tekshiring!
    """
    
    await callback.message.edit_text(text, reply_markup=get_admin_menu())

@router.message(Command("premium_activate"))
@admin_only
async def activate_premium_command(message: Message):
    try:
        # Extract user_id from command
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Format: /premium_activate [user_id]")
            return
        
        target_user_id = int(parts[1])
        
        # Activate premium for 30 days
        await activate_premium(target_user_id, 30)
        
        # Send confirmation to admin
        await message.answer(f"✅ Foydalanuvchi {target_user_id} uchun premium 30 kunga faollashtirildi!")
        
        # Send notification to user
        try:
            await message.bot.send_message(
                target_user_id,
                "🎉 <b>Premium obuna faollashdi!</b>\n\n"
                "✅ Premium obunangiz 30 kunga faollashtirildi\n"
                "💎 Endi barcha premium kontentlardan foydalanishingiz mumkin!\n\n"
                "To'lov uchun rahmat! 🙏"
            )
        except Exception:
            pass  # User might have blocked the bot
            
    except ValueError:
        await message.answer("❌ Noto'g'ri user_id format!")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")

@router.message(Command("premium_deactivate"))
@admin_only
async def deactivate_premium_command(message: Message):
    try:
        # Extract user_id from command
        parts = message.text.split()
        if len(parts) != 2:
            await message.answer("❌ Format: /premium_deactivate [user_id]")
            return
        
        target_user_id = int(parts[1])
        
        # Deactivate premium
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("""
                UPDATE users 
                SET is_premium = FALSE, premium_expires_at = NULL
                WHERE user_id = ?
            """, (target_user_id,))
            await db.commit()
        
        await message.answer(f"✅ Foydalanuvchi {target_user_id} uchun premium bekor qilindi!")
        
        # Send notification to user
        try:
            await message.bot.send_message(
                target_user_id,
                "❌ <b>Premium obuna bekor qilindi</b>\n\n"
                "Sizning premium obunangiz admin tomonidan bekor qilindi.\n"
                "Savollaringiz bo'lsa admin bilan bog'laning: @chang_chi_won"
            )
        except Exception:
            pass
            
    except ValueError:
        await message.answer("❌ Noto'g'ri user_id format!")
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")


# Scheduler test functions for admin
@router.callback_query(F.data == "admin_test_messages")
@admin_only
async def admin_test_messages(callback: CallbackQuery):
    """Admin panel for testing scheduler messages"""
    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    test_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌟 Motivatsion xabar", callback_data="test_motivational"),
            InlineKeyboardButton(text="💎 Premium taklif", callback_data="test_premium")
        ],
        [
            InlineKeyboardButton(text="📊 Scheduler holati", callback_data="scheduler_status")
        ],
        [
            InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin_panel")
        ]
    ])
    
    await callback.message.edit_text(
        "📨 <b>Test Xabarlar Paneli</b>\\n\\n"
        "Bu bo\\\"limda scheduler funksiyalarini test qilishingiz mumkin.\\n"
        "Xabarlar hozirgi faol foydalanuvchilarga yuboriladi.\\n\\n"
        "🎯 <b>Qaysi xabarni test qilmoqchisiz?</b>",
        reply_markup=test_keyboard
    )

@router.callback_query(F.data == "test_motivational")
@admin_only
async def test_motivational_message(callback: CallbackQuery):
    """Test motivational messages manually"""
    await callback.answer("📤 Motivatsion xabarlar yuborilmoqda...", show_alert=True)
    
    try:
        import aiosqlite
        from config import DATABASE_PATH
        
        # Direct test without scheduler import
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("""
                SELECT user_id, first_name, rating_score, words_learned, quiz_score_total, 
                       total_sessions, last_activity
                FROM users 
                WHERE last_activity > date('now', '-7 days') AND total_sessions >= 1
                ORDER BY rating_score DESC, last_activity DESC
                LIMIT 500
            """)
            active_users = await cursor.fetchall()
        
        print(f"[DIRECT TEST] Found {len(active_users)} active users")
        sent_count = 0
        
        for user_id, first_name, rating, words, quiz_score, sessions, last_activity in active_users:
            try:
                name = first_name or "Do'stim"
                print(f"[DIRECT TEST] Sending to user {user_id} ({name})")
                
                # Real motivational message with premium promotion
                if rating >= 100:  # High achievers
                    message = f"""
🏆 <b>Mukammal natijalar, {name}!</b>

Siz haqiqatan ham ajoyib o'rganyapsiz! 

📊 Sizning yutuqlaringiz:
• Reyting: {rating:.1f} ball (TOP darajada!)
• O'rganilgan so'zlar: {words or 0} ta
• Test natijalari: {quiz_score or 0} ball
• Sessiyalar: {sessions} ta

🌟 Siz professional darajaga yaqin turibsiz!

💎 <b>Premium bilan yanada tezroq rivojlaning:</b>
• Maxsus professional darslar
• AI bilan amaliy suhbat
• Batafsil grammatika tushuntirishlari
• Individual o'quv rejasi

/premium - batafsil ma'lumot olish

Davom eting - muvaffaqiyat sizni kutmoqda! 🚀
                    """
                elif rating >= 50:  # Medium achievers
                    message = f"""
⭐ <b>Ajoyib natijalar, {name}!</b>

Siz yaxshi yo'lda ketyapsiz!

📈 Hozirgi yutuqlaringiz:
• Reyting: {rating:.1f} ball
• So'zlar: {words or 0} ta
• Testlar: {quiz_score or 0} ball
• Sessiyalar: {sessions} ta

🎯 <b>Top darajaga chiqish uchun:</b>

💎 Premium obuna bilan 2x tezroq o'rganing:
• Video darsliklar (Recipe, SOULT seriyalari)
• AI bilan koreys/yapon tilida suhbat
• Grammar AI - har qanday savolga javob
• Reklama yo'q tajriba

💰 Faqat 50,000 so'm/oy
👥 Yoki 10 ta do'st taklif qiling = 1 oy BEPUL!

/premium buyrug'ini yuboring!

Bu hafta yangi cho'qqilarga chiqaylik! 📚
                    """
                else:  # Beginners
                    message = f"""
🚀 <b>Ajoyib boshlanish, {name}!</b>

Til o'rganish sayohatingiz boshlanmoqda!

📊 Hozirgi natijalar:
• Sessiyalar: {sessions} ta
• Reyting: {rating or 0} ball
• So'zlar: {words or 0} ta

💡 <b>Tezroq o'rganish uchun maslahatlar:</b>
• Har kuni 15-20 daqiqa vaqt ajrating
• Testlarni muntazam yechib turing
• Yangi so'zlarni takrorlang
• Video darslarni ko'ring

🌟 Premium bilan yanada samarali o'rganing:
• Professional video darslar
• AI bilan amaliy mashqlar
• Batafsil tushuntirishlar

/premium - batafsil ma'lumot

Kichik qadamlar katta natijalarga olib keladi! 📖
                    """
                
                await callback.message.bot.send_message(user_id, message.strip())
                print(f"[DIRECT TEST] ✅ Message sent to {user_id}")
                sent_count += 1
                
            except Exception as e:
                print(f"[DIRECT TEST] ❌ Failed to send to {user_id}: {e}")
                continue
        
        await callback.message.edit_text(
            f"✅ <b>Test yakunlandi!</b>\n\n"
            f"📊 Topilgan foydalanuvchilar: {len(active_users)} ta\n"
            f"📤 Yuborilgan xabarlar: {sent_count} ta\n\n"
            f"Konsolda batafsil ma'lumotlarni ko'ring!",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔙 Test paneli", callback_data="admin_test_messages")
            ]])
        )
        
    except Exception as e:
        print(f"[DIRECT TEST] Error: {e}")
        await callback.message.edit_text(
            f"❌ <b>Xatolik yuz berdi:</b>\n\n{str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔙 Test paneli", callback_data="admin_test_messages")
            ]])
        )

@router.callback_query(F.data == "test_premium")
@admin_only
async def test_premium_message(callback: CallbackQuery):
    """Test premium promotion messages manually"""
    from utils.scheduler import send_premium_promotion_messages
    
    await callback.answer("💎 Premium takliflar yuborilmoqda...", show_alert=True)
    
    try:
        await send_premium_promotion_messages(callback.message.bot)
        await callback.message.edit_text(
            "✅ <b>Premium takliflar yuborildi!</b>\\n\\n"
            "Premium bo\\\"lmagan faol foydalanuvchilarga personal takliflar yuborildi.\\n"
            "Har bir foydalanuvchining faollik darajasiga mos xabar yuborildi.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔙 Test paneli", callback_data="admin_test_messages")
            ]])
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ <b>Xatolik yuz berdi:</b>\\n\\n{str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔙 Test paneli", callback_data="admin_test_messages")
            ]])
        )

@router.callback_query(F.data == "scheduler_status")
@admin_only
async def scheduler_status(callback: CallbackQuery):
    """Show scheduler status and next execution times"""
    from utils.scheduler import scheduler
    
    try:
        jobs_info = []
        for job in scheduler.get_jobs():
            next_run = job.next_run_time.strftime("%Y-%m-%d %H:%M:%S") if job.next_run_time else "N/A"
            jobs_info.append(f"• <b>{job.name}</b>\\n  Keyingi: {next_run}")
        
        status_text = "📊 <b>Scheduler Holati</b>\\n\\n"
        if jobs_info:
            status_text += "🟢 <b>Faol ishlar:</b>\\n\\n" + "\\n\\n".join(jobs_info)
        else:
            status_text += "🔴 Hech qanday faol ish yo\\\"q"
        
        status_text += f"\\n\\n📈 <b>Umumiy:</b> {len(jobs_info)} ta ish faol"
        
        await callback.message.edit_text(
            status_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔙 Test paneli", callback_data="admin_test_messages")
            ]])
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ <b>Scheduler holatini olishda xatolik:</b>\\n\\n{str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="🔙 Test paneli", callback_data="admin_test_messages")
            ]])
        )

# ================================
# BROADCAST SYSTEM - ADMIN BULK MESSAGING  
# ================================

@router.callback_query(F.data == "admin_broadcast")
@admin_only
async def admin_broadcast_menu(callback: CallbackQuery, state: FSMContext):
    """Broadcast menu - simple and reliable"""
    await state.clear()
    
    if not callback.message:
        return
        
    await callback.message.edit_text(
        "📢 <b>Barchaga xabar yuborish</b>\n\n"
        "🎯 Barcha aktiv foydalanuvchilarga matn xabar yuborish\n\n"
        "⚠️ Xabar yuborishdan oldin tekshirish bo'ladi",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Matn xabar yuborish", callback_data="broadcast_text")],
            [InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin_panel")]
        ])
    )

@router.callback_query(F.data == "broadcast_text")
@admin_only 
async def broadcast_text_start(callback: CallbackQuery, state: FSMContext):
    """Start text broadcast"""
    await state.set_state(AdminStates.broadcast_text)
    
    if not callback.message:
        return
        
    await callback.message.edit_text(
        "📝 <b>Matn xabar yozish</b>\n\n"
        "Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yozing:\n\n"
        "💡 /cancel - bekor qilish",
        reply_markup=None
    )

@router.message(AdminStates.broadcast_text)
@admin_only
async def broadcast_text_received(message: Message, state: FSMContext):
    """Process text message for broadcast"""
    if not message.text:
        return
        
    if message.text == "/cancel":
        await state.clear()
        await message.answer("❌ Bekor qilindi")
        return
    
    # Save message
    await state.update_data(message_text=message.text, message_type="text")
    
    # Show confirmation
    await message.answer(
        f"📋 <b>Tasdiqlash</b>\n\n"
        f"📝 <b>Xabar:</b>\n{message.text}\n\n"
        f"⚠️ Bu xabar barchaga yuboriladi!",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Yuborish", callback_data="confirm_broadcast"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_broadcast")
            ]
        ])
    )

@router.callback_query(F.data == "confirm_broadcast")
@admin_only
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    """Execute broadcast"""
    data = await state.get_data()
    
    if not data or not callback.message:
        await callback.answer("❌ Xatolik!", show_alert=True)
        return
        
    await callback.message.edit_text("🚀 Yuborilmoqda...")
    
    # Send to all users
    sent_count = await send_broadcast_message(data)
    
    await state.clear()
    await callback.message.edit_text(
        f"✅ <b>Xabar yuborildi!</b>\n\n"
        f"📊 {sent_count} ta foydalanuvchiga yuborildi",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin_panel")]
        ])
    )

@router.callback_query(F.data == "cancel_broadcast")
@admin_only
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Cancel broadcast"""
    await state.clear()
    
    if not callback.message:
        return
        
    await callback.message.edit_text(
        "❌ <b>Xabar yuborish bekor qilindi</b>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin_panel")]
        ])
    )

async def send_broadcast_message(data):
    """Send message to all active users"""
    import asyncio
    from aiogram import Bot
    from config import BOT_TOKEN
    
    bot = Bot(token=BOT_TOKEN)
    sent_count = 0
    
    try:
        # Get all users
        async with aiosqlite.connect("language_bot.db") as db:
            cursor = await db.execute("SELECT user_id FROM users")
            users = await cursor.fetchall()
        
        message_text = data.get("message_text", "")
        
        if not message_text:
            return 0
            
        for (user_id,) in users:
            try:
                await bot.send_message(user_id, message_text)
                sent_count += 1
                await asyncio.sleep(0.05)  # Rate limiting
            except Exception:
                continue
        
        return sent_count
        
    except Exception as e:
        print(f"Broadcast error: {e}")
        return sent_count

# Delete sections handlers
@router.callback_query(F.data == "admin_delete_sections")
@admin_only
async def delete_sections_menu(callback: CallbackQuery):
    """Show sections deletion menu"""
    async with aiosqlite.connect("language_bot.db") as db:
        cursor = await db.execute("SELECT id, name, language FROM sections ORDER BY name")
        sections = await cursor.fetchall()
    
    if not sections:
        await callback.answer("❌ Hech qanday bo'lim topilmadi!", show_alert=True)
        return
    
    text = "🗑 <b>Bo'limlarni o'chirish</b>\n\n"
    text += "O'chirmoqchi bo'lgan bo'limni tanlang:\n\n"
    
    keyboard = []
    for section in sections:
        section_id, name, language = section
        keyboard.append([InlineKeyboardButton(
            text=f"🗑 {name} ({language})",
            callback_data=f"delete_section_{section_id}"
        )])
    
    keyboard.append([InlineKeyboardButton(
        text="🔙 Admin panel",
        callback_data="admin_panel"
    )])
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data.startswith("delete_section_"))
@admin_only
async def confirm_section_deletion(callback: CallbackQuery):
    """Confirm section deletion"""
    section_id = int(callback.data.replace("delete_section_", ""))
    
    # Get section info and related data
    async with aiosqlite.connect("language_bot.db") as db:
        cursor = await db.execute("SELECT name, language FROM sections WHERE id = ?", (section_id,))
        section_info = await cursor.fetchone()
        
        if not section_info:
            await callback.answer("❌ Bo'lim topilmadi!", show_alert=True)
            return
        
        section_name, language = section_info
        
        # Count subsections and content
        cursor = await db.execute("SELECT COUNT(*) FROM subsections WHERE section_id = ?", (section_id,))
        subsections_count = (await cursor.fetchone())[0]
        
        cursor = await db.execute("""
            SELECT COUNT(*) FROM content c 
            JOIN subsections s ON c.subsection_id = s.id 
            WHERE s.section_id = ?
        """, (section_id,))
        content_count = (await cursor.fetchone())[0]
    
    text = f"⚠️ <b>Bo'limni o'chirishni tasdiqlang</b>\n\n"
    text += f"📚 Bo'lim: <b>{section_name}</b> ({language})\n"
    text += f"📁 Pastki bo'limlar: {subsections_count} ta\n"
    text += f"📄 Kontent fayllari: {content_count} ta\n\n"
    text += "❗️ <b>Diqqat:</b> Bu amal qaytarib bo'lmaydi!\n"
    text += "Barcha pastki bo'limlar va kontent ham o'chiriladi."
    
    keyboard = [
        [
            InlineKeyboardButton(text="✅ Ha, o'chirish", callback_data=f"confirm_delete_{section_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin_delete_sections")
        ]
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

@router.callback_query(F.data.startswith("confirm_delete_"))
@admin_only
async def execute_section_deletion(callback: CallbackQuery):
    """Execute section deletion"""
    section_id = int(callback.data.replace("confirm_delete_", ""))
    
    try:
        async with aiosqlite.connect("language_bot.db") as db:
            # Get section name for confirmation
            cursor = await db.execute("SELECT name FROM sections WHERE id = ?", (section_id,))
            section_info = await cursor.fetchone()
            
            if not section_info:
                await callback.answer("❌ Bo'lim topilmadi!", show_alert=True)
                return
            
            section_name = section_info[0]
            
            # Delete content related to this section
            await db.execute("""
                DELETE FROM content WHERE subsection_id IN (
                    SELECT id FROM subsections WHERE section_id = ?
                )
            """, (section_id,))
            
            # Delete subsections
            await db.execute("DELETE FROM subsections WHERE section_id = ?", (section_id,))
            
            # Delete section
            await db.execute("DELETE FROM sections WHERE id = ?", (section_id,))
            
            await db.commit()
        
        await callback.message.edit_text(
            f"✅ <b>Bo'lim muvaffaqiyatli o'chirildi!</b>\n\n"
            f"📚 O'chirilgan bo'lim: <b>{section_name}</b>\n"
            f"🗑 Barcha bog'liq ma'lumotlar ham o'chirildi.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🗑 Boshqa bo'limni o'chirish", callback_data="admin_delete_sections")],
                [InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin_panel")]
            ])
        )
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ <b>Xatolik yuz berdi!</b>\n\n"
            f"Xatolik: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin_panel")]
            ])
        )

