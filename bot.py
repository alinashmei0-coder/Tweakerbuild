import os
import logging
import asyncio
import json
import base64
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import httpx
from github import Github

# تحميل المتغيرات البيئية
load_dotenv()

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# المتغيرات البيئية
TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_REPO = os.getenv('GITHUB_REPO', 'username/repo-name')

# التحقق من وجود المتغيرات
if not all([TELEGRAM_TOKEN, DEEPSEEK_API_KEY, GITHUB_TOKEN]):
    raise ValueError("Missing required environment variables")

# ============================================
# دوال DeepSeek API
# ============================================
async def ask_deepseek(prompt: str) -> str:
    """إرسال طلب إلى DeepSeek API والحصول على الرد"""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                'https://api.deepseek.com/v1/chat/completions',
                headers={
                    'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
                    'Content-Type': 'application/json'
                },
                json={
                    'model': 'deepseek-chat',
                    'messages': [
                        {'role': 'system', 'content': 'أنت خبير في تطوير توييكات iOS باستخدام Theos و Logos. قم بكتابة كود Tweak كامل (ملف .xm) جاهز للبناء. أرسل الكود فقط بدون أي شرح أو مقدمات.'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'max_tokens': 4000,
                    'temperature': 0.3
                }
            )
            response.raise_for_status()
            data = response.json()
            return data['choices'][0]['message']['content']
    except Exception as e:
        logger.error(f"DeepSeek API error: {e}")
        return None

# ============================================
# دوال GitHub Actions
# ============================================
def trigger_github_workflow(code: str, filename: str) -> str:
    """تشغيل GitHub Actions لبناء التوييك"""
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(GITHUB_REPO)
        
        # إنشاء ملف الكود في المستودع
        file_path = f'tweak/{filename}'
        commit_message = f'Add {filename} - {datetime.now().isoformat()}'
        
        try:
            # محاولة تحديث الملف إذا كان موجوداً
            contents = repo.get_contents(file_path)
            repo.update_file(
                contents.path,
                commit_message,
                code,
                contents.sha,
                branch='main'
            )
        except:
            # إنشاء ملف جديد
            repo.create_file(
                file_path,
                commit_message,
                code,
                branch='main'
            )
        
        # تشغيل GitHub Actions عبر API
        # ملاحظة: هذا يتطلب وجود workflow_dispatch في ملف workflow
        workflow = repo.get_workflow('build.yml')
        workflow.create_dispatch(ref='main')
        
        return "✅ تم تشغيل البناء بنجاح! سيتم إرسال الملف عند الانتهاء."
        
    except Exception as e:
        logger.error(f"GitHub Actions error: {e}")
        return f"❌ فشل تشغيل البناء: {str(e)}"

# ============================================
# أوامر البوت
# ============================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """رسالة الترحيب"""
    await update.message.reply_text(
        "🤖 مرحباً! أنا بوت بناء توييكات iOS.\n\n"
        "📌 أرسل لي وصفاً للميزة التي تريدها، وسأقوم بـ:\n"
        "1️⃣ كتابة الكود باستخدام DeepSeek AI\n"
        "2️⃣ بناء التوييك عبر GitHub Actions\n"
        "3️⃣ إرسال الملف النهائي إليك\n\n"
        "💡 مثال: 'ابني لي توييك يحجب الإعلانات في يوتيوب'"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالجة رسائل المستخدم"""
    user_message = update.message.text
    user_id = update.message.from_user.id
    
    # إرسال رد فوري
    await update.message.reply_text("⏳ جارٍ توليد الكود وتحضير الأداة... قد يستغرق ذلك دقيقة.")
    
    # طلب الكود من DeepSeek
    prompt = f"""
    قم بكتابة توييك (Tweak) كامل لتطبيق iOS باستخدام Theos و Logos.
    المتطلبات: {user_message}
    
    أرسل الكود كاملاً مع ملف Makefile وملف .plist وملف .xm.
    استخدم الهيكل التالي:
    1. Makefile
    2. tweak.plist
    3. Tweak.xm
    
    أرسل الملفات بشكل منفصل مع أسمائها.
    """
    
    code = await ask_deepseek(prompt)
    
    if not code:
        await update.message.reply_text("❌ عذراً، حدث خطأ في توليد الكود. حاول مرة أخرى.")
        return
    
    # محاولة استخراج الكود المناسب
    # (هنا يمكنك تحسين منطق استخراج الكود حسب تنسيق الرد)
    files = extract_code_files(code)
    
    if not files:
        await update.message.reply_text("❌ لم أتمكن من استخراج الكود. حاول صياغة الطلب بشكل أوضح.")
        return
    
    # تشغيل GitHub Actions
    for filename, content in files.items():
        result = trigger_github_workflow(content, filename)
    
    await update.message.reply_text(
        "✅ تم بناء الأداة بنجاح!\n\n"
        "📦 سيتم إرسال الملف النهائي عند اكتمال البناء.\n"
        "⏱️ قد يستغرق البناء 2-3 دقائق."
    )

def extract_code_files(response: str) -> dict:
    """استخراج ملفات الكود من رد DeepSeek"""
    files = {}
    current_file = None
    current_content = []
    
    for line in response.split('\n'):
        # التعرف على أسماء الملفات
        if line.strip().startswith('```') and current_file is None:
            # استخراج اسم الملف من السطر
            parts = line.strip().split()
            if len(parts) > 1:
                current_file = parts[1].strip()
                if not current_file.endswith(('.xm', '.plist', '.mk', '.yml', '.yaml')):
                    current_file = None
            continue
        
        if line.strip().startswith('```') and current_file is not None:
            # نهاية الملف
            if current_file and current_content:
                files[current_file] = '\n'.join(current_content)
            current_file = None
            current_content = []
            continue
        
        if current_file is not None:
            current_content.append(line)
    
    # إذا لم يتم استخراج ملفات، نحاول تخمين الكود
    if not files and response.strip():
        files['Tweak.xm'] = response
    
    return files

# ============================================
# تشغيل البوت
# ============================================
def main():
    """تشغيل البوت"""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # بدء البوت
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
