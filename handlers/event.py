from config import *
from utils.db import DB

@dp.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> MEMBER))
async def bot_added_as_member(event: ChatMemberUpdated, state: FSMContext):
    db = DB()
    if db.is_group_exists(event.chat.id) is False:
        chat_info = await bot.get_chat(event.chat.id)
        if chat_info.permissions.can_send_messages:
            creator = f"<a href='tg://user?id={event.from_user.id}'>{event.from_user.full_name}</a>"
            await event.answer(
                text=f"Привет! 👋 Вижу, что вы добавили меня в вашу группу.\n" +
                     f'Теперь пришлите мне ваш номер группы ответом на это сообщение ✍️\n' +
                     f'(Настраивать может только {creator})',
                    disable_web_page_preview=True 
            )
            await state.set_state(States.GROUP_reg_group)
            await state.update_data(id=str(event.chat.id))
            await state.update_data(user_id=event.from_user.id)
        else:
            await bot.send_message(
                chat_id=event.from_user.id,
                text=f'Я не могу писать сообщения в группу "{event.chat.title}". Предоставьте право писать сообщения'
            )
    else:
        group = db.cursor.execute(f"SELECT \"group\" FROM groups WHERE id = ?", (event.chat.id,)).fetchone()
        await event.answer(
            text=f"Привет! 👋 Кажется, я уже был в этой беседе.\n"
                 f"Ваш номер группы {group[0]}?\n"
                 f"Если это не так, измените в настройках"
        )



@dp.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=MEMBER >> ADMINISTRATOR))
async def bot_added_as_admin(event: ChatMemberUpdated, state: FSMContext):
    await bot_added_as_admin_and_leave(event)
    
@dp.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=IS_NOT_MEMBER >> ADMINISTRATOR))
async def bot_added_as_admin(event: ChatMemberUpdated, state: FSMContext):
    await bot_added_as_admin_and_leave(event)

@dp.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=ADMINISTRATOR >> IS_NOT_MEMBER \
                                           or MEMBER >> IS_NOT_MEMBER))
async def bot_kicked_from_group(event: ChatMemberUpdated, state: FSMContext):
    await state.clear()

async def bot_added_as_admin_and_leave(event: ChatMemberUpdated):
    if str(event.chat.id) == BACKUP_CHAT_ID:
        return
    if event.chat.type != "supergroup":
        text = "Не добавляйте меня в беседу как Администратора! ⚠️ Это может повлечь за собой потерю всех сообщений."
        await event.answer(text)
        await bot.leave_chat(event.chat.id)
        await bot.send_message(event.from_user.id, text=text)