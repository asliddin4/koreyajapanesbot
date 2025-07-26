from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite

from database import get_user, create_user, update_user_activity, add_referral
from utils.subscription_check import check_subscriptions
from utils.rating_system import update_user_rating
from keyboards import get_main_menu, get_subscription_keyboard
from messages import WELCOME_MESSAGE, SUBSCRIPTION_REQUIRED_MESSAGE
from config import ADMIN_ID, DATABASE_PATH

router = Router()

class StartStates(StatesGroup):
    waiting_for_subscription = State()

@router.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    # Check if user exists
    user = await get_user(user_id)
    
    # Handle referral code
    referred_by = None
    if message.text and len(message.text.split()) > 1:
        referral_code = message.text.split()[1]
        # Get referrer by referral code
        import aiosqlite
        from config import DATABASE_PATH
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                "SELECT user_id FROM users WHERE referral_code = ?", 
                (referral_code,)
            )
            referrer = await cursor.fetchone()
            if referrer:
                referred_by = referrer[0]
    
    # Create user if doesn't exist
    if not user:
        await create_user(
            user_id=user_id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            referred_by=referred_by
        )
        
        # Add referral record if user was referred
        if referred_by:
            await add_referral(referred_by, user_id)
            # Notify referrer
            try:
                await message.bot.send_message(
                    referred_by,
                    f"🎉 <b>Yangi referral!</b>\n\n"
                    f"👤 {message.from_user.first_name} sizning taklifingiz bilan qo'shildi!\n"
                    f"💎 Premium uchun yana bir qadam oldinga!"
                )
            except Exception:
                pass  # Referrer might have blocked the bot
    
    # Update user activity
    await update_user_activity(user_id)
    await update_user_rating(user_id, 'session_start')
    
    # Check subscriptions (temporarily disabled for testing)
    # subscription_status = await check_subscriptions(user_id, message.bot)
    
    # if not subscription_status['all_subscribed']:
    #     await message.answer(
    #         SUBSCRIPTION_REQUIRED_MESSAGE.format(
    #             missing_channels=subscription_status['missing_channels']
    #         ),
    #         reply_markup=get_subscription_keyboard()
    #     )
    #     await state.set_state(StartStates.waiting_for_subscription)
    #     return
    
    # User is subscribed, show main menu
    await message.answer(
        WELCOME_MESSAGE.format(
            first_name=message.from_user.first_name
        ),
        reply_markup=get_main_menu(user_id == ADMIN_ID)
    )

@router.callback_query(F.data == "check_subscription")
async def check_subscription_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    subscription_status = await check_subscriptions(user_id, callback.bot)
    
    if not subscription_status['all_subscribed']:
        await callback.answer(
            "❌ Siz hali barcha kanallarga obuna bo'lmagansiz!",
            show_alert=True
        )
        return
    
    # User is now subscribed
    await callback.message.edit_text(
        WELCOME_MESSAGE.format(
            first_name=callback.from_user.first_name
        ),
        reply_markup=get_main_menu(user_id == ADMIN_ID)
    )
    await state.clear()

@router.callback_query(F.data == "main_menu")
async def main_menu_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    # Check subscriptions again
    subscription_status = await check_subscriptions(user_id, callback.bot)
    
    if not subscription_status['all_subscribed']:
        await callback.message.edit_text(
            SUBSCRIPTION_REQUIRED_MESSAGE.format(
                missing_channels=subscription_status['missing_channels']
            ),
            reply_markup=get_subscription_keyboard()
        )
        return
    
    await callback.message.edit_text(
        WELCOME_MESSAGE.format(
            first_name=callback.from_user.first_name
        ),
        reply_markup=get_main_menu(user_id == ADMIN_ID)
    )

@router.message(Command("help"))
async def help_command(message: Message):
    help_text = """
🤖 <b>Bot haqida yordam</b>

<b>Asosiy buyruqlar:</b>
/start - Botni ishga tushirish
/help - Yordam
/profile - Profilingizni ko'rish
/leaderboard - Reytingli foydalanuvchilar ro'yxati

<b>Botdan foydalanish:</b>
1️⃣ Barcha kanallarga obuna bo'ling
2️⃣ Tilni tanlang (Koreys/Yapon)
3️⃣ Bo'limlarni o'rganing
4️⃣ Testlarni bajaring
5️⃣ Premium obuna bo'ling yoki do'stlaringizni taklif qiling

<b>Premium imkoniyatlari:</b>
• Barcha premium kontentlarga kirish
• Maxsus testlar va materiallar
• Kengaytirilgan statistika

<b>Premium olish yo'llari:</b>
💰 Oyiga 50,000 som to'lash
👥 10 ta do'stni taklif qilish (1 oy bepul)

Savollaringiz bo'lsa admin bilan bog'laning: @chang_chi_won
    """
    await message.answer(help_text)

