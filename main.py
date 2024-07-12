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

# Ensure you have the necessary NLTK data files
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('stopwords')
nltk.download('wordnet')

# Extract Time
def date_time(s):
    pattern = r'^(\d+/\d+/\d+, \d+:\d+\s?[APMapm]{2}) -'
    result = re.match(pattern, s)
    return bool(result)

# Find Authors or Contacts
def find_author(s):
    parts = s.split(": ")
    if len(parts) >= 2:
        return True
    return False

# Finding Messages
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

# Read data from file
data = []
conversation = 'chat.txt'
with open(conversation, encoding="utf-8") as fp:
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

# Mapping Hebrew names to English names
name_mapping = {
    'זיו שהינו': 'Ziv',
    'קרקו': 'Karako',
    'שגיא כהן': 'Sagi',
    'רם עכו': 'Ram',
    'איתי דרעי': 'Itay',
    'מעיין אסולין': 'Asulin',
    'מתן לרון': 'Matan',
    'אורן ארזי': 'Oran',
    'אסף סבח': 'Asaf',
    'דן סאסי': 'Dan'
}

""" Use this to use the contacts names"""
df['Author'] = df['Author'].apply(lambda x: x[::-1] if isinstance(x, str) and re.search(r'[\u0590-\u05FF]', x) else x)

""" Use this to use the mapping"""
# df['Author'] = df['Author'].replace(name_mapping)

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
print(data.head(5))

# Chatting statistics
total_messages = df.shape[0]
media_messages = df[df['Message'] == 'Media'].shape[0]
links = np.sum(df['Url_Count']) if 'Url_Count' in df else 0
print('Group Chatting Stats:')
print(f'Total Number of Messages: {total_messages}')
print(f'Total Number of Media Messages: {media_messages}')
print(f'Total Number of Links: {links}')

# Plot the number of messages per author
plt.figure(figsize=(12, 6))
df['Author'].value_counts().plot(kind='bar', color='skyblue')
plt.title('Number of Messages per Author')
plt.xlabel('Author')
plt.ylabel('Number of Messages')
plt.xticks(rotation=45)
plt.show()

# Analyze which author sent the most media messages
media_df = df[df['Message'] == 'Media']
media_counts = media_df['Author'].value_counts()

# Plot the number of media messages per author
plt.figure(figsize=(12, 6))
media_counts.plot(kind='bar', color='orange')
plt.title('Number of Media Messages per Author')
plt.xlabel('Author')
plt.ylabel('Number of Media Messages')
plt.xticks(rotation=45)
plt.show()

# Uncomment the following block to generate a word cloud
"""
# Word Cloud of mostly used words in the group
text = " ".join(review for review in df.Message)
# Reshape and reverse Hebrew text
reshaped_text = arabic_reshaper.reshape(text)
bidi_text = get_display(reshaped_text)
# Path to the font file (make sure to adjust this to the correct path on your system)
font_path = 'dejavu-sans-ttf-2.37/ttf/DejaVuSans.ttf'  # Adjust this path
wordcloud = WordCloud(stopwords=STOPWORDS, background_color="white", font_path=font_path).generate(bidi_text)
# Display the generated image
plt.figure(figsize=(10, 5))
plt.imshow(wordcloud, interpolation='bilinear')
plt.axis("off")
plt.show()
"""

# Uncomment the following block to analyze the most active day in the group
"""
# Mostly Active day in the Group
plt.figure(figsize=(8, 5))
active_day = df['Day'].value_counts()
# Top 10 people that are mostly active in our group
a_d = active_day.head(10)
a_d.plot.bar()
plt.xlabel('Day', fontdict={'fontsize': 12, 'fontweight': 10})
plt.ylabel('No. of messages', fontdict={'fontsize': 12, 'fontweight': 10})
plt.title('Mostly active day of the week in the group', fontdict={'fontsize': 18, 'fontweight': 8})
plt.show()
"""

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

# Display the counts and percentages
print("Number of messages containing only 'ח' by each author:")
print(chet_message_counts)
print("Percentage of 'ח' messages by each author:")
print(chet_message_percentage)

# Plot the percentage of messages containing only 'ח' per author
plt.figure(figsize=(12, 6))
chet_message_percentage.plot(kind='bar', color='green')
title = "מי זורק עלינו זין ושולח רק חחח"
plt.title(title[::-1])
plt.xlabel('Author')
plt.ylabel("Percentage of 'ח' Messages")
plt.xticks(rotation=45)
plt.show()


