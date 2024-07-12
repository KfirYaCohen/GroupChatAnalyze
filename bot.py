import re
import pandas as pd
import numpy as np
import emoji
from collections import Counter
import matplotlib.pyplot as plt
from PIL import Image
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
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from config import BOT_TOKEN


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

def analyze_chat_data(filepath):
    # Read data from file
    data = []
    with open(filepath, encoding="utf-8") as fp:
        fp.readline()  # Skip the first line
        messageBuffer = []
        date, time, author = None, None, None
        while True:
            line = fp.readline()
            if not line:
                if messageBuffer:  # Save the last message
                    data.append([date, time, author, ' '.join(messageBuffer)])
                break
            line = line.strip()
            if date_time(line):
                if messageBuffer:
                    data.append([date, time, author, ' '.join(messageBuffer)])
                messageBuffer.clear()
                date, time, author, message = getDatapoint(line)
                messageBuffer.append(message)
            else:
                messageBuffer.append(line)

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
        reshaped_text = arabic_reshaper.reshape(text)
        bidi_text = get_display(reshaped_text)
        return bidi_text

    df['Message'] = df['Message'].apply(reshape_and_reverse)

    # Drop NaN values
    data = df.dropna()

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
    plt.savefig('messages_per_author.png')
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
    plt.savefig('media_messages_per_author.png')
    plt.close()

    # Plot the percentage of messages containing only 'ח' per author
    plt.figure(figsize=(12, 6))
    chet_message_percentage.plot(kind='bar', color='green')
    title = "מי זורק עלינו זין ושולח רק חחח"
    plt.title(title[::-1])
    plt.xlabel('Author')
    plt.ylabel("Percentage of 'ח' Messages")
    plt.xticks(rotation=45)
    plt.savefig('chet_messages_percentage.png')
    plt.close()


async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Hi! Please send the chat text file to analyze.')

async def handle_file(update: Update, context: CallbackContext) -> None:
    file = await update.message.document.get_file()
    filepath = 'chat.txt'
    await file.download_to_drive(filepath)
    analyze_chat_data(filepath)
    chat_id = update.message.chat_id
    await context.bot.send_photo(chat_id, photo=open('messages_per_author.png', 'rb'))
    await context.bot.send_photo(chat_id, photo=open('media_messages_per_author.png', 'rb'))
    await context.bot.send_photo(chat_id, photo=open('chet_messages_percentage.png', 'rb'))

def main():
    # Replace 'YOUR_BOT_TOKEN' with your actual bot token
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.MimeType("text/plain"), handle_file))

    application.run_polling()

if __name__ == '__main__':
    main()
