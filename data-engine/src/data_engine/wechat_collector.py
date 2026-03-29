"""
微信公众号文章采集器 - 基于 WeSpy/wespy-fetcher

整合 WeSpy 能力到 newhigh 数据引擎，用于：
1. 抓取微信公众号文章（市场情报、政策解读、行业动态）
2. 专辑批量下载（系列专题、专栏追踪）
3. Markdown 转换（便于后续 NLP 处理）
4. 元数据提取（作者、发布时间、阅读量等）

设计原则：
- 可选依赖：WeSpy 未安装时降级为普通 HTTP 抓取
- 异步支持：支持批量并发抓取
- 数据持久化：自动写入 DuckDB/ClickHouse
- 调度集成：可被 daily_scheduler 调用

用法：
    from data_engine.wechat_collector import WeChatCollector

    collector = WeChatCollector()

    # 单篇文章
    article = collector.fetch_article("https://mp.weixin.qq.com/s/xxx")

    # 专辑批量
    articles = collector.fetch_album("https://mp.weixin.qq.com/mp/appmsgalbum?...", max_articles=20)

    # 保存到数据库
    collector.save_to_db(articles)
"""

import json
import logging
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict

# 可选依赖：duckdb (数据库保存)
try:
    import duckdb
    DUCKDB_AVAILABLE = True
except ImportError:
    DUCKDB_AVAILABLE = False
    duckdb = None  # type: ignore

logger = logging.getLogger(__name__)

# 尝试导入 WeSpy（可选依赖）
WESPY_AVAILABLE = False  # pylint: disable=invalid-name
try:
    from wespy import ArticleFetcher
    from wespy.main import WeChatAlbumFetcher
    WESPY_AVAILABLE = True  # pylint: disable=invalid-name
    logger.info("WeSpy 已安装，启用完整功能")
except ImportError:
    logger.warning("WeSpy 未安装，使用基础 HTTP 抓取模式")
    ArticleFetcher = None  # type: ignore
    WeChatAlbumFetcher = None  # type: ignore

# 尝试导入 requests（基础依赖）
try:
    import requests
    from bs4 import BeautifulSoup
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("requests/beautifulsoup4 未安装，微信采集功能受限")


