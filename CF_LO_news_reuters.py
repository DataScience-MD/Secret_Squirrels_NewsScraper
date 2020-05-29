# -*- coding: utf-8 -*-
"""
Created on Sat Jul 13 15:23:39 2019

@author: Dr. Mark M. Bailey | National Intelligence 
# Changelog 18 May 2020 by team Bad Ozone Grasshoppers
- 1. main() updated to take two options "browser_agent" and "news_dump_filename"
  -- 1.1. browser agents supported are 'Firefox' and 'Chrome'
  -- 1.2. filename should be passed in "[filename].json" format
  -- 1.3. If filename provided points to non-existent file the user will be notified and the file will be created

- 2. Updated to use pandas to read and save JSON files instead of pickle files 
     This was done to reduce code complexity and increase security
  -- 2.1. save_pickle() replaced with pd.DataFrame.to_json()
  -- 2.2. open_pickle() replaced with pd.DataFrame.read_json()
  -- 2.3. concat_lists() replaced with pd.concat()
  
- 3. Updated get_soup_links() function to remove duplicate links from list prior to returning list

- 4. Added check_chrome() feature to install chrome driver if it is not found 

- 5. Updated on 19 May to support modified https://www.reuters.com/theWire webpage
  -- New webpage is no longer an infinite scroll page and links are relative vs absolute
- 6. Modified by Truthiiness & DataScience-MD
"""

# News Scrape

# Import libraries
import selenium.webdriver as webdriver
import time
import requests
import pandas as pd
import os
import urllib.request
from urllib.parse import urlparse
import zipfile
import platform
import base64
from textblob import TextBlob
import numpy as np

# Import methods
from selenium.webdriver.chrome.options import Options
from lxml import html
from bs4 import BeautifulSoup


# Define functions
"""
GENERAL FUNCTIONS
"""

# Open news object file
# Accepts filepath (news_object_path) and filename (news_object_file) as strings
# Target file must be JSON format with columns ["date", "time", "source", "Title", "Text", "url"]
# If target file does not exist it will be created 
# If the target file is badly malformed the file will be overwritten
# Pandas library is used to open the JSON file as a dataframe and access the set of URLs
# Code provides basic format checking of input file based on the "url" column if that column does not exist program crashes with exception warning
def open_file(news_object_path, news_object_file):
    news_object_file = os.path.join(news_object_path, news_object_file)
    try:
        old_news_df = pd.read_json(news_object_file)
    except ValueError:
        #print('NOTICE: News object file [', news_object_file, '] not found or unreadable.  \nScraper will create/overwrite the file upon execution completion.')
        old_news_df = pd.DataFrame(columns = ['date', 'time', 'source', 'Title', 'Text', 'url'])
    try:
        old_url_set = set(old_news_df['url'].values)
    except:
        print('**********************************************************************************\n' + 
              'WARNING: News object file [', news_object_file, '] is malformed!.\n' +
              'JSON file must be formated with columns ["date", "time", "source", "Title", "Text", "url"]')
    return old_news_df, old_url_set


# url check
def url_check(old_url_set, url):
    scheme = urlparse(url) # parses the url into parts
    url_set = {url}
    test_set = old_url_set & url_set
    if len(test_set) == 0 and scheme.scheme: # Fixed parse error added scheme validation, will not process urls without scheme i.e. url missin 'https://'
        check = False
    else:
        check = True
    return check


"""
GET LINKS FROM HTML
"""


# get HTML with page scroll
# Function updated to allow user to define the browser agent
# Browser flag allows the user to define the type of browser used by selenium
# Code supports Firefox and Chrome, default is Chrome if no browser agent is specified
def get_html_scroll(url, browser_agent="Firefox"):
    # calls the webdriver based on the user's selection
    if browser_agent == "Firefox":
        browser = webdriver.Firefox()
    elif browser_agent == "Chrome":
        chrome_options = Options() # Using Options() to fix deprecation warning of manual options declarations
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        browser = webdriver.Chrome('chromedriver', options=chrome_options) # Using 'options=' to fix deprecation warning
    # else:
    # else section intentionally empty and reserved for future use
    # the else section is not needed in this code as get_html_scroll() is designed to be called by main()
    # and the main() process checks the browser_agent prior to passing to get_html_scroll()

    browser.get(url)
    lenOfPage = browser.execute_script("window.scrollTo(0, document.body.scrollHeight);" +
                                       "var lenOfPage=document.body.scrollHeight;" +
                                       "return lenOfPage;")
    match = False
    while (match == False):
        lastCount = lenOfPage
        time.sleep(4)
        lenOfPage = browser.execute_script("window.scrollTo(0, document.body.scrollHeight);" +
                                           "var lenOfPage=document.body.scrollHeight;" +
                                           "return lenOfPage;")
        if lastCount == lenOfPage:
            time.sleep(4)
            match = True
    post_elms = browser.page_source
    return post_elms


