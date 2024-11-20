import logging
from typing import List, Tuple, Optional
from datetime import datetime
import random
import time
import re
from contextlib import contextmanager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
from langchain_ollama import ChatOllama
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from tenacity import retry, stop_after_attempt, wait_exponential
from langchain_core.output_parsers import StrOutputParser

# TODO 这模块导入不知道有没有问题
# TODO 该文件应该只提供newscollector，不应该提供语音播报，语音播报应该在Function中实现（newscollector+GPTSoVits）
# 需要重构下
# 单独测试模块没有问题
from  Models.TTS.GPTSoVits.GPTSoVits_class import GPTSoVitsAgent

NEWS_CATEGORIES = ['科技', '军事', '医药', '教育', '金融', '政治', '其他']
SOURCES_SOUHU = [
    'https://www.sohu.com/xchannel/tag?key=新闻-国际',
]
SOURCES_TENCENT = []
MAX_NEWS_COUNT = 20
WAIT_TIMEOUT = 10 


class NewsCollector:
    def __init__(self, 
                 model: str = 'llama3.2', 
                 temperature: float = 0.0, 
                 batch_size: int = 5) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        if temperature < 0 or temperature > 1:
            raise ValueError("temperature must be between 0 and 1")
        self.llm = ChatOllama(model=model, temperature=temperature)
        self.setup_chrome_driver()
        self.setup_chains()
        self.min_delay = 2
        self.max_delay = 5
        self.cookies = self._load_cookies()
        self.batch_size = batch_size
        self.GPTSoVitsAgent = GPTSoVitsAgent()

    def setup_chrome_driver(self):
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        ]
        self.chrome_options.add_argument(f'user-agent={random.choice(user_agents)}')
        self.service = Service('/usr/bin/chromedriver')

    def setup_chains(self):
        classification_prompt = PromptTemplate(
            input_variables=["news_content"],
            template=f"请严格遵守以下规则对以下新闻内容进行分类，从提供的分类中选出最符合的一种，并仅回答该类别。\
                    \
                    注意：\
                    1. 你只能输出一个类别词语，且必须从以下列表中选择：{NEWS_CATEGORIES}。\
                    2. 不得输出任何其他内容，包括解释或评论。\
                    3. 如果内容无法明确归类，请选择最接近的类别。\
                    \
                    新闻内容：\
                    {{news_content}}\
                    \
                    新闻结束。请回答：属于哪一个类别？"
        )
        summarization_prompt = PromptTemplate(
            input_variables=["news_content"],
            template="请严格遵守以下规则总结下方新闻内容：\
                        \
                        1. 你只能输出 **一句话**。\
                        2. 严禁针对新闻提供任何建议和意见。\
                        3. 不得回答新闻中的任何问题。\
                        4. 只需概括核心内容，用一句话总结结论或观点。\
                        5. 如不遵守规则，请自行修正，确保输出准确。\
                        6. 严格用不超过100个字完成总结。\
                        7. 不得发表任何个人观点或额外内容。\
                        \
                        新闻内容：\
                        {news_content}\
                        \
                        新闻结束。注意：总结内容不得超过100字，且仅用一句话完成。"
        )
        corrected_prompt = PromptTemplate(
            template="请再次总结，并严格遵守以下规则：只能输出一句话，且不得发表任何个人观点或额外内容。总结："
        )
        # self.classification_chain = LLMChain(llm=self.llm, prompt=classification_prompt)
        # self.summarization_chain = LLMChain(llm=self.llm, prompt=summarization_prompt)

        self.classification_chain =  classification_prompt | self.llm | StrOutputParser()
        self.summarization_chain = summarization_prompt | self.llm |  StrOutputParser()
        self.correct_chain = corrected_prompt | self.llm |  StrOutputParser()

    @contextmanager
    def get_driver(self):
        driver = webdriver.Chrome(service=self.service, options=self.chrome_options)
        try:
            yield driver
        finally:
            driver.quit()

    def _random_delay(self):
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)

    def find_news(self, sources: List[str], driver: webdriver.Chrome) -> List[Tuple[str, str]]:
        news_list = []
        ad_keywords = ['特惠', '抢购', '广告', '促销']
        ad_domains = ['qidian36.com', 'ad.example.com']

        for source in sources:
            try:
                self._random_delay()
                driver.get(source)
                WebDriverWait(driver, WAIT_TIMEOUT).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'item-text-content-title'))
                )
                soup = BeautifulSoup(driver.page_source, 'html.parser')

                count = 0
                for item in soup.find_all('div', class_='item-text-content-title'):
                    if count >= MAX_NEWS_COUNT:
                        break
                    title = item.get_text(strip=True)
                    link_element = item.find_parent('a', href=True)
                    if link_element and re.match(r'^https?:\/\/', link_element['href']):
                        link = link_element['href']
                        if any(keyword in title for keyword in ad_keywords) or \
                                any(domain in link for domain in ad_domains) or \
                                not link.startswith("https://www.sohu.com"):
                            logging.info(f"Skipping potentially unreliable link: {link}")
                            continue
                        news_list.append((title, link))
                        count += 1
            except Exception as e:
                logging.error(f"Error fetching news from {source}: {e}")

        logging.info("抓取的新闻列表:")
        for title, link in news_list:
            logging.info(title)
            logging.info(link)
        return news_list

    def fetch_news_content(self, news_list: List[Tuple[str, str]], driver: webdriver.Chrome) -> List[Tuple[str, str, str]]:
        news_content = []
        for i in range(0, len(news_list), self.batch_size):
            batch = news_list[i:i+self.batch_size]
            for _, link in batch:
                res = self._fetch_news_content_aux(link, driver)
                if res is not None:
                    news_content.append(res)
            time.sleep(random.uniform(10, 15))
        return news_content

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _fetch_news_content_aux(self, news_url: str, driver: webdriver.Chrome) -> Optional[Tuple[str, str, str]]:
        try:
            self._random_delay()
            driver.get(news_url)
            WebDriverWait(driver, WAIT_TIMEOUT).until(
                EC.presence_of_element_located((By.TAG_NAME, 'article'))
            )
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            title_div = soup.find('div', class_='text-title')
            title = title_div.find('h1').get_text(strip=True) if title_div else "未找到标题"

            publish_time_span = soup.find('span', class_='time')
            publish_time = publish_time_span.get_text(strip=True) if publish_time_span else "未找到发布时间"

            publish_time_cleaned = re.sub(r'编辑于', '', publish_time).strip()
            date_match = re.search(r'\d{4}-\d{2}-\d{2}', publish_time_cleaned)
            if date_match:
                publish_date = datetime.strptime(date_match.group(), "%Y-%m-%d")
            else:
                logging.error(f"无法解析的日期格式: {publish_time}")
                return None

            if publish_date.date() != datetime.now().date():
                return None

            content_div = soup.find('article', class_='article')
            news_content = self._extract_content(content_div) if content_div else "未找到新闻正文内容"

            return title, publish_time_cleaned, news_content

        except Exception as e:
            logging.error(f"Error fetching news content from {news_url}: {str(e)}")
            raise

    def _extract_content(self, content_div) -> str:
        news_content = ""
        paragraphs = content_div.find_all(['p', 'div'], recursive=True)
        for paragraph in paragraphs:
            if (paragraph.find('a', href=True) and '返回搜狐' in paragraph.get_text()) or \
               '负责编辑' in paragraph.get_text():
                continue
            news_content += paragraph.get_text(strip=True) + "\n"
        return news_content

    def summarize_news(self, news_list: List[Tuple[str, str, str]]) -> List[Tuple[str, str, str]]:
        summarized_news = []
        for _, news_time, news_content in news_list:
            # 分类
            classification_result = self.classification_chain.invoke(news_content)
            # 总结
            summary = self.summarization_chain.invoke(news_content)
            if len(summary.split("。")) > 2:
                summary = self.correct_chain.invoke(summary)
            summarized_news.append((classification_result, news_time, summary))
        return summarized_news

    def show_news(self, news_list: List[Tuple[str, str, str]]):
        for category, pubtime, abstract in news_list:
            print(f"[{category}] {pubtime} {abstract}")

    def run(self):
        with self.get_driver() as driver:
            self._apply_cookies(driver)
            sources = SOURCES_SOUHU + SOURCES_TENCENT
            news_list = self.find_news(sources, driver)
            news_list = self.fetch_news_content(news_list, driver)
            summarized_news = self.summarize_news(news_list)
            self.show_news(summarized_news)
            self.broadcast_news(summarized_news)

    def broadcast_news(self, summarized_news: List[Tuple[str, str, str]]):
        for category, _, content in summarized_news:
            res = self.GPTSoVitsAgent.infer_tts_get(content)
            logging.info(f"播报新闻：{category} {content}")

    def _load_cookies(self) -> List[dict]:
        cookies = []
        try:
            with open('cookies.txt', 'r') as file:
                for line in file:
                    name, value, domain = line.strip().split(',')
                    cookies.append({
                        'name': name,
                        'value': value,
                        'domain': domain
                    })
        except FileNotFoundError:
            logging.warning("Cookie文件未找到，使用默认Cookie")
        return cookies

    def _apply_cookies(self, driver: webdriver.Chrome) -> None:
        if self.cookies:
            for cookie in self.cookies:
                try:
                    domain = cookie['domain']
                    if domain.startswith('.'):
                        domain = domain[1:]
                    driver.get(f"https://{domain}")
                    driver.add_cookie(cookie)
                except Exception as e:
                    logging.warning(f"Failed to add cookie: {e}") 


def main():
    print("running")
    n = NewsCollector()
    n.run()
    
    
if __name__ == "__main__":
    main()