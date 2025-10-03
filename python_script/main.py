import os
import time
import ast
import asyncio
from playwright.async_api import async_playwright
from video_to_text import get_bilibili_video_subtitle
from save_md import generate_full_md, save_md_file

# 设置响应文件保存路径
OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "src", "content", "posts"
)

# 设置是否无头浏览器
HEADLESS = True


async def get_series_list():
    """获取系列列表，全部内容"""
    user_responses: list[dict] = []
    got_urls = set()
    get_signal = asyncio.Event()
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=HEADLESS,
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
            nonlocal user_responses, got_urls, get_signal
            # 获取响应所属页面的 URL
            page_url = response.request.url if response.request else ""
            # 检查当前页面的用户 ID
            if f"api.bilibili.com/x/polymer/web-space/seasons_archives_lis" in page_url:
                if page_url not in got_urls:
                    got_urls.add(page_url)
                    user_responses.append(await response.json())
                get_signal.set()

        context.on("response", handle_response)

        page = await context.new_page()
        await page.add_init_script(
            """
            // 覆盖无头浏览器的特征检测
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3]});  // 模拟插件
            Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});  // 模拟语言
        """
        )
        await page.goto(
            f"https://space.bilibili.com/268941858/lists/3041938?type=season"
        )
        await get_signal.wait()
        next_page = page.get_by_role("button", name="下一页")
        while await next_page.is_visible():
            await next_page.click()
            await get_signal.wait()
            next_page = page.get_by_role("button", name="下一页")
            get_signal.clear()
        await page.close()
    return user_responses, got_urls


async def get_subtitle(video_urls: list) -> dict[str:str]:
    """获取指定视频的字幕信息"""
    subtitle_text_dict = await get_bilibili_video_subtitle(
        video_urls, headless=HEADLESS
    )
    return subtitle_text_dict


def parse_json_to_videos(json_data: dict) -> dict[str:dict]:
    """将JSON数据解析为视频列表"""
    videos = dict()
    for item in json_data:
        archives = item.get("data", {}).get("archives", [])
        if not archives:
            continue
        for video in archives:
            bvid = video.get("bvid")
            if not bvid:
                continue
            video = {
                "title": video.get("title"),
                "bvid": bvid,
                "cover": video.get("pic"),
                "link": f"https://www.bilibili.com/video/{bvid}",
                "duration": video.get("duration"),  # 时长，单位是秒
                "play": video.get("stat", "{}").get("view", 0),  # 播放量
                "pub_time": time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(video.get("pubdate"))
                ),  # 发布时间，格式化
                "cre_time": time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(video.get("ctime"))
                ),  # 创建时间，格式化
            }
            videos[bvid] = video
    return videos


def get_urls_by_dir() -> list:
    video_urls = []
    try:
        files = os.listdir(OUTPUT_DIR)
        video_urls = [f"{file.split('.')[0]}" for file in files if file.endswith(".md")]
    except Exception as e:
        pass
    return video_urls


def process_videos(videos: list) -> bool:
    """处理视频"""
    try:
        # print(f"处理视频: {video['title']}")
        # 获取字幕信息

        video_urls = [video["link"] for video in videos]
        subtitle_text_dict: dict[str:str] = asyncio.run(get_subtitle(video_urls))
        for video in videos:
            video["subtitle"] = subtitle_text_dict.get(video["link"], "")
            # 保存到指定的markdown文件
            markdown_content, file_name = generate_full_md(video)
            if markdown_content:
                save_md_file(markdown_content, file_name)
                # print(f"已保存到: {file_name}")
        return True
    except Exception as e:
        print(f"处理视频 {video['title']} 时出错: {e}")
        return False


def main():
    # 从文件夹中加载已经获取的数据
    videos_old = get_urls_by_dir()

    # 获取新数据
    print("从API获取系列列表...")
    user_responses, got_urls = asyncio.run(get_series_list())
    videos = parse_json_to_videos(user_responses)

    # 筛选 videos 有而 videos_old 没有的键，并返回对应值
    new_videos = {key: videos[key] for key in videos.keys() - videos_old}
    videos = new_videos

    print(f"准备处理 {len(videos)} 个视频")

    # 获取字幕
    video_list = list(videos.values())
    if not video_list:  # 列表为空
        return
    process_videos(video_list)


def experimental_main():
    # 从文件夹中加载已经获取的数据
    videos_old = get_urls_by_dir()

    # 获取新数据
    print("从API获取系列列表...")
    user_responses, got_urls = asyncio.run(get_series_list())
    videos: dict[str:dict] = parse_json_to_videos(user_responses)

    # 筛选 videos 有而 videos_old 没有的键，并返回对应值
    new_videos = {key: videos[key] for key in videos.keys() - videos_old}
    videos = new_videos

    print(f"准备处理 {len(videos)} 个视频")

    # 获取字幕
    video_list = list(videos.values())
    if not video_list:  # 列表为空
        return

    video_urls = [video["link"] for video in videos.values()]
    from tqdm import tqdm

    async def get_subtitle_(video_urls: list) -> dict[str:str]:
        import video_to_text_old as experiments

        subtitle_text_dict: dict[str:str] = {}
        for url in tqdm(video_urls):
            # 使用自定义的函数
            subtitle_text = await experiments.get_bilibili_video_subtitle(
                url, headless=HEADLESS
            )
            subtitle_text_dict[url] = subtitle_text
        return subtitle_text_dict

    subtitle_text_dict: dict[str:str] = asyncio.run(get_subtitle_(video_urls))
    for video in videos.values():
        video["subtitle"] = subtitle_text_dict.get(video["link"], "")
        # 保存到指定的markdown文件
        markdown_content, file_name = generate_full_md(video)
        if markdown_content:
            save_md_file(markdown_content, file_name)


def edit_ct():
    """
    编辑调整md文件的创建时间和发布时间。
    """
    # 获取新数据
    print("从API获取系列列表...")
    user_responses, got_urls = asyncio.run(get_series_list())
    videos: dict[str:dict] = parse_json_to_videos(user_responses)
    from t import modify_times_in_file

    for bvid, video in videos.items():
        file_path = os.path.join(OUTPUT_DIR, f"{bvid}.md")
        modify_times_in_file(
            file_path=file_path,
            save_path=file_path,
            new_published=video["pub_time"],  # 修改front matter中的published
            new_create_time=video["cre_time"],  # 修改创建时间
            new_publish_time=video["pub_time"],  # 修改文末的发布时间
        )


if __name__ == "__main__":
    main()
