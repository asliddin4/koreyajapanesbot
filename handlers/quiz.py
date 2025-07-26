from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import aiosqlite
from datetime import datetime

from database import is_premium_active
from keyboards import get_quiz_languages_keyboard, get_quizzes_keyboard, get_quiz_question_keyboard, get_quiz_result_keyboard
from utils.rating_system import update_user_rating
from config import DATABASE_PATH, ADMIN_ID

router = Router()

class QuizStates(StatesGroup):
    taking_quiz = State()
    quiz_finished = State()

@router.callback_query(F.data == "quizzes")
async def choose_quiz_language(callback: CallbackQuery):
    await callback.message.edit_text(
        "🧠 <b>Testlar bo'limi</b>\n\n"
        "🌐 Qaysi tildagi testlarni yechmoqchisiz?",
        reply_markup=get_quiz_languages_keyboard()
    )

@router.callback_query(F.data.in_(["quiz_korean", "quiz_japanese"]))
async def show_quizzes(callback: CallbackQuery):
    language = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    # Get available quizzes
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT id, title, description, is_premium
            FROM quizzes 
            WHERE language = ?
            ORDER BY created_at DESC
        """, (language,))
        quizzes = await cursor.fetchall()
    
    if not quizzes:
        lang_name = "Koreys" if language == "korean" else "Yapon"
        await callback.message.edit_text(
            f"🧠 <b>{lang_name} tili testlari</b>\n\n"
            "❌ Hozircha testlar mavjud emas.\n"
            "Tez orada qo'shiladi! 🔜",
            reply_markup=get_quiz_languages_keyboard()
        )
        return
    
    # Filter out premium quizzes if user doesn't have premium
    is_user_premium = await is_premium_active(user_id)
    available_quizzes = []
    
    for quiz in quizzes:
        if not quiz[3] or is_user_premium:  # not premium or user has premium
            available_quizzes.append(quiz)
    
    lang_name = "Koreys" if language == "korean" else "Yapon"
    quiz_text = f"🧠 <b>{lang_name} tili testlari</b>\n\n"
    
    if not available_quizzes:
        quiz_text += "💎 Barcha testlar premium!\n"
        quiz_text += "Premium obuna oling yoki do'stlaringizni taklif qiling."
    else:
        quiz_text += f"📊 Mavjud testlar: {len(available_quizzes)} ta\n\n"
        quiz_text += "Testni tanlang:"
    
    await callback.message.edit_text(
        quiz_text,
        reply_markup=get_quizzes_keyboard(available_quizzes, language)
    )

@router.callback_query(F.data.startswith("start_quiz_"))
async def start_quiz(callback: CallbackQuery, state: FSMContext):
    quiz_id = int(callback.data.split("_")[2])
    user_id = callback.from_user.id
    
    # Get quiz details and questions
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Get quiz info
        cursor = await db.execute("""
            SELECT title, description, is_premium, language
            FROM quizzes WHERE id = ?
        """, (quiz_id,))
        quiz_info = await cursor.fetchone()
        
        if not quiz_info:
            await callback.answer("❌ Test topilmadi!", show_alert=True)
            return
        
        # Check premium access
        if quiz_info[2] and not await is_premium_active(user_id):
            await callback.answer(
                "💎 Bu premium test! Premium obuna oling yoki do'stlaringizni taklif qiling.",
                show_alert=True
            )
            return
        
        # Get questions
        cursor = await db.execute("""
            SELECT id, question, option_a, option_b, option_c, option_d, correct_answer, points
            FROM quiz_questions 
            WHERE quiz_id = ?
            ORDER BY id
        """, (quiz_id,))
        questions = await cursor.fetchall()
    
    if not questions:
        await callback.answer("❌ Testda savollar mavjud emas!", show_alert=True)
        return
    
    # Initialize quiz session
    await state.update_data(
        quiz_id=quiz_id,
        quiz_title=quiz_info[0],
        quiz_language=quiz_info[3],
        questions=questions,
        current_question=0,
        score=0,
        user_answers=[],
        start_time=datetime.now()
    )
    
    # Update user rating for starting quiz
    await update_user_rating(user_id, 'quiz_start')
    
    # Show first question
    await show_quiz_question(callback, state)

async def show_quiz_question(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    questions = data['questions']
    current_q = data['current_question']
    
    if current_q >= len(questions):
        await finish_quiz(callback, state)
        return
    
    question = questions[current_q]
    question_id, question_text, option_a, option_b, option_c, option_d, correct_answer, points = question
    
    # Prepare question text
    quiz_text = f"🧠 <b>{data['quiz_title']}</b>\n\n"
    quiz_text += f"❓ <b>Savol {current_q + 1}/{len(questions)}</b>\n\n"
    quiz_text += f"{question_text}\n\n"
    
    # Create options list
    options = [
        ("A", option_a),
        ("B", option_b)
    ]
    
    if option_c:
        options.append(("C", option_c))
    if option_d:
        options.append(("D", option_d))
    
    for letter, option in options:
        quiz_text += f"{letter}) {option}\n"
    
    quiz_text += f"\n💯 Ball: {points}"
    
    await callback.message.edit_text(
        quiz_text,
        reply_markup=get_quiz_question_keyboard(options, current_q)
    )
    await state.set_state(QuizStates.taking_quiz)

@router.callback_query(F.data.startswith("quiz_answer_"), QuizStates.taking_quiz)
async def process_quiz_answer(callback: CallbackQuery, state: FSMContext):
    answer = callback.data.split("_")[2]
    question_index = int(callback.data.split("_")[3])
    
    data = await state.get_data()
    questions = data['questions']
    current_question = questions[question_index]
    
    # Check if answer is correct
    correct_answer = current_question[6]
    points = current_question[7]
    is_correct = answer.upper() == correct_answer.upper()
    
    # Update score and answers
    new_score = data['score'] + (points if is_correct else 0)
    user_answers = data['user_answers']
    user_answers.append({
        'question_id': current_question[0],
        'user_answer': answer,
        'correct_answer': correct_answer,
        'is_correct': is_correct,
        'points': points if is_correct else 0
    })
    
    await state.update_data(
        score=new_score,
        user_answers=user_answers,
        current_question=question_index + 1
    )
    
    # Show next question or finish quiz
    await show_quiz_question(callback, state)

async def finish_quiz(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_id = callback.from_user.id
    
    quiz_id = data['quiz_id']
    quiz_title = data['quiz_title']
    score = data['score']
    total_questions = len(data['questions'])
    user_answers = data['user_answers']
    start_time = data['start_time']
    end_time = datetime.now()
    
    # Calculate max possible score
    max_score = sum(q[7] for q in data['questions'])
    
    # Save quiz attempt to database
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO quiz_attempts (user_id, quiz_id, score, total_questions)
            VALUES (?, ?, ?, ?)
        """, (user_id, quiz_id, score, total_questions))
        
        # Update user statistics
        await db.execute("""
            UPDATE users 
            SET quiz_score_total = quiz_score_total + ?, 
                quiz_attempts = quiz_attempts + 1
            WHERE user_id = ?
        """, (score, user_id))
        
        await db.commit()
    
    # Update user rating based on performance
    performance_ratio = score / max_score if max_score > 0 else 0
    if performance_ratio >= 0.8:
        await update_user_rating(user_id, 'quiz_excellent')
    elif performance_ratio >= 0.6:
        await update_user_rating(user_id, 'quiz_good')
    else:
        await update_user_rating(user_id, 'quiz_complete')
    
    # Calculate percentage
    percentage = (score / max_score * 100) if max_score > 0 else 0
    correct_answers = sum(1 for ans in user_answers if ans['is_correct'])
    
    # Determine grade
    if percentage >= 90:
        grade = "🏆 A'lo"
        grade_emoji = "🌟"
    elif percentage >= 80:
        grade = "🥇 Yaxshi"
        grade_emoji = "⭐"
    elif percentage >= 70:
        grade = "🥈 Qoniqarli"
        grade_emoji = "✨"
    elif percentage >= 60:
        grade = "🥉 O'rtacha"
        grade_emoji = "💫"
    else:
        grade = "📚 Takrorlash kerak"
        grade_emoji = "📖"
    
    # Duration calculation
    duration = end_time - start_time
    duration_minutes = int(duration.total_seconds() / 60)
    duration_seconds = int(duration.total_seconds() % 60)
    
    result_text = f"🎯 <b>Test yakunlandi!</b>\n\n"
    result_text += f"📚 Test: {quiz_title}\n"
    result_text += f"📊 Natija: {score}/{max_score} ball ({percentage:.1f}%)\n"
    result_text += f"✅ To'g'ri javoblar: {correct_answers}/{total_questions}\n"
    result_text += f"⏱ Vaqt: {duration_minutes}:{duration_seconds:02d}\n"
    result_text += f"{grade_emoji} Baho: {grade}\n\n"
    
    if percentage >= 80:
        result_text += "🎉 Ajoyib natija! Davom eting!"
    elif percentage >= 60:
        result_text += "👍 Yaxshi natija! Ko'proq mashq qiling."
    else:
        result_text += "📚 Materialni takrorlang va qayta urinib ko'ring."
    
    await callback.message.edit_text(
        result_text,
        reply_markup=get_quiz_result_keyboard(quiz_id, data['quiz_language'])
    )
    
    await state.set_state(QuizStates.quiz_finished)

