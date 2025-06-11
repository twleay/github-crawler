import requests
import time
import csv
import json
from bs4 import BeautifulSoup


class GitHubSpider:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        self.projects = []

    def parse_number(self, text):
        #解析数字（处理k, m等单位）
        try:
            text = text.lower().strip()
            if 'k' in text:
                return int(float(text.replace('k', '')) * 1000)
            elif 'm' in text:
                return int(float(text.replace('m', '')) * 1000000)
            return int(text)
        except:
            return 0

    def crawl(self, keyword="python", pages=2):
        #爬取项目
        for page in range(1, pages + 1):
            url = f"https://github.com/search?q={keyword}&type=repositories&p={page}"

            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                if response.status_code != 200:
                    print(f"第{page}页请求失败，状态码: {response.status_code}")
                    continue

                soup = BeautifulSoup(response.text, 'html.parser')
                items = soup.select('div[data-testid="results-list"] > div')

                for item in items:
                    try:
                        title_link = item.select_one('h3 a')
                        if not title_link:
                            continue

                        name = title_link.get_text(strip=True)
                        url = 'https://github.com' + title_link.get('href', '')

                        desc = item.select_one('p')
                        description = desc.get_text(strip=True) if desc else ""

                        stars_elem = item.select_one('a[href*="/stargazers"]')
                        stars = self.parse_number(stars_elem.get_text()) if stars_elem else 0

                        time_elem = item.select_one('relative-time')
                        updated_at = time_elem.get('datetime', '') if time_elem else ''

                        self.projects.append({
                            'name': name,
                            'url': url,
                            'description': description,
                            'stars': stars,
                            'updated_at': updated_at
                        })

                    except:
                        continue

                print(f"第{page}页完成")
                time.sleep(2)

            except Exception as e:
                print(f"第{page}页失败: {e}")

    def save_csv(self, filename="github_projects.csv"):
        #保存为CSV
        if not self.projects:
            return

        with open(filename, 'w', newline='', encoding='utf-8-sig') as f:
            writer = csv.DictWriter(f, fieldnames=['name', 'url', 'description', 'stars', 'updated_at'])
            writer.writeheader()
            writer.writerows(self.projects)
        print(f"已保存{len(self.projects)}个项目到 {filename}")

    def save_json(self, filename="github_projects.json"):
        #保存为JSON
        if not self.projects:
            return

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.projects, f, ensure_ascii=False, indent=2)
        print(f"已保存{len(self.projects)}个项目到 {filename}")


if __name__ == "__main__":
    spider = GitHubSpider()

    keyword = input("搜索关键词 (默认: python): ").strip() or "python"
    pages = input("爬取页数 (默认: 2): ").strip()
    pages = int(pages) if pages.isdigit() and int(pages) > 0 else 2

    print(f"\n开始爬取关键词 '{keyword}' 的项目，共{pages}页...")

    spider.crawl(keyword, pages)
    spider.save_csv()
    spider.save_json()