# get HTML file
def get_html(url):
    page = requests.get(url)
    html_out = html.fromstring(page.content)
    text = page.text
    return html_out, text


# get soup
def get_soup(html_string):
    soup = BeautifulSoup(html_string, 'html.parser')
    return soup


# get links
def get_soup_links(soup):
    links = []
    for link in soup.find_all('a'):
        out_link = link.get('href')
        links.append(out_link)
    # Remove duplicates from links
    # Below line removes all duplicate links prior to passing the list of links back
    # This is accomplished by converting the list of links into a dictionary and then back to a list
    links = list(dict.fromkeys(links))
    return links


"""
REUTERS FUNCTIONS
"""


# get article links
# This function stopped working on 19 May 2020 when Reuters updated their https://www.reuters.com/theWire page
# The https://www.reuters.com/theWire page updated to change from a infinite scroll to paginated
# Additionally, the updated webpage uses relative not absolute links
# Fixed code by prepending https://www.reuters.com to link if it is missing
def get_articles_reuters(links, old_url_set):
    articles = []
    for link in links:
        try:
             if '/article/' in link:
                if 'https://www.reuters.com' not in link: 
                    link = 'https://www.reuters.com' + link
                if not url_check(old_url_set, link):
                    articles.append(link)
        except:
            continue
    return articles


# get article html
def get_html_reuters(articles):
    soup_list = []
    for article in articles:
        _, text = get_html(article)
        soup = get_soup(text)
        soup_list.append(soup)
    return soup_list


# date formatter
def format_date(date):
    date_dict = {'January': '1', 'February': '2', 'March': '3', 'April': '4', 'May': '5', 'June': '6', 'July': '7',
                 'August': '8', 'September': '9', 'October': '10', 'November': '11', 'December': '12'}
    split_date = date.split(' ')
    year = split_date[2]
    day_list = split_date[1].split(',')[0]
    day = day_list
    month = date_dict[split_date[0]]
    out_date = year + '-' + month + '-' + day
    return out_date


# get elements
def get_reuters_elements(soup_list, articles):
    out_list = []
    i = 0
    for article in soup_list:
        link = articles[i]
        i += 1
        try:
            article_body = article.find_all('div', {'class': 'StandardArticleBody_body'})
            article_headline = article.find_all('h1', {'class': 'ArticleHeader_headline'})
            article_date = article.find_all('div', {'class': 'ArticleHeader_date'})
            try:
                date_time = article_date[0].text.split(' / ')
                date_in = date_time[0]
                date = format_date(date_in)
                a_time = date_time[1][1:]
            except:
                date = article_date[0].text
                time = article_date[0].text
            headline = article_headline[0].text
            article_p = []
            for item in article_body:
                p_list = item.find_all('p')
                for p in p_list:
                    article_p.append(p.text)
            out_text = ' '.join(article_p)
            out_dict = dict([('date', date), ('time', a_time), ('source', 'www.reuters.com'), ('Title', headline),
                             ('Text', out_text), ('url', link)])
            out_list.append(out_dict)
        except:
            print('Unable to decode...skipping article...')
            continue
    return out_list


# Execute Reuters script
def reuters(old_url_set, browser_agent):
    print('Getting Reuters articles...')
    url = 'https://www.reuters.com/theWire'
    post_elms = get_html_scroll(url, browser_agent)
    soup = get_soup(post_elms)
    links = get_soup_links(soup)
    articles = get_articles_reuters(links, old_url_set)
    soup_list = get_html_reuters(articles)
    reuters_list = get_reuters_elements(soup_list, articles)
    return reuters_list


