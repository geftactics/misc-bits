import random
import requests
from bs4 import BeautifulSoup
from collections import Counter
from string import punctuation

potential_words = []
ignore_list = ["record", "people", "against", "likely", "", "the", "to", "of", "for", "on", "to", "the", "in", "what", "are", "a", "how", "and", "for", "of", "can", "be", "who", "will", "on", "does", "i", "matter", "from", "why", "your", "is", "bbc", "home", "uk", "should", "after", "my", "happened", "when", "new", "do", "back", "now", "questions", "news", "end", "over", "by", "but", "them", "need", "again", "day", "has", "open", "this", "city", "out", "where", "v", "could", "many", "have", "go", "hit", "wear", "it", "five", "they", "know", "about", "being", "we", "app", "model"]

r = requests.get("http://feeds.bbci.co.uk/news/rss.xml")

soup = BeautifulSoup(r.content, features="xml")
text = (''.join(s.findAll(text=True))for s in soup.findAll('title'))
c = Counter((x.rstrip(punctuation).lower() for y in text for x in y.split()))

for w in c.most_common():

    word = w[0]
    count = w[1]

    if word not in ignore_list and len(word)>5 and "'" not in word:

        potential_words.append(word)
        if len(potential_words) == 25: break

print(random.choice(potential_words))
