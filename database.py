import aiosqlite
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Tuple, Any
from config import DATABASE_PATH

async def init_db():
    """Initialize database with all required tables"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        # Users table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_premium BOOLEAN DEFAULT FALSE,
                premium_expires_at TIMESTAMP,
                referral_code TEXT UNIQUE,
                referred_by INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total_sessions INTEGER DEFAULT 0,
                words_learned INTEGER DEFAULT 0,
                quiz_score_total INTEGER DEFAULT 0,
                quiz_attempts INTEGER DEFAULT 0,
                rating_score REAL DEFAULT 0.0,
                referral_count INTEGER DEFAULT 0
            )
        """)
        
        # Sections table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                language TEXT,
                is_premium BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER
            )
        """)
        
        # Subsections table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subsections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_id INTEGER,
                name TEXT NOT NULL,
                description TEXT,
                is_premium BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (section_id) REFERENCES sections (id)
            )
        """)
        
        # Content table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subsection_id INTEGER,
                title TEXT NOT NULL,
                content_text TEXT,
                file_id TEXT,
                file_type TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (subsection_id) REFERENCES subsections (id)
            )
        """)
        
        # Referrals table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS referrals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER,
                referred_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (referrer_id) REFERENCES users (user_id),
                FOREIGN KEY (referred_id) REFERENCES users (user_id)
            )
        """)
        
        # Quizzes table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS quizzes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                language TEXT,
                is_premium BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER
            )
        """)
        
        # Quiz questions table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS quiz_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quiz_id INTEGER,
                question TEXT NOT NULL,
                option_a TEXT NOT NULL,
                option_b TEXT NOT NULL,
                option_c TEXT,
                option_d TEXT,
                correct_answer TEXT NOT NULL,
                points INTEGER DEFAULT 1,
                FOREIGN KEY (quiz_id) REFERENCES quizzes (id)
            )
        """)
        
        # Quiz attempts table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS quiz_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                quiz_id INTEGER,
                score INTEGER,
                total_questions INTEGER,
                completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (quiz_id) REFERENCES quizzes (id)
            )
        """)
        
        # User progress table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                content_id INTEGER,
                completed BOOLEAN DEFAULT FALSE,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id),
                FOREIGN KEY (content_id) REFERENCES content (id)
            )
        """)
        
        # Premium content table for Topik1, Topik2, JLPT
        await db.execute("""
            CREATE TABLE IF NOT EXISTS premium_content (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_type TEXT NOT NULL CHECK(section_type IN ('topik1', 'topik2', 'jlpt')),
                title TEXT NOT NULL,
                description TEXT,
                file_id TEXT,
                file_type TEXT CHECK(file_type IN ('photo', 'video', 'audio', 'document', 'music', 'text')),
                content_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                order_index INTEGER DEFAULT 0
            )
        """)
        
        await db.commit()

async def get_user(user_id: int) -> Optional[Tuple[Any, ...]]:
    """Get user by ID"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        )
        return await cursor.fetchone()

async def update_user_activity(user_id: int, activity_type: Optional[str] = None) -> None:
    """Update user's last activity and session count"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE users 
            SET last_activity = CURRENT_TIMESTAMP,
                total_sessions = total_sessions + 1
            WHERE user_id = ?
        """, (user_id,))
        await db.commit()

async def create_user(user_id: int, username: Optional[str], first_name: str, last_name: Optional[str] = None, referred_by: Optional[int] = None) -> None:
    """Create new user"""
    import secrets
    referral_code = f"REF{secrets.randbelow(999999):06d}"
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO users 
            (user_id, username, first_name, last_name, referral_code, referred_by)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, username or "", first_name, last_name or "", referral_code, referred_by))
        await db.commit()

async def get_user_referrals_count(user_id: int) -> int:
    """Get count of successful referrals for user"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user_id,)
        )
        result = await cursor.fetchone()
        return result[0] if result else 0

async def add_referral(referrer_id: int, referred_id: int) -> None:
    """Add a referral record"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO referrals (referrer_id, referred_id)
            VALUES (?, ?)
        """, (referrer_id, referred_id))
        await db.commit()

async def activate_premium(user_id: int, duration_days: int = 30) -> None:
    """Activate premium for user"""
    expires_at = datetime.now() + timedelta(days=duration_days)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            UPDATE users 
            SET is_premium = TRUE, premium_expires_at = ?
            WHERE user_id = ?
        """, (expires_at, user_id))
        await db.commit()

async def is_premium_active(user_id: int) -> bool:
    """Check if user's premium is active"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT is_premium, premium_expires_at FROM users WHERE user_id = ?
        """, (user_id,))
        result = await cursor.fetchone()
        
        if not result or not result[0]:
            return False
            
        expires_at = datetime.fromisoformat(result[1])
        return datetime.now() < expires_at

async def get_sections(language: Optional[str] = None, is_premium: Optional[bool] = None) -> List[Tuple[Any, ...]]:
    """Get sections, optionally filtered by language and premium status"""
    query = "SELECT * FROM sections WHERE 1=1"
    params = []
    
    if language:
        query += " AND language = ?"
        params.append(language)
    
    if is_premium is not None:
        query += " AND is_premium = ?"
        params.append(is_premium)
    
    query += " ORDER BY created_at"
    
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(query, params)
        return await cursor.fetchall()

async def get_leaderboard(limit: int = 8) -> List[Tuple[Any, ...]]:
    """Get top users by comprehensive performance metrics"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT user_id, first_name, username, rating_score, words_learned, quiz_score_total, quiz_attempts
            FROM users 
            WHERE rating_score IS NOT NULL AND rating_score > 0
            ORDER BY 
                rating_score DESC,
                words_learned DESC, 
                quiz_score_total DESC,
                total_sessions DESC
            LIMIT ?
        """, (limit,))
        return await cursor.fetchall()

# Premium content functions
async def add_premium_content(section_type: str, title: str, description: Optional[str] = None, file_id: Optional[str] = None, file_type: Optional[str] = None, content_text: Optional[str] = None) -> bool:
    """Add premium content to database"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO premium_content (section_type, title, description, file_id, file_type, content_text, order_index)
            VALUES (?, ?, ?, ?, ?, ?, (SELECT COALESCE(MAX(order_index), 0) + 1 FROM premium_content WHERE section_type = ?))
        """, (section_type, title, description, file_id, file_type, content_text, section_type))
        await db.commit()
        return True

async def get_premium_content(section_type: str) -> List[Tuple[Any, ...]]:
    """Get all premium content for a section"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute("""
            SELECT id, title, description, file_id, file_type, content_text, order_index
            FROM premium_content 
            WHERE section_type = ?
            ORDER BY order_index ASC
        """, (section_type,))
        return await cursor.fetchall()

async def delete_premium_content(content_id: int) -> bool:
    """Delete premium content"""
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("DELETE FROM premium_content WHERE id = ?", (content_id,))
        await db.commit()
        return True