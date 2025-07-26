import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from handlers import start, admin, premium, content, quiz, conversation, custom_sections, custom_content, premium_content
from utils.scheduler import start_scheduler

# Bot versiya: 2.0.1 - AI Conversation Update (2025-01-24)
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global bot instance for other modules to use
bot = None

async def main():
    global bot
    
    # Initialize database
    await init_db()
    
    # Initialize bot and dispatcher
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher(storage=MemoryStorage())
    
    # Include routers
    dp.include_router(start.router)
    dp.include_router(admin.router)
    dp.include_router(premium.router)
    dp.include_router(content.router)
    dp.include_router(quiz.router)
    dp.include_router(conversation.router)
    dp.include_router(custom_sections.router)
    dp.include_router(custom_content.router)
    dp.include_router(premium_content.router)
    
    # Start scheduler for automated messages
    await start_scheduler(bot)
    
    # Start polling
    logger.info("Bot started")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
