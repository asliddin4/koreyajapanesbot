import asyncio
import aiosqlite
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import BOT_TOKEN, ADMIN_ID, DATABASE_PATH, PREMIUM_PRICE_UZS
from database import get_user, update_user_activity
from keyboards import get_admin_menu

router = Router()

class AdminStates(StatesGroup):
    creating_section = State()
    creating_quiz = State()
    broadcast_text = State()

def admin_only(func):
    """Decorator to restrict access to admin only"""
    async def wrapper(update, *args, **kwargs):
        user_id = None
        if isinstance(update, Message):
            user_id = update.from_user.id if update.from_user else None
        elif isinstance(update, CallbackQuery):
            user_id = update.from_user.id if update.from_user else None
        
        if user_id != ADMIN_ID:
            if isinstance(update, Message):
                await update.answer("❌ Sizda admin huquqlari yo'q!")
            elif isinstance(update, CallbackQuery):
                await update.answer("❌ Sizda admin huquqlari yo'q!", show_alert=True)
            return
        
        return await func(update, *args, **kwargs)
    return wrapper

@router.callback_query(F.data == "admin_panel")
@admin_only
async def admin_panel(callback: CallbackQuery, state: FSMContext):
    """Show admin panel"""
    await state.clear()
    
    if not callback.message:
        return
        
    await callback.message.edit_text(
        "🔧 <b>Admin Panel</b>\n\n"
        "🎯 Botni boshqarish uchun quyidagi tugmalardan foydalaning:",
        reply_markup=get_admin_menu()
    )

@router.callback_query(F.data == "admin_stats") 
@admin_only
async def admin_stats(callback: CallbackQuery):
    """Show bot statistics"""
    if not callback.message:
        return
        
    try:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            # Total users
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            result = await cursor.fetchone()
            total_users = result[0] if result else 0
            
            # Premium users
            cursor = await db.execute("SELECT COUNT(*) FROM users WHERE is_premium = 1")
            result = await cursor.fetchone()
            premium_users = result[0] if result else 0
            
            # Active today
            cursor = await db.execute("""
                SELECT COUNT(*) FROM users 
                WHERE last_activity > datetime('now', '-1 day')
            """)
            result = await cursor.fetchone()
            active_today = result[0] if result else 0
            
            # Total sections
            cursor = await db.execute("SELECT COUNT(*) FROM sections")
            result = await cursor.fetchone()
            total_sections = result[0] if result else 0
            
            # Total quizzes
            cursor = await db.execute("SELECT COUNT(*) FROM quizzes")
            result = await cursor.fetchone()
            total_quizzes = result[0] if result else 0

        stats_text = f"""📊 <b>Bot Statistikasi</b>

👥 <b>Foydalanuvchilar:</b>
• Jami: {total_users}
• Premium: {premium_users}
• Bugun faol: {active_today}

📚 <b>Kontent:</b>
• Bo'limlar: {total_sections}
• Testlar: {total_quizzes}

💰 <b>Premium narxi:</b> {PREMIUM_PRICE_UZS:,} so'm"""

        await callback.message.edit_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin_panel")]
            ])
        )
    except Exception as e:
        await callback.message.edit_text(
            f"❌ Xatolik: {str(e)}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin_panel")]
            ])
        )

# ================================ 
# BROADCAST SYSTEM
# ================================

@router.callback_query(F.data == "admin_broadcast")
@admin_only
async def admin_broadcast_menu(callback: CallbackQuery, state: FSMContext):
    """Broadcast menu"""
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
    if not message or not message.text:
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
    bot = Bot(token=BOT_TOKEN)
    sent_count = 0
    
    try:
        # Get all users
        async with aiosqlite.connect(DATABASE_PATH) as db:
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
        
        await bot.session.close()
        return sent_count
        
    except Exception as e:
        print(f"Broadcast error: {e}")
        try:
            await bot.session.close()
        except:
            pass
        return sent_count

# ================================
# SECTION MANAGEMENT  
# ================================

