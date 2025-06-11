from bs4 import BeautifulSoup
import csv
import json
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import threading
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pymysql


class GitHubCrawler:
    def __init__(self, keyword='python', max_pages=3, threads=2,mysql_config=None):
        self.keyword = keyword  # 搜索关键词
        self.max_pages = max_pages  # 爬取页数
        self.threads = threads  # 使用的线程数
        self.results = []  # 存储结果
        self.lock = threading.Lock()  # 线程锁用于同步写入结果
        self.mysql_config = mysql_config or {
            'host': 'localhost',
            'user': 'root',
            'password': '123456',
            'database': 'github_data'
        }

    def init_driver(self):
        # 初始化无头浏览器
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--disable-web-security')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        return webdriver.Chrome(options=options)

    def extract_description(self, repo_element):
        # 提取仓库描述
        desc_candidates = repo_element.select('span')
        for span in desc_candidates:
            text = span.get_text(strip=True)
            if (text and 15 < len(text) < 200 and '/' not in text and
                not text.endswith('stars') and not text.endswith('star') and
                'updated' not in text.lower()):
                return text
        return ''

    def extract_stars(self, repo_element):
        # 提取 star 数量
        try:
            star_tag = repo_element.select_one('a[href$="/stargazers"]')
            if star_tag:
                stars_text = star_tag.get_text(strip=True).replace(',', '')

                if 'k' in stars_text.lower():
                    return str(int(float(stars_text[:-1]) * 1000))
                return str(int(stars_text))
        except Exception as e:
            print(f"提取 stars 时异常: {e}")
        return '0'

    def parse_projects(self, driver):
        # 解析当前页面的所有仓库项目信息
        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-testid="results-list"]'))
            )
            time.sleep(2)
        except:
            return []

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        repo_items = soup.select('[data-testid="results-list"] > div')
        projects = []

        for repo in repo_items:
            try:
                title_elem = repo.select_one('a[href*="/"]')
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                url = title_elem['href']
                if not url.startswith('http'):
                    url = 'https://github.com' + url
                desc = self.extract_description(repo)
                stars = self.extract_stars(repo)
                projects.append({
                    'title': title,
                    'url': url,
                    'description': desc,
                    'stars': stars
                })
            except:
                continue
        return projects

    def crawl_page(self, page_num):
        # 爬取指定页数的仓库列表
        url = f"https://github.com/search?q={self.keyword}&type=repositories&p={page_num}"
        driver = self.init_driver()
        try:
            driver.get(url)
            time.sleep(3)
            projects = self.parse_projects(driver)
            with self.lock:
                self.results.extend(projects)
        finally:
            driver.quit()

    def run(self):
        # 主运行函数，使用多线程爬取多个页面
        print(f"正在爬取关键词 '{self.keyword}'，共 {self.max_pages} 页，线程数: {self.threads}")
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            for i in range(1, self.max_pages + 1):
                executor.submit(self.crawl_page, i)
        print(f"完成，共获取 {len(self.results)} 个项目")
        self.save_all()
        return self.results

    def save_all(self):
        # 同时保存为 txt，csv，json，以及mysql数据库
        timestamp = int(time.time())
        base = f"github_{self.keyword}_{timestamp}"
        self.save_txt(base + ".txt")
        self.save_csv(base + ".csv")
        self.save_json(base + ".json")
        self.save_mysql()

    def save_mysql(self):
        try:
            conn = pymysql.connect(
                host=self.mysql_config['host'],
                user=self.mysql_config['user'],
                password=self.mysql_config['password'],
                database=self.mysql_config['database'],
                charset='utf8mb4'
            )
            cursor = conn.cursor()
            # 创建表（如果不存在）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS github_projects (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255),
                    url TEXT,
                    description TEXT,
                    stars INT
                );
            """)
            # 插入数据
            for item in self.results:
                try:
                    cursor.execute("""
                        INSERT INTO github_projects (title, url, description, stars)
                        VALUES (%s, %s, %s, %s);
                    """, (
                        item['title'],
                        item['url'],
                        item['description'],
                        int(item['stars']) if item['stars'].isdigit() else 0
                    ))
                except Exception as e:
                    print(f"[!] 插入失败: {e} -> {item}")
            conn.commit()
            print("MySQL 保存成功")
        except Exception as e:
            print(f"[!] MySQL 错误: {e}")
        finally:
            try:
                conn.close()
            except:
                pass
    def save_txt(self, filename):
        # 保存为 TXT 格式
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"GitHub 项目搜索 - 关键词: {self.keyword}\n")
                f.write(f"共获取 {len(self.results)} 个项目\n")
                f.write("=" * 50 + "\n\n")
                for i, proj in enumerate(self.results, 1):
                    f.write(f"{i}. {proj['title']} ({proj['stars']} stars)\n")
                    f.write(f"URL: {proj['url']}\n")
                    if proj['description']:
                        f.write(f"描述: {proj['description']}\n")
                    f.write("\n")
            print(f"TXT 已保存: {filename}")
        except Exception as e:
            print(f"TXT 保存失败: {e}")

    def save_csv(self, filename):
        try:
            with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=['title', 'url', 'description', 'stars'],
                    quoting=csv.QUOTE_ALL
                )
                writer.writeheader()
                writer.writerows(self.results)
            print(f"CSV 已保存：{filename}")
        except Exception as e:
            print(f"CSV 保存失败：{e}")

    def save_json(self, filename):
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            print(f"JSON 已保存: {filename}")
        except Exception as e:
            print(f"JSON 保存失败: {e}")

if __name__ == "__main__":
    print("== GitHub 项目爬虫 ==")
    keyword = input("请输入关键词（默认 python）: ").strip() or 'python'
    pages = int(input("请输入要爬取页数（默认 3）: ").strip() or 3)
    threads = int(input("线程数（默认 2）: ").strip() or 2)
    crawler = GitHubCrawler(keyword, pages, threads)
    results = crawler.run()

    if results:
        for i, r in enumerate(results[:10], 1):
            print(f"{i}. {r['title']} ({r['stars']})")
            print(f" {r['url']}")
            print(f" {r['description'] or '[无描述]'}\n")
