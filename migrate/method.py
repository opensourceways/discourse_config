import logging
import time
from typing import Optional

import html2text
import requests


class ArticlePoster:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                          'Chrome/137.0.0.0 Safari/537.36',
        })
        self._session.headers.update({'Referer': 'https://www.hiascend.com'})

        self.token = "d515e3f18974e6d150d406082c870c003cf213c6eef293f2acdcc5ab6315c63f"
        self.token = "ab4dc320f1520c46d111c3abedfabd0958fc40b2ebf21f61d5f469805cb8dbab"
        self.base_url = "https://discuss.mindspore.cn"
        self.community_id = ""
        self.category_ids = {
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

    def get_list(self, topic_id: str) -> list:
        """
        获取话题链接列表中的数字ID

        Args:
            topic_id: 地图文章ID

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
                with open('test.txt', 'w', encoding='utf-8') as f:
                    f.write(html_content)

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

                h.bypass_tables = False
                markdown = h.handle(html_content)

                return {
                    "title": title,
                    "markdown": markdown,
                }

            except Exception as e:
                self.logger.error(f"HTML to Markdown conversion failed: {str(e)}")
                return {
                    "title": title,
                    "markdown": html_content,  # 降级返回原始HTML
                }

        except Exception as e:
            self.logger.error(f"Unexpected error processing topic {topic_id}: {str(e)}", exc_info=True)
            return {}

    def post(self, topic_id:str, category_id:int, **kwargs) -> dict:

        content_data = self._get_topic_content(topic_id)
        posted_articles = []

        if not content_data or not content_data.get("markdown"):
            logging.warning(f"Skipping empty content for topic {topic_id}")

        api_url = f"{self.base_url}/posts.json"
        headers = {
            "Content-Type": "application/json",
            "Api-Key": self.token,
            "Api-Username": self.community_id
        }

        # 直接从返回数据中获取标题
        title = content_data.get("title", "")  # 限制标题长度

        data = {
            "title": title,
            "raw": content_data["markdown"],
            "category": category_id
        }

        # 4. 发送POST请求
        try:
            response = requests.post(
                api_url,
                headers=headers,
                json=data,
                timeout=30
            )
            print(response)
            response.raise_for_status()

            if response.status_code == 200:
                response_json = response.json()
                logging.info(f"Successfully posted topic {topic_id} as '{title}'")

                # 构建文章链接
                topic_url = f"{self.base_url}/t/{response_json.get('topic_slug', 'topic')}/{response_json['topic_id']}"

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