# Get Chrome
# Adds local support for chrome driver if not found. function in OS aware, and fetches the appropriate version of
# chrome driver for the OS, extracts the zip, places the executable in the current working directory. This is the
# first checked PATH option for execution flow, then /bin, then /sbin, etc. Local placement allows for simpler
# environment set-up, and removes the requirement to force a non standard PATH variable into sys.
def check_chrome():
    os_platform = platform.system()

    try:
        if os_platform == 'Windows':
            open('chromedriver.exe')
        else:
            open('chromedriver')
    except Exception:
        dl_url = ''
        print("Chrome Driver not found...installing locally...")

        if os_platform == 'Windows':
           #dl_url = 'https://chromedriver.storage.googleapis.com/81.0.4044.138/chromedriver_win32.zip'
           dl_url = 'https://chromedriver.storage.googleapis.com/83.0.4103.39/chromedriver_win32.zip'
        else:
            dl_url = 'https://chromedriver.storage.googleapis.com/83.0.4103.39/chromedriver_linux64.zip'

        with urllib.request.urlopen(dl_url) as dl_file:
            with open('chromedriver.zip', 'wb') as out_file:
                out_file.write(dl_file.read())
                out_file.close()
        with zipfile.ZipFile('chromedriver.zip', 'r') as zip_file:
            zip_file.extractall()
            zip_file.close()
        os.remove('chromedriver.zip')
        pass

# Useless but fun
def banner():
    print(base64.b64decode("PT09PT09PT09PT09PT09PT09PT09PT09PT09PT09CnwgICBCYWQgT3pvbmUgR3" +
                           "Jhc3Nob3BwZXJzICAgfAo9PT09PT09PT09PT09PT09PT09PT09PT09PT09PT0=").decode('utf8'))

# Cleanup of temporary file
# Updated to use os.path.isfile() method to check if file exists
def cleanup():
    if os.path.isfile('chromedriver.exe'):
        os.remove('chromedriver.exe')
    elif os.path.isfile('chromedriver'):
        os.remove('chromedriver')
    elif os.path.isfile('geckodriver.log'):
        os.remove('geckodriver.log')
    return


"""
MAIN SCRIPT
Updated function to allow user to specify a browser agent and news_dump_object filename
If not specified the code will default to a browser agent of "Chrome" and filename of "news_dump_object.json"

"""


def main(browser_agent="Chrome", news_object_file='news_dump_object.json'):
    banner()
    # Check if the requested browser agent is Firefox or Chrome
    # If no agent is passed code will default to Chrome
    if browser_agent == "Chrome" or browser_agent == "Firefox":
        print("Executing using", browser_agent, "webdriver")
        if browser_agent == "Chrome":
            check_chrome()
    else:
        print(browser_agent, " is not a recognized browser agent, please use 'Firefox' or 'Chrome'")
    news_object_path = os.getcwd()
    output_path = os.getcwd()
    # updated below line of code to allow user to specify a news_object_filename
    old_news_df, old_url_set = open_file(news_object_path, news_object_file) # loads the file
    print(old_news_df.index.size, 'articles loaded from', news_object_file) # inform user of how many articles loaded
    
    # Run the webscraper and save output to dataframe
    reuters_list_df = pd.DataFrame(reuters(old_url_set, browser_agent))
    print(reuters_list_df.index.size, 'new articles scraped') #display how many articles scraped
    #Check if any new information was
    if 'date' in  reuters_list_df.columns:
        # Formats the date column as a pandas date-time format
        reuters_list_df['date'] = reuters_list_df['date'].astype('datetime64') 
    
    # Updated to use pandas concat function 
    output_reuters_df = pd.concat([old_news_df, reuters_list_df], ignore_index=True)

    print('Saving news object...')
    output_file = os.path.join(output_path, news_object_file)
    # Save output to JSON file using pandas
    output_reuters_df.to_json(path_or_buf=output_file)
    output_reuters = output_reuters_df.to_json()
    cleanup()
    return output_reuters


"""
EXECUTE SCRIPT
"""
if __name__ == '__main__':
    output_reuters = main()

"""
TEXT ANALYSIS
* Code Added by Secret Squirrels*  
"""
file_path = r'news_dump_object.json'
def open_text(file_path):
    with open(file_path, 'r') as document:
        text = document.read()
    return text
print('\n **Additional Analysis added by Secret Squirrels**\n \n Typical methods for news article analysis is to look at the '
      'Polarity, Objectivity or Subjectivity and the number of times of occurrence for key words, referred to as'
      ' "Mentions. Also an overall sentiment analysis gives an impression of the news (positive or negative)."\n')
