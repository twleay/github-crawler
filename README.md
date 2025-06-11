# github-crawler
一个非常简单的爬取github项目基本信息的python脚本（学生版）
（Spider-a是最初版本，非常简陋，可以忽略）
（学生自己测试用）
# GitHub 项目爬虫

一个基于 Selenium + BeautifulSoup 的 GitHub 仓库信息爬虫，支持关键字搜索，结果可保存至本地文件和 MySQL 数据库。

## 使用方法

运行程序后，根据提示输入：

- 搜索关键词（默认：python）
- 爬取页数（默认：3）
- 线程数（默认：2）

程序会自动开始爬取并保存结果。

## 环境依赖

- Python 3.7 及以上
- Chrome 浏览器及对应版本的 chromedriver（需添加至系统 PATH）

### 安装依赖：

```bash
pip install selenium beautifulsoup4 pymysql
MySQL 表结构
程序会自动创建如下数据表：

sql
复制
编辑
CREATE TABLE github_projects (
  id INT AUTO_INCREMENT PRIMARY KEY,
  title VARCHAR(255),
  url TEXT,
  description TEXT,
  stars INT
);
请确保你已创建好数据库，并在代码中正确配置连接信息。

注意事项
设置合理的线程数和爬取页数，避免触发 GitHub 的反爬机制

确保 chromedriver 与 Chrome 浏览器版本一致

如遇写入 MySQL 失败，请检查数据库连接、权限及数据格式
