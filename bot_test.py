import unittest
from datetime import datetime
import pandas as pd
from bot import date_time, find_author, getDatapoint, analyze_chat_data

def remove_nnbsp(text):
    return text.replace('\u202F', ' ')  # Replace NNBSP with regular space

class TestChatAnalysis(unittest.TestCase):

    def test_date_time(self):
        self.assertTrue(date_time("7/11/24, 2:58 PM -"))
        self.assertFalse(date_time("7-11-24, 2:58 PM -"))
        self.assertFalse(date_time("Random text"))

    def test_find_author(self):
        self.assertTrue(find_author("John Doe: Hey, just saw what you sent. Good morning!"))
        self.assertFalse(find_author("No author here"))

    def test_getDatapoint(self):
        line = remove_nnbsp("7/11/24, 2:58 PM - John Doe: Hey, just saw what you sent. Good morning!")
        date, time, author, message = getDatapoint(line)
        self.assertEqual(date, "7/11/24")
        self.assertEqual(time, "2:58 PM")
        self.assertEqual(author, "John Doe")
        self.assertEqual(message, "Hey, just saw what you sent. Good morning!")

        def test_analyze_chat_data(self):
            file_content = """7/11/24, 2:58 PM - John Doe: Hey, just saw what you sent. Good morning!
    7/11/24, 6:12 PM - Jane Smith: <Media omitted>
    7/11/24, 6:12 PM - Jane Smith: John started a new project! Mike is next.
    7/12/24, 12:47 AM - Mike Johnson: I'll join the project too, sounds fun!
    7/12/24, 2:45 PM - Sarah Lee: <Media omitted>
    7/12/24, 2:54 PM - John Doe: Haha, your charts are hilarious. The company is not doing well.
    7/12/24, 2:54 PM - John Doe: It's a terrible field, full of problems.
    7/12/24, 3:06 PM - Sarah Lee: Why are they failing?
    7/12/24, 3:07 PM - Mike Johnson: <Media omitted>
    7/12/24, 3:07 PM - John Doe: Sales dropped in the US."""

            start_date, end_date, buf1, buf2, buf3 = analyze_chat_data(file_content, time_period="All_Time")

            # Convert 'Date' column to datetime format
            data = []
            lines = file_content.splitlines()
            for line in lines:
                if date_time(line):
                    date, time, author, message = getDatapoint(line)
                    data.append([date, time, author, message])

            df = pd.DataFrame(data, columns=["Date", 'Time', 'Author', 'Message'])
            df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%y', errors='coerce')

            # Check number of entries for each date
            entries_7_11 = df[df['Date'] == pd.to_datetime('7/11/24', format='%m/%d/%y')]
            entries_7_12 = df[df['Date'] == pd.to_datetime('7/12/24', format='%m/%d/%y')]

            self.assertEqual(len(entries_7_11), 3, "There should be 3 entries for 7/11/24")
            self.assertEqual(len(entries_7_12), 7, "There should be 7 entries for 7/12/24")


if __name__ == '__main__':
    unittest.main()