print('- OBJECTIVITY measures how objective or subjective a sentence is. A Subjective statement relates to personal'
      ' perspectives or feelings whereas an objective statement is considered based on irrefutable facts.'
      ' A value of Zero (0) would be COMPLETELY OBJECTIVE and a measure of 1 is COMPLETELY SUBJECTIVE.\n'
      '- POLARITY measures how positive or negative the "feeling" of the sentance is.  Polarity is measured on a '
      'scale from -1 ("bad" feelings) to +1 ("good" feelings).\n'
      '- MENTIONS - This computation is simply the number of sentences that contain the key word.  This gives an '
      'overall appreciation of how much a topic is discussed.\n'
      '- SENTIMENT - A measure of sentiment is based on the two components of objectivity and polarity. The exact'
      ' way sentiment is measured is unique based on how the coder writes the script.  In general, it is presumed'
      ' to be "a good rule of thumb" to place a higher weight on sentences that are more subjective (because facts'
      ' technically are irrefutable (let us put aside the recent "Fake News" trend for now). As such, we chose to define'
      ' sentiment as:\n'
      '      Average sentiment = [Objectivity*Polarity]/total # of observations  \n \n'
      'Each time the query is run, the reader can make their own determination based on the key information above of the '
      'Polarity, Subjectivity or Objectivity, the amount the topic is discussed, and the overall Sentiment of the topic.\n')

text = open_text(file_path)
blob = TextBlob(text)
blob_sentences = blob.sentences

corona_sentences = []
for sentence in blob_sentences:
    if 'corona' in sentence:
        corona_sentences.append(sentence)

trump_sentences = []
trump_polarity = []
trump_subjectivity = []
for sentence in corona_sentences:
    if 'Trump' in sentence:
        trump_sentences.append(sentence)
        trump_polarity.append(sentence.sentiment.polarity)
        trump_subjectivity.append(sentence.sentiment.subjectivity)
trump_sentiment =[]
for i in trump_sentences:
    sentiment = i.polarity*i.sentiment.subjectivity
    trump_sentiment.append(sentiment)
trump_avg_sentiment = np.average(trump_sentiment)
print("Trump Coronavirus Polarity:", np.mean(trump_polarity))
print("Trump Coronavirus Sujectivity:", np.mean(trump_subjectivity))
print("Trump Coronavirus Mentions:", len(trump_sentences))
print("Trump Coronavirus Sentiment:", trump_avg_sentiment,'\n') 

biden_sentences = []
biden_polarity = []
biden_subjectivity = []
for sentence in corona_sentences:
    if 'Biden' in sentence:
        biden_sentences.append(sentence)
        biden_polarity.append(sentence.sentiment.polarity)
        biden_subjectivity.append(sentence.sentiment.subjectivity)
biden_sentiment =[]
for i in biden_sentences:
    sentiment = i.polarity*i.sentiment.subjectivity
    biden_sentiment.append(sentiment)
biden_avg_sentiment = np.average(biden_sentiment)        
        
print("Biden Coronavirus Polarity:", np.mean(biden_polarity))
print("Biden Coronavirus Sujectivity:", np.mean(biden_subjectivity))
print("Biden Coronavirus Mentions:", len(biden_sentences))
print("Biden Coronavirus Sentiment:", biden_avg_sentiment,'\n') 

china_sentences = []
china_polarity = []
china_subjectivity = []
for sentence in corona_sentences:
    if 'China' in sentence:
        china_sentences.append(sentence)
        china_polarity.append(sentence.sentiment.polarity)
        china_subjectivity.append(sentence.sentiment.subjectivity)
china_sentiment =[]
for i in china_sentences:
    sentiment = i.polarity*i.sentiment.subjectivity
    china_sentiment.append(sentiment)
china_avg_sentiment = np.average(china_sentiment) 

print("China Coronavirus Polarity:", np.mean(china_polarity))
print("China Coronavirus Sujectivity:", np.mean(china_subjectivity))
print("China Coronavirus Mentions:", len(china_sentences))
print("China Coronavirus Sentiment:", china_avg_sentiment,'\n') 

russia_sentences = []
russia_polarity = []
russia_subjectivity = []
for sentence in corona_sentences:
    if 'Russia' in sentence:
        russia_sentences.append(sentence)
        russia_polarity.append(sentence.sentiment.polarity)
        russia_subjectivity.append(sentence.sentiment.subjectivity)
        
russia_sentiment =[]
for i in russia_sentences:
    sentiment = i.polarity*i.sentiment.subjectivity
    russia_sentiment.append(sentiment)
russia_avg_sentiment = np.average(russia_sentiment)         
print("Russia Coronavirus Polarity:", np.mean(russia_polarity))
print("Russia Coronavirus Sujectivity:", np.mean(russia_subjectivity))
print("Russia Coronavirus Mentions:", len(russia_sentences))
print("Russia Coronavirus Sentiment:", russia_avg_sentiment,'\n') 