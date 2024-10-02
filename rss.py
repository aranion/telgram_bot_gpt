import feedparser


class Source(object):
    def __init__(self, link):
        self.link = link
        self.news = []
        self.refresh()

    def refresh(self):
        data = feedparser.parse(self.link)
        self.news = [
            {
                'title': i['title'],
                'link': i['link'],
                'published': i['published'],
                'id': i['id'],
                'summary': i['summary']
            } for i in data['entries']
        ]
        print(self.news)


d = Source('https://www.sciencedaily.com/rss/all.xml')
print(d)