@router.message(Command("profile"))
async def profile_command(message: Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    
    if not user:
        await message.answer("❌ Foydalanuvchi topilmadi.")
        return
    
    from database import get_user_referrals_count, is_premium_active
    
    referrals_count = await get_user_referrals_count(user_id)
    is_premium = await is_premium_active(user_id)
    
    profile_text = f"""
👤 <b>Sizning profilingiz</b>

🆔 ID: {user_id}
👤 Ism: {user[2]} {user[3] or ''}
📊 Reyting: {user[14]:.1f}
📚 O'rganilgan so'zlar: {user[10]}
🧠 Test natijalari: {user[11]}/{user[12]} (ball/urinish)
📈 Umumiy sessiyalar: {user[9]}

💎 Premium status: {"✅ Faol" if is_premium else "❌ Faol emas"}
👥 Taklif qilinganlar: {referrals_count}/10

🔗 Sizning referral kodingiz: <code>{user[6]}</code>

<i>Bu kodni do'stlaringiz bilan baham ko'ring!</i>
    """
    
    await message.answer(profile_text)

@router.message(Command("leaderboard"))
async def leaderboard_command(message: Message):
    from database import get_leaderboard
    
    try:
        leaders = await get_leaderboard(10)
        
        if not leaders:
            await message.answer("📊 Hozircha reyting jadvalida hech kim yo'q.")
            return
        
        leaderboard_text = "🏆 <b>Top 10 foydalanuvchilar</b>\n\n"
        
        for i, (first_name, rating, words, quiz_score, quiz_attempts) in enumerate(leaders, 1):
            name = first_name or "Noma'lum"
            
            # Medal emojis for top 3
            if i == 1:
                medal = "🥇"
            elif i == 2:
                medal = "🥈"
            elif i == 3:
                medal = "🥉"
            else:
                medal = f"{i}."
            
            leaderboard_text += f"{medal} <b>{name}</b>\n"
            leaderboard_text += f"   📊 Reyting: {rating:.1f}\n"
            leaderboard_text += f"   📚 So'zlar: {words or 0} | 🧠 Test: {quiz_score or 0}\n\n"
        
        await message.answer(leaderboard_text)
        
    except Exception as e:
        await message.answer("❌ Reyting ma'lumotlarini yuklashda xatolik yuz berdi.")



@router.callback_query(F.data == "show_rating")
async def show_rating_callback(callback: CallbackQuery):
    """Show user's detailed rating and leaderboard"""
    user_id = callback.from_user.id
    
    try:
        from database import get_user, get_leaderboard
        
        # Get user data from database
        user = await get_user(user_id)
        if not user:
            await callback.answer("❌ Foydalanuvchi ma'lumotlari topilmadi!", show_alert=True)
            return
        
        # Extract user data
        rating_score = user[14] if len(user) > 14 else 0.0  # rating_score
        words_learned = user[10] if len(user) > 10 else 0   # words_learned
        quiz_score = user[11] if len(user) > 11 else 0      # quiz_score_total
        quiz_attempts = user[12] if len(user) > 12 else 0   # quiz_attempts
        total_sessions = user[9] if len(user) > 9 else 0    # total_sessions
        
        # Calculate level and ranking
        level = min(100, max(1, int(rating_score / 50) + 1))
        
        # Get ranking by counting users with higher rating
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("""
                SELECT COUNT(*) + 1 as ranking
                FROM users 
                WHERE rating_score > ? AND rating_score > 0
            """, (rating_score,))
            ranking = (await cursor.fetchone())[0]
        
        # Get top 8 users with highest ratings and best performance  
        leaderboard = await get_leaderboard(8)
        
        # Color code based on rating
        if rating_score >= 200:
            level_emoji = "🥇"
            level_color = "OLTIN"
        elif rating_score >= 100:
            level_emoji = "🥈"
            level_color = "KUMUSH"
        elif rating_score >= 50:
            level_emoji = "🥉"
            level_color = "BRONZA"
        else:
            level_emoji = "📊"
            level_color = "BOSHLANG'ICH"
        
        rating_text = f"""📊 <b>SIZNING REYTINGINGIZ</b>
        
{level_emoji} <b>Daraja:</b> {level} ({level_color})
📈 <b>Reyting:</b> {rating_score:.1f} ball
🏆 <b>O'rin:</b> {ranking}-chi
📚 <b>O'rganilgan so'zlar:</b> {words_learned}
🧠 <b>Test natijalari:</b> {quiz_score}/{quiz_attempts}
📱 <b>Umumiy sessiyalar:</b> {total_sessions}

🏆 <b>TOP 8 ENG YAXSHI FOYDALANUVCHILAR</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
        
        # Add leaderboard - show top 8 users
        if leaderboard and len(leaderboard) > 0:
            for i, leader in enumerate(leaderboard[:8], 1):
                user_id_leader, first_name, username, rating, words, quiz_score_leader, quiz_attempts_leader = leader
                name = first_name or "Noma'lum"
                
                if i == 1:
                    medal = "🥇"
                elif i == 2:
                    medal = "🥈" 
                elif i == 3:
                    medal = "🥉"
                else:
                    medal = f"{i}."
                
                # Highlight current user
                if user_id_leader == callback.from_user.id:
                    rating_text += f"\n{medal} <b>👤 {name} (SIZ)</b> - {rating:.1f} ball"
                else:
                    rating_text += f"\n{medal} <b>{name}</b> - {rating:.1f} ball"
            
            # Show total users count
            rating_text += f"\n\n👥 <b>Jami ishtirokchilar:</b> {len(leaderboard)} ta"
        else:
            rating_text += f"\n\n🎯 <b>Birinchi bo'ling!</b>"
            rating_text += f"\n• Testlarni ishlang va ball to'plang"
            rating_text += f"\n• So'zlarni o'rganing va reyting oshiring"
            rating_text += f"\n• Boshqa o'quvchilar qo'shilganida siz birinchi bo'lasiz!"
        
        next_level_points = (level * 50) - rating_score
        if next_level_points > 0:
            rating_text += f"\n\n💡 <b>Keyingi daraja uchun:</b> {next_level_points:.1f} ball kerak"
        else:
            rating_text += f"\n\n🎉 <b>Siz eng yuqori darajadasiz!</b>"
        
        # Add motivational message
        if rating_score == 0:
            rating_text += f"\n\n🚀 <b>Boshlang:</b> Birinchi testni ishlang!"
        elif rating_score < 10:
            rating_text += f"\n\n📚 <b>Davom eting:</b> Ko'proq test ishlang!"
        elif rating_score < 50:
            rating_text += f"\n\n⭐ <b>Ajoyib:</b> Siz yaxshi yo'ldasiz!"
        else:
            rating_text += f"\n\n🏆 <b>Zo'r:</b> Siz professional darajada!"
        
        try:
            await callback.message.edit_text(rating_text, reply_markup=get_main_menu(user_id == ADMIN_ID))
        except Exception as edit_error:
            if "message is not modified" in str(edit_error).lower():
                await callback.answer("📊 Ma'lumotlar allaqachon yangi", show_alert=False)
            else:
                raise edit_error
        
    except Exception as e:
        print(f"Rating callback error: {e}")
        # Fallback to simple rating display
        try:
            user = await get_user(user_id)
            if user:
                rating_score = user[14] if len(user) > 14 else 0.0
                words_learned = user[10] if len(user) > 10 else 0
                simple_text = f"""📊 <b>SIZNING REYTINGINGIZ</b>

📈 <b>Reyting:</b> {rating_score:.1f} ball
📚 <b>O'rganilgan so'zlar:</b> {words_learned}

🔄 <b>Batafsil ma'lumot yuklanmoqda...</b>
Iltimos, qaytadan urinib ko'ring."""
                await callback.message.edit_text(simple_text, reply_markup=get_main_menu(user_id == ADMIN_ID))
            else:
                await callback.answer("❌ Foydalanuvchi ma'lumotlari topilmadi!", show_alert=True)
        except:
            await callback.answer("❌ Reyting ma'lumotlarini yuklashda xatolik!", show_alert=True)

@router.callback_query(F.data == "admin_panel")
async def admin_panel_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    # Check admin access
    if user_id != ADMIN_ID:
        await callback.answer("❌ Bu buyruq faqat admin uchun!", show_alert=True)
        return
    
    from messages import ADMIN_WELCOME_MESSAGE
    from keyboards import get_admin_menu
    
    await callback.message.edit_text(
        ADMIN_WELCOME_MESSAGE,
        reply_markup=get_admin_menu()
    )

@router.callback_query(F.data == "rating")
async def show_rating(callback: CallbackQuery):
    """Reyting va statistika bo'limi"""
    user_id = callback.from_user.id
    
    try:
        # Foydalanuvchi ma'lumotlarini oling
        from utils.rating_system import get_user_rating_details
        from database import get_leaderboard
        
        user_rating = await get_user_rating_details(user_id)
        leaderboard = await get_leaderboard(10)
        
        if not user_rating:
            await callback.message.edit_text(
                "❌ Reyting ma'lumotlari topilmadi.",
                reply_markup=get_main_menu(user_id == ADMIN_ID)
            )
            return
        
        # Foydalanuvchi statistikasi
        rating_text = f"""📊 <b>Sizning reytingingiz</b>

🏆 <b>Reyting ball:</b> {user_rating['rating_score']:.1f}
📈 <b>Daraja:</b> {user_rating['level']} 
🥇 <b>Rang:</b> #{user_rating['ranking']}
📚 <b>O'rganilgan so'zlar:</b> {user_rating['words_learned']}
🎯 <b>Quiz balli:</b> {user_rating['quiz_score_total']}
📝 <b>Quiz urinishlari:</b> {user_rating['quiz_attempts']}
💻 <b>Jami sessiyalar:</b> {user_rating['total_sessions']}

⭐ <b>Top 10 Foydalanuvchilar:</b>
"""
        
        # Leaderboard qo'shing
        for i, (user_name, score, words, quiz_score, quiz_attempts) in enumerate(leaderboard, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            rating_text += f"{medal} {user_name or 'Anonim'}: {score:.1f} ball\n"
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Yangilash", callback_data="rating")],
            [InlineKeyboardButton(text="🏠 Bosh menu", callback_data="main_menu")]
        ])
        
        await callback.message.edit_text(rating_text, reply_markup=keyboard)
        await callback.answer("📊 Reyting yangilandi")
            
    except Exception as e:
        await callback.message.edit_text(
            "❌ Reyting ma'lumotlarini yuklashda xatolik yuz berdi.",
            reply_markup=get_main_menu(callback.from_user.id == ADMIN_ID)
        )

