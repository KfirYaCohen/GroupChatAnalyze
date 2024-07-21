import re
import pandas as pd
import numpy as np
import emoji
from collections import Counter
import matplotlib.pyplot as plt
from io import BytesIO
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator
import nltk
from nltk.tokenize import word_tokenize
from nltk import pos_tag
from nltk.corpus import stopwords
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from nltk import pos_tag, word_tokenize
import arabic_reshaper
from bidi.algorithm import get_display
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from config import BOT_TOKEN
from datetime import datetime, timedelta

# Ensure you have the necessary NLTK data files
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('stopwords')
nltk.download('wordnet')

def date_time(s):
    pattern = r'^(\d+/\d+/\d+, \d+:\d+\s?[APMapm]{2}) -'
    result = re.match(pattern, s)
    return bool(result)

def find_author(s):
    parts = s.split(": ")
    if len(parts) >= 2:
        return True
    return False

def getDatapoint(line):
    splitline = line.split(' - ', 1)
    dateTime = splitline[0]
    date, time = dateTime.split(", ")
    message = splitline[1]
    if find_author(message):
        splitmessage = message.split(": ", 1)
        author = splitmessage[0]
        message = splitmessage[1]
    else:
        author = None
    return date, time, author, message

def analyze_chat_data(file_content, time_period="All_Time"):
    # Read data from content
    data = []
    lines = file_content.splitlines()
    messageBuffer = []
    date, time, author = None, None, None
    for line in lines:
        line = line.strip()
        if date_time(line):
            if messageBuffer:
                data.append([date, time, author, ' '.join(messageBuffer)])
            messageBuffer.clear()
            date, time, author, message = getDatapoint(line)
            messageBuffer.append(message)
        else:
            messageBuffer.append(line)
    if messageBuffer:
        data.append([date, time, author, ' '.join(messageBuffer)])

    # Create DataFrame
    df = pd.DataFrame(data, columns=["Date", 'Time', 'Author', 'Message'])

    # Convert 'Date' column to datetime format
    df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%y')

    # Combine 'Date' and 'Time' into a single datetime column
    df['DateTime'] = df.apply(lambda row: pd.to_datetime(row['Date'].strftime('%Y-%m-%d') + ' ' + row['Time']), axis=1)

    df['Author'] = df['Author'].apply(lambda x: x[::-1] if isinstance(x, str) and re.search(r'[\u0590-\u05FF]', x) else x)

    # Remove "Media omitted" from messages
    df['Message'] = df['Message'].str.replace('<Media omitted>', 'Media')

    # Reshape and reverse Hebrew text for messages
    def reshape_and_reverse(text):
        try:
            reshaped_text = arabic_reshaper.reshape(text)
            bidi_text = get_display(reshaped_text)
            return bidi_text
        except AssertionError as e:
            print(f"Error reshaping text: {text}, Error: {e}")
            return text

    df['Message'] = df['Message'].apply(reshape_and_reverse)

    # Filter data based on the time period
    end_date = datetime.now()
    if time_period == "Last_Week":
        start_date = end_date - timedelta(days=7)
    elif time_period == "Last_Month":
        start_date = end_date - timedelta(days=30)
    else:
        start_date = df['DateTime'].min()
    df = df[(df['DateTime'] >= start_date) & (df['DateTime'] <= end_date)]

    # Drop NaN values
    df = df.dropna()

    # Function to check if a message contains only the letter ח (one or more times)
    def contains_only_chet(message):
        return re.fullmatch(r'ח+', message) is not None

    # Filter messages that contain only the letter ח
    chet_messages = df[df['Message'].apply(contains_only_chet)]

    # Count the number of such messages by each author
    chet_message_counts = chet_messages['Author'].value_counts()

    # Total messages by each author
    total_message_counts = df['Author'].value_counts()

    # Calculate the percentage of 'ח' messages for each author
    chet_message_percentage = (chet_message_counts / total_message_counts * 100).fillna(0)
    chet_message_percentage = chet_message_percentage.sort_values(ascending=False)

    # Plot the number of messages per author
    plt.figure(figsize=(12, 6))
    df['Author'].value_counts().plot(kind='bar', color='skyblue')
    plt.title('Number of Messages per Author')
    plt.xlabel('Author')
    plt.ylabel('Number of Messages')
    plt.xticks(rotation=45)
    buf1 = BytesIO()
    plt.savefig(buf1, format='png')
    buf1.seek(0)
    plt.close()

    # Plot the number of media messages per author
    media_df = df[df['Message'] == 'Media']
    media_counts = media_df['Author'].value_counts()
    plt.figure(figsize=(12, 6))
    media_counts.plot(kind='bar', color='orange')
    plt.title('Number of Media Messages per Author')
    plt.xlabel('Author')
    plt.ylabel('Number of Media Messages')
    plt.xticks(rotation=45)
    buf2 = BytesIO()
    plt.savefig(buf2, format='png')
    buf2.seek(0)
    plt.close()

    # Plot the percentage of messages containing only 'ח' per author
    plt.figure(figsize=(12, 6))
    chet_message_percentage.plot(kind='bar', color='green')
    title = "מי זורק עלינו זין ושולח רק חחח"
    plt.title(title[::-1])
    plt.xlabel('Author')
    plt.ylabel("Percentage of 'ח' Messages")
    plt.xticks(rotation=45)
    buf3 = BytesIO()
    plt.savefig(buf3, format='png')
    buf3.seek(0)
    plt.close()

    return start_date, end_date, buf1, buf2, buf3


async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Hi! Please send the chat text file to analyze.')

async def handle_file(update: Update, context: CallbackContext) -> None:
    file = await update.message.document.get_file()
    file_content = await file.download_as_bytearray()
    context.user_data['file_content'] = file_content.decode('utf-8')
    await update.message.reply_text('File received. Please choose the time period to analyze:', reply_markup=await get_time_buttons())

async def get_time_buttons() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("All Time", callback_data='All_Time')],
        [InlineKeyboardButton("Last Month", callback_data='Last_Month')],
        [InlineKeyboardButton("Last Week", callback_data='Last_Week')]
    ]
    return InlineKeyboardMarkup(buttons)

async def button_click(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    time_period = query.data
    await query.edit_message_text(text=f"Selected option: {time_period}. Analyzing data, please wait...")
    file_content = context.user_data.get('file_content')
    if file_content:
        start_date, end_date, buf1, buf2, buf3 = analyze_chat_data(file_content, time_period)
        chat_id = query.message.chat_id
        await context.bot.send_message(chat_id, text=f"Analyzing data from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        await context.bot.send_photo(chat_id, photo=buf1)
        await context.bot.send_photo(chat_id, photo=buf2)
        await context.bot.send_photo(chat_id, photo=buf3)
    else:
        await query.message.reply_text('No file found. Please send the chat text file again.')

def main():
    # Replace 'YOUR_BOT_TOKEN' with your actual bot token
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.MimeType("text/plain"), handle_file))
    application.add_handler(CallbackQueryHandler(button_click))

    application.run_polling()

if __name__ == '__main__':
    main()