@router.callback_query(F.data.startswith("quiz_review_"))
async def review_quiz_answers(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    user_answers = data['user_answers']
    quiz_title = data['quiz_title']
    
    if not user_answers:
        await callback.answer("❌ Javoblar topilmadi!", show_alert=True)
        return
    
    review_text = f"📝 <b>{quiz_title} - Javoblarni ko'rish</b>\n\n"
    
    for i, answer_data in enumerate(user_answers, 1):
        is_correct = answer_data['is_correct']
        user_answer = answer_data['user_answer']
        correct_answer = answer_data['correct_answer']
        points = answer_data['points']
        
        status = "✅" if is_correct else "❌"
        review_text += f"{status} <b>Savol {i}:</b>\n"
        review_text += f"   Sizning javobingiz: {user_answer}\n"
        
        if not is_correct:
            review_text += f"   To'g'ri javob: {correct_answer}\n"
        
        review_text += f"   Ball: {points}\n\n"
    
    await callback.message.edit_text(
        review_text,
        reply_markup=get_quiz_result_keyboard(data['quiz_id'], data['quiz_language'])
    )

@router.callback_query(F.data.startswith("retake_quiz_"))
async def retake_quiz(callback: CallbackQuery, state: FSMContext):
    quiz_id = int(callback.data.split("_")[2])
    
    # Clear current state and restart quiz
    await state.clear()
    
    # Simulate clicking start quiz button
    callback.data = f"start_quiz_{quiz_id}"
    await start_quiz(callback, state)

@router.callback_query(F.data.startswith("back_to_quizzes_"))
async def back_to_quizzes(callback: CallbackQuery, state: FSMContext):
    language = callback.data.split("_")[3]
    await state.clear()
    
    # Simulate clicking quiz language button
    callback.data = f"quiz_{language}"
    await show_quizzes(callback)

@router.callback_query(F.data == "quiz_stats")
async def show_quiz_statistics(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Get overall statistics
        cursor = await db.execute("""
            SELECT COUNT(*) as total_attempts, 
                   AVG(score) as avg_score,
                   MAX(score) as max_score
            FROM quiz_attempts 
            WHERE user_id = ?
        """, (user_id,))
        overall_stats = await cursor.fetchone()
        
        # Get statistics by language
        cursor = await db.execute("""
            SELECT q.language, COUNT(*) as attempts, 
                   AVG(qa.score) as avg_score,
                   MAX(qa.score) as max_score
            FROM quiz_attempts qa
            JOIN quizzes q ON qa.quiz_id = q.id
            WHERE qa.user_id = ?
            GROUP BY q.language
        """, (user_id,))
        language_stats = await cursor.fetchall()
        
        # Get recent attempts
        cursor = await db.execute("""
            SELECT q.title, qa.score, qa.total_questions, qa.completed_at
            FROM quiz_attempts qa
            JOIN quizzes q ON qa.quiz_id = q.id
            WHERE qa.user_id = ?
            ORDER BY qa.completed_at DESC
            LIMIT 5
        """, (user_id,))
        recent_attempts = await cursor.fetchall()
    
    stats_text = "📊 <b>Test statistikalaringiz</b>\n\n"
    
    if overall_stats[0] == 0:
        stats_text += "❌ Hozircha test yechmadingiz.\n"
        stats_text += "Birinchi testni yechish uchun 'Testlar' bo'limiga o'ting!"
    else:
        total_attempts = overall_stats[0]
        avg_score = overall_stats[1] or 0
        max_score = overall_stats[2] or 0
        
        stats_text += f"🎯 <b>Umumiy statistika:</b>\n"
        stats_text += f"   📝 Jami urinishlar: {total_attempts}\n"
        stats_text += f"   📊 O'rtacha ball: {avg_score:.1f}\n"
        stats_text += f"   🏆 Eng yuqori ball: {max_score}\n\n"
        
        # Language-specific stats
        if language_stats:
            stats_text += f"🌐 <b>Tillar bo'yicha:</b>\n"
            for language, attempts, avg_score_lang, max_score_lang in language_stats:
                lang_name = "Koreys" if language == "korean" else "Yapon"
                flag = "🇰🇷" if language == "korean" else "🇯🇵"
                stats_text += f"{flag} <b>{lang_name}:</b> {attempts} ta, o'rtacha {avg_score_lang:.1f}\n"
            stats_text += "\n"
        
        # Recent attempts
        if recent_attempts:
            stats_text += f"📚 <b>So'nggi testlar:</b>\n"
            for title, score, total_questions, completed_at in recent_attempts:
                date = completed_at[:10]
                percentage = (score / (total_questions * 1)) * 100  # Assuming 1 point per question
                stats_text += f"• {title}: {score} ball ({percentage:.0f}%) - {date}\n"
    
    from keyboards import get_main_menu
    try:
        await callback.message.edit_text(
            stats_text,
            reply_markup=get_main_menu(user_id == ADMIN_ID)
        )
    except Exception as e:
        # If message is same, just answer the callback
        await callback.answer("📊 Statistika yangilandi")
