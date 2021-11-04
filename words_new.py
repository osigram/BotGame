from bs4 import BeautifulSoup
import requests
import re
import lxml
import json

categories = ['Базовая категория']
words = []
result = []

for category in categories:
    url = "https://ru.wiktionary.org/wiki/Категория:{0}/ru".format(category)
    contents = requests.get(url).text
    soup = BeautifulSoup(contents, 'lxml')
    # Categories hunting
    if len(categories) <= 10000:
        subcats = soup.find_all('div', {'class': 'CategoryTreeItem'})
        for subcat in subcats:
            data_sub = subcat.find('a')
            if data_sub.string.split('/')[0] not in categories:
                categories.append(data_sub.string.split('/')[0])
    # Words hunting
    words_page = soup.find('div', {'id': 'mw-pages'})
    if words_page != None: 
        words_page_list = words_page.find_all('a')
        for word in words_page_list:
            str_word = word.string.lower()
            if set(str_word) & set([chr(a) for a in range(ord('а'), ord('я') + 1)]) == set(str_word) and len(str_word) > 4 and str_word not in words and str_word != category.lower():
                result.append([str_word, category.lower()])
                words.append(str_word)

with open('words.json', 'w', encoding='UTF-8') as filew:
    json.dump(result, filew, ensure_ascii=False)