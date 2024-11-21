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
from langchain.chains.llm import LLMChain
from tenacity import retry, stop_after_attempt, wait_exponential
from langchain_core.output_parsers import StrOutputParser

# TODO 这模块导入不知道有没有问题
# TODO 该文件应该只提供newscollector，不应该提供语音播报，语音播报应该在Function中实现（newscollector+GPTSoVits）
# 需要重构下
# 单独测试模块没有问题
# from Models.TTS.GPTSoVits.GPTSoVits_class import GPTSoVitsAgent

# 新闻类别和来源配置
NEWS_CATEGORIES = ['科技', '军事', '医药', '教育', '金融', '政治', '其他']
SOURCES_SOUHU = [
    'https://www.sohu.com/xchannel/tag?key=新闻-国际',
]
SOURCES_TENCENT = []
MAX_NEWS_COUNT = 20
WAIT_TIMEOUT = 10 

"""
    NewsCollector从SOURCES搜集新闻（暂时为搜狐）
    返回一个List[Tuple[str,str,str,str]]
    即List[Tuple[新闻类型,发布时间,新闻正文,新闻链接]]
"""

class NewsCollector:
    def __init__(self, 
                 model: str = 'llama3.2', 
                 temperature: float = 0.0, 
                 batch_size: int = 5
                 ) -> None:
        # 初始化新闻收集器，设置模型、温度和批处理大小
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        if temperature < 0 or temperature > 1:
            raise ValueError("temperature must be between 0 and 1")
        
        self.llm = ChatOllama(model=model, temperature=temperature)
        self._setup_chrome_driver()  # 设置Chrome驱动
        self._setup_chains()  # 设置LLM链
        self.min_delay = 2  # 最小延迟秒数
        self.max_delay = 5  # 最大延迟秒数
        self.cookies = self._load_cookies()  # 从文件或数据库加载Cookie
        self.batch_size = batch_size  # 每批处理的新闻数量
        # self.GPTSoVitsAgent = GPTSoVitsAgent()  # 初始化语音播报代理

    def _setup_chrome_driver(self):
        """设置Chrome驱动相关配置"""
        self.chrome_options = Options()
        self.chrome_options.add_argument("--headless")  # 无头模式
        self.chrome_options.add_argument("--no-sandbox")
        self.chrome_options.add_argument("--disable-dev-shm-usage")
        
        # 添加随机User-Agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        ]
        self.chrome_options.add_argument(f'user-agent={random.choice(user_agents)}')
        self.service = Service('/usr/bin/chromedriver')  # 指定ChromeDriver路径

    def _setup_chains(self):
        """设置LLM链"""
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
        
        # 创建分类和总结链
        self.classification_chain = classification_prompt | self.llm | StrOutputParser()
        self.summarization_chain = summarization_prompt | self.llm | StrOutputParser()
        self.correct_chain = corrected_prompt | self.llm | StrOutputParser()

    @contextmanager
    def _get_driver(self):
        """获取Chrome驱动的上下文管理器"""
        driver = webdriver.Chrome(service=self.service, options=self.chrome_options)
        try:
            yield driver
        finally:
            driver.quit()  # 确保驱动关闭

    def _random_delay(self):
        """添加随机延迟"""
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)  # 随机等待一段时间

    def find_news(self, sources: List[str], driver: webdriver.Chrome) -> List[Tuple[str, str]]:
        """
        抓取新闻列表，过滤掉广告
        Args:
            sources(List[str]): 新闻来源链接
            
        Returns:
            List[Tuple[str,str]]: List[Tuple[新闻标题，链接]]
        """
        news_list = []
        ad_keywords = ['特惠', '抢购', '广告', '促销']  # 定义广告关键词
        ad_domains = ['qidian36.com', 'ad.example.com']  # 定义广告域名

        for source in sources:
            try:
                self._random_delay()  # 每次请求前添加随机延迟
                driver.get(source)  # 打开新闻源页面
                WebDriverWait(driver, WAIT_TIMEOUT).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'item-text-content-title'))
                )
                soup = BeautifulSoup(driver.page_source, 'html.parser')

                count = 0
                for item in soup.find_all('div', class_='item-text-content-title'):
                    if count >= MAX_NEWS_COUNT:
                        break
                    title = item.get_text(strip=True)  # 获取新闻标题
                    link_element = item.find_parent('a', href=True)
                    if link_element and re.match(r'^https?:\/\/', link_element['href']):
                        link = link_element['href']
                        # 检查标题和链接是否包含广告关键词或域名
                        if any(keyword in title for keyword in ad_keywords) or \
                                any(domain in link for domain in ad_domains) or \
                                not link.startswith("https://www.sohu.com"):
                            logging.info(f"Skipping potentially unreliable link: {link}")
                            continue  # 跳过广告
                        news_list.append((title, link))  # 添加新闻标题和链接
                        count += 1
            except Exception as e:
                logging.error(f"Error fetching news from {source}: {e}")

        logging.info("抓取的新闻列表:")
        for title, link in news_list:
            logging.info(title)
            logging.info(link)
        return news_list

    def fetch_news_content(self, 
                           news_list: List[Tuple[str, str]],
                           driver: webdriver.Chrome
                           ) -> List[Tuple[str, str, str, str]]:
        """
        分批获取新闻内容
        Args:
            news_list(List[Tuple[str,str]]): List[Tuple[新闻标题，新闻链接]]
        
        Returns:
            List[Tuple[str,str,str,str]]: List[Tuple[新闻标题，发布时间，新闻内容，新闻链接]]
        """
        news_content = []
        for i in range(0, len(news_list), self.batch_size):
            batch = news_list[i:i+self.batch_size]
            for _, link in batch:
                res = self._fetch_news_content_aux(link, driver)
                if res is not None:
                    news_content.append(res)
            # 每批处理完后等待较长时间
            time.sleep(random.uniform(10, 15))
        return news_content

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def _fetch_news_content_aux(self, 
                                news_url: str, driver: webdriver.Chrome
                                ) -> Optional[Tuple[str, str, str, str]]:
        """
        分批获取新闻内容
        Args:
            news_url(str): 新闻链接
            driver(webdriver): chrome webdriver (默认，不用修改)
        
        Returns:
            Optional[Tuple[新闻标题，发布时间，新闻内容，新闻链接]]
        """
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

            # 去除“编辑于”字样并使用正则表达式提取日期
            publish_time_cleaned = re.sub(r'编辑于', '', publish_time).strip()
            date_match = re.search(r'\d{4}-\d{2}-\d{2}', publish_time_cleaned)
            if date_match:
                publish_date = datetime.strptime(date_match.group(), "%Y-%m-%d")
            else:
                logging.error(f"无法解析的日期格式: {publish_time}")
                return None

            if publish_date.date() != datetime.now().date():
                return None  # 只处理当天的新闻

            content_div = soup.find('article', class_='article')
            news_content = self._extract_content(content_div) if content_div else "未找到新闻正文内容"

            return title, publish_time_cleaned, news_content, news_url

        except Exception as e:
            logging.error(f"Error fetching news content from {news_url}: {str(e)}")
            raise  # 重要：让retry装饰器知道需要重试

    def _extract_content(self, content_div) -> str:
        """提取新闻正文内容"""
        news_content = ""
        paragraphs = content_div.find_all(['p', 'div'], recursive=True)
        for paragraph in paragraphs:
            if (paragraph.find('a', href=True) and '返回搜狐' in paragraph.get_text()) or \
               '负责编辑' in paragraph.get_text():
                continue  # 跳过不相关的段落
            news_content += paragraph.get_text(strip=True) + "\n"
        return news_content

    def summarize_news(self, 
                       news_list: List[Tuple[str, str, str, str]]
                       ) -> List[Tuple[str, str, str, str]]:
        """
        对新闻进行分类和总结
        
        Args:
            news_list: List[Tuple[新闻标题，发布时间，新闻内容(总结前)，新闻链接]]
            
        Return:
            List[Tuple[新闻标题，发布时间，新闻内容(总结后)，新闻链接]]
        """
        summarized_news = []
        for _, news_time, news_content, link in news_list:
            # 分类
            classification_result = self.classification_chain.invoke(news_content)
            # 总结
            summary = self.summarization_chain.invoke(news_content)
            if len(summary.split("。")) > 2:
                summary = self.correct_chain.invoke(summary)
            summarized_news.append((classification_result, news_time, summary, link))
        return summarized_news

    def show_news(self, news_list: List[Tuple[str, str, str, str]]):
        """
        展示新闻结果
        
        Args:
            List[Tuple[新闻类型-str,发布时间-str,新闻正文-str,新闻链接-str]]
        
        Return:
            None
        """
        print("当天新闻列表：")
        for category, pubtime, abstract in news_list:
            print(f"[{category}] {pubtime} {abstract}")

    def run(self) -> List[Tuple[str, str, str, str]]:
        """
        运行新闻收集流程
        
        Args:
            None
            
        Returns:
            List[Tuple[新闻类型-str,发布时间-str,新闻正文-str,新闻链接-str]]
        """
        with self._get_driver() as driver:
            self._apply_cookies(driver)  # 应用Cookies
            sources = SOURCES_SOUHU + SOURCES_TENCENT  # 新闻来源
            # 标题 + 链接
            news_list = self.find_news(sources, driver)  # 抓取新闻
            
            news_list = self.fetch_news_content(news_list, driver)  # 获取新闻内容
            summarized_news = self.summarize_news(news_list)  # 分类和总结新闻
            # self.show_news(summarized_news)
            return summarized_news
            # self.broadcast_news(summarized_news)

    # def broadcast_news(self, summarized_news: List[Tuple[str, str, str]]):
    #     """
    #     播报新闻,调用GPTSoVits来语音合成，
    #     现在已弃用
        
    #     Args:
    #         List[Tuple[新闻类型-str,发布时间-str,新闻正文-str]]
        
    #     """
    #     for category, _, content in summarized_news:
    #         res = self.GPTSoVitsAgent.infer_tts_get(content)
    #         logging.info(f"播报新闻：{category} {content}")

    def _load_cookies(self) -> List[dict]:
        """加载Cookie池"""
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
        """应用Cookie到当前会话"""
        if self.cookies:
            for cookie in self.cookies:
                try:
                    # 需要先访问对应域名的页面才能设置cookie
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