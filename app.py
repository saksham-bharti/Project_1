import os
from flask import Flask, render_template, request, redirect, url_for, session  # Import necessary Flask modules
import psycopg2  # Import PostgreSQL adapter
from bs4 import BeautifulSoup  # Import BeautifulSoup for web scraping
import requests  # Import requests library for HTTP requests
import re  # Import re for regular expressions
import nltk  # Import nltk for natural language processing
from nltk.tokenize import word_tokenize, sent_tokenize  # Import tokenizers from NLTK
from nltk import pos_tag  # Import part-of-speech tagger from NLTK
import json  # Import json module for handling JSON data
from newspaper import Article

app = Flask(__name__)

def connect_db():
    conn = psycopg2.connect(
        dbname=os.environ ['postgres://news_wrap_user:UpwrbQ88lxx4Rk81DA7VbVQ3bCbyWITF@dpg-cnm808021fec7395ojr0-a5432/news_wrap'],
    )
    return conn

# Function to clean text from a given URL
def cleaned_text(url):
    response = requests.get(url)  # Send HTTP GET request to the provided URL
    if response.status_code == 200:  # If the request is successful
        soup = BeautifulSoup(response.content, 'html.parser')
        headline = soup.find('h1').get_text()  # Extracting headline from the title tag
        article = Article(url)
        article.download()
        article.parse()
        content= article.text
        return headline, content
    else:  # If the request fails
        print("Failed to retrieve the webpage. Status code:", response.status_code)



@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    url = request.form['name']  # Get the URL from the submitted form
    try:
        heading, text = cleaned_text(url)  # Call the function to get cleaned text from the URL
        words_list = word_tokenize(text)
        sent_list = sent_tokenize(text)

        count_stop_words = 0
        for i in words_list:
            if i.lower() in nltk.corpus.stopwords.words('english'):
                count_stop_words += 1

        def words(string):
            punc_list = ['.', ',', '!', '?']
            word_lst = word_tokenize(text)
            for i in word_lst:
                if i in punc_list:
                    word_lst.remove(i)
            return len(word_lst)

        dict_upos = {}
        list_new = [x for x in nltk.pos_tag(words_list, tagset='universal')]
        for i in list_new:
            if i[1] not in dict_upos.keys():
                dict_upos[i[1]] = 1
            else:
                dict_upos[i[1]] += 1

        sent_count = len(sent_list)
        words_count = words(text)
        pos_tag_count = sum(dict_upos.values())

        # Store summary data in a dictionary
        summary = {'words_count': words_count, 'sentences_count': sent_count, 'POS_tag_count': sum(dict_upos.values())}

        # Connect to the database
        conn = connect_db()
        cur = conn.cursor()

        
        def create_table(conn):
            cur = conn.cursor()
            cur.execute("""
        CREATE TABLE IF NOT EXISTS news_wrap (
            id SERIAL PRIMARY KEY,
            url VARCHAR(1000),
            text TEXT,
            word_count INTEGER,
            sentence_count INTEGER,
            postag_count INTEGER
        )
    """)
            conn.commit()
            cur.close()

        conn = connect_db()
        create_table(conn)
        cur = conn.cursor()
        
        # Insert data into the database
        cur.execute("""
            INSERT INTO news_wrap (url, text, word_count, sentence_count, postag_count)
            VALUES (%s, %s, %s, %s, %s)
        """, (url, text, words_count, sent_count, pos_tag_count))

        conn.commit()  # Commit changes
        cur.close()
        conn.close()  # Close database connection

        # Render the content.html template with the extracted data
        return render_template('output_text.html', heading=heading, text=text,
                            word_count=words_count, sentense_count=sent_count, dict_upos=dict_upos,
                            postag_count=pos_tag_count)
    except:
        # If it's not a URL, handle the error
        error_message = "Invalid input. Please enter a valid URL."
        return render_template('index.html', error=error_message)
    

@app.route('/admin')  # Route for admin login
def admin():
    return render_template('sign_in.html')  # Render the admin.html template


@app.route('/login', methods=['POST'])  # Route for handling login form submission
def login():
    email = request.form.get('email')  # Get email from the submitted form
    password = request.form.get('password')  # Get password from the submitted form
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("SELECT * FROM admin WHERE email=%s AND password=%s", (email.lower(), password))
    user = cur.fetchone()

    if user:
        return redirect('/admin')
    else:
        return "Invalid email or password"
        
@app.route('/admin/welcome')  # Route for admin welcome page
def admin_welcome():
    return render_template('admin.html')  # 

if __name__ == '__main__':
    app.run(debug=True)
