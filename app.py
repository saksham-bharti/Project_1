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
from authlib.integrations.flask_client import OAuth
#nltk.download('all')
app = Flask(__name__)


def connect_db():
    conn = psycopg2.connect(
        host='dpg-cnm808021fec7395ojr0-a', database='news_wrap', user='news_wrap_user' , password='UpwrbQ88lxx4Rk81DA7VbVQ3bCbyWITF'
    )
    return conn
    
app.config['SECRET_KEY'] = "THIS SHOULD BE SECRET"
app.config['GITHUB_CLIENT_ID'] = "3b63478995dd60c2e980"
app.config['GITHUB_CLIENT_SECRET'] = "a83a89bd91a99b5f72fcb7af6d169eb308f877c0"
github_admin_usernames=['saksham-bharti']
github = OAuth.register(
    name='github',
    client_id=app.config["GITHUB_CLIENT_ID"],
    client_secret=app.config["GITHUB_CLIENT_SECRET"],
    access_token_url='https://github.com/login/oauth/access_token',
    access_token_params=None,
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

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
        return redirect('/admin/welcome')
    else:
        return "Invalid email or password"
            
@app.route('/admin/welcome')  # Route for admin welcome page
def admin_welcome():
    return render_template('admin.html')  # 

@app.route('/login/github')
def github_login():
    '''Route for initiating GitHub OAuth login'''
    github = oauth.create_client('github')  # Create a GitHub OAuth client
    redirect_uri = url_for('github_authorize', _external=True)  # It Generate the redirect URI for authorization
    return github.authorize_redirect(redirect_uri)  # Redirect the user to GitHub for authorization


# Github authorize route
@app.route('/login/github/authorize')
def github_authorize():
    '''Route for handling GitHub OAuth authorization'''
    # main function for github that check if the user is admin the it redirect to history page 
    # It take connection 
    conn = connect_db()  
    cur = conn.cursor()  
    
    try:
        github = OAuth.create_client('github')  # Create a GitHub OAuth client
        token = github.authorize_access_token()  # Get the access token from the authorization response
        session['github_token'] = token  # Store the access token in the session
        resp = github.get('user').json()  # Get the user's information from GitHub
        # print(f"\n{resp}\n")
        logged_in_username = resp.get('login')  # Get the username from the user's information
        if logged_in_username in github_admin_usernames:  # Check if the username is in the list of admin usernames
            cur.execute('select * from news_wrap')  
            data = cur.fetchall()  # Fetch all rows from the 'news' table
            conn.close()  
            return render_template("admin.html")
        else:
            return render_template("index.html")  
    except:
        return render_template("index.html") 

# Logout route for GitHub
@app.route('/logout/github')
def github_logout():
    '''Route for logging out from GitHub OAuth'''
    session.pop('github_token', None)  # Remove the access token from the session
    return redirect(url_for('submit'))

    if __name__ == '__main__':
        app.run(debug=True)
