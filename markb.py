import logging
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ConversationHandler
from telegram import ReplyKeyboardMarkup
import sqlite3

# всего для заявок статусов: NEW(нерассмотренная)
# DEN(отклонённая)
# PER(принятая)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)
con = sqlite3.connect('instance/marketplace.db')
cur = con.cursor()
ADMIN = [i[0] for i in cur.execute("""SELECT id_user FROM messages WHERE status = 'PER'""")]
GOD = [828984897]


async def showrequest_command(update, context):
    global con
    if update.effective_user.id in ADMIN or update.effective_user.id in GOD:
        cur = con.cursor()
        r = cur.execute("""SELECT * FROM messages WHERE status='NEW'""").fetchall()
        if len(r) == 0:
            await update.message.reply_text('Сейчас нет новых заявок')
            return ConversationHandler.END
        await update.message.reply_text('Номер заявки, Email заявителя, Краткое имя в telegram')
        for i in r:
            await update.message.reply_text(f'{str(i[0])}, {i[1]}, {i[3]}')
            await update.message.reply_text(f'Комментарий: {i[5]}')
        await update.message.reply_text('Напишите id заявки с которой желаете взаимодействовать')
        return 1
    else:
        await update.message.reply_text('К сожалению, у вас недостаточно прав для данного действия')
        return ConversationHandler.END


async def adm_question(update, context):
    global con
    cur = con.cursor()
    idd = [str(i[0]) for i in cur.execute("""SELECT id FROM messages WHERE status='NEW'""")]
    if update.message.text in idd:
        context.user_data['sel_id'] = int(update.message.text)
        await update.message.reply_text('Для принятия заявки пришлите "+", а для отклонения - "-"')
        return 2
    else:
        await update.message.reply_text('Некорректный id')
        return ConversationHandler.END


async def adm_decision(update, context):
    global con
    if update.message.text == '-':
        cur = con.cursor()
        cur.execute(f"""UPDATE messages SET status = 'DEN' WHERE id = {context.user_data['sel_id']}""")
        con.commit()
        await update.message.reply_text(f"Заявка с id {context.user_data['sel_id']} успешно отклонена")
        return ConversationHandler.END
    elif update.message.text == '+':
        cur = con.cursor()
        cur.execute(f"""UPDATE messages SET status = 'PER' WHERE id = {context.user_data['sel_id']}""")
        em = cur.execute(f"""SELECT email FROM messages WHERE id = {context.user_data['sel_id']}""").fetchall()[0][0]
        cur.execute(f"""UPDATE users SET role = 'admin' WHERE email = '{em}'""")
        con.commit()
        await update.message.reply_text(f"Заявка с id {context.user_data['sel_id']} успешно принята")
        return ConversationHandler.END


async def request_command(update, context):
    if update.effective_user.id in ADMIN or update.effective_user.id in GOD:
        await update.message.reply_text('Вы уже являетесь администратором')
        return ConversationHandler.END
    await update.message.reply_text('Введите адрес вашей зарегистрированной электронной почты')
    return 1


async def send_request(update, context):
    global con
    cur = con.cursor()
    y = [i[0] for i in cur.execute("""SELECT email FROM users""").fetchall()]
    m = [i[0] for i in cur.execute("""SELECT email FROM messages""").fetchall()]
    if update.message.text.lower() not in y:
        await update.message.reply_text('Данная почта не зарегистрирована на сайте')
        return ConversationHandler.END
    elif update.message.text.lower() in m:
        await update.message.reply_text('Завяка с данной почтой уже была отправлена!')
        return ConversationHandler.END        
    else:
        context.user_data['email'] = update.message.text.lower()
        await update.message.reply_text('Отправьте короткий комментарий к своей заявке')
        return 2

    
async def send_comm(update, context):
    if update.effective_user.username:
        insert = """INSERT INTO messages (email,id_user,name,status,comment) VALUES(?,?,?,?,?)"""
        data = (context.user_data['email'], update.effective_user.id, update.effective_user.username, 'NEW', update.message.text)
    else:
        insert = """INSERT INTO messages (email,id_user,name,status,comment) VALUES(?,?,?,?,?)"""
        data = (context.user_data['email'], update.effective_user.id, 'Не указано', 'NEW', update.message.text)
    cur.execute(insert, data)
    con.commit()
    await update.message.reply_text('Запрос успешно отправлен')
    return ConversationHandler.END

    
async def myrequest_command(update, context):
    global con
    cur = con.cursor()
    if (update.effective_user.id in [i[0] for i in
            cur.execute("""SELECT id_user FROM messages""").fetchall()]):
        req = cur.execute(f"""SELECT * FROM messages WHERE id_user = {update.effective_user.id}""").fetchall()
        for i in req:
            if i[4] == 'NEW':
                await update.message.reply_text(f'{i[1]} - заявка ещё не рассмотрена')
            elif i[4] == 'DEN':
                await update.message.reply_text(f'{i[1]} - заявка отклонена')
            elif i[4] == 'PER':
                await update.message.reply_text(f'{i[1]} - заявка одобрена')
    else:
        await update.message.reply_text('Вы ещё не подавали заявок')


