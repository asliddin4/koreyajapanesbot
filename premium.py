from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from database import get_user, get_user_referrals_count, activate_premium, is_premium_active
from keyboards import get_premium_menu, get_referral_keyboard, get_main_menu
from messages import PREMIUM_INFO_MESSAGE, REFERRAL_MESSAGE
from config import PREMIUM_PRICE_UZS, REFERRAL_THRESHOLD, ADMIN_ID

router = Router()

class PremiumStates(StatesGroup):
    waiting_payment = State()

@router.callback_query(F.data == "premium")
async def premium_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = await get_user(user_id)
    
    if not user:
        await callback.answer("❌ Foydalanuvchi topilmadi!", show_alert=True)
        return
    
    is_premium = await is_premium_active(user_id)
    referrals_count = await get_user_referrals_count(user_id)
    
    premium_text = PREMIUM_INFO_MESSAGE.format(
        price=PREMIUM_PRICE_UZS,
        referral_threshold=REFERRAL_THRESHOLD,
        current_referrals=referrals_count,
        remaining_referrals=max(0, REFERRAL_THRESHOLD - referrals_count),
        premium_status="✅ Faol" if is_premium else "❌ Faol emas"
    )
    
    await callback.message.edit_text(
        premium_text,
        reply_markup=get_premium_menu(is_premium, referrals_count >= REFERRAL_THRESHOLD)
    )