@router.callback_query(F.data == "admin_create_section")
@admin_only
async def create_section_start(callback: CallbackQuery, state: FSMContext):
    """Start section creation"""
    await state.set_state(AdminStates.creating_section)
    
    if not callback.message:
        return
        
    await callback.message.edit_text(
        "📚 <b>Yangi bo'lim yaratish</b>\n\n"
        "📝 Bo'lim ma'lumotlarini kiriting:\n"
        "Format: Nom|Til|Premium(ha/yo'q)\n\n"
        "Misol: Boshlang'ich darslar|Korean|yo'q",
        reply_markup=None
    )

@router.message(AdminStates.creating_section)
@admin_only
async def create_section_process(message: Message, state: FSMContext):
    """Process section creation"""
    if not message or not message.text:
        await message.answer("❌ Matn kiriting!")
        return
        
    text = message.text.strip()
    
    if text == "/cancel":
        await state.clear()
        await message.answer("❌ Bekor qilindi")
        return
    
    try:
        parts = text.split('|')
        if len(parts) != 3:
            await message.answer("❌ Noto'g'ri format! Format: Nom|Til|Premium(ha/yo'q)")
            return
        
        name = parts[0].strip()
        language = parts[1].strip()
        is_premium = parts[2].strip().lower() in ['ha', 'yes', 'true', '1']
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("""
                INSERT INTO sections (name, language, is_premium, created_by)
                VALUES (?, ?, ?, ?)
            """, (name, language, is_premium, ADMIN_ID))
            await db.commit()
        
        await state.clear()
        premium_text = "Ha" if is_premium else "Yoq"
        await message.answer(
            f"✅ <b>Bo'lim yaratildi!</b>\n\n"
            f"📚 Nom: {name}\n"
            f"🌐 Til: {language}\n"
            f"💎 Premium: {premium_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin_panel")]
            ])
        )
        
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")

# ================================
# QUIZ MANAGEMENT
# ================================

@router.callback_query(F.data == "admin_create_quiz")
@admin_only
async def create_quiz_start(callback: CallbackQuery, state: FSMContext):
    """Start quiz creation"""
    await state.set_state(AdminStates.creating_quiz)
    
    if not callback.message:
        return
        
    await callback.message.edit_text(
        "🧩 <b>Yangi test yaratish</b>\n\n"
        "📝 Test ma'lumotlarini kiriting:\n"
        "Format: Sarlavha|Tavsif|Til|Premium(ha/yo'q)\n\n"
        "Misol: Korean 1-daraja|Boshlang'ich test|Korean|yo'q",
        reply_markup=None
    )

@router.message(AdminStates.creating_quiz)
@admin_only
async def create_quiz_process(message: Message, state: FSMContext):
    """Process quiz creation"""
    if not message or not message.text:
        await message.answer("❌ Matn kiriting!")
        return
        
    text = message.text.strip()
    
    if text == "/cancel":
        await state.clear()
        await message.answer("❌ Bekor qilindi")
        return
    
    try:
        parts = text.split('|')
        if len(parts) != 4:
            await message.answer("❌ Noto'g'ri format! Format: Sarlavha|Tavsif|Til|Premium(ha/yo'q)")
            return
        
        title = parts[0].strip()
        description = parts[1].strip()
        language = parts[2].strip()
        is_premium = parts[3].strip().lower() in ['ha', 'yes', 'true', '1']
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("""
                INSERT INTO quizzes (title, description, language, is_premium, created_by)
                VALUES (?, ?, ?, ?, ?)
            """, (title, description, language, is_premium, ADMIN_ID))
            await db.commit()
        
        await state.clear()
        premium_text = "Ha" if is_premium else "Yoq"
        await message.answer(
            f"✅ <b>Test yaratildi!</b>\n\n"
            f"📝 Sarlavha: {title}\n"
            f"📄 Tavsif: {description}\n"
            f"🌐 Til: {language}\n"
            f"💎 Premium: {premium_text}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Admin panel", callback_data="admin_panel")]
            ])
        )
        
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")