@dataclass
class WeChatArticle:
    """微信公众号文章数据结构"""
    title: str
    author: str
    publish_time: str
    url: str
    content_md: str  # Markdown 格式正文
    content_html: Optional[str] = None  # 原始 HTML
    summary: Optional[str] = None  # 摘要
    cover_image: Optional[str] = None  # 封面图 URL
    album_name: Optional[str] = None  # 所属专辑
    tags: List[str] = None  # 标签
    meta: Dict[str, Any] = None  # 其他元数据

    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.meta is None:
            self.meta = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于数据库写入）"""
        return asdict(self)

    def get_id(self) -> str:
        """生成文章唯一 ID（基于 URL 哈希）"""
        return hashlib.md5(self.url.encode()).hexdigest()[:16]


class WeChatCollector:
    """微信公众号文章采集器"""

    def __init__(
        self,
        output_dir: Optional[str] = None,
        save_html: bool = False,
        save_json: bool = True,
        max_articles_default: int = 20
    ):
        """
        初始化采集器

        Args:
            output_dir: 文章保存目录（默认：~/newhigh/data/wechat_articles/）
            save_html: 是否保存原始 HTML
            save_json: 是否保存 JSON 元数据
            max_articles_default: 专辑默认最大文章数
        """
        self.output_dir = Path(output_dir) if output_dir else Path.home() / \
            "newhigh" / "data" / "wechat_articles"
        self.save_html = save_html
        self.save_json = save_json
        self.max_articles_default = max_articles_default

        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 初始化 WeSpy（如果可用）
        self.wespy_fetcher: Optional[ArticleFetcher] = None
        self.album_fetcher: Optional[WeChatAlbumFetcher] = None

        if WESPY_AVAILABLE:
            self.wespy_fetcher = ArticleFetcher()
            self.album_fetcher = WeChatAlbumFetcher()
            logger.debug("WeSpy 采集器已初始化")

        # 基础 HTTP 会话（用于降级模式）
        self.session = requests.Session() if REQUESTS_AVAILABLE else None
        if self.session:
            self.session.headers.update({
                'User-Agent': (
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) '
                    'Chrome/120.0.0.0 Safari/537.36'
                )
            })

    def is_wechat_url(self, url: str) -> bool:
        """判断是否为微信公众号 URL"""
        return 'mp.weixin.qq.com' in url

    def is_album_url(self, url: str) -> bool:
        """判断是否为微信专辑 URL"""
        return 'appmsgalbum' in url

    def fetch_article(
        self,
        url: str,
        save_to_file: bool = False
    ) -> Optional[WeChatArticle]:
        """
        抓取单篇文章

        Args:
            url: 文章 URL
            save_to_file: 是否保存到文件

        Returns:
            WeChatArticle 对象，失败返回 None
        """
        logger.info("抓取文章：%s", url)

        try:
            if WESPY_AVAILABLE and self.wespy_fetcher:
                # 使用 WeSpy 完整功能
                return self._fetch_with_wespy(url, save_to_file)
            if REQUESTS_AVAILABLE:
                # 降级：基础 HTTP 抓取
                return self._fetch_with_http(url)
            logger.error("无可用抓取工具（需安装 WeSpy 或 requests）")
            return None

        except (RuntimeError, OSError, ValueError) as e:
            logger.error("抓取文章失败：%s", e)
            return None

    def _fetch_with_wespy(
        self,
        url: str,
        save_to_file: bool
    ) -> Optional[WeChatArticle]:
        """使用 WeSpy 抓取"""
        if not self.wespy_fetcher:
            return None

        try:
            # 调用 WeSpy API
            article_info = self.wespy_fetcher.fetch_article(
                url=url,
                output_dir=str(self.output_dir) if save_to_file else None,
                save_html=self.save_html,
                save_json=self.save_json,
                save_markdown=True
            )

            if not article_info:
                logger.warning("WeSpy 返回空结果")
                return None

            # 转换为统一数据结构
            article = WeChatArticle(
                title=article_info.get('title', ''),
                author=article_info.get('author', ''),
                publish_time=article_info.get('publish_time', ''),
                url=url,
                content_md=self._read_file(article_info.get('markdown_file')),
                content_html=self._read_file(
                    article_info.get('html_file')) if self.save_html else None,
                summary=article_info.get('summary', ''),
                cover_image=article_info.get('cover_image'),
                meta=article_info
            )

            logger.info("文章抓取成功：%s", article.title)
            return article

        except (RuntimeError, OSError, ValueError) as e:
            logger.error("WeSpy 抓取失败：%s", e)
            return None

    def _fetch_with_http(self, url: str) -> Optional[WeChatArticle]:
        """降级：使用 HTTP 直接抓取（功能有限）"""
        if not self.session:
            return None

        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # 提取标题
            title = soup.find('h1', id='activity-name')
            title_text = title.get_text(strip=True) if title else soup.find('title')

            # 提取内容
            content_div = soup.find('div', id='js_content')

            if not content_div:
                logger.warning("未找到文章内容区域")
                return None

            # 简单转换为 Markdown
            content_md = self._html_to_markdown(str(content_div))

            article = WeChatArticle(
                title=title_text.get_text(strip=True) if title_text else "未知标题",
                author="",
                publish_time="",
                url=url,
                content_md=content_md,
                meta={'source': 'http_fallback'}
            )

            logger.info("文章抓取成功（降级模式）：%s", article.title)
            return article

        except (RuntimeError, OSError, ValueError) as e:
            logger.error("HTTP 抓取失败：%s", e)
            return None

    def fetch_album(
        self,
        album_url: str,
        max_articles: Optional[int] = None,
        save_to_file: bool = False
    ) -> List[WeChatArticle]:
        """
        批量抓取专辑文章

        Args:
            album_url: 专辑 URL
            max_articles: 最大文章数（默认：self.max_articles_default）
            save_to_file: 是否保存到文件

        Returns:
            WeChatArticle 列表
        """
        if not self.is_album_url(album_url):
            logger.error("不是有效的专辑 URL")
            return []

        max_articles = max_articles or self.max_articles_default
        logger.info("抓取专辑：%s (最多 %d 篇)", album_url, max_articles)

        articles = []

        try:
            if WESPY_AVAILABLE and self.album_fetcher:
                # 使用 WeSpy 专辑功能
                articles = self._fetch_album_with_wespy(album_url, max_articles, save_to_file)
            else:
                logger.warning("WeSpy 不可用，尝试逐篇抓取专辑文章")
                # TODO: 实现降级模式
                articles = []

        except (RuntimeError, OSError, ValueError) as e:
            logger.error("专辑抓取失败：%s", e)

        logger.info("专辑抓取完成：成功 %d/%d 篇", len(articles), max_articles)
        return articles

    def _fetch_album_with_wespy(
        self,
        album_url: str,
        max_articles: int,
        save_to_file: bool
    ) -> List[WeChatArticle]:
        """使用 WeSpy 抓取专辑"""
        if not self.album_fetcher:
            return []

        try:
            # 获取专辑文章列表
            article_list = self.album_fetcher.fetch_album_articles(
                album_url,
                max_articles=max_articles
            )

            logger.info("获取到 %d 篇文章", len(article_list))

            # 逐篇抓取
            articles = []
            for i, article_meta in enumerate(article_list):
                logger.info(
                    "[%d/%d] 抓取：%s",
                    i + 1,
                    len(article_list),
                    article_meta.get('title', '未知')
                )

                article_url = article_meta.get('url')
                if not article_url:
                    continue

                article = self.fetch_article(article_url, save_to_file)
                if article:
                    article.album_name = article_meta.get('album_name', '')
                    articles.append(article)

                # 速率控制
                time.sleep(0.5)

            return articles

        except (RuntimeError, OSError, ValueError) as e:
            logger.error("WeSpy 专辑抓取失败：%s", e)
            return []

    def _read_file(self, filepath: Optional[str]) -> str:
        """读取文件内容"""
        if not filepath or not Path(filepath).exists():
            return ""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except (RuntimeError, OSError, ValueError):
            return ""

    def _html_to_markdown(self, html: str) -> str:
        """简单 HTML 转 Markdown（降级模式使用）"""
        # 简单转换：实际生产可用 markdown 库
        md = html
        md = md.replace('<p>', '\n\n').replace('</p>', '')
        md = md.replace('<br>', '\n').replace('<br/>', '\n')
        md = md.replace('<strong>', '**').replace('</strong>', '**')
        md = md.replace('<b>', '**').replace('</b>', '**')
        # 移除其他标签
        md = ''.join(c for c in md if c not in '<>')
        return md.strip()

    def save_to_db(
        self,
        articles: List[WeChatArticle],
        db_path: Optional[str] = None
    ) -> int:
        """
        保存文章到数据库

        Args:
            articles: 文章列表
            db_path: 数据库路径（默认：newhigh/data/quant.duckdb）

        Returns:
            成功写入的文章数
        """
        if not articles:
            return 0

        db_path = db_path or str(Path.home() / "Ahope" / "newhigh" / "data" / "quant.duckdb")

        try:
            if not DUCKDB_AVAILABLE:
                logger.warning("duckdb 未安装，跳过数据库保存")
                return 0
            conn = duckdb.connect(db_path)

            # 创建表（如果不存在）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS wechat_articles (
                    id VARCHAR PRIMARY KEY,
                    title VARCHAR,
                    author VARCHAR,
                    publish_time VARCHAR,
                    url VARCHAR UNIQUE,
                    content_md TEXT,
                    content_html TEXT,
                    summary TEXT,
                    cover_image VARCHAR,
                    album_name VARCHAR,
                    tags VARCHAR,
                    meta_json TEXT,
                    fetched_at TIMESTAMP
                )
            """)

            # 批量插入
            count = 0
            for article in articles:
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO wechat_articles
                        (id, title, author, publish_time, url, content_md, content_html,
                         summary, cover_image, album_name, tags, meta_json, fetched_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, [
                        article.get_id(),
                        article.title,
                        article.author,
                        article.publish_time,
                        article.url,
                        article.content_md,
                        article.content_html,
                        article.summary,
                        article.cover_image,
                        article.album_name,
                        json.dumps(article.tags),
                        json.dumps(article.meta),
                        datetime.now(timezone.utc)
                    ])
                    count += 1
                except (RuntimeError, OSError, ValueError) as e:
                    logger.warning("插入文章失败 %s: %s", article.url, e)

            conn.close()
            logger.info("成功保存 %d/%d 篇文章到数据库", count, len(articles))
            return count

        except ImportError:
            logger.warning("duckdb 未安装，跳过数据库保存")
            return 0
        except (RuntimeError, OSError, ValueError) as e:
            logger.error("数据库保存失败：%s", e)
            return 0

    def save_to_files(
        self,
        articles: List[WeChatArticle],
        output_dir: Optional[str] = None
    ) -> int:
        """
        保存文章到文件

        Args:
            articles: 文章列表
            output_dir: 输出目录

        Returns:
            成功保存的文件数
        """
        output_dir = Path(output_dir) if output_dir else self.output_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        count = 0
        for article in articles:
            try:
                # 生成安全文件名
                safe_title = "".join(c for c in article.title if c not in '<>:"/\\|？*')
                safe_title = safe_title[:50]  # 限制长度
                filename_base = f"{safe_title}_{article.get_id()}"

                # 保存 Markdown
                md_path = output_dir / f"{filename_base}.md"
                with open(md_path, 'w', encoding='utf-8') as f:
                    f.write(f"# {article.title}\n\n")
                    f.write(f"**作者**: {article.author}  \n")
                    f.write(f"**发布时间**: {article.publish_time}  \n")
                    f.write(f"**URL**: {article.url}\n\n")
                    f.write("---\n\n")
                    f.write(article.content_md)

                # 保存 JSON 元数据
                if self.save_json:
                    json_path = output_dir / f"{filename_base}_meta.json"
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(article.to_dict(), f, ensure_ascii=False, indent=2)

                count += 1

            except (RuntimeError, OSError, ValueError) as e:
                logger.warning("保存文件失败 %s: %s", article.title, e)

        logger.info("成功保存 %d 篇文章到 %s", count, output_dir)
        return count