async def changerequest_command(update, context):
    global con
    cur = con.cursor()
    r = cur.execute("""SELECT * FROM messages WHERE status != 'NEW'""").fetchall()
    if len(r) == 0:
        await update.message.reply_text('Сейчас нет обработанных ранее заявок')
        return ConversationHandler.END
    await update.message.reply_text('Номер заявки, Email заявителя, Краткое имя в telegram, Статус')
    for i in r:
        if i[4] == 'PER':
            await update.message.reply_text(f'{str(i[0])}, {i[1]}, {i[3]}, Одобрена')
            await update.message.reply_text(f'Комментарий: {i[5]}')
        elif i[4] == 'DEN':
            await update.message.reply_text(f'{str(i[0])}, {i[1]}, {i[3]}, Отклонена')
            await update.message.reply_text(f'Комментарий: {i[5]}')
    await update.message.reply_text('Напишите id заявки с которой желаете взаимодействовать')
    return 1


async def choose_id(update, context):
    global con
    cur = con.cursor()
    idd = [str(i[0]) for i in cur.execute("""SELECT id FROM messages WHERE status != 'NEW'""")]
    if update.message.text in idd:
        context.user_data['change'] = [int(update.message.text),
                                       cur.execute(f"""SELECT status FROM messages WHERE id={update.message.text}""").fetchall()[0][0]]
        if context.user_data['change'][1] == 'DEN':
            await update.message.reply_text('Вы уверены, что хотите одобрить данную заявку? Для подтверждения пришлите "+", для отклонения - "-"')
        elif context.user_data['change'][1] == 'PER':
            await update.message.reply_text('Вы уверены, что хотите отклонить данную заявку? Для подтверждения пришлите "+", для отклонения - "-"')
        return 2
    else:
        await update.message.reply_text('Некорректный id')
        return ConversationHandler.END

    
async def commit_change(update, context):
    global con
    if context.user_data['change'][1] == 'DEN' and update.message.text == '+':
        cur = con.cursor()
        cur.execute(f"""UPDATE messages SET status = 'PER' WHERE id = {context.user_data['change'][0]}""")
        em = cur.execute(f"""SELECT email FROM messages WHERE id = {context.user_data['change'][0]}""").fetchall()[0][0]
        cur.execute(f"""UPDATE users SET role = 'admin' WHERE email = '{em}'""")
        con.commit()
        await update.message.reply_text(f"Заявка с id {context.user_data['change'][0]} успешно принята")
        return ConversationHandler.END        
    elif context.user_data['change'][1] == 'PER' and update.message.text == '+':
        cur = con.cursor()
        cur.execute(f"""UPDATE messages SET status = 'DEN' WHERE id = {context.user_data['change'][0]}""")
        em = cur.execute(f"""SELECT email FROM messages WHERE id = {context.user_data['change'][0]}""").fetchall()[0][0]
        cur.execute(f"""UPDATE users SET role = 'user' WHERE email = '{em}'""")
        con.commit()
        await update.message.reply_text(f"Заявка с id {context.user_data['change'][0]} успешно отклонена")
        return ConversationHandler.END 
    else:
        await update.message.reply_text('Отмена')
        return ConversationHandler.END
    


async def help_command(update, context):
    await update.message.reply_text('Данный бот предназначен для подачи и принятия заявок на admin-права в MarketHub')
    if update.effective_user.username in GOD:
        await update.message.reply_text('Команда "/showrequests" позволяет взаимодействовать c поданными заявками')
        await update.message.reply_text('Команда "/changerequests" позволяет взаимодействовать с уже обработанными ранее заявками')
    else:
        await update.message.reply_text('Команда "/request" позволяет отправить заявку на рассмотрение')
        await update.message.reply_text('Команда "/myrequest" позволяет отслеживать все заявки, отправленные с текущего аккаунта telegram')


async def start_command(update, context):
    if update.effective_user.id in GOD:
        reply_keyboard = [['/start', '/help'],
                          ['/showrequests', '/changerequests']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)
    elif update.effective_user.id in ADMIN:
        reply_keyboard = [['/start', '/help'],
                         ['/showrequests']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)
    else:
        reply_keyboard = [['/start', '/help'],
                          ['/request', '/myrequest']]
        markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)        
    await update.message.reply_text(
        "Приветствую",
        reply_markup=markup
    )


async def stop(update, context):
    return ConversationHandler.END


def main():
    #тут должен быть токен
    application = Application.builder().token('TOKEN').build()
    conv_req = ConversationHandler(entry_points=[CommandHandler('request', request_command)],
                                 states={
                                     1: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_request)],
                                     2: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_comm)]},
                                 fallbacks=[CommandHandler('stop', stop)])
    conv_adm = ConversationHandler(entry_points=[CommandHandler('showrequests', showrequest_command)],
                                   states={
                                       1: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_question)],
                                       2: [MessageHandler(filters.TEXT & ~filters.COMMAND, adm_decision)]},
                                   fallbacks=[CommandHandler('stop', stop)])
    conv_adv_ch = ConversationHandler(entry_points=[CommandHandler('changerequests', changerequest_command)],
                                    states={
                                      1: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_id)],
                                      2: [MessageHandler(filters.TEXT & ~filters.COMMAND, commit_change)]},
                                    fallbacks=[CommandHandler('stop', stop)])
    application.add_handler(conv_adv_ch)
    application.add_handler(conv_req)
    application.add_handler(conv_adm)
    application.add_handler(CommandHandler('myrequest', myrequest_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, start_command))

    application.run_polling()


if __name__ == '__main__':
    main()
    con.close()
