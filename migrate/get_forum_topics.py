from datetime import datetime
import logging
import time
from typing import Optional, List, Dict

import pandas as pd
import requests
import html2text
import json
import logging
import requests
import time

category_ids = {
    "问题求助 Help": 4,
    "经验分享 Tech Blogs": 15,
    "活动公告 Activities": 14,
    "动态图 PyNative": 33,
    "易用性 Usability": 34,
    "异构融合 Heterogeneous Fusion": 35,
    "大模型推理部署 LLM Inference Serving": 36,
    "科学计算 Science": 37,
    "端侧部署 Lite": 38,
    "大模型套件 MindSpore Transformers": 39,
    "量子计算 Quantum": 40,
    "建议与反馈 Feedback": 2,
    "Staff": 3,
    "安装部署 Installation": 5,
    "模型开发 Model Development": 6,
    "数据处理 Dataset": 7,
}


token = ""
base_url = "https://discuss.mindspore.cn"


# token = ""
# base_url = "https://discourse.openfuyao.test.osinfra.cn"

class CANNForumCollector():
    SECTION_ID = "01114178463500214017"
    TOPIC_CLASS_ID = "0697178463509282006"

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
        })
        self._session.headers.update({'Referer': 'https://www.hiascend.com'})
        # Initialize logger
        self.logger = logging.getLogger(__name__)

    def _request(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        try:
            response = self._session.request(
                method,
                url,
                timeout=30,
                **kwargs
            )
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            return None

    @property
    def source_name(self) -> str:
        return "forum"

    def collect(self, start_date: datetime):
        all_data = []
        first_page_response = self._fetch_page(self.SECTION_ID, 1)
        if not first_page_response:
            self.logger.error(f"获取第一页数据失败")
            return
        self.logger.info(self._session.headers)
        first_page_data = first_page_response.json().get('data', {})
        total_count = first_page_data.get('totalCount', 0)
        total_pages = (total_count + 99) // 100
        self.logger.info(f"总数据量: {total_count} 条，共 {total_pages} 页")
        all_data.extend(self._process_page(first_page_data, start_date))

        for page in range(2, total_pages + 1):
            self.logger.info(f"正在获取第 {page}/{total_pages} 页...")
            if page_data := self._fetch_page(self.SECTION_ID, page):
                all_data.extend(self._process_page(page_data.json().get('data', {}), start_date))
            time.sleep(0.5)  # 防止请求过于频繁被封禁
        self.logger.info(f"共有 {len(all_data)} 个主题")
        return all_data

    def _fetch_page(self, section_id: str, page: int) -> Optional[requests.Response]:
        return self._request(
            'GET',
            "https://www.hiascend.com/ascendgateway/ascendservice/devCenter/bbs/servlet/get-topic-list",
            params={
                'sectionId': section_id,
                'topicClassId': self.TOPIC_CLASS_ID,
                'filterCondition': '1',
                'pageIndex': page,
                'pageSize': 100,
            }
        )

    def _process_page(self, page_data: dict, start_date: datetime) -> List[Dict]:
        print(len(page_data.get('resultList', [])))
        return [self._parse_topic(t) for t in page_data.get('resultList', [])]
        # return [self._parse_topic(t) for t in page_data.get('resultList', [])
        #         if self._is_valid_time(t['lastPostTime'], start_date)]

    def _is_valid_time(self, create_time: str, start_date: datetime) -> bool:  # 这里参数类型也改为datetime类
        return start_date <= datetime.strptime(create_time, "%Y%m%d%H%M%S")  # 使用正确的datetime类

    def _is_closed(self, topic: dict) -> bool:
        return topic.get('solved', '') == 1

    def _parse_topic(self, topic: dict) -> Dict:
        topicId = topic['topicId']
        print(datetime.strptime(topic['createTime'], "%Y%m%d%H%M%S"))
        return {
            'id': topicId,
            'title': topic['title'],
            'url': f'https://www.hiascend.com/forum/thread-{topicId}-1-1.html',
            'body': self._get_topic_content(topicId).get("markdown",""),
            'created_at': datetime.strptime(topic['createTime'], "%Y%m%d%H%M%S"),
            'updated_at': datetime.strptime(topic['lastPostTime'], "%Y%m%d%H%M%S"),
            'type': 'forum',
            'state': 'closed' if self._is_closed(topic) else 'open',
        }

    def get_list(self, topic_id: str) -> list:
        """
        获取话题链接列表中的数字ID

        Args:
            topic_id: 话题ID

        Returns:
            包含所有href最后数字ID的列表（失败时返回空列表）
        """
        response = self._request(
            'GET',
            "https://www.hiascend.com/ascendgateway/ascendservice/devCenter/bbs/servlet/get-topic-detail",
            params={'topicId': topic_id}
        )

        if not response or response.status_code != 200:
            self.logger.error(f"Failed to fetch topic list. Status: {getattr(response, 'status_code', 'NO_RESPONSE')}")
            return []

        try:
            href_info_list = response.json().get('data', {}).get('result', {}).get('hrefInfoList', [])
            # 提取所有href链接最后的数字部分
            ids = []
            for item in href_info_list:
                href = item.get('href', '')
                if href:
                    # 提取URL最后一部分的数字
                    last_part = href.split('/')[-1]
                    if last_part.isdigit():  # 确保是纯数字
                        ids.append(last_part)
            return ids
        except (AttributeError, ValueError, KeyError) as e:
            self.logger.error(f"Failed to parse topic list: {str(e)}")
            return []

    def _get_topic_content(self, topic_id: str) -> dict:
        """
        获取话题内容并转换为Markdown格式

        Args:
            topic_id: 话题ID

        Returns:
            包含markdown内容和title的字典（失败时返回空字典）
            {
                "markdown": str,  # 转换后的Markdown内容
                "title": str      # 话题标题
            }
        """
        try:
            # 1. 请求API获取原始数据
            response = self._request(
                'GET',
                "https://www.hiascend.com/ascendgateway/ascendservice/devCenter/bbs/servlet/get-topic-detail",
                params={'topicId': topic_id}
            )

            if not response or response.status_code != 200:
                self.logger.error(
                    f"Failed to fetch topic {topic_id}. Status: {getattr(response, 'status_code', 'NO_RESPONSE')}")
                return {}

            # 2. 解析JSON数据
            try:
                data = response.json().get('data', {}).get('result', {})
                title = data.get('title', '')
                html_content = data.get('content', '')
                if not html_content:
                    self.logger.warning(f"Empty content in topic {topic_id}")
                    return {"markdown": "", "title": title}
            except (AttributeError, ValueError) as e:
                self.logger.error(f"JSON parse failed for topic {topic_id}: {str(e)}")
                return {}

            # 3. 替换动态链接（hrefInfoList）
            href_info_list = data.get('hrefInfoList', [])
            for idx, href_info in enumerate(href_info_list):
                cid = f"cid:link_{idx}"
                href = href_info.get('href', '')
                if not (cid and href):
                    continue

                html_content = html_content.replace(f'href="{cid}"', f'href="{href}"')
                html_content = html_content.replace(cid, href)
                self.logger.debug(f"Replaced link placeholder {cid} -> {href}")

            # 4. 替换动态图片（uploadInfoList）
            upload_info_list = data.get('uploadInfoList', [])
            for idx, upload_info in enumerate(upload_info_list):
                cid = f"cid:pic_{idx}"
                file_path = upload_info.get('filePath', '')
                if not (cid and file_path):
                    continue

                html_content = html_content.replace(f'src="{cid}"', f'src="{file_path}"')
                self.logger.debug(f"Replaced image placeholder {cid} -> {file_path}")

            # 5. HTML转Markdown
            try:
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.escape_all = True  # 转义特殊字符
                h.body_width = 0  # 禁用自动换行

                # 自定义处理（示例：保留表格格式）
                h.bypass_tables = False

                markdown = h.handle(html_content)

                # 后处理：清理多余空行
                # markdown = '\n'.join(line for line in markdown.split('\n') if line.strip())
                return {
                    "markdown": markdown,
                    "title": title
                }

            except Exception as e:
                self.logger.error(f"HTML to Markdown conversion failed: {str(e)}")
                return {
                    "markdown": html_content,  # 降级返回原始HTML
                    "title": title
                }

        except Exception as e:
            self.logger.error(f"Unexpected error processing topic {topic_id}: {str(e)}", exc_info=True)
            return {}


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    collector = CANNForumCollector()

    # 初始化结果列表
    posted_articles = []

    # 1. 获取文章列表
    topic_list = collector.get_list("0229108045633055169")
    print(topic_list)
    if not topic_list:
        logging.error("Failed to get topic list")
        exit(1)

    # 2. 取前3篇文章
    for i, topic_id in enumerate(topic_list[0:4], start=1):
        logging.info(f"Processing article {i}/{min(3, len(topic_list))} - ID: {topic_id}")

        # 获取文章内容（现在返回的是字典）
        content_data = collector._get_topic_content(topic_id)
        print(content_data)
        if not content_data or not content_data.get("markdown"):
            logging.warning(f"Skipping empty content for topic {topic_id}")
            continue

        # 3. 准备API请求数据
        api_url = f"{base_url}/posts.json"
        headers = {
            "Content-Type": "application/json",
            "Api-Key": token,
            "Api-Username": "Wenl4ng"
        }

        # 直接从返回数据中获取标题
        title = content_data.get("title", f"Untitled Post {i}")  # 限制标题长度

        data = {
            "title": title,
            "raw": content_data["markdown"],
            "category": 17
        }

        # 4. 发送POST请求
        try:
            response = requests.post(
                api_url,
                headers=headers,
                json=data,
                timeout=30
            )
            print(response.json())
            response.raise_for_status()

            if response.status_code == 200:
                response_json = response.json()
                logging.info(f"Successfully posted topic {topic_id} as '{title}'")

                # 构建文章链接
                topic_url = f"{base_url}/t/{response_json.get('topic_slug', 'topic')}/{response_json['topic_id']}"

                # 添加到结果列表
                posted_articles.append({
                    "title": title,
                    "url": topic_url
                })

            else:
                logging.error(f"Failed to post topic {topic_id}. Status: {response.status_code}")
                logging.debug(f"Response: {response.text}")

        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed for topic {topic_id}: {str(e)}")

        # 避免频繁请求
        time.sleep(5)

    # 将结果保存到文件
    if posted_articles:
        try:
            with open('2.txt', 'w', encoding='utf-8') as f:
                # 转换为序号:内容的格式
                result = {str(i + 1): article for i, article in enumerate(posted_articles)}
                json.dump(result, f, ensure_ascii=False, indent=2)
            logging.info(f"Successfully saved {len(posted_articles)} articles to 1.txt")
        except IOError as e:
            logging.error(f"Failed to save results to file: {str(e)}")