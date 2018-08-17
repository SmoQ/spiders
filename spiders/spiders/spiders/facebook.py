import re
from datetime import datetime
from time import sleep

from scrapy import Spider
from scrapy.selector import Selector
from selenium import webdriver


def get_published_date(post):
    return post.xpath('.//abbr/@data-utime').extract_first()


def get_posts(selector):
    return selector.css("._1xnd").xpath('.//div[@class="_4-u2 _4-u8"]')


class FacebookSpider(Spider):
    name = 'facebook'
    allowed_domains = ['facebook.com']

    def __init__(self, url, webdriver_path, days=30):
        self.days = int(days)
        url = '{}/posts/'.format(url)
        self.start_urls = [url]
        self.driver = webdriver.Chrome(webdriver_path)

    def parse(self, response):
        self.driver.get(response.url)

        while True:
            self.driver.execute_script(
                'window.scrollTo(0, document.body.scrollHeight);')
            sleep(1.5)

            sel = Selector(text=self.driver.page_source)

            posts = get_posts(sel)
            if not posts:
                break

            last_post = posts[-1]

            published_date = get_published_date(last_post)
            published_date_datetime = datetime.fromtimestamp(int(published_date))
            days_ago = (datetime.now() - published_date_datetime).days
            if days_ago > self.days:
                break

        sleep(1)
        sel = Selector(text=self.driver.page_source)

        posts = get_posts(sel)
        for post in posts:
            yield self.parse_post(post, response)

    def parse_post(self, post, response):
        content_html = post.xpath('.//p').extract()
        content = self.strip_content_html(content_html)

        published_date = get_published_date(post)

        images = post.xpath('.//a/@data-ploi').extract()
        images = images + post.xpath('.//div[@class="mtm"]//img/@src').extract()
        images = set(images)

        if post.xpath('.//video').extract():
            videos = [
                response.urljoin(url)
                for url in post.xpath('.//a/@ajaxify').extract()
            ]
        else:
            videos = []

        shares_number, likes = 0, 0
        shares = post.xpath('.//a[@class="UFIShareLink"]/text()').extract_first()
        if shares:
            shares_number = re.findall(r'\d+', shares)[0]

        likes_text = post.xpath(
            './/div[@class="UFILikeSentenceText"]/span/text()').extract_first()
        if likes_text:
            try:
                like_number = int(re.findall(r'\d+', likes_text)[0])
                like_string_count = len(likes_text.split(','))
                likes = like_number + like_string_count
            except IndexError:
                pass

        return {
            'published_date': published_date,
            'content': content,
            'images': list(images),
            'video': videos,
            'likes': likes,
            'shares': int(shares_number)
        }

    def strip_content_html(self, content_html):
        """
        Remove all html tags from content of article.
        """
        content = '\n '.join(content_html)
        return re.sub(re.compile('<.*?>'), '', content)

    def close(self, reason):
        self.driver.quit()