@router.callback_query(F.data == "buy_premium")
async def buy_premium(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    
    # Check if already premium
    if await is_premium_active(user_id):
        await callback.answer("✅ Sizda allaqachon premium obuna bor!", show_alert=True)
        return
    
    payment_text = f"""
💳 <b>Premium obuna xarid qilish</b>

💰 Narx: {PREMIUM_PRICE_UZS:,} so'm/oy
⏰ Muddati: 30 kun

💳 <b>To'lov ma'lumotlari:</b>
🏦 Bank: KAPITALBANK
💳 Karta turi: VISA
💳 Karta raqami: <code>4278 3100 2775 4068</code>
👤 Egasi: <b>HOSHIMJON MAMADIYEV</b>

<b>To'lov qilish tartibi:</b>
1️⃣ Yuqoridagi karta raqamiga pul o'tkazing
2️⃣ To'lov chekini rasmga oling
3️⃣ Admin bilan bog'laning: @chang_chi_won
4️⃣ To'lov chekini adminga yuboring
5️⃣ Admin tasdiqlashi bilan premium faollashadi

📞 <b>Admin bilan bog'lanish:</b>
• Telegram: @chang_chi_won
• Premium obuna bo'yicha barcha savollar uchun

<b>Premium imkoniyatlari:</b>
• Barcha premium kontentlarga kirish
• Maxsus testlar va materiallar  
• Kengaytirilgan statistika
• Reklama yo'q
• Birinchi bo'lib yangi kontentlarni ko'rish

⚠️ <b>Diqqat:</b> To'lov chekini albatta saqlang va adminga yuboring!
    """
    
    # Admin bilan bog'lanish tugmasi qo'shish
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    
    buttons = [
        [
            InlineKeyboardButton(
                text="📞 Admin bilan bog'lanish", 
                url="https://t.me/chang_chi_won"
            )
        ],
        [
            InlineKeyboardButton(text="👥 Do'stlarni taklif qilish", callback_data="referral_premium")
        ],
        [
            InlineKeyboardButton(text="🔙 Premium", callback_data="premium")
        ]
    ]
    
    await callback.message.edit_text(
        payment_text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
    )

@router.callback_query(F.data == "referral_premium")
async def referral_premium(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = await get_user(user_id)
    
    if not user:
        await callback.answer("❌ Foydalanuvchi topilmadi!", show_alert=True)
        return
    
    referrals_count = await get_user_referrals_count(user_id)
    referral_code = user[6]  # referral_code from database
    
    if referrals_count >= REFERRAL_THRESHOLD:
        # User can activate premium
        await activate_premium(user_id, 30)
        await callback.message.edit_text(
            f"🎉 <b>Tabriklaymiz!</b>\n\n"
            f"Siz {REFERRAL_THRESHOLD} ta do'stni taklif qildingiz va 1 oy bepul premium oldingiz!\n\n"
            f"✅ Premium obuna faollashtirildi!",
            reply_markup=get_main_menu(user_id == ADMIN_ID)
        )
        return
    
    referral_text = REFERRAL_MESSAGE.format(
        referral_code=referral_code,
        current_referrals=referrals_count,
        remaining_referrals=REFERRAL_THRESHOLD - referrals_count,
        bot_username="KoreYap_ProGradBot"
    )
    
    await callback.message.edit_text(
        referral_text,
        reply_markup=get_referral_keyboard()
    )

@router.callback_query(F.data == "my_referral_code")
async def my_referral_code(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = await get_user(user_id)
    
    if not user:
        await callback.answer("❌ Foydalanuvchi topilmadi!", show_alert=True)
        return
    
    referral_code = user[6]  # referral_code from database
    referrals_count = await get_user_referrals_count(user_id)
    
    # Referral link yaratish
    referral_link = f"https://t.me/KoreYap_ProGradBot?start={referral_code}"
    
    referral_text = f"""
🔗 <b>Sizning referral linkingiz</b>

<code>{referral_link}</code>

<b>Qanday ishlatish kerak:</b>
1️⃣ Yuqoridagi linkni copy qiling
2️⃣ Do'stlaringizga yuboring  
3️⃣ Ular shu linkni bosib botga kirishsin

<b>Joriy holat:</b>
✅ Tayyor referrallar: {referrals_count}
⏳ Kerakli referrallar: {max(0, REFERRAL_THRESHOLD - referrals_count)}

<b>Do'stlaringizga yuboring:</b>
"Koreys va Yapon tilini o'rganish uchun bu linkni bosing: {referral_link}

Bu orqali kirsangiz, biz ikkalamiz ham premium olishimiz mumkin! 🎁"

{REFERRAL_THRESHOLD} ta do'st taklif qiling va 1 oy bepul premium oling! 🎉
    """
    
    try:
        await callback.message.edit_text(
            referral_text,
            reply_markup=get_referral_keyboard()
        )
    except Exception:
        # If can't edit, send new message
        await callback.message.answer(
            referral_text,
            reply_markup=get_referral_keyboard()
        )

@router.callback_query(F.data == "my_referrals")
async def my_referrals(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    # Get referral details
    import aiosqlite
    from config import DATABASE_PATH
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT u.first_name, u.username, r.created_at
            FROM referrals r
            JOIN users u ON r.referred_id = u.user_id
            WHERE r.referrer_id = ?
            ORDER BY r.created_at DESC
        """, (user_id,))
        referrals = await cursor.fetchall()
    
    if not referrals:
        referrals_text = "👥 <b>Sizning taklif qilganlaringiz</b>\n\n❌ Hozircha hech kimni taklif qilmagansiz."
    else:
        referrals_list = list(referrals)
        referrals_text = f"👥 <b>Sizning taklif qilganlaringiz</b>\n\n📊 Jami: {len(referrals_list)} ta\n\n"
        
        for i, referral in enumerate(referrals_list[:10], 1):  # Show last 10
            name = referral[0] or referral[1] or "Anonim"
            date = referral[2][:10] if referral[2] else "N/A"  # Get date part only
            referrals_text += f"{i}. {name} - {date}\n"
        
        if len(referrals_list) > 10:
            referrals_text += f"\n... va yana {len(referrals_list) - 10} ta"
        
        remaining = max(0, REFERRAL_THRESHOLD - len(referrals_list))
        if remaining > 0:
            referrals_text += f"\n\n🎯 Premium uchun yana {remaining} ta do'st taklif qiling!"
        else:
            referrals_text += f"\n\n🎉 Premium olish uchun yetarli referral to'pladingiz!"
    
    try:
        await callback.message.edit_text(
            referrals_text,
            reply_markup=get_referral_keyboard()
        )
    except Exception:
        # If can't edit, send new message
        await callback.message.answer(
            referrals_text,
            reply_markup=get_referral_keyboard()
        )

@router.callback_query(F.data == "premium_features")
async def premium_features(callback: CallbackQuery):
    features_text = """
💎 <b>Premium obuna imkoniyatlari</b>

📚 <b>Kontent:</b>
• Barcha premium bo'limlarga kirish
• Maxsus darsliklar va materiallar
• Premium testlar va savol-javoblar
• Audio va video kurslar
• PDF kitoblar va qo'llanmalar

🧠 <b>Testlar:</b>
• Premium testlar
• Batafsil javob tahlillari
• Individual o'rganish rejasi
• Xatolar ustida ishlash

📊 <b>Statistika:</b>
• Batafsil o'rganish hisoboti
• Haftalik va oylik tahlil
• Reyting tizimida ustunlik
• O'sish grafiklari

🎯 <b>Qo'shimcha:</b>
• Reklama yo'q
• Birinchi bo'lib yangi kontentlar
• Shaxsiy maslahatlar
• Admin bilan aloqa

💰 <b>Narx:</b>
• 50,000 so'm/oy
• 10 ta do'st taklif qiling = 1 oy bepul

🎁 <b>Bonus:</b>
Har oyda yangi premium materiallar qo'shiladi!
    """
    
    await callback.message.edit_text(
        features_text,
        reply_markup=get_premium_menu(False, False)
    )

@router.message(PremiumStates.waiting_payment)
async def handle_payment_proof(message: Message, state: FSMContext):
    # Forward payment proof to admin
    try:
        username_text = message.from_user.username or "Yo'q"
        await message.bot.send_message(
            ADMIN_ID,
            f"💳 <b>Yangi to'lov cheki</b>\n\n"
            f"👤 Foydalanuvchi: {message.from_user.first_name}\n"
            f"🆔 ID: {message.from_user.id}\n"
            f"👤 Username: @{username_text}\n\n"
            f"💰 Summa: {PREMIUM_PRICE_UZS:,} so'm"
        )
        
        # Forward the actual message (photo/document)
        await message.forward(ADMIN_ID)
        
        await message.answer(
            "✅ <b>To'lov cheki qabul qilindi!</b>\n\n"
            "📤 Chek admin @chang_chi_won ga yuborildi\n"
            "⏰ Admin tekshirgandan so'ng premium faollashadi\n"
            "🕐 Odatda 1-2 soat ichida amalga oshiriladi\n\n"
            "❓ Savollar bo'lsa admin bilan bog'laning: @chang_chi_won"
        )
        await state.clear()
        
    except Exception as e:
        await message.answer(
            f"❌ Xatolik yuz berdi: {str(e)}\n\n"
            "Iltimos admin bilan bog'laning: @chang_chi_won"
        )

# Admin commands for premium management
@router.message(F.text.startswith("/activate_premium"))
async def activate_premium_command(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❌ Foydalanish: /activate_premium USER_ID [days]")
            return
        
        user_id = int(parts[1])
        days = int(parts[2]) if len(parts) > 2 else 30
        
        await activate_premium(user_id, days)
        
        # Notify user
        try:
            await message.bot.send_message(
                user_id,
                f"🎉 <b>Tabriklaymiz!</b>\n\n"
                f"✅ Premium obuna faollashtirildi!\n"
                f"📅 Muddati: {days} kun\n\n"
                f"Endi barcha premium kontentlardan foydalanishingiz mumkin!"
            )
        except:
            pass
        
        await message.answer(
            f"✅ Premium faollashtirildi!\n"
            f"👤 Foydalanuvchi: {user_id}\n"
            f"📅 Muddat: {days} kun"
        )
        
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")

@router.message(F.text.startswith("/deactivate_premium"))
async def deactivate_premium_command(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        parts = message.text.split()
        if len(parts) < 2:
            await message.answer("❌ Foydalanish: /deactivate_premium USER_ID")
            return
        
        user_id = int(parts[1])
        
        import aiosqlite
        from config import DATABASE_PATH
        
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute("""
                UPDATE users 
                SET is_premium = FALSE, premium_expires_at = NULL
                WHERE user_id = ?
            """, (user_id,))
            await db.commit()
        
        # Notify user
        try:
            await message.bot.send_message(
                user_id,
                "⚠️ <b>Premium obuna bekor qilindi!</b>\n\n"
                "Yangi premium obuna olish uchun /premium buyrug'ini ishlating."
            )
        except:
            pass
        
        await message.answer(
            f"✅ Premium bekor qilindi!\n"
            f"👤 Foydalanuvchi: {user_id}"
        )
        
    except Exception as e:
        await message.answer(f"❌ Xatolik: {str(e)}")

@router.callback_query(F.data == "referral_program")
async def referral_program_handler(callback: CallbackQuery):
    """Referral dasturi haqida ma'lumot"""
    user_id = callback.from_user.id
    user = await get_user(user_id)
    
    if not user:
        await callback.answer("❌ Foydalanuvchi topilmadi!", show_alert=True)
        return
    
    referrals_count = await get_user_referrals_count(user_id)
    referral_code = user[6]  # referral_code column
    
    referral_text = f"""👥 <b>Referral dasturi</b>

🎯 <b>10 do'st = 1 oy Premium bepul!</b>

📊 <b>Sizning natijangiz:</b>
• Taklif qilinganlar: {referrals_count}/10
• Qolgan: {max(0, 10 - referrals_count)} kishi

🔗 <b>Sizning referral kodingiz:</b>
<code>{referral_code}</code>

📝 <b>Qanday ishlatish:</b>
1️⃣ Do'stlaringizga shu kodni ayting
2️⃣ Ular botni ishga tushirganida kodni kiritishadi
3️⃣ Har bir do'st uchun +1 referral
4️⃣ 10 ta referral = 1 oy Premium bepul

💰 <b>Referral bonuslari:</b>
• Har bir referral uchun +5 reyting ball
• 5 referral = Maxsus badge
• 10 referral = 1 oy Premium bepul
• 20 referral = 2 oy Premium bepul

🚀 <b>Tez-tez so'raladigan savollar:</b>
• Referral kodi abadiy faol
• Cheksiz do'st taklif qilishingiz mumkin
• Premium bonuslar avtomatik qo'llaniladi
• Do'stlaringiz ham siz kabi foyda ko'radi

📢 <b>Do'stlaringizga ayting:</b>
"Men ajoyib kores/yapon tili botini topdim! @KoreYap_ProGradBot ishga tushirib, '{referral_code}' kodni kiriting. Ikkalamiz ham bonusga ega bo'lamiz!" """

    from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
    
    referral_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 Kodni nusxalash", callback_data=f"copy_referral_{referral_code}")
        ],
        [
            InlineKeyboardButton(text="💎 Premium", callback_data="premium"),
            InlineKeyboardButton(text="📊 Statistika", callback_data="my_referrals")
        ],
        [
            InlineKeyboardButton(text="🔙 Bosh menu", callback_data="main_menu")
        ]
    ])
    
    await callback.message.edit_text(
        referral_text,
        reply_markup=referral_keyboard
    )
