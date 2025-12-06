from aiogram import types
from  loader import dp




@dp.message_handler(content_types=['photo'])
async def get_photo_id(message: types.Message):
    file_id = message.photo[-1].file_id
    await message.reply(f"FILE_ID:\n<code>{file_id}</code>", parse_mode='HTML')


