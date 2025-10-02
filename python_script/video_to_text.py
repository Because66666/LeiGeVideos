from tqdm import tqdm
import asyncio
import logging
import re
from playwright.async_api import async_playwright

# 配置日志记录
logger = logging.getLogger("B站视频字幕提取")
logger.setLevel(logging.INFO)

# 创建控制台处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

# 创建格式化器
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)

# 将处理器添加到日志记录器
logger.addHandler(console_handler)


class VideoSubtitleExtractor:
    def __init__(self, headless=True):
        self.headless = headless

    async def extract_subtitle_content(self, video_urls: list) -> dict[str:dict]:
        """从飞鱼视频页面提取字幕内容，飞鱼：https://www.feiyudo.com/caption/subtitle/bilibili"""
        subtitle_contents: dict = {}
        current_video_url = None
        get_status = asyncio.Event()
        error_flag = False
        sleep_time = 0

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-web-security",
                    "--disable-features=VizDisplayCompositor",
                    "--no-first-run",
                    "--no-zygote",
                    "--autoplay-policy=no-user-gesture-required",
                    "--enable-media-stream",
                    "--use-fake-device-for-media-stream",
                    "--disable-background-timer-throttling",
                    "--disable-backgrounding-occluded-windows",
                    "--disable-renderer-backgrounding",
                    "--disable-ipc-flooding-protection",
                    "--enable-unsafe-webgpu",
                    "--enable-features=VaapiVideoDecoder,VaapiVideoEncoder",
                    "--disable-software-rasterizer",
                    "--enable-accelerated-video-decode",
                    "--enable-accelerated-mjpeg-decode",
                    "--enable-gpu-rasterization",
                ],
            )
            context = await browser.new_context(
                # 添加用户代理和其他配置来模拟真实浏览器
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
                # 启用媒体播放权限
                permissions=["camera", "microphone"],
                # 添加额外的浏览器配置
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate, br",
                    "DNT": "1",
                    "Connection": "keep-alive",
                    "Upgrade-Insecure-Requests": "1",
                },
                # 忽略HTTPS错误
                ignore_https_errors=True,
            )

            # 监听所有响应事件
            async def handle_response(response):
                nonlocal subtitle_contents, current_video_url, error_flag, sleep_time
                # 获取响应所属页面的 URL
                page_url = response.request.url if response.request else ""
                # 检查当前页面的用户 ID
                if f"/api/video/subtitleExtract" in page_url:
                    if (current_video_url is not None) and (
                        current_video_url not in subtitle_contents
                    ):
                        response_json = await response.json()
                        code = response_json.get("code", -1)
                        if code == 200:
                            subtitle_contents[current_video_url] = response_json
                        elif code == 530:
                            logger.error(
                                f"获取字幕异常，视频URL：{current_video_url}，错误码：{code}，响应内容: {response_json}"
                            )

                            sleep_time = 30
                        elif code == 500:
                            logger.error(
                                f"获取字幕异常，视频URL：{current_video_url}，错误码：{code}，响应内容: {response_json}"
                            )
                            error_flag = True
                        else:
                            logger.error(
                                f"获取字幕失败，视频URL：{current_video_url}，错误码：{code}，响应内容: {response_json}"
                            )
                            error_flag = True
                        get_status.set()

            context.on("response", handle_response)
            page = await context.new_page()
            await page.goto(f"https://www.feiyudo.com/caption/subtitle/bilibili")
            await page.wait_for_timeout(100)
            input_element = page.get_by_role(
                "textbox", name="请将链接粘贴到这里，并点击提取按钮"
            )
            click_button = page.get_by_role("button", name="提取")
            for video_url in tqdm(video_urls, desc="提取字幕"):
                current_video_url = video_url
                await input_element.fill(video_url)
                await click_button.click()
                await get_status.wait()
                if error_flag:
                    break
                if sleep_time > 0:
                    await page.wait_for_timeout(sleep_time * 1000)
                    sleep_time = 0
                get_status.clear()
                await input_element.clear()

        return subtitle_contents

    def extract_text_from_subtitle(
        self, subtitle_data: dict[str:dict]
    ) -> dict[str:str]:
        """从字幕数据中提取文本内容"""
        full_text_dict = {}
        for video_url, subtitle_rawdict in subtitle_data.items():
            full_text = ""
            # 正则表达式：排除序号行（纯数字）、时间行，匹配非空内容行
            pattern = r"(?m)^(?!\d+$)(?!\d+:\d+:\d+,\d+ --> \d+:\d+:\d+,\d+$).*\S.*"
            # 步骤1：从 subtitle_rawdict 中取 "data" 键，默认值为空字典 {}
            data = subtitle_rawdict.get("data", {})

            # 步骤2：从 data 中取 "subtitleItemVoList" 键，默认值为 [{}]（含一个空字典的列表）
            subtitle_list = data.get("subtitleItemVoList", [{}])

            # 步骤3：取列表的第 0 个元素（索引 0）
            if not subtitle_list:
                continue
            first_item = subtitle_list[0]

            # 步骤4：从第 0 个元素中取 "content" 键，默认值为 None
            subtitle_raw = first_item.get("content", None)
            if subtitle_raw is None:
                continue
            # 提取匹配的内容（flags=re.M 启用多行模式）
            result = re.findall(pattern, subtitle_raw, flags=re.M)

            # 打印提取结果
            # 按每5个元素初步分组
            groups = [result[i : i + 5] for i in range(0, len(result), 5)]

            # 若最后一组长度≤3且存在至少两组，则合并到倒数第二组
            if len(groups) > 1 and len(groups[-1]) <= 3:
                groups[-2].extend(groups[-1])  # 合并元素
                groups.pop()  # 移除最后一组

            # 组内用逗号连接，组间用.\n\n连接
            full_text = "。\n\n".join("，".join(group) for group in groups)

            logger.debug(f"提取到字幕文本，总长度: {len(full_text)}")
            full_text_dict[video_url] = full_text
        return full_text_dict

    async def get_video_subtitle_text(self, video_urls: list) -> dict[str:str]:
        """完整流程：获取视频字幕文本"""
        try:
            # 1. 提取字幕URL
            subtitle_contents: dict[str:dict] = await self.extract_subtitle_content(
                video_urls
            )

            if not subtitle_contents:
                logger.warning("未找到字幕内容")
                return {"": ""}

            # 2. 提取文本内容
            text_content_dict: dict[str:str] = self.extract_text_from_subtitle(
                subtitle_contents
            )

            return text_content_dict

        except Exception as e:
            logger.error(f"获取视频字幕失败: {e}")
            import traceback

            traceback.print_exc()
            return ""


# 便捷函数
async def get_bilibili_video_subtitle(video_urls: list, headless=True) -> dict[str:str]:
    """便捷函数：获取B站视频字幕

    Args:
        video_url: B站视频URL
        headless: 是否无头模式（默认True）

    Returns:
        dict[str:str]: 视频URL到字幕文本内容的映射
    """
    extractor = VideoSubtitleExtractor(headless=headless)
    return await extractor.get_video_subtitle_text(video_urls)


if __name__ == "__main__":

    async def main():
        # 测试代码
        video_url = [
            "https://www.bilibili.com/video/BV1ikHjz5EVP/",
            "https://www.bilibili.com/video/BV1t5HxzsEsx",
        ]
        subtitle_text_dict = await get_bilibili_video_subtitle(
            video_url, headless=False
        )
        if subtitle_text_dict:
            print("\n=== 字幕内容 ===")
            for video_url, subtitle_text in subtitle_text_dict.items():
                print(f"{video_url}:\n {subtitle_text}")
        else:
            print("未获取到字幕内容")

    asyncio.run(main())
