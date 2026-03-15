from environs import Env

# environs kutubxonasidan foydalanish
env = Env()
env.read_env()

# .env fayl ichidan quyidagilarni o'qiymiz
BOT_TOKEN = env.str("BOT_TOKEN")  # Bot toekn
ADMINS = list(map(int, env.list("ADMINS")))
IP = env.str("ip")  # Xosting ip manzili
OPENAI_API_KEY = env.str("OPENAI_API_KEY")