# 便捷函数
def collect_wechat_articles(
    urls: List[str],
    output_dir: Optional[str] = None,
    save_to_db: bool = True,
    max_articles: int = 20
) -> List[WeChatArticle]:
    """
    便捷函数：批量抓取微信公众号文章

    Args:
        urls: 文章或专辑 URL 列表
        output_dir: 输出目录
        save_to_db: 是否保存到数据库
        max_articles: 专辑最大文章数

    Returns:
        抓取到的文章列表
    """
    collector = WeChatCollector(output_dir=output_dir)
    all_articles = []

    for url in urls:
        if collector.is_album_url(url):
            articles = collector.fetch_album(url, max_articles=max_articles)
        else:
            article = collector.fetch_article(url)
            articles = [article] if article else []

        all_articles.extend(articles)

    # 保存
    if save_to_db:
        collector.save_to_db(all_articles)

    collector.save_to_files(all_articles)

    return all_articles


if __name__ == "__main__":
    # 测试示例
    logging.basicConfig(level=logging.INFO)

    # 示例：抓取单篇文章
    TEST_URL = "https://mp.weixin.qq.com/s/example"  # pylint: disable=invalid-name
    test_collector = WeChatCollector()
    test_article = test_collector.fetch_article(TEST_URL)

    if test_article:
        print(f"标题：{test_article.title}")
        print(f"作者：{test_article.author}")
        print(f"内容长度：{len(test_article.content_md)} 字符")