@router.callback_query(F.data == "conversation")
async def show_conversation_menu(callback: CallbackQuery):
    """Premium AI suhbat menu"""
    user_id = callback.from_user.id
    user = await get_user(user_id)
    
    # Premium foydalanuvchi tekshiruvi
    from database import is_premium_active
    is_premium = await is_premium_active(user_id) if user else False
    
    if not is_premium:
        # Premium reklama xabari
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        premium_ad_text = """🤖 <b>AI bilan suhbat - Premium xizmat</b>

🌟 <b>PREMIUM AI BILAN SUHBAT AFZALLIKLARI:</b>

🧠 <b>Haqiqiy AI tajriba:</b>
• Sizni tushunuvchi va javob beruvchi AI
• Kores va yapon tillarida professional suhbat
• 12,000+ so'z va ibora lug'ati
• Cultural awareness va context understanding

💎 <b>Exclusive Premium foydalari:</b>
• Cheksiz AI suhbat sessiyalari
• Har xabar uchun +1.5 reyting ball
• Personal AI language tutor
• 24/7 mavjudlik va tez javob

🚀 <b>Til o'rganishda super tezlik:</b>
• Interactive conversation practice
• Real-time grammar correction
• Vocabulary expansion
• Pronunciation guidance

📈 <b>Progress tracking:</b>
• Sizning til darajangizni kuzatadi
• Individual learning path
• Achievement system
• Weekly progress reports

💰 <b>Premium obuna:</b>
• Oyiga 50,000 som
• Yoki 10 ta referral = 1 oy bepul
• Premium content access
• AI conversation unlimited

🎯 <b>Natija kafolati:</b>
• 30 kun ichida sezilarli o'sish
• Professional conversation skills
• Native speaker confidence level
• Sertifikat olish imkoniyati"""

        premium_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="💎 Premium sotib olish", callback_data="premium")
            ],
            [
                InlineKeyboardButton(text="👥 10 Referral to'plash", callback_data="referral_program")
            ],
            [
                InlineKeyboardButton(text="🔙 Bosh menu", callback_data="main_menu")
            ]
        ])
        
        await callback.message.edit_text(
            premium_ad_text,
            reply_markup=premium_keyboard
        )
    else:
        # Premium foydalanuvchi uchun AI suhbat
        from keyboards import get_conversation_menu
        await callback.message.edit_text(
            "🤖 <b>Premium AI bilan suhbat</b>\n\n✨ Siz Premium a'zosiz! Tilni tanlang:",
            reply_markup=get_conversation_menu()
